import csv
import json
import click


@click.command()
@click.argument('csv_file', type=click.File('r'))
@click.argument('output_file', type=click.File('w'))
def csv_to_geojson(csv_file, output_file):
    reader = csv.DictReader(csv_file)
    fieldnames = reader.fieldnames

    if 'Latitude' not in fieldnames or 'Longitude' not in fieldnames:
        raise click.UsageError("CSV must contain 'Latitude' and 'Longitude' fields")

    features = []

    for row in reader:
        try:
            lat = float(row['Latitude'])
            lon = float(row['Longitude'])
        except ValueError:
            click.echo(f"Skipping row with invalid Latitude/Longitude: {row}")
            continue

        properties = {
            key: value
            for key, value in row.items()
            if key and key not in ['Latitude', 'Longitude']
        }

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": properties
        }

        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    json.dump(geojson, output_file, indent=2)
    click.echo(f"GeoJSON written to {output_file.name}")


if __name__ == '__main__':
    csv_to_geojson()
