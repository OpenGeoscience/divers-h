import click
import json

@click.command()
@click.argument("json_file1", type=click.Path(exists=True))
@click.argument("json_file2", type=click.Path(exists=True))
@click.argument("output", default="combined.json", type=click.Path())
def combine_json(json_file1, json_file2, output):
    """Combine two JSON files by concatenating arrays for matching keys."""
    
    # Load first JSON file
    with open(json_file1, "r") as f:
        data1 = json.load(f)
    
    # Load second JSON file
    with open(json_file2, "r") as f:
        data2 = json.load(f)
    
    # Merge data
    combined_data = {}
    all_keys = set(data1.keys()).union(data2.keys())
    
    for key in all_keys:
        value1 = data1.get(key, None)
        value2 = data2.get(key, None)
        
        if isinstance(value1, list) and isinstance(value2, list):
            combined_data[key] = value1 + value2
        elif isinstance(value1, list):
            combined_data[key] = value1
        elif isinstance(value2, list):
            combined_data[key] = value2
        else:
            ValueError('Key is not valid in either data')
    
    # Save combined JSON
    with open(output, "w") as f:
        json.dump(combined_data, f, separators=(',', ':'))
    
    click.echo(f"Combined JSON saved to {output}")

if __name__ == "__main__":
    combine_json()
