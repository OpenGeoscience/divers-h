import json
import click

@click.command()
@click.argument("geojson_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
def extract_hru_ids(geojson_file, output_file):
    """Extracts hru_id from a GeoJSON file and saves them as a JSON array."""
    
    with open(geojson_file, "r") as f:
        geojson_data = json.load(f)

    # Extract hru_id from each feature and ensure it's 8 digits with leading zeros
    hru_ids = [
        f"{int(feature['properties']['hru_id']):08d}"
        for feature in geojson_data.get("features", [])
        if "hru_id" in feature.get("properties", {})
    ]

    # Save output JSON
    with open(output_file, "w") as f:
        json.dump(hru_ids, f, indent=4)

    click.echo(f"Extracted {len(hru_ids)} HRU IDs to {output_file}")

if __name__ == "__main__":
    extract_hru_ids()
