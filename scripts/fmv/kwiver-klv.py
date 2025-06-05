# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "click",
#   "shapely",
#   "pyproj",
# ]
# ///
 
"""
KWIVER Dump to JSON Converter
Uses the kitware/kwiver docker file to run dump-klv to create
a CSV file with the output data (CSV is chosen becase the json file is a bit obtuse).
The CSV file is converted to a JSON file for easer processing and from there it creates 3 files:
output_metadata.geojson - geojson file with the camera footprint plus the camera positioning indexed by frame number
ground_frame_mapping.json - dictionary where the keys are video frames and the values are a bounding box representing the video location
bbox_frame.geojson - A geojson file of all of the ground mapped bounding boxes where each has a property of the frame.

Usage:
    uv kwiver-klv.py path/to/video.mpg ./output
"""

import csv
import json
import subprocess
from pathlib import Path
import click
from shapely.geometry import Point, Polygon, mapping
from shapely.ops import unary_union
import pyproj

@click.command()
@click.argument('video', type=click.Path(exists=True), required=True)
@click.argument('output_dir', type=click.Path(), default='./output')
def main(video, output_dir):
    video_path = Path(video).resolve()
    output_dir = Path(output_dir).resolve()

    output_dir.mkdir(parents=True, exist_ok=True)

    output_csv = output_dir / 'output.csv'
    output_json = output_dir / 'output.json'
    geojson_out = output_dir / 'output_metadata.geojson'
    bbox_out = output_dir / 'ground_frame_mapping.json'
    bbox_geojson_out = output_dir / 'bbox_frame.geojson'
    click.echo(f'Processing video: {video_path}')
    click.echo('Running KWIVER via Docker to extract metadata...')

    output_csv_file = Path(video_path.parent / 'output.csv')
    cmd = [
        'docker', 'run', '--rm',
        '-v', f'{video_path.parent}:/data',
        'kitware/kwiver:latest',
        'dump-klv', f'/data/{video_path.name}',
        '-l', f'/data/output.csv',
        '-e', 'csv'
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        click.secho(f'Error running KWIVER: {e}', fg='red')
        return

    if not output_csv_file.exists():
        click.secho('KWIVER did not generate the expected CSV output.', fg='red')
        return

    click.echo(f'KWIVER output saved to {output_csv}')

    click.echo(f'Reading {output_csv_file} and converting to JSON...')
    with open(output_csv_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        frames = [row for row in reader]

    with open(output_json, 'w') as f:
        json.dump(frames, f, indent=2)

    click.secho(f'JSON output written to {output_json}', fg='green')

    create_geojson_and_bbox(frames, geojson_out, bbox_out, bbox_geojson_out)
    click.secho(f'GeoJSON written to {geojson_out}', fg='cyan')
    click.secho(f'Bounding box mapping written to {bbox_out}', fg='cyan')


def create_geojson_and_bbox(frames, geojson_out, bbox_out, bbox_geojson_out):
    geod = pyproj.Geod(ellps='WGS84')
    features = []
    polygons = []
    frame_polygons = []
    frame_to_bbox = {}
    total = len(frames)

    for frame in frames:
        try:
            frame_id = frame.get("Frame ID", None)
            if frame_id is None:
                continue

            # Sensor location
            sensor_lat = float(frame["Sensor Geodetic Latitude (EPSG:4326)"])
            sensor_lon = float(frame["Sensor Geodetic Longitude (EPSG:4326)"])

            # Frame center and bounding
            center_lat = float(frame["Geodetic Frame Center Latitude (EPSG:4326)"])
            center_lon = float(frame["Geodetic Frame Center Longitude (EPSG:4326)"])
            width = float(frame["Target Width (meters)"])

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
            feature = {
                "type": "Feature",
                "geometry": mapping(point),
                "properties": {
                    "Frame ID": frame_id,
                    "Platform Ground Speed": frame.get("Platform Ground Speed (m/s)"),
                    "Platform Vertical Speed": frame.get("Platform Vertical Speed (m/s)")
                }
            }
            features.append(feature)

        except (KeyError, ValueError) as e:
            print(f"Skipping frame due to error: {e}")
            continue

    # Add unioned polygon
    if polygons:
        merged = unary_union(polygons)
        features.append({
            "type": "Feature",
            "geometry": mapping(merged),
            "properties": {
                "type": "Unioned Bounding Box"
            }
        })

    # Save GeoJSON
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(geojson_out, 'w') as f:
        json.dump(geojson, f, indent=2)

    # Save bbox mapping
    with open(bbox_out, 'w') as f:
        json.dump(frame_to_bbox, f, indent=2)

    def get_gradient_color(idx, total):
        r = int(255 * (idx / (total - 1)))
        b = int(255 * (1 - idx / (total - 1)))
        return f"#{r:02x}00{b:02x}"

    # Individual frame bbox polygons with styling
    bbox_features = []
    for idx, (frame_id, poly) in enumerate(frame_polygons):
        color = get_gradient_color(idx, total)
        feature = {
            "type": "Feature",
            "geometry": mapping(poly),
            "properties": {
                "frame_id": frame_id,
                "type": "Unioned Bounding Box",
                "stroke": color,
                "stroke-width": 2,
                "stroke-opacity": 1,
                "fill": "#ff0000",
                "fill-opacity": 0.5
            }
        }
        bbox_features.append(feature)

    bbox_geojson = {
        "type": "FeatureCollection",
        "features": bbox_features
    }

    with open(bbox_geojson_out, 'w') as f:
        json.dump(bbox_geojson, f, indent=2)

if __name__ == '__main__':
    main()
