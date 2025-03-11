import json
import logging

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db.models import Extent
from django.contrib.gis.geos import GEOSGeometry
from django.db import connection
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django_large_image.rest import LargeImageFileDetailMixin
import numpy as np
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from uvdat.core.models import (
    LayerRepresentation,
    NetCDFData,
    NetCDFLayer,
    RasterMapLayer,
    VectorFeature,
    VectorMapLayer,
)
from uvdat.core.rest.serializers import (
    NetCDFLayerSerializer,
    RasterMapLayerSerializer,
    VectorMapLayerDetailSerializer,
    VectorMapLayerSerializer,
)

from .permissions import DefaultPermission

logger = logging.getLogger(__name__)

VECTOR_TILE_SQL = """
 WITH tile_bounds AS (
    SELECT ST_Transform(ST_TileEnvelope(%(z)s, %(x)s, %(y)s), 4326) AS te
),
tilenvbounds as (
    SELECT
        ST_XMin(te) as xmin,
        ST_YMin(te) as ymin,
        ST_XMax(te) as xmax,
        ST_YMax(te) as ymax,
        (ST_XMax(te) - ST_XMin(te)) / 4 as segsize
    FROM tile_bounds
),
env as (
    SELECT ST_Segmentize(
        ST_MakeEnvelope(
            xmin,
            ymin,
            xmax,
            ymax,
            4326
        ),
        segsize
    ) as seg
    FROM tilenvbounds
),
bounds as (
    SELECT
        seg as geom,
        seg::box2d as b2d
    FROM env
),
vector_features AS (
    SELECT
        ST_AsMVTGeom(
            ST_Transform(geometry, 3857),
            ST_Transform((SELECT geom from bounds), 3857)
        ) as geom,
        map_layer_id,
        Id as vectorfeatureid,
        properties
    FROM core_vectorfeature
    WHERE ST_Intersects(geometry, (SELECT geom from bounds))
    AND core_vectorfeature.map_layer_id = %(map_layer_id)s
)
SELECT ST_AsMVT(vector_features.*) AS mvt FROM vector_features
;
"""


class RasterMapLayerViewSet(ModelViewSet, LargeImageFileDetailMixin):
    queryset = RasterMapLayer.objects.select_related('dataset').all()
    serializer_class = RasterMapLayerSerializer
    FILE_FIELD_NAME = 'cloud_optimized_geotiff'
    permission_classes = [DefaultPermission]

    @action(
        detail=True,
        methods=['get'],
        url_path=r'raster-data/(?P<resolution>[\d*\.?\d*]+)',
        url_name='raster_data',
    )
    def get_raster_data(self, request, resolution: str = '1', **kwargs):
        raster_map_layer = self.get_object()
        data = raster_map_layer.get_image_data(float(resolution))
        return HttpResponse(json.dumps(data), status=200)

    @action(
        detail=True,
        methods=['get'],
        url_path='bbox',
        url_name='bbox',
    )
    def get_raster_bbox(self, request, **kwargs):
        raster_map_layer = self.get_object()

        if raster_map_layer.bounds:
            bounds = raster_map_layer.bounds.extent
            bbox_dict = {'xmin': bounds[0], 'ymin': bounds[1], 'xmax': bounds[2], 'ymax': bounds[3]}
            return JsonResponse(bbox_dict)

        data = raster_map_layer.get_bbox()
        return JsonResponse(data, status=200, safe=False)

    @action(
        detail=True,
        methods=['get'],
        url_path='raster-statistics',
        url_name='raster_statistics',
    )
    def raster_statistics(self, request, pk=None):
        left = request.query_params.get('left', None)
        top = request.query_params.get('top', None)
        right = request.query_params.get('right', None)
        bottom = request.query_params.get('bottom', None)
        source = self.get_tile_source(request, pk, style=False)
        kwargs = dict(
            bins=int(self.get_query_param(request, 'bins', 256)),
        )
        if all(var is not None for var in [left, right, top, bottom]):
            kwargs['region'] = {
                'left': int(left),
                'right': int(right),
                'top': int(top),
                'bottom': int(bottom),
            }
        result = source.histogram(**kwargs)
        if 'histogram' in result:
            result = result['histogram']
            for entry in result:
                for key in {'bin_edges', 'hist', 'range'}:
                    if key in entry:
                        entry[key] = [float(val) for val in list(entry[key])]
                for key in {'min', 'max', 'samples'}:
                    if key in entry:
                        entry[key] = float(entry[key])
        return Response(result)


