import os
import json
import click
from girder_client import GirderClient

EXCLUDED_FIELDS = {'datetime', 'unix_time', 'site_no'}
GIRDER_API_KEY = 'Replace with API Key'


def authenticate(client: GirderClient):
    client.authenticate(apiKey=GIRDER_API_KEY)


def get_public_folder(gc: GirderClient):
    user = gc.get('user/me')
    user_id = user['_id']
    folders = gc.get(f'folder?parentType=user&parentId={user_id}&text=Public')
    if folders:
        return folders[0]
    raise RuntimeError('No Public folder found for the user.')


def create_folder(client: GirderClient, parent_id, name: str):
    folder = client.createFolder(parent_id, name, reuseExisting=True)
    return folder['_id']


def upload_file(client: GirderClient, folder_id: str, file_path: str):
    file_name = os.path.basename(file_path)
    existing = list(client.listItem(folder_id, name=file_name))
    if existing:
        file_id = existing[0]['_id']
        return f'https://data.kitware.com/api/v1/file/{file_id}/download'
    item = client.uploadFileToFolder(folder_id, file_path)
    return f'https://data.kitware.com/api/v1/file/{item["_id"]}/download'


def create_graph_metadata(tabular_data, geojson_url, tabular_url):
    files = []

    vectorFeatureTableGraphs = []
    mapLayerFeatureTableGraphs = []

    for entry in tabular_data:
        table_name = entry["type"]
        print(table_name)
        headers = entry["header"]


        for item in headers:
            if item not in EXCLUDED_FIELDS:
                vectorFeatureTableGraphs.append({
                    "name": f"{table_name} {item}",
                    "type": table_name,
                    "xAxis": "unix_time",
                    "yAxis": item,
                    "xAxisLabel": "Date",
                    "yAxisLabel": item
                })
                mapLayerFeatureTableGraphs.append({
                    "name": f"{table_name} {item}",
                    "type": table_name,
                    "xAxis": "unix_time",
                    "yAxis": item,
                    "indexer": "site_no",
                    "xAxisLabel": "Date",
                    "yAxisLabel": item
                })


    files.append({
        "name": 'StreamTemperature',
        "type": "geojson",
        "path": './data/StreamTemperature/stream_temperature.geojson',
        "url": geojson_url,
        "metadata": {
            "tabular": {
                "name": "StreamTemperature_data",
                "path": './data/StreamTemperature/stream_temperature_tabular.json',
                "url": tabular_url,
                "featurePropertyMatcher": "Site Number"
            },
            "default_style": {
                "layers": {
                    "fill": {"color": "#888888", "enabled": False},
                    "line": {"size": 1, "color": "#000000", "enabled": False},
                    "text": {"color": "#888888", "enabled": False},
                    "circle": {
                        "color": {"type": "ColorCategoricalString", "attribute": "Site Number", "colorPairs":
                                  {"02205522": "#ffe080", "02208130": "#ff0050", "02208150": "#86702d", "02217274": "#90ff00", "02218565": "#c7ff80", "02330450": "#ff00e0", "02334430": "#ffc200", "02334480": "#5f862d", "02334578": "#6f00ff", "02334885": "#ff80ef", "02335000": "#86442d", "02335350": "#ff80a7", "02336000": "#532d86", "02336030": "#862d7b", "02336120": "#862d49", "02336240": "#ffa180", "02336300": "#b780ff", "02336313": "#ff4400", "02336360": "#ffe080", "02336410": "#ff0050", "02336526": "#86702d", "02336728": "#90ff00", "02337170": "#c7ff80", "02397000": "#ff00e0", "02397530": "#ffc200", "02423130": "#5f862d", "02423397": "#6f00ff", "02423496": "#ff80ef", "02455980": "#86442d", "02457595": "#ff80a7", "02458450": "#532d86", "03306000": "#862d7b", "03307000": "#862d49", "03313000": "#ffa180", "03428200": "#b780ff", "03430200": "#ff4400", "03431083": "#ffe080", "03431091": "#ff0050", "03431514": "#86702d", "0351706800": "#90ff00"},
                                  "defaultColor": "#FFFFFF"}, "legend": True, "enabled": True, "selectable": "singleSelect", "selectColor": "#00FFFF"},
                                  "fill-extrusion": {"color": "#888888", "enabled": False}},
                                  "properties": {"availableProperties": {
                                      "Site Number": {
                                          "key": "Site Number", "type": "string", "values":
                                                                                         ["02205522", "02208130", "02208150", "02217274", "02218565", "02330450", "02334430", "02334480", "02334578", "02334885", "02335000", "02335350", "02336000", "02336030", "02336120", "02336240", "02336300", "02336313", "02336360", "02336410", "02336526", "02336728", "02337170", "02397000", "02397530", "02423130", "02423397", "02423496", "02455980", "02457595", "02458450", "03306000", "03307000", "03313000", "03428200", "03430200", "03431083", "03431091", "03431514", "0351706800"], "display": False, "tooltip": False, "description": "", "displayName": "Site Number"}}},
                "vectorFeatureTableGraphs": vectorFeatureTableGraphs,
                "mapLayerFeatureTableGraphs": mapLayerFeatureTableGraphs
            }
        }
    })
    return files


@click.command()
@click.argument('tabular_json', type=click.Path(exists=True))
@click.argument('geojson_file', type=click.Path(exists=True))
@click.option('--save-path', default='stream_context.json', help='Path to save context JSON.')
def main(tabular_json, geojson_file, save_path):
    client = GirderClient(apiUrl='https://data.kitware.com/api/v1')
    authenticate(client)

    # Set up Girder folders
    public_folder = get_public_folder(client)
    stream_folder_id = create_folder(client, public_folder['_id'], 'StreamTemperature')

    # Upload files
    geojson_url = upload_file(client, stream_folder_id, geojson_file)
    tabular_url = upload_file(client, stream_folder_id, tabular_json)

    # Load tabular data
    with open(tabular_json, 'r') as f:
        tabular_data = json.load(f)
        for key in tabular_data.keys():
            base_tab_data = tabular_data[key]
            break
    # Create metadata entries
    graph_style_files = create_graph_metadata(
        tabular_data=base_tab_data,
        geojson_url=geojson_url,
        tabular_url=tabular_url,
    )

    # Build context
    context = {
        "type": "Context",
        "name": "StreamTemperature",
        "default_map_center": [37.5, -95.5],
        "default_map_zoom": 5,
        "datasets": [
            {
                "name": "StreamTemperature Data",
                "category": "stream_temperature",
                "description": "Tabular and geojson stream temperature data",
                "files": graph_style_files
            }
        ]
    }

    # Save context
    with open(save_path, 'w') as f:
        json.dump([context], f, indent=2)

    click.echo(f"Context saved to {save_path}")


if __name__ == '__main__':
    main()
