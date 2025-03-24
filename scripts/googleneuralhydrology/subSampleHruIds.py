import json
import click

@click.command()
@click.argument('geojson_file', type=click.Path(exists=True))
@click.argument('id_list_file', type=click.Path(exists=True))
@click.option('--output', default='matching_hru_ids.geojson', help='Output GeoJSON filename')
def filter_geojson(geojson_file, id_list_file, output):
    """Filter features from a GEOJSON file based on matching HRU IDs from a JSON array."""
    
    # Load the list of HRU IDs
    with open(id_list_file, 'r') as f:
        try:
            hru_ids = {str(id).zfill(8) for id in json.load(f)}  # Convert values to a set of zero-padded strings
        except (ValueError, TypeError) as e:
            click.echo(f"Error reading ID list file: {e}")
            return

    # Load the GeoJSON file
    with open(geojson_file, 'r') as f:
        geojson_data = json.load(f)
    
    if 'features' not in geojson_data:
        click.echo("Invalid GeoJSON file: No 'features' key found.")
        return

    # Filter features based on matching hru_id, ensuring zero-padding
    filtered_features = []
    for feature in geojson_data['features']:
        if 'properties' in feature and 'hru_id' in feature['properties']:
            hru_id = str(feature['properties']['hru_id']).zfill(8)  # Ensure 8-digit format
            if hru_id in hru_ids:
                feature['properties']['hru_id'] = hru_id  # Update the feature to ensure zero-padding
                filtered_features.append(feature)

    # Create new GeoJSON structure
    filtered_geojson = {
        "type": "FeatureCollection",
        "features": filtered_features
    }

    # Write the output file
    with open(output, 'w') as f:
        json.dump(filtered_geojson, f, indent=2)
    
    click.echo(f"Filtered GeoJSON saved to {output}")

if __name__ == '__main__':
    filter_geojson()
