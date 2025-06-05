import click
import csv
import json
import re
from datetime import datetime
from shapely.wkb import loads
from shapely.geometry import Point


import re
from datetime import datetime

def convert_to_unix_time(datetime_str):
    """Convert a datetime string to a Unix timestamp, extracting only YYYY-MM-DD HH:MM:SS."""
    try:
        # Step 1: Use regex to extract the part of the datetime string in the format YYYY-MM-DD HH:MM:SS
        match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', datetime_str)
        if match:
            datetime_str = match.group(0)  # Extract the matched part

        # Step 2: Convert the string to a datetime object
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

        # Step 3: Return Unix timestamp
        return int(dt.timestamp())
    
    except ValueError as e:
        print(f"Error parsing datetime: {datetime_str}")
        raise e

@click.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.argument('geojson_file', type=click.Path())
def csv_to_geojson(csv_file, geojson_file):
    """Convert CSV to GeoJSON with specific formatting and handling of NULL values."""
    
    features = []
    
    with open(csv_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            # Skip row if coordinates are NULL
            if row['coordinates'] == 'NULL':
                continue

            # Parse WKT coordinates into GeoJSON Point
            point = loads(row['coordinates'])

            # Create properties dictionary
            properties = {}
            for key, value in row.items():
                if value != 'NULL':
                    if key == 'start_datetime':
                        # Add original start_datetime
                        properties['start_datetime'] = value
                        print(value)
                        # Convert to unix_time and add it to properties
                        properties['unix_time'] = convert_to_unix_time(value)
                    elif key in ['depth', 'magnitude']:
                        # Set to 0 if value is NULL
                        properties[key] = float(value) if value != 'NULL' else 0
                    else:
                        properties[key] = value

            # Create feature
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [point.x, point.y]
                },
                "properties": properties
            }
            
            features.append(feature)

    # Create the GeoJSON structure
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    # Write to output GeoJSON file
    with open(geojson_file, 'w', encoding='utf-8') as outfile:
        json.dump(geojson, outfile, indent=4)


if __name__ == '__main__':
    csv_to_geojson()
