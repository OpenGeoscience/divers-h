from django.db import connection
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from django.core.files.storage import default_storage

from uvdat.core.models import FMVLayer

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
        id as fmvvectorfeatureid,
        properties
    FROM core_fmvvectorfeature
    WHERE ST_Intersects(geometry, (SELECT geom from bounds))
    AND map_layer_id = %(map_layer_id)s
)
SELECT ST_AsMVT(vector_features.*) AS mvt FROM vector_features;
"""

class FMVLayerViewSet(ViewSet):
    """
    ViewSet for accessing FMVLayer data and tiles.
    """
    def retrieve(self, request, pk=None):
        try:
            layer = FMVLayer.objects.get(pk=pk)
        except FMVLayer.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        presigned_url = None
        if layer.fmv_video and hasattr(layer.fmv_video, 'name'):
            presigned_url = default_storage.url(layer.fmv_video.name)
        else:
            presigned_url = None
        data = {
            "id": layer.id,
            "name": layer.name,
            "bbox": list(layer.bounds.extent) if layer.bounds else None,
            "frameId_to_bbox": layer.get_ground_frame_mapping(),
            "fmv_video_url": presigned_url
        }
        return Response(data)

    @action(
        detail=True,
        methods=["get"],
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
