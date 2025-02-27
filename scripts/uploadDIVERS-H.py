import os
import json
import re
import click
import xarray as xr
from girder_client import GirderClient
import matplotlib.pyplot as plt

baseApiKey = 'GET API KEY HERE'


def authenticate(client: GirderClient):
    client.authenticate(apiKey=baseApiKey)


def create_folder(client, parent_id, name):
    folder = client.createFolder(parent_id, name, reuseExisting=True)
    return folder['_id']


def parse_nc_filename(filename):
    pattern = (
        r'(?P<variable>\w+)_Amon_(?P<model>[\w\-]+)_ssp(?P<scenario>\d+)_'
        r'(?P<ensemble>r\d+i\d+p\d+f?\d*)_?(?P<grid>\w+)?_(?P<time_range>\d{4,6}-\d{4,6})\.nc'
    )
    match = re.match(pattern, filename)
    if match:
        return {
            'Variable': match.group('variable'),
            'Model': match.group('model'),
            'Scenario': f'ssp{match.group("scenario")}',
            'Ensemble': match.group('ensemble'),
            'Grid': match.group('grid'),
            'Time Range': match.group('time_range')
        }
    else:
        return {'Filename': filename}

def parse_geojson_filename(filename):
    pattern = (
        r'PowerPlant_(?P<model>[\w\-]+)_ssp(?P<scenario>\d+)_'
        r'(?P<ensemble>r\d+i\d+p\d+f?\d*)_tabular\.json'
    )
    match = re.match(pattern, filename)
    if match:
        return {
            'Model': match.group('model'),
            'Scenario': f'ssp{match.group("scenario")}',
            'Ensemble': match.group('ensemble'),
        }
    else:
        return {'Filename': filename}


def extract_netcdf_metadata(file_path, variable_name=None):
    ds = xr.open_dataset(file_path)

    # Select variable with at least 3 dimensions if variable_name is not provided or doesn't match
    if variable_name not in ds.variables:
        var = next((v for v in ds.data_vars.values() if len(v.dims) >= 3), None)
    else:
        var = ds[variable_name]

    if var is None:
        raise ValueError("No suitable variable with at least 3 dimensions found.")

    dimensions = list(var.dims)
    x_dim = next((dim for dim in dimensions if 'lon' in dim.lower() or 'longitude' in dim.lower()), None)
    y_dim = next((dim for dim in dimensions if 'lat' in dim.lower() or 'latitude' in dim.lower()), None)
    time_dim = next((dim for dim in dimensions if 'time' in dim.lower()), None)

    # Extract long_name or standard_name
    long_name = var.attrs.get('long_name', None)
    standard_name = var.attrs.get('standard_name', None)

    ds.close()

    return {
        'x_dim': x_dim,
        'y_dim': y_dim,
        'time_dim': time_dim,
        'variable_name': var.name,
        'long_name': long_name if long_name else standard_name
    }


def get_color_map(variable):
    color_maps = {
        'evspsbl': 'Blues',
        'pr': 'Greens',
        'tas': 'Reds',
        'PminusE': 'turbo'
    }
    return color_maps.get(variable, 'viridis')

def get_public_folder(gc: GirderClient):
    current_user = gc.sendRestRequest('GET', 'user/me')
    userId = current_user['_id']
    folders = gc.sendRestRequest('GET', f'folder?parentType=user&parentId={userId}&text=Public&limit=50&sort=lowerName&sortdir=1')
    if len(folders) > 0:
        uploadFolder = folders[0]
    else:
        print('No folder found for the user')
    return uploadFolder


def upload_nc_files(client: GirderClient, local_folder, remote_folder_id, base_path):
    file_metadata = []
    for root, _, files in os.walk(local_folder):
        count = 0
        for file in files:
            if not file.endswith('.nc'):
                continue
            local_file_path = os.path.join(root, file)
            existing_item = list(client.listItem(remote_folder_id, name=file))
            print(f'Uploading File: {file} {count} of {len(files)}')
            if len(existing_item) > 0:
                file_id = existing_item[0]['_id']
                file_url = f'https://data.kitware.com/api/v1/file/{file_id}/download'
            else:
                item = client.uploadFileToFolder(remote_folder_id, local_file_path)
                file_url = f'https://data.kitware.com/api/v1/file/{item["_id"]}/download'
            
            parsed = parse_nc_filename(file)
            print(file)
            print(parsed)
            netcdf_metadata = extract_netcdf_metadata(local_file_path, parsed['Variable'])
            x_dim = netcdf_metadata['x_dim']
            y_dim = netcdf_metadata['y_dim']
            time_dim = netcdf_metadata['time_dim']
            long_name = netcdf_metadata['long_name']
            variable_name = netcdf_metadata['variable_name']
            name = variable_name
            if long_name:
                name = long_name
            color_scheme = get_color_map(parsed['Variable'])
            
            main_tag = 'Input'
            if 'Output' in base_path:
                main_tag = 'Output'
            parsed['Input/Output'] = main_tag
            file_metadata.append({
                'name': os.path.splitext(file)[0],
                'path': f'./data/{base_path}/{file}',
                'url': file_url,
                'type': 'netcdf',
                'metadata': {
                    'generate': [
                        {
                            'name': os.path.splitext(file)[0],
                            'x_variable': x_dim,
                            'y_variable': y_dim,
                            'variable': variable_name,
                            'sliding_variable': time_dim,
                            'color_map': color_scheme
                        }
                    ],
                    'tags': {
                        'filters': parsed,
                    }
                }
            })
            count += 1
    return file_metadata


