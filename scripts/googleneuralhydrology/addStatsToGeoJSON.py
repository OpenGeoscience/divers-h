import click
import json
import geojson
from collections import defaultdict

def flatten_dict(d, parent_key='', sep='.', result=None):
    """Flattens a nested dictionary."""
    if result is None:
        result = {}
    for key, value in d.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            flatten_dict(value, new_key, sep=sep, result=result)
        else:
            result[new_key] = value
    return result

def process_geojson(geojson_file, json_file, output_file):
    """Process GeoJSON and JSON to combine data based on hru_id."""
    
    # Load the geojson file
    with open(geojson_file, 'r') as f:
        geo_data = geojson.load(f)
    
    # Load the JSON file with HRU stats
    with open(json_file, 'r') as f:
        stats_data = json.load(f)

    # Iterate over the features in the GeoJSON file
    for feature in geo_data['features']:
        hru_id = feature['properties'].get('hru_id')
        
        if hru_id and str(hru_id) in stats_data:
            stats = stats_data[str(hru_id)]
            
            # Flatten the statistics for 'Obs-Sim' and 'Percentage_Off'
            flattened_stats = {}
            for category in ['Obs-Sim', 'Percentage_Off']:
                if category in stats:
                    flattened_stats.update(flatten_dict(stats[category], parent_key=category))
            
            # Add the flattened stats to the GeoJSON feature properties
            feature['properties'].update(flattened_stats)
    
    # Save the modified GeoJSON to the output file
    with open(output_file, 'w') as f:
        geojson.dump(geo_data, f, separators=(',', ':'))

    click.echo(f"Processed GeoJSON saved to {output_file}")

@click.command()
@click.argument('geojson_file', default='matching_hru_ids.geojson', type=click.Path(exists=True))
@click.argument('json_file', default='nc_stat_mapping.json', type=click.Path(exists=True))
@click.argument('output_file', default='CAMEL_USGS_Stats.geojson', type=click.Path())
def process_files(geojson_file, json_file, output_file):
    """CLI tool to merge HRU stats from a JSON file into a GeoJSON file."""
    process_geojson(geojson_file, json_file, output_file)

if __name__ == "__main__":
    process_files()
