from collections import defaultdict

from django.db import connection
from django.http import HttpResponse
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from uvdat.core.models import VectorFeature, VectorFeatureRowData, VectorFeatureTableData
from uvdat.core.rest.serializers import VectorFeatureTableDataSerializer

# TODO THIS IS INCOMPLETE
VECTOR_TILE_DYNAMIC_SQL = """
    WITH tile_bounds AS (
        SELECT ST_Transform(ST_TileEnvelope(%(z)s, %(x)s, %(y)s), 4326) AS te
    ),
    tilenvbounds AS (
        SELECT
            ST_XMin(te) as xmin,
            ST_YMin(te) as ymin,
            ST_XMax(te) as xmax,
            ST_YMax(te) as ymax,
            (ST_XMax(te) - ST_XMin(te)) / 4 as segsize
        FROM tile_bounds
    ),
    env AS (
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
    bounds AS (
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
            vf.properties,
            vfrd.row_data
        FROM core_vectorfeature vf
        LEFT JOIN core_vectorfeaturerowdata vfrd ON vf.vector_feature_id = vfrd.vector_feature_table_id
        WHERE ST_Intersects(vf.geometry, (SELECT geom from bounds))
        AND vf.map_layer_id = %(map_layer_id)s
        {% if sliding_value %}
            AND vfrd.row_data->>%(sliding_value)s IS NOT NULL
        {% endif %}
    )
    SELECT
        ST_AsMVT(vector_features.*) AS mvt
    FROM vector_features;
"""


class VectorFeatureTableDataViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, mixins.CreateModelMixin
):
    queryset = VectorFeatureTableData.objects.all()
    serializer_class = VectorFeatureTableDataSerializer

    @action(detail=False, methods=['get'], url_path='table-summary')
    def table_summary(self, request, *args, **kwargs):
        layer_id = request.query_params.get('layerId')
        if not layer_id:
            return Response({'error': 'layerId is required'}, status=status.HTTP_400_BAD_REQUEST)

        tables = VectorFeatureTableData.objects.filter(map_layer=layer_id)
        feature_count = VectorFeature.objects.filter(map_layer=layer_id).count()
        # Create a defaultdict to store types and their corresponding columns
        type_columns_map = defaultdict(set)
        table_count_map = defaultdict(int)

        # Iterate over the tables and collect the types and columns
        for table in tables:
            if len(type_columns_map[table.type]) == 0:
                type_columns_map[table.type] = set(table.columns)
            elif type_columns_map[table.type] != set(table.columns):
                raise ValidationError(
                    f"Table Columns don't match for all tables: {type_columns_map[table.type]} vs { set(table.columns)}"
                )
            table_count_map[table.type] += 1

        # Convert the defaultdict to a normal dict (optional)
        type_columns_map = dict(type_columns_map)
        output = {'vectorFeatureCount': feature_count, 'tables': {}}
        for key in type_columns_map:
            output['tables'][key] = {
                'tableCount': table_count_map[key],
                'columns': type_columns_map[key],
            }

        return Response(output, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='feature-graph')
    def feature_graph(self, request, *args, **kwargs):
        table_type = request.query_params.get('tableType')  # array of Ids
        vector_feature = request.query_params.get('vectorFeatureId')
        x_axis = request.query_params.get('xAxis', 'index')
        y_axis = request.query_params.get('yAxis', 'mean_va')
        filter_param = request.query_params.get('filter', 'parameter_cd')
        filter_vals = request.query_params.getlist(
            'filterVals', ['00060', '00065']
        )  # ['00060', '00065']

        if not table_type:
            return Response({'error': 'tableType is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            table = VectorFeatureTableData.objects.get(
                type=table_type, vector_feature=vector_feature
            )
            table_data = {'table_name': table.name, 'tables': []}
            x_axis_index = table.columns.index(x_axis)
            y_axis_index = table.columns.index(y_axis)
            if filter_param and len(filter_vals):
                filter_param_index = table.columns.index(filter_param)
            if filter_param and len(filter_vals):
                table_data['data'] = {}
                for filter_val in filter_vals:
                    table_data['data'][filter_val] = {
                        'x_data': [],
                        'y_data': [],
                        'filterVal': filter_val,
                    }
            else:
                table_data['data'] = {'default': {'x_data': [], 'y_data': []}}
            rows = VectorFeatureRowData.objects.filter(vector_feature_table=table)
            for row in rows:
                row_data = row.row_data
                filter_row = row_data[filter_param_index]
                x_val = row_data[x_axis_index]
                y_val = row_data[y_axis_index]
                if filter_param and len(filter_vals):
                    for filter_val in filter_vals:
                        if filter_row == filter_val:
                            table_data['data'][filter_val]['x_data'].append(x_val)
                            table_data['data'][filter_val]['y_data'].append(y_val)
                else:
                    table_data['data']['default']['x_data'].append(x_val)
                    table_data['data']['default']['y_data'].append(y_val)
            print(table_data)
            return Response(table_data, status=status.HTTP_200_OK)
        except VectorFeatureTableData.DoesNotExist:
            return Response({'error': 'Table not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='generate-layer')
    @permission_classes([IsAuthenticated])
    def generate_layer(self, request, *args, **kwargs):
        table_id = request.data.get('table_id')
        filter_value = request.data.get('filter_value')
        if not table_id or not filter_value:
            return Response(
                {'error': 'table_id and filter_value are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Layer generation logic would go here...
        return Response({'message': 'Layer generated successfully'}, status=status.HTTP_201_CREATED)


@action(detail=False, methods=['get'], url_path='vector-tile-tab')
def get_vector_tile_tab(self, request, x: str, y: str, z: str, pk: str):
    table_id = request.query_params.get('table_id')
    sliding_value = request.query_params.get(
        'sliding_value'
    )  # Column name to split vector features by

    if not table_id or not sliding_value:
        return Response(
            {'error': 'table_id and sliding_value are required'}, status=status.HTTP_400_BAD_REQUEST
        )

    with connection.cursor() as cursor:
        cursor.execute(
            VECTOR_TILE_DYNAMIC_SQL,
            {
                'z': z,
                'x': x,
                'y': y,
                'map_layer_id': pk,
                'sliding_value': sliding_value,  # Add the sliding_value to SQL execution parameters
            },
        )
        row = cursor.fetchone()

    tile = row[0]
    return HttpResponse(
        tile,
        content_type='application/octet-stream',
        status=200 if tile else 204,
    )
