import csv
import json
import logging
import os
from pathlib import Path
import subprocess
import tempfile

from django.contrib.gis.geos import GEOSGeometry
from django.core.files.base import ContentFile
import pyproj
from shapely.geometry import Point, Polygon, mapping
from shapely.ops import unary_union

from uvdat.core.models import (
    FMVLayer,
    FMVVectorFeature,
)

logger = logging.getLogger(__name__)


def create_fmv_layer(file_item, style_options, file_name, metadata=None):
    # First we grab the video file
    with tempfile.TemporaryDirectory() as temp_dir:
        video_ext = os.path.splitext(file_name)[1]
        logger.info(f'file_name: {file_name} extension: {video_ext}')
        layer_name = metadata.get('name', file_name)
        raw_data_path = Path(temp_dir, f'video{video_ext}')
        logger.info(f'RAW DATA PATH {raw_data_path}')
        with open(raw_data_path, 'wb') as raw_data:
            with file_item.file.open('rb') as raw_data_archive:
                raw_data.write(raw_data_archive.read())
        # Now lets see if the FMV file has FMV data
        output_csv = Path(temp_dir, 'output.csv')
        cmd = [
            'bash',
            '/entrypoint.sh',
            'dump-klv',
            str(raw_data_path),
            '-l',
            str(output_csv),
            '-e',
            'csv',
        ]
        # cmd = [
        #     '/opt/kitware/kwiver/bin/kwiver',
        #     'dump-klv', str(raw_data_path),
        #     '-l', str(output_csv),
        #     '-e', 'csv'
        # ]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f'Error running KWIVER: {e}')
            return

        if not output_csv.exists():
            logger.error('KWIVER did not generate the expected CSV output.')
            return

        with open(output_csv, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            frames = [row for row in reader]
        output_json = Path(temp_dir, 'output.json')
        with open(output_json, 'w') as f:
            json.dump(frames, f, indent=2)

        logger.info(f'JSON output written to {output_json}')

        logger.info('Creating the GeoJSON from the FMV Data')
        frame_geojson = create_geojson_and_bbox(frames)

        transcoded_path = Path(temp_dir, 'transcoded.mp4')
        transcode_cmd = [
            'ffmpeg',
            '-i',
            str(raw_data_path),
            '-c:v',
            'libx264',
            '-preset',
            'fast',
            '-crf',
            '23',
            str(transcoded_path),
        ]
        try:
            subprocess.run(transcode_cmd, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f'Error during video transcoding: {e}')
            return

        # Get the metadata from the video file using ffprobe
        ffprobe_cmd = [
            'ffprobe',
            '-v',
            'error',
            '-select_streams',
            'v:0',
            '-show_entries',
            'stream=width,height,avg_frame_rate,nb_frames',
            '-of',
            'json',
            str(transcoded_path),
        ]
        try:
            ffprobe_result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
            ffprobe_data = json.loads(ffprobe_result.stdout)
            stream = ffprobe_data['streams'][0]
            width = int(stream.get('width', 0))
            height = int(stream.get('height', 0))
            # avg_frame_rate is like "25/1"
            avg_frame_rate = stream.get('avg_frame_rate', '0/1')
            if '/' in avg_frame_rate:
                num, denom = avg_frame_rate.split('/')
                fps = float(num) / float(denom) if float(denom) != 0 else 0
            else:
                fps = float(avg_frame_rate)
            frame_count = int(stream.get('nb_frames', 0))
        except Exception as e:
            logger.error(f'Error extracting video metadata: {e}')
            width = height = frame_count = 0
            fps = 0.0

        # Read video and GeoJSON into Django content fields
        with open(transcoded_path, 'rb') as f:
            fmv_video_file = ContentFile(f.read(), name='video.mp4')

        with open(raw_data_path, 'rb') as f:
            raw_video_file = ContentFile(f.read(), name=file_name)

        geojson_str = json.dumps(frame_geojson, indent=2)
        geojson_file = ContentFile(geojson_str.encode('utf-8'), name='vectordata.geojson')

        # Create FMVLayer object
        fmv_layer = FMVLayer.objects.create(
            dataset=file_item.dataset,
            fmv_source_video=raw_video_file,
            fmv_video=fmv_video_file,
            geojson_file=geojson_file,
            default_style=style_options,
            metadata=metadata,
            name=layer_name,
            fmv_fps=fps,
            fmv_frame_count=frame_count,
            fmv_video_width=width,
            fmv_video_height=height,
        )

        # Set bounds from GeoJSON
        fmv_layer.set_bounds()

        # Create FMVVectorFeature entries
        for feature in frame_geojson['features']:
            geometry = GEOSGeometry(json.dumps(feature['geometry']))
            FMVVectorFeature.objects.create(
                map_layer=fmv_layer, geometry=geometry, properties=feature['properties']
            )

        logger.info(
            f'Successfully created FMVLayer: {fmv_layer.id} with {len(frame_geojson["features"])} features'
        )
        return fmv_layer


def create_geojson_and_bbox(
    frames,
):
    geod = pyproj.Geod(ellps='WGS84')
    features = []
    polygons = []
    frame_polygons = []
    frame_to_bbox = {}

    for frame in frames:
        try:
            frame_id = frame.get('Frame ID', None)
            if frame_id is None:
                continue

            # Sensor location
            sensor_lat = float(frame['Sensor Geodetic Latitude (EPSG:4326)'])
            sensor_lon = float(frame['Sensor Geodetic Longitude (EPSG:4326)'])

            # Frame center and bounding
            center_lat = float(frame['Geodetic Frame Center Latitude (EPSG:4326)'])
            center_lon = float(frame['Geodetic Frame Center Longitude (EPSG:4326)'])
            width = float(frame['Target Width (meters)'])

            # Compute bounding box corners around center
            corners = []
            for az in (0, 90, 180, 270):
                lon, lat, _ = geod.fwd(center_lon, center_lat, az, width / 2)
                corners.append((lon, lat))
            corners.append(corners[0])  # close the polygon

            polygon = Polygon(corners)
            polygons.append(polygon)
            frame_polygons.append((frame_id, polygon))
            frame_to_bbox[frame_id] = corners

            # Point feature at sensor location
            point = Point(sensor_lon, sensor_lat)
            properties = {'fmvType': 'flight_path'}
            properties['frameId'] = int(frame_id)
            for key, value in frame.items():
                properties[key] = value

            feature = {
                'type': 'Feature',
                'geometry': mapping(point),
                'properties': properties,
            }
            features.append(feature)

        except (KeyError, ValueError) as e:
            print(f'Skipping frame due to error: {e}')
            continue

    # Add unioned polygon
    if polygons:
        merged = unary_union(polygons)
        features.append(
            {
                'type': 'Feature',
                'geometry': mapping(merged),
                'properties': {'fmvType': 'ground_union'},
            }
        )

    # Individual frame bbox polygons with styling
    for _idx, (frame_id, poly) in enumerate(frame_polygons):
        feature = {
            'type': 'Feature',
            'geometry': mapping(poly),
            'properties': {
                'frameId': int(frame_id),
                'fmvType': 'ground_frame',
            },
        }
        features.append(feature)

    geojson = {'type': 'FeatureCollection', 'features': features}

    return geojson