def upload_tabular_files(client: GirderClient, local_folder, remote_folder_id, base_path, powerplant_geojson, base_default_style):
    file_metadata = []
    existing_power_plantitem = list(client.listItem(remote_folder_id, name=powerplant_geojson))
    powerplant_url = ''
    with open(base_default_style, "r") as f:
        default_style = json.load(f)  # data is now a Python dictionary

    if len(existing_power_plantitem) > 0:
        powerplant_id = existing_power_plantitem[0]['_id']
        powerplant_url = f'https://data.kitware.com/api/v1/file/{powerplant_id}/download'
    else:
        item = client.uploadFileToFolder(remote_folder_id, powerplant_geojson)
        powerplant_url = f'https://data.kitware.com/api/v1/file/{item["_id"]}/download'

    for root, _, files in os.walk(local_folder):
        count = 0
        for file in files:
            if not file.endswith('.json'):
                continue
            local_file_path = os.path.join(root, file)
            existing_item = list(client.listItem(remote_folder_id, name=file))
            if len(existing_item) > 0:
                file_id = existing_item[0]['_id']
                file_url = f'https://data.kitware.com/api/v1/file/{file_id}/download'
            else:
                print(f'Uploading File: {file} {count} of {len(files)}')
                item = client.uploadFileToFolder(remote_folder_id, local_file_path)
                file_url = f'https://data.kitware.com/api/v1/file/{item["_id"]}/download'
            
            parsed = parse_geojson_filename(file)
            print(file)
            print(parsed)
            # now we open the file and check for the table name
            with open(local_file_path, "r") as f:
                tabular_data = json.load(f)  # data is now a Python dictionary
            table_name  = ''
            for key in tabular_data.keys():
                tab_data = tabular_data[key][0]
                table_name = tab_data['type']
                break
            print(f'TABLENAME {table_name}')
            print(default_style['vectorFeatureTableGraphs'])
            for index, item in enumerate(default_style['vectorFeatureTableGraphs']):
                print(f'Updating vectorFeatureTableGraphs defaultStyle: {table_name}')
                default_style['vectorFeatureTableGraphs'][index]['type'] = table_name
            for index, item in enumerate(default_style['mapLayerFeatureTableGraphs']):
                print(f'Updating mapLayerFeatureTableGraphs defaultStyle: {table_name}')
                default_style['mapLayerFeatureTableGraphs'][index]['type'] = table_name
            main_tag = 'Ouput'
            parsed['Input/Output'] = main_tag
            file_metadata.append({
                'name': f'{os.path.splitext(file)[0]}',
                'path': f'./data/{base_path}/{powerplant_geojson}',
                'url': powerplant_url,
                'type': 'geojson',
                'metadata': {
                    "tabular": {
                        'path': f'./data/{base_path}/{file}',
                        'name': f'{os.path.splitext(file)[0]}_data',
                        'url': file_url,
                        'featurePropertyMatcher': 'Plant_Code'
                    },
                    'tags': {
                        'filters': parsed,
                    },
                    'default_style': default_style,
                }
            })
            count += 1
    return file_metadata


@click.command()
@click.argument('input_folder', type=click.Path(exists=True))
@click.argument('output_folder', type=click.Path(exists=True))
@click.argument('powerplant_geojson', default='TVAPowerPlants.geojson', type=click.Path(exists=True))
@click.argument('base_powerplant_style', default='base_default_style.json', type=click.Path(exists=True))
@click.option('--save-path', default='uploaded_file_context.json', help='Path to save the context JSON.')
def main(input_folder, output_folder, powerplant_geojson, base_powerplant_style, save_path):
    client = GirderClient(apiUrl='https://data.kitware.com/api/v1')
    authenticate(client)

    # Get the Public folder ID
    public_folder = get_public_folder(client)
    uvdat_folder = list(client.listFolder(public_folder['_id'], name='UVDAT'))[0]

    # Create DIVERS-H folder
    divers_h_folder_id = create_folder(client, uvdat_folder['_id'], 'DIVERS-H')

    # Create Input and Output folders
    input_folder_id = create_folder(client, divers_h_folder_id, 'Input')
    output_folder_id = create_folder(client, divers_h_folder_id, 'Output')
    tab_folder_id = create_folder(client, divers_h_folder_id, 'PowerPlants')

    # Upload files
    input_files = upload_nc_files(client, input_folder, input_folder_id, 'DIVERS-H/Input')
    output_files = upload_nc_files(client, output_folder, output_folder_id, 'DIVERS-H/Output')
    tabular_files = upload_tabular_files(client, output_folder, tab_folder_id, 'DIVERS-H/PowerPlants', powerplant_geojson, base_powerplant_style)

    # Save context JSON
    context = {
        "type": "Context",
        "name": "Input/Outputs",
        "default_map_center": [
            34.8019,
            -86.1794
        ],
        "default_map_zoom": 6,
        "datasets": []
    }
    input_dataset = {
        "name": "Inputs",
        "description": "DIVERS-H Inputs",
        "category": "inputs",
        "metadata": {},
        "files": input_files
    }
    output_dataset = {
        "name": "Outputs",
        "description": "DIVERS-H Outputs",
        "category": "outputs",
        "metadata": {},
        "files": output_files
    }

    tabular_dataset = {
        "name": "PowerPlants",
        "description": "DIVERS-H PowerPlant data",
        "category": "merged",
        "metadata": {},
        "files": tabular_files
    }

    context['datasets'].append(input_dataset)
    context['datasets'].append(output_dataset)
    context['datasets'].append(tabular_dataset)
    with open(save_path, 'w') as f:
        json.dump([context], f, indent=4)

    click.echo(f'Context with download URLs saved to {save_path}')


if __name__ == '__main__':
    main()
