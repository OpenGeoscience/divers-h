from django.core.files.storage import default_storage
from django.db import connection
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from uvdat.core.models import FMVLayer
from uvdat.core.rest.serializers import FMVLayerSerializer

FMV_TILE_SQL = """
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
        id as vectorfeatureid,
        properties
    FROM core_fmvvectorfeature
    WHERE ST_Intersects(geometry, (SELECT geom from bounds))
    AND map_layer_id = %(map_layer_id)s
)
SELECT ST_AsMVT(vector_features.*) AS mvt FROM vector_features;
"""


class FMVLayerViewSet(ModelViewSet):
    queryset = FMVLayer.objects.select_related('dataset').all()
    serializer_class = FMVLayerSerializer

    def retrieve(self, request, pk=None):
        try:
            layer = FMVLayer.objects.get(pk=pk)
        except FMVLayer.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)

        presigned_url = None
        if layer.fmv_video and hasattr(layer.fmv_video, 'name'):
            presigned_url = default_storage.url(layer.fmv_video.name)

        # Get bbox as [xmin, ymin, xmax, ymax]
        bbox = list(layer.bounds.extent) if layer.bounds else None

        data = {
            'name': layer.name,
            'fmvVideoUrl': presigned_url,
            'fmvFps': layer.fmv_fps,
            'fmvFrameCount': layer.fmv_frame_count,
            'fmvFrameWidth': layer.fmv_video_width,
            'fmvFrameHeight': layer.fmv_video_height,
            'bbox': bbox,
            'frameIdToBBox': layer.get_ground_frame_mapping(),
        }
        return Response(data)

    @action(
        detail=True,
        methods=['get'],
        url_path=r'tiles/(?P<z>\d+)/(?P<x>\d+)/(?P<y>\d+)',
        url_name='fmv_tiles',
    )
    def get_vector_tile(self, request, pk=None, x=None, y=None, z=None):
        with connection.cursor() as cursor:
            cursor.execute(
                FMV_TILE_SQL,
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

    @action(
        detail=True,
        methods=['get'],
        url_path='bbox',
        url_name='bbox',
    )
    def get_fmv_bbox(self, request, **kwargs):
        fmv_map_layer = self.get_object()

        if fmv_map_layer.bounds:
            bounds = fmv_map_layer.bounds.extent
            bbox_dict = {'xmin': bounds[0], 'ymin': bounds[1], 'xmax': bounds[2], 'ymax': bounds[3]}
            return JsonResponse(bbox_dict)

        data = fmv_map_layer.get_bbox()
        return JsonResponse(data, status=200, safe=False)
