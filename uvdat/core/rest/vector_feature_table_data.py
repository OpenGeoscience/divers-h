from collections import defaultdict
import logging

from django.contrib.gis.geos import Polygon
from django.db import connection
from django.http import HttpResponse
import numpy as np
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
import scipy.stats as stats

from uvdat.core.models import VectorFeature, VectorFeatureRowData, VectorFeatureTableData
from uvdat.core.rest.serializers import VectorFeatureTableDataSerializer

logger = logging.getLogger(__name__)
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

        type_columns_map = defaultdict(set)
        table_count_map = defaultdict(int)
        column_summaries = defaultdict(lambda: defaultdict(dict))

        # Iterate over tables to collect type-based column definitions and summary stats
        for table in tables:
            table_type = table.type
            table_summary = table.summary or {}

            # Ensure all tables of the same type have consistent columns
            if len(type_columns_map[table_type]) == 0:
                type_columns_map[table_type] = set(table.columns)
            for column in table.columns:
                type_columns_map[table_type].add(column)

            table_count_map[table_type] += 1

            # Aggregate summary statistics per column
            for column, stats_col in table_summary.items():
                if 'type' not in column_summaries[table_type][column]:
                    column_summaries[table_type][column]['type'] = stats_col.get('type')

                if stats_col.get('type') == 'number':
                    column_summaries[table_type][column]['min'] = min(
                        column_summaries[table_type][column].get('min', float('inf')),
                        stats_col.get('min', float('inf')),
                    )
                    column_summaries[table_type][column]['max'] = max(
                        column_summaries[table_type][column].get('max', float('-inf')),
                        stats_col.get('max', float('-inf')),
                    )
                    column_summaries[table_type][column]['value_count'] = column_summaries[
                        table_type
                    ][column].get('value_count', 0) + stats_col.get('value_count', 0)

                elif stats_col.get('type') == 'string':
                    existing_values = set(column_summaries[table_type][column].get('values', []))
                    new_values = set(stats_col.get('values', []))
                    column_summaries[table_type][column]['values'] = list(
                        existing_values.union(new_values)
                    )
                    column_summaries[table_type][column]['value_count'] = column_summaries[
                        table_type
                    ][column].get('value_count', 0) + stats_col.get('value_count', 0)

                if stats_col.get('description', None):
                    column_summaries[table_type][column]['description'] = stats_col.get(
                        'description', 'Unknown'
                    )
        # Construct the response
        output = {'vectorFeatureCount': feature_count, 'tables': {}}
        for table_type in type_columns_map:
            output['tables'][table_type] = {
                'type': table_type,
                'tableCount': table_count_map[table_type],
                'columns': list(type_columns_map[table_type]),
                'summary': column_summaries[table_type],
            }

        return Response(output, status=status.HTTP_200_OK)

    def get_graphs(
        self,
        table_type,
        vector_ids,
        x_axis,
        y_axis,
        indexer='vectorFeatureId',
        moving_avg_window=None,
        confidence_level=95,
        data_types=None,
        aggregate_all=False,
    ):
        if data_types is None:
            data_types = ['data', 'trendLine']  # Default to base data and trendline

        tables = VectorFeatureTableData.objects.filter(
            type=table_type, vector_feature__in=vector_ids
        )
        if not tables.exists():
            return {
                'error': f'No tables found for the given vector features {table_type} - {vector_ids}'
            }

        table_data = {'tableName': tables.first().name, 'graphs': {}}
        all_x_vals = {}
        all_x_list = []  # <<< Added
        all_y_list = []  # <<< Added

        for table in tables:
            if y_axis not in table.columns or x_axis not in table.columns:
                logger.warning(
                    f'Columns {x_axis} and {y_axis} not found in table {table.name} with id: {table.pk}'
                )
                continue

            x_axis_index = table.columns.index(x_axis)
            y_axis_index = table.columns.index(y_axis)
            vector_feature_id = table.vector_feature.pk
            index_val = table.vector_feature.properties.get(indexer, vector_feature_id)

            rows = VectorFeatureRowData.objects.filter(vector_feature_table=table)
            data = {}

            for row in rows:
                x_val = row.row_data[x_axis_index]
                y_val = row.row_data[y_axis_index]
                if y_val is None:
                    continue

                if x_val not in data:
                    data[x_val] = []
                data[x_val].append(y_val)

            if not data:
                continue

            sorted_x_vals = sorted(data.keys())
            x_vals = sorted_x_vals
            y_vals = [np.mean(data[x]) for x in sorted_x_vals]

            # Add x and y values to global list for min/max later
            all_x_list.extend(x_vals)
            all_y_list.extend(y_vals)

            for x, y in zip(x_vals, y_vals):
                if x not in all_x_vals:
                    all_x_vals[x] = []
                all_x_vals[x].append(y)
            moving_avg_val = None
            if moving_avg_window:
                moving_avg_val = int(moving_avg_window)

            result = {'indexer': index_val, 'vectorFeatureId': vector_feature_id}
            if aggregate_all:
                break
            if 'data' in data_types:
                y_output_vals = [data[x][0] for x in sorted_x_vals]
                result['data'] = list(zip(sorted_x_vals, y_output_vals))

            if 'trendLine' in data_types:
                slope, intercept, _, _, _ = stats.linregress(x_vals, y_vals)
                result['trendLine'] = [(x, slope * x + intercept) for x in x_vals]

            if 'confidenceInterval' in data_types:
                slope, intercept, _, _, _ = stats.linregress(x_vals, y_vals)
                confidence_val = int(confidence_level)
                alpha = 1 - (confidence_val / 100)
                z_score = stats.norm.ppf(1 - alpha / 2)
                y_pred = np.array([slope * x + intercept for x in x_vals])
                residuals = np.array(y_vals) - y_pred
                std_dev = np.std(residuals)
                result['confidenceIntervals'] = [
                    (x, y_pred[i] - z_score * std_dev, y_pred[i] + z_score * std_dev)
                    for i, x in enumerate(x_vals)
                ]

            if 'movingAverage' in data_types and moving_avg_val is not None and moving_avg_val > 1:
                moving_avg = np.convolve(
                    y_vals, np.ones(moving_avg_val) / moving_avg_val, mode='same'
                )
                moving_avg_x = x_vals[moving_avg_val - 1 :]
                result['movingAverage'] = list(zip(moving_avg_x, moving_avg))

            table_data['graphs'][vector_feature_id] = result

        if aggregate_all and all_x_vals:
            sorted_x_vals = sorted(all_x_vals.keys())
            avg_y_vals = [np.mean(all_x_vals[x]) for x in sorted_x_vals]
            aggregate_result = {'indexer': 'all', 'vectorFeatureId': 'all'}

            all_x_list.extend(sorted_x_vals)
            all_y_list.extend(avg_y_vals)

            if 'data' in data_types:
                aggregate_result['data'] = list(zip(sorted_x_vals, avg_y_vals))

            if 'trendLine' in data_types:
                slope, intercept, _, _, _ = stats.linregress(sorted_x_vals, avg_y_vals)
                aggregate_result['trendLine'] = [(x, slope * x + intercept) for x in sorted_x_vals]

            if 'confidenceInterval' in data_types:
                slope, intercept, _, _, _ = stats.linregress(sorted_x_vals, avg_y_vals)
                confidence_val = int(confidence_level)
                alpha = 1 - (confidence_val / 100)
                z_score = stats.norm.ppf(1 - alpha / 2)
                y_pred = np.array([slope * x + intercept for x in sorted_x_vals])
                residuals = np.array(avg_y_vals) - y_pred
                std_dev = np.std(residuals)
                aggregate_result['confidenceIntervals'] = [
                    (x, y_pred[i] - z_score * std_dev, y_pred[i] + z_score * std_dev)
                    for i, x in enumerate(sorted_x_vals)
                ]

            if 'movingAverage' in data_types and moving_avg_val is not None and moving_avg_val > 1:
                moving_avg = np.convolve(
                    avg_y_vals, np.ones(moving_avg_val) / moving_avg_val, mode='valid'
                )
                moving_avg_x = sorted_x_vals[moving_avg_val - 1 :]
                aggregate_result['movingAverage'] = list(zip(moving_avg_x, moving_avg))

            table_data['graphs'][-1] = aggregate_result

        if all_x_list and all_y_list:
            table_data['xAxisRange'] = [min(all_x_list), max(all_x_list)]
            table_data['yAxisRange'] = [min(all_y_list), max(all_y_list)]

        return table_data

    @action(detail=False, methods=['get'], url_path='feature-graph')
    def feature_graph(self, request, *args, **kwargs):
        table_type = request.query_params.get('tableType')  # array of Ids
        vector_feature = request.query_params.get('vectorFeatureId')
        x_axis = request.query_params.get('xAxis', 'index')
        y_axis = request.query_params.get('yAxis', '00060')
        indexer = request.query_params.get('indexer', 'vectorFeatureId')
        moving_average_window = request.query_params.get('movingAverage', None)
        confidence_interval = request.query_params.get('confidenceLevel', 95)
        display = request.query_params.getlist('display', ['data'])
        if not table_type:
            return Response({'error': 'tableType is required'}, status=status.HTTP_400_BAD_REQUEST)

        graphs = self.get_graphs(
            table_type,
            [vector_feature],
            x_axis,
            y_axis,
            indexer,
            moving_average_window,
            confidence_interval,
            display,
        )
        return Response(graphs, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='feature-graphs')
    def feature_graphs(self, request, *args, **kwargs):
        table_types = request.query_params.getlist('tableType')  # List of table types
        vector_feature = request.query_params.get('vectorFeatureId')
        x_axes = request.query_params.getlist('xAxis') or ['index']
        y_axes = request.query_params.getlist('yAxis') or ['00060']
        indexers = request.query_params.getlist('indexer') or ['vectorFeatureId']
        moving_average_window = request.query_params.get('movingAverage', None)
        confidence_interval = request.query_params.get('confidenceLevel', 95)
        display = request.query_params.getlist('display', ['data'])

        if not table_types:
            return Response({'error': 'tableType is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Pad indexers if not all provided
        while len(indexers) < len(table_types):
            indexers.append('vectorFeatureId')

        result = []

        for i, (table_type, x_axis, y_axis, indexer) in enumerate(zip(table_types, x_axes, y_axes, indexers)):
            graphs = self.get_graphs(
                table_type=table_type,
                vector_ids=[vector_feature],
                x_axis=x_axis,
                y_axis=y_axis,
                indexer=indexer,
                moving_avg_window=moving_average_window,
                confidence_level=confidence_interval,
                data_types=display,
            )
            result.append({
                'tableType': table_type,
                'xAxis': x_axis,
                'yAxis': y_axis,
                'indexer': indexer,
                'graphs': graphs,
            })

        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='map-layer-feature-graph')
    def map_layer_feature_graph(self, request, *args, **kwargs):
        table_type = request.query_params.get('tableType')  # Required
        map_layer_id = request.query_params.get('mapLayerId')  # Required
        x_axis = request.query_params.get('xAxis', 'index')
        y_axis = request.query_params.get('yAxis', 'mean_va')
        indexer = request.query_params.get('indexer', 'vectorFeatureId')
        bbox = request.query_params.get('bbox', None)  # Optional: [min_x, min_y, max_x, max_y]
        moving_average_window = request.query_params.get('movingAverage', None)
        confidence_interval = request.query_params.get('confidenceLevel', 95)
        display = request.query_params.getlist('display', ['data'])
        aggregate_all = request.query_params.get('aggregateAll', False)

        if not bbox:
            return Response({'error': 'bbox parameter is required'}, status=400)

        try:
            xmin, ymin, xmax, ymax = map(float, bbox.split(','))
            bbox_polygon = Polygon.from_bbox((xmin, ymin, xmax, ymax))
        except ValueError:
            return Response(
                {'error': 'Invalid bbox format. Expected format: xmin,ymin,xmax,ymax'}, status=400
            )

        vector_features = VectorFeature.objects.filter(
            geometry__intersects=bbox_polygon, map_layer=map_layer_id
        ).values_list('id', flat=True)
        if not table_type:
            return Response({'error': 'tableType is required'}, status=status.HTTP_400_BAD_REQUEST)

        graphs = self.get_graphs(
            table_type,
            vector_features,
            x_axis,
            y_axis,
            indexer,
            moving_average_window,
            confidence_interval,
            display,
            aggregate_all == 'true',
        )
        return Response(graphs, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='generate-layer')
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
