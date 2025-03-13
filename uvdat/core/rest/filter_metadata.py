import logging

from django.contrib.gis.geos import GEOSGeometry
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from uvdat.core.models import NetCDFLayer, RasterMapLayer, VectorMapLayer

logger = logging.getLogger(__name__)


class MetadataFilterViewSet(viewsets.GenericViewSet):
    # Custom action to handle metadata filtering (GET request)
    @action(detail=False, methods=['get'])
    def get_filters(self, request, *args, **kwargs):
        models = [RasterMapLayer, VectorMapLayer, NetCDFLayer]

        filters = {}

        for model in models:
            layers = model.objects.all()

            for layer in layers:
                if layer.metadata is None:
                    continue
                metadata = layer.metadata.get('tags', {}).get('filters', {})
                for key, value in metadata.items():
                    if value is not None:
                        if key not in filters:
                            filters[key] = set()
                        filters[key].update(
                            value if (isinstance(value, list) and len(value)) else [value]
                        )

        # Convert sets to lists for JSON response
        filters = {key: list(value) for key, value in filters.items()}
        return Response(filters)

    # Custom action to handle filtering layers based on provided filters (POST request)
    @action(detail=False, methods=['post'])
    def filter_layers(self, request, *args, **kwargs):
        filters = request.data.get('filters', {})  # DRF will automatically parse the JSON body
        search_query = request.data.get('search', '').strip().lower()  # Search term
        bbox = request.data.get('bbox', None)  # Bounding box filter

        # Collecting all models
        models = [RasterMapLayer, VectorMapLayer, NetCDFLayer]
        matching_ids = []
        type_mapper = {
            'RasterMapLayer': 'raster',
            'VectorMapLayer': 'vector',
            'NetCDFLayer': 'netcdf',
        }
        for model in models:
            layers = model.objects.all()

            # Apply search filtering if provided
            if search_query:
                layers = layers.filter(Q(name__icontains=search_query))

            if bbox:
                xmin, ymin, xmax, ymax = map(float, bbox.split(','))
                bbox_geom = GEOSGeometry(
                    f'POLYGON(({xmin} {ymin}, {xmin} {ymax}, {xmax} {ymax}, {xmax} {ymin}, {xmin} {ymin}))'
                )
                layers = layers.filter(bounds__intersects=bbox_geom)

            for layer in layers:
                if layer.metadata is None:
                    continue

                metadata = layer.metadata.get('tags', {}).get('filters', {})

                matches = {}
                filter_length = sum(1 for values in filters.values() if values)
                match = 0
                # Check if all filter criteria match
                for key, values in filters.items():
                    if key in metadata and metadata[key] is not None:
                        for value in values:
                            if value in metadata[key]:
                                match += 1
                                matches[key] = value

                if match == filter_length:
                    matching_ids.append(
                        {
                            'id': layer.id,
                            'name': layer.name,
                            'type': type_mapper[model.__name__],
                            'matches': matches,
                        }
                    )
        return Response(matching_ids)
