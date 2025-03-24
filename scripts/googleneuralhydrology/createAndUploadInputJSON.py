import os
import json
import re
import click
import xarray as xr
from girder_client import GirderClient
import matplotlib.pyplot as plt

baseApiKey = 'OxhoPyCrzkGsnQiiRYZm3BgTlPhscKvILVyRdasT'


def authenticate(client: GirderClient):
    client.authenticate(apiKey=baseApiKey)


def create_folder(client, parent_id, name):
    folder = client.createFolder(parent_id, name, reuseExisting=True)
    return folder['_id']




def get_public_folder(gc: GirderClient):
    current_user = gc.sendRestRequest('GET', 'user/me')
    userId = current_user['_id']
    folders = gc.sendRestRequest('GET', f'folder?parentType=user&parentId={userId}&text=Public&limit=50&sort=lowerName&sortdir=1')
    if len(folders) > 0:
        uploadFolder = folders[0]
    else:
        print('No folder found for the user')
    return uploadFolder




def upload_data(client: GirderClient, remote_folder_id, base_geojson, base_tab_json, base_default_style):
    file_metadata = []
    existing_base_geojson = list(client.listItem(remote_folder_id, name=base_geojson))
    existing_base_tab = list(client.listItem(remote_folder_id, name=base_tab_json))
    powerplant_url = ''
    base_default_style_dict= {}
    with open(base_default_style, "r") as f:
        base_default_style_dict = json.load(f)  # data is now a Python dictionary

    if len(existing_base_geojson) > 0:
        geojson_id = existing_base_geojson[0]['_id']
        geojson_url = f'https://data.kitware.com/api/v1/file/{geojson_id}/download'
    else:
        item = client.uploadFileToFolder(remote_folder_id, base_geojson)
        geojson_url = f'https://data.kitware.com/api/v1/file/{item["_id"]}/download'

    if len(existing_base_tab) > 0:
        tab_id = existing_base_tab[0]['_id']
        tab_url = f'https://data.kitware.com/api/v1/file/{tab_id}/download'
    else:
        item = client.uploadFileToFolder(remote_folder_id, base_tab_json)
        tab_url = f'https://data.kitware.com/api/v1/file/{item["_id"]}/download'


    # now we open the file and check for the table name
    with open(base_tab_json, "r") as f:
        tabular_data = json.load(f)  # data is now a Python dictionary
    table_name  = ''
    headers = []
    for key in tabular_data.keys():
        tab_data_charts = tabular_data[key]
        break
    vectorFeatureTableGraphs = []
    mapLayerFeatureTableGraphs = []
    for tab_data in tab_data_charts:
        headers = tab_data['header']
        table_name = tab_data['type']
        for item in headers:
            if item in ['time', 'date_str', 'year_nu', 'month_nu', 'day_nu']:
                continue
            if item != 'unix_time':
                vectorFeatureTableGraphs.append({
                    "name": item,
                    "type": table_name,
                    "xAxis": "unix_time",
                    "yAxis": item,
                    "indexer": "hru_id",
                    "xAxisLabel": "Date",
                    "yAxisLabel": item
                })
                mapLayerFeatureTableGraphs.append({
                    "name": item,
                    "type": table_name,
                    "xAxis": "unix_time",
                    "yAxis": item,
                    "indexer": "hru_id",
                    "xAxisLabel": "Date",
                    "yAxisLabel": item
                })
    default_style = base_default_style_dict.copy()
    default_style['vectorFeatureTableGraphs'] = vectorFeatureTableGraphs
    default_style['mapLayerFeatureTableGraphs'] = mapLayerFeatureTableGraphs
    print(default_style['mapLayerFeatureTableGraphs'])
    file_metadata.append({
        'name': f'Google Eural Hydrology Data',
        'path': f'./data/GoogleNeuralHydrology/{base_geojson}',
        'url': geojson_url,
        'type': 'geojson',
        'metadata': {
            "tabular": {
                'path': f'./data/GoogleNeuralHydrology/{base_tab_json}',
                'name': f'Google Neural Hydrology Tabular Data',
                'url': tab_url,
                'featurePropertyMatcher': 'hru_id'
            },
            'default_style': default_style,
        }
    })
    return file_metadata


@click.command()
@click.argument('base_geojson', type=click.Path(exists=True))
@click.argument('base_tabular', type=click.Path(exists=True))
@click.argument('base_default_style', default='base_default_style.json', type=click.Path(exists=True))
@click.option('--save-path', default='uploaded_file_context.json', help='Path to save the context JSON.')
def main(base_geojson, base_tabular, base_default_style, save_path):
    client = GirderClient(apiUrl='https://data.kitware.com/api/v1')
    authenticate(client)

    # Get the Public folder ID
    public_folder = get_public_folder(client)
    uvdat_folder = list(client.listFolder(public_folder['_id'], name='UVDAT'))[0]

    # Create GoogleNeuralHydrology folder
    google_hydrology_id = create_folder(client, uvdat_folder['_id'], 'GoogleNeuralHydrology')

    # Create Input and Output folders

    # Upload files

    tabular_files = upload_data(client, google_hydrology_id, base_geojson, base_tabular, base_default_style)

    # Save context JSON
    context = {
        "type": "Context",
        "name": "Google Neural Hydrology",
        "default_map_center": [
            34.8019,
            -86.1794
        ],
        "default_map_zoom": 6,
        "datasets": []
    }
    google_dataset = {
        "name": "Google Neural Hydrology",
        "description": "Google Neural Hydrology",
        "category": "Google Neural Hydrology",
        "metadata": {},
        "files": tabular_files
    }


    context['datasets'].append(google_dataset)
    with open(save_path, 'w') as f:
        json.dump([context], f, indent=4)

    click.echo(f'Context with download URLs saved to {save_path}')


if __name__ == '__main__':
    main()
