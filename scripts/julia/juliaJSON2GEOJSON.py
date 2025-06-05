import click
import json
from shapely.geometry import Point, mapping

@click.command()
@click.argument('json_file', type=click.Path(exists=True))
@click.argument('output_geojson', type=click.Path())
def json_to_geojson(json_file, output_geojson):
    # Load JSON data
    with open(json_file, 'r') as f:
        data = json.load(f)

    # Extract DataFrame
    dataframe = data['Dataframe']
    columns = dataframe['columns']
    data_array = dataframe['data']

    # Ensure all columns have the same length
    num_rows = len(data_array[0])  # Number of rows (values per column)
    for column_data in data_array:
        if len(column_data) != num_rows:
            raise ValueError("Not all columns in data_array have the same number of values.")

    # Find latitude and longitude columns
    lat_index = columns.index('Lat')
    lon_index = columns.index('Lon')

    # Create GeoJSON features
    features = []
    for i in range(num_rows):
        latitude = data_array[lat_index][i]
        longitude = data_array[lon_index][i]
        
        # Create properties dictionary for each feature
        properties = {
            columns[j]: data_array[j][i]
            for j in range(len(columns)) if j != lat_index and j != lon_index
        }

        # Create Point geometry for each feature
        geometry = Point(longitude, latitude)
        
        # Construct feature
        feature = {
            'type': 'Feature',
            'geometry': mapping(geometry),
            'properties': properties
        }
        features.append(feature)

    # Create GeoJSON structure
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    # Write to GeoJSON file
    with open(output_geojson, 'w') as f:
        json.dump(geojson, f, indent=2)

    click.echo(f"GeoJSON file saved to {output_geojson}")

if __name__ == '__main__':
    json_to_geojson()
