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

    geojson_data = create_geojson_and_bbox(frames)
    with open(geojson_out, 'w') as f:
        json.dump(geojson_data, f, indent=2)
    click.secho(f'GeoJSON data created with {len(geojson_data["features"])} features.', fg='green')
    click.secho(f'GeoJSON written to {geojson_out}', fg='cyan')


def create_geojson_and_bbox(
    frames,
):
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
            sensor_lat = float(frame['Sensor Geodetic Latitude (EPSG:4326)'])
            sensor_lon = float(frame['Sensor Geodetic Longitude (EPSG:4326)'])

            # Frame center and bounding
            center_lat = float(frame['Geodetic Frame Center Latitude (EPSG:4326)'])
            center_lon = float(frame['Geodetic Frame Center Longitude (EPSG:4326)'])
            target_width = float(frame['Target Width (meters)'])
            image_width = float(frame['Image Width'])
            image_height = float(frame['Image Height'])
            platform_heading = float(frame['Platform Heading Angle (degrees)'])
            sensor_heading = float(frame['Sensor Relative Azimuth Angle (degrees)'])
            heading = platform_heading + sensor_heading
            # Build a rectangular footprint centered at the center point, rotated by heading
            # Compute height in meters based on aspect ratio
            target_height = (image_height / image_width) * target_width

            # Half dimensions
            half_width = target_width / 2
            half_height = target_height / 2

            # Corner offsets (dx, dy) relative to center
            corner_offsets = [(-half_width, half_height), (half_width, half_height),
                            (half_width, -half_height), (-half_width, -half_height)]

            corners = []
            for dx, dy in corner_offsets:
                distance = (dx**2 + dy**2) ** 0.5
                angle = (heading + np.degrees(np.arctan2(dx, dy))) % 360
                lon, lat, _ = geod.fwd(center_lon, center_lat, angle, distance)
                corners.append((lon, lat))
            corners.append(corners[0])  # Close polygon            polygon = Polygon(corners)
            polygons.append(polygon)
            frame_polygons.append((frame_id, polygon))
            frame_to_bbox[frame_id] = corners

            # Point feature at sensor location
            point = Point(sensor_lon, sensor_lat)
            properties = {"fmvType": "flight_path"}
            properties["frameId"] = int(frame_id)
            for key, value in frame.items():
                properties[key] = value

            feature = {
                "type": "Feature",
                "geometry": mapping(point),
                "properties": properties,
            }
            features.append(feature)

        except (KeyError, ValueError) as e:
            print(f"Skipping frame due to error: {e}")
            continue

    # Add unioned polygon
    if polygons:
        merged = unary_union(polygons)
        features.append(
            {
                "type": "Feature",
                "geometry": mapping(merged),
                "properties": {"fmvType": "ground_union"},
            }
        )

    # Individual frame bbox polygons with styling
    for idx, (frame_id, poly) in enumerate(frame_polygons):
        feature = {
            "type": "Feature",
            "geometry": mapping(poly),
            "properties": {
                "frameId": int(frame_id),
                "fmvType": "ground_frame",
            },
        }
        features.append(feature)

    geojson = {"type": "FeatureCollection", "features": features}

    return geojson

if __name__ == '__main__':
    main()
