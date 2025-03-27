import json
import click

@click.command()
@click.argument('input', required=True, type=click.Path(exists=True))
@click.argument('output', required=True, type=click.Path())
def convert_file(input, output):
    """Convert a line-by-line JSON file to a single JSON object."""
    result = {}

    # Read the input file line by line
    with open(input, 'r') as infile:
        for line in infile:
            try:
                # Parse the JSON object from the line
                data = json.loads(line.strip())
                # Extract the 8-digit number from the "name" field
                name = data.get("name", "")
                site_number = name.split('_')[0] if name else None
                
                if site_number and len(site_number) == 8:  # Check if the site_number is valid (8 digits)
                    # Add the data to the result dictionary with the 8-digit number as the key
                    result[site_number] = {k: v for k, v in data.items() if k != "name"}  # Exclude "name" field
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON line: {line.strip()}")

    # Write the result to the output file in a dense JSON format (no indentation or newlines)
    with open(output, 'w') as outfile:
        json.dump(result, outfile, separators=(',', ':'))

    print(f"Conversion complete. Output written to {output}")

if __name__ == '__main__':
    convert_file()