class VectorMapLayerViewSet(ModelViewSet):
    queryset = VectorMapLayer.objects.select_related('dataset').all()
    serializer_class = VectorMapLayerSerializer
    permission_classes = [DefaultPermission]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = VectorMapLayerDetailSerializer(instance)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['get'],
        url_path=r'tiles/(?P<z>\d+)/(?P<x>\d+)/(?P<y>\d+)',
        url_name='tiles',
    )
    def get_vector_tile(self, request, x: str, y: str, z: str, pk: str):
        with connection.cursor() as cursor:
            cursor.execute(
                VECTOR_TILE_SQL,
                {
                    'z': z,
                    'x': x,
                    'y': y,
                    'map_layer_id': pk,
                },
            )
            row = cursor.fetchone()

        tile = row[0]
        return HttpResponse(
            tile,
            content_type='application/octet-stream',
            status=200 if tile else 204,
        )

    # TODO: For large map layers this could take long and may be better in a task
    @action(
        detail=True,
        methods=['get'],
        url_path='property-summary',
        url_name='property-summary',
    )
    def property_summary(self, request, pk=None):
        limit = int(request.query_params.get('limit', 100))  # Default limit of 100

        # Get all VectorFeature properties for the specific map layer
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT properties
                FROM core_vectorfeature
                WHERE map_layer_id = %s;
            """,
                [pk],
            )
            features = cursor.fetchall()

        # Analyze properties
        property_summary = {}
        for feature in features:
            properties = feature[0]

            # Check if properties is a string, and parse it if necessary
            if isinstance(properties, str):
                try:
                    properties = json.loads(properties)
                except json.JSONDecodeError:
                    continue  # Skip if it cannot be parsed as JSON

            for key, value in properties.items():
                if key not in property_summary:
                    property_summary[key] = {'type': None, 'values': set(), 'value_count': 0}

                if isinstance(value, bool):
                    property_summary[key]['type'] = 'bool'
                    property_summary[key]['value_count'] += 1
                elif isinstance(value, (int, float)):
                    property_summary[key]['type'] = 'number'
                    property_summary[key]['value_count'] += 1
                    if 'min' not in property_summary[key] or value < property_summary[key]['min']:
                        property_summary[key]['min'] = value
                    if 'max' not in property_summary[key] or value > property_summary[key]['max']:
                        property_summary[key]['max'] = value
                elif isinstance(value, str):
                    if 'values' not in property_summary[key]:
                        property_summary[key]['values'] = set()
                    property_summary[key]['value_count'] += 1
                    property_summary[key]['type'] = 'string'
                    property_summary[key]['values'].add(value)

        # Finalize property summary
        final_output = {}
        for key, summary in property_summary.items():
            if summary['type'] is None:
                continue
            if summary['type'] == 'number':
                if summary['value_count'] == 1:
                    summary['values'] = summary.get('min', summary.get('max'))
                    del summary['min']
                    del summary['max']
                elif summary['min'] == summary['max']:
                    val = summary['min']
                    del summary['values']
                    del summary['min']
                    del summary['max']
                    summary['static'] = True
                    summary['value'] = val
                else:
                    del summary['values']
            elif (
                summary['type'] == 'string'
                and 'values' in summary
                and not summary.get('searchable')
            ):
                summary['values'] = sorted(summary['values'])
                if len(summary['values']) >= limit:
                    summary['searchable'] = True
                    summary['unique'] = len(summary['values'])
                    del summary['values']
            elif summary['type'] == 'bool':
                del summary['values']
            final_output[key] = summary
        return JsonResponse(final_output, safe=False)

    @action(
        detail=True,
        methods=['get'],
        url_path='bbox',
        url_name='bbox',
    )
    def get_vector_bbox(self, request, pk=None):
        map_layer = VectorMapLayer.objects.filter(pk=pk).first()
        if not map_layer:
            return JsonResponse({'error': 'Map layer not found.'}, status=404)

        if map_layer.bounds:
            bounds = map_layer.bounds.extent
            bbox_dict = {'xmin': bounds[0], 'ymin': bounds[1], 'xmax': bounds[2], 'ymax': bounds[3]}
            return JsonResponse(bbox_dict)
        try:
            bbox = VectorFeature.objects.filter(map_layer_id=pk).aggregate(Extent('geometry'))[
                'geometry__extent'
            ]

            if not bbox:
                return JsonResponse(
                    {'error': 'No bounding box found for this vector map layer.'}, status=404
                )

            bbox_dict = {'xmin': bbox[0], 'ymin': bbox[1], 'xmax': bbox[2], 'ymax': bbox[3]}
            return JsonResponse(bbox_dict)

        except Exception as e:
            logger.error(f'Error fetching bounding box for VectorMapLayer {pk}: {e}')
            return JsonResponse(
                {'error': 'An error occurred while fetching the bounding box.'}, status=500
            )

    @action(
        detail=True,
        methods=['get'],
        url_path='property-statistics',
        url_name='property_statistics',
    )
    def property_statistics(self, request, pk=None):
        # Get the 'property_keys' from query parameters (comma-separated)
        property_keys = request.query_params.get('property_keys')
        if not property_keys:
            return Response(
                {'error': 'property_keys parameter is required'}, status=status.HTTP_400_BAD_REQUEST
            )

        # Split property keys into a list
        property_keys = property_keys.split(',')

        # Get the 'bins' parameter for histogram calculation, default to 10 bins
        bins = int(request.query_params.get('bins', 10))

        # Check for optional bounding box (xmin, ymin, xmax, ymax)
        bbox = request.query_params.get('bbox')
        if bbox:
            try:
                xmin, ymin, xmax, ymax = map(float, bbox.split(','))
                bbox_condition = True
            except ValueError:
                return Response(
                    {'error': 'Invalid bbox parameter. Must be in format xmin,ymin,xmax,ymax'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            bbox_condition = False

        # Query the database for property values
        property_statements = ', '.join([f'properties ->> %s as "{key}"' for key in property_keys])
        sql_query = f"""
            SELECT {property_statements}, ST_AsText(geometry)
            FROM core_vectorfeature
            WHERE map_layer_id = %s
        """

        query_params = property_keys + [pk]

        if bbox_condition:
            sql_query += """
                AND ST_Intersects(
                    geometry,
                    ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                )
            """
            query_params.extend([xmin, ymin, xmax, ymax])

        with connection.cursor() as cursor:
            cursor.execute(sql_query, query_params)
            rows = cursor.fetchall()

        if not rows:
            return JsonResponse(
                {
                    'error': 'No values found for the specified property keys or within the bounding box'
                },
                status=404,
            )

        # Initialize result dictionary for each property key
        result = {key: {'type': None, 'values': [], 'numerical_stats': {}} for key in property_keys}

        # Process the results
        for row in rows:
            for idx, key in enumerate(property_keys):
                value = row[idx]
                # Attempt to treat value as a float to check if it's numerical
                if value is None:
                    continue
                try:
                    numerical_value = float(value)
                    result[key]['values'].append(numerical_value)
                    result[key]['type'] = 'number'
                except (ValueError, TypeError):
                    # Handle string values
                    result[key]['values'].append(value)
                    if result[key]['type'] is None:
                        result[key]['type'] = 'string'

        # Generate statistics for each property key
        final_result = {}
        for key, data in result.items():
            if data['type'] == 'number':
                # Handle numerical data
                numerical_values = np.array(data['values'])

                min = np.min(numerical_values)
                max = np.max(numerical_values)
                mean = np.mean(numerical_values)
                median = np.median(numerical_values)
                std_dev = np.std(numerical_values)

                # Create a histogram with the specified number of bins
                hist, bin_edges = np.histogram(numerical_values, bins=bins)

                final_result[key] = {
                    'type': 'number',
                    'mean': mean,
                    'min': min,
                    'max': max,
                    'median': median,
                    'std_dev': std_dev,
                    'histogram': {
                        'bins': bins,
                        'bin_edges': bin_edges.tolist(),
                        'counts': hist.tolist(),
                    },
                }
            elif data['type'] == 'string':
                # Handle string data
                value_counts = {}
                for value in data['values']:
                    if value in value_counts:
                        value_counts[value] += 1
                    else:
                        value_counts[value] = 1

                final_result[key] = {
                    'type': 'string',
                    'unique_values': len(value_counts),
                    'values': [
                        {'value': key, 'count': count} for key, count in value_counts.items()
                    ],
                }

        return JsonResponse(final_result, safe=False)


class MapLayerViewSet(GenericViewSet):
    # This function is used to get the map-layers associated with a specific collection
    def create(self, request, *args, **kwargs):
        layers_data = request.data.get('layers')
        enabled_param = request.query_params.get('enabled', '').lower() == 'true'
        if not layers_data:
            return Response([], status=status.HTTP_200_OK)

        # Prepare the response data
        response_data = []

        for layer_info in layers_data:
            layer_id = layer_info.get('layerId')
            layer_representation_id = layer_info.get('defaultLayerRepresentationId')

            # Try to find the layer (raster or vector)
            map_layer = None
            raster_layer = RasterMapLayer.objects.filter(id=layer_id).first()
            vector_layer = VectorMapLayer.objects.filter(id=layer_id).first()
            netcdf_layer = NetCDFLayer.objects.filter(id=layer_id).first()
            map_layer = raster_layer or vector_layer or netcdf_layer

            if map_layer is None:
                continue  # Skip if no layer is found for the provided ID

            # Determine which serializer to use based on layer type
            if isinstance(map_layer, RasterMapLayer):
                serializer = RasterMapLayerSerializer(map_layer)
            elif isinstance(map_layer, VectorMapLayer):  # It must be a VectorMapLayer
                serializer = VectorMapLayerSerializer(map_layer)
            elif isinstance(map_layer, NetCDFLayer):
                serializer = NetCDFLayerSerializer(map_layer)
            # Get the serialized data
            layer_response = serializer.data
            if raster_layer:
                layer_response['type'] = 'raster'
            elif vector_layer:
                layer_response['type'] = 'vector'
            elif netcdf_layer:
                layer_response['type'] = 'netcdf'

            # Check for LayerRepresentation if provided
            if layer_representation_id is not None:
                if enabled_param:
                    layer_representation = LayerRepresentation.objects.filter(
                        id=layer_representation_id, enabled=enabled_param
                    )
                else:
                    layer_representation = LayerRepresentation.objects.filter(
                        id=layer_representation_id
                    )
                if layer_representation.exists():
                    layer_rep_obj = layer_representation.first()
                    if layer_rep_obj and layer_rep_obj.map_layer == map_layer:
                        # Override name and default_style with LayerRepresentation
                        layer_response['default_style'] = (
                            layer_rep_obj.default_style or layer_response.get('default_style')
                        )
                        layer_response['layerRepresentationId'] = layer_representation_id

            # Add the layer to the response
            response_data.append(layer_response)

        # Return the combined data
        return Response(response_data, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        map_layer_ids = request.query_params.getlist('mapLayerIds', [])
        map_layer_types = request.query_params.getlist('mapLayerTypes', [])

        if not map_layer_ids:
            return Response([], status=status.HTTP_200_OK)

        response_data = []

        # Query for layers based on ID and type
        for index in range(len(map_layer_ids)):
            layer_id = map_layer_ids[index]
            layer_type = map_layer_types[index]
            map_layer = None
            serializer = None
            if 'raster' == layer_type:
                map_layer = RasterMapLayer.objects.filter(id=layer_id).first()
                serializer_class = RasterMapLayerSerializer
            if not map_layer and 'vector' == layer_type:
                map_layer = VectorMapLayer.objects.filter(id=layer_id).first()
                serializer_class = VectorMapLayerSerializer
            if not map_layer and 'netcdf' == layer_type:
                map_layer = NetCDFLayer.objects.filter(id=layer_id).first()
                serializer_class = NetCDFLayerSerializer

            if not map_layer:
                continue  # Skip if no matching layer is found

            # Serialize layer data
            serializer = serializer_class(map_layer)
            layer_response = serializer.data
            layer_response['type'] = (
                'raster'
                if isinstance(map_layer, RasterMapLayer)
                else ('vector' if isinstance(map_layer, VectorMapLayer) else 'netcdf')
            )

            # Check for LayerRepresentation if provided
            layer_representation = None
            if layer_type == 'raster' or layer_type == 'vector':
                layer_representation = LayerRepresentation.objects.filter(
                    object_id=map_layer.id, map_type=ContentType.objects.get_for_model(map_layer)
                )

            if layer_representation and layer_representation.exists():
                layer_rep_obj = layer_representation.first()
                layer_response['default_style'] = layer_rep_obj.default_style or layer_response.get(
                    'default_style'
                )
                layer_response['layerRepresentationId'] = layer_rep_obj.id

            response_data.append(layer_response)

        return Response(response_data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['get'],
        url_path='bbox',
        url_name='bbox',
    )
    def map_layer_bbox(self, request, *args, **kwargs):
        # Get the lists of map layer IDs from the query parameters
        raster_map_layer_ids = request.query_params.getlist('rasterMapLayerIds')
        vector_map_layer_ids = request.query_params.getlist('vectorMapLayerIds')
        netcdf_map_layer_ids = request.query_params.getlist('netCDFMapLayerIds')

        # Initialize variables to track the overall bounding box
        overall_bbox = {
            'xmin': float('inf'),
            'ymin': float('inf'),
            'xmax': float('-inf'),
            'ymax': float('-inf'),
        }

        # Calculate bbox for raster map layers
        if raster_map_layer_ids:
            for raster_layer_id in raster_map_layer_ids:
                raster_layer = RasterMapLayer.objects.filter(id=raster_layer_id).first()
                if raster_layer:
                    # Get the bounding box for the current raster layer
                    raster_bbox = raster_layer.get_bbox()
                    if raster_bbox:
                        # Update the overall bounding box
                        overall_bbox['xmin'] = min(overall_bbox['xmin'], raster_bbox['xmin'])
                        overall_bbox['ymin'] = min(overall_bbox['ymin'], raster_bbox['ymin'])
                        overall_bbox['xmax'] = max(overall_bbox['xmax'], raster_bbox['xmax'])
                        overall_bbox['ymax'] = max(overall_bbox['ymax'], raster_bbox['ymax'])
        # Calculate bbox for vector map layers
        if vector_map_layer_ids:
            vector_bboxes = VectorFeature.objects.filter(
                map_layer_id__in=vector_map_layer_ids
            ).aggregate(extent=Extent('geometry'))['extent']

            if vector_bboxes:
                overall_bbox['xmin'] = min(overall_bbox['xmin'], vector_bboxes[0])
                overall_bbox['ymin'] = min(overall_bbox['ymin'], vector_bboxes[1])
                overall_bbox['xmax'] = max(overall_bbox['xmax'], vector_bboxes[2])
                overall_bbox['ymax'] = max(overall_bbox['ymax'], vector_bboxes[3])

        if netcdf_map_layer_ids:
            netcdf_bbox = NetCDFLayer.objects.filter(pk__in=netcdf_map_layer_ids).aggregate(
                extent=Extent('bounds')
            )['extent']

            if vector_bboxes:
                overall_bbox['xmin'] = min(overall_bbox['xmin'], netcdf_bbox[0])
                overall_bbox['ymin'] = min(overall_bbox['ymin'], netcdf_bbox[1])
                overall_bbox['xmax'] = max(overall_bbox['xmax'], netcdf_bbox[2])
                overall_bbox['ymax'] = max(overall_bbox['ymax'], netcdf_bbox[3])
        # Check if the bbox values were updated; if not, return an error message
        if overall_bbox['xmin'] == float('inf'):
            return JsonResponse(
                {'error': 'No valid bounding boxes found for the provided map layers.'}, status=404
            )

        # Return the overall bounding box
        return JsonResponse(overall_bbox)

    @action(
        detail=False,
        methods=['patch'],
        url_path='update-name',
        url_name='update_name',
    )
    def update_name(self, request, *args, **kwargs):
        layer_id = request.data.get('id')
        layer_type = request.data.get('type')
        new_name = request.data.get('name')

        if not layer_id or not layer_type or not new_name:
            return Response(
                {'error': 'id, type, and name fields are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Fetch the appropriate layer based on type
            if layer_type == 'vector':
                VectorMapLayer.objects.filter(id=layer_id).update(name=new_name)
            elif layer_type == 'raster':
                RasterMapLayer.objects.filter(id=layer_id).update(name=new_name)
            elif layer_type == 'netcdf':
                NetCDFData.objects.filter(id=layer_id).update(name=new_name)
            else:
                return Response(
                    {'error': 'Invalid layer type. Must be "vector" or "raster".'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {'success': f'{layer_type.capitalize()}MapLayer name updated successfully.'},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f'Error updating name for {layer_type} map layer {layer_id}: {e}')
            return Response(
                {'error': 'An error occurred while updating the name.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=False,
        methods=['post'],
        url_path='search-features',
        url_name='search_features',
    )
    def search_vector_features(self, request, *args, **kwargs):
        data = request.data
        map_layer_id = data.get('mapLayerId')
        main_text_search_fields = [
            field.get('value')
            for field in data.get('mainTextSearchFields', [])
            if isinstance(field, dict)
        ]
        search_query = data.get('search', '').strip()
        filters = data.get('filters', {})
        bbox = data.get('bbox', None)
        sort_key = data.get('sortKey', None)
        title_key = data.get('titleKey', '')
        subtitle_keys = [item.get('key') for item in data.get('subtitleKeys', [])]
        detail_keys = [item.get('key') for item in data.get('detailStrings', [])]

        if not map_layer_id or not title_key:
            return Response(
                {'error': 'mapLayerId and titleKey are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = VectorFeature.objects.filter(map_layer_id=map_layer_id)

        # Apply text search
        if search_query and main_text_search_fields:
            search_conditions = Q()
            for field in main_text_search_fields:
                search_conditions |= Q(**{f'properties__{field}__icontains': search_query})
            queryset = queryset.filter(search_conditions)

        # Apply filters
        for key, filter_data in filters.items():
            filter_type = filter_data.get('type')
            value = filter_data.get('value')

            if filter_type == 'bool':
                queryset = queryset.filter(**{f'properties__{key}': bool(value)})
            elif filter_type == 'number':
                if isinstance(value, list) and len(value) == 2:  # Range filter
                    queryset = queryset.filter(
                        **{f'properties__{key}__gte': value[0], f'properties__{key}__lte': value[1]}
                    )
                else:
                    queryset = queryset.filter(**{f'properties__{key}': value})
            elif filter_type == 'string':
                queryset = queryset.filter(**{f'properties__{key}__icontains': value})

        # Apply bounding box filter
        if bbox:
            try:
                min_x, min_y, max_x, max_y = map(float, bbox.split(','))
                bbox_geom = GEOSGeometry(
                    f'POLYGON(({min_x} {min_y}, {min_x} {max_y}, {max_x} {max_y}, {max_x} {min_y}, {min_x} {min_y}))'
                )
                queryset = queryset.filter(geometry__intersects=bbox_geom)
            except ValueError:
                return Response(
                    {'error': 'Invalid BBOX format'}, status=status.HTTP_400_BAD_REQUEST
                )

        # Apply sorting
        if sort_key:
            queryset = queryset.order_by(f'properties__{sort_key}')

        # Serialize response
        response_data = [
            {
                'id': feature.id,
                'title': feature.properties.get(title_key, ''),
                'subtitles': [
                    {'key': key, 'value': feature.properties.get(key, '')} for key in subtitle_keys
                ],
                'details': [
                    {'key': key, 'value': feature.properties.get(key, '')} for key in detail_keys
                ],
                'center': (
                    {
                        'lat': feature.geometry.centroid.y,
                        'lon': feature.geometry.centroid.x,
                    }
                    if feature.geometry
                    else None
                ),
            }
            for feature in queryset
        ]

        return Response(response_data, status=status.HTTP_200_OK)
