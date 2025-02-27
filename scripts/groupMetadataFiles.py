import os
import re
import click
import xarray as xr
import geopandas as gpd
import json
import numpy as np
import pandas as pd
from datetime import datetime
import cftime
# Global flag to skip uploading
skip_upload = False

def parse_filename(filename):
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

def generate_model_scenario_ensemble_listing(input_folder, output_folder):
    model_scenario_ensemble_files = {}

    # Process Input files
    for root, _, files in os.walk(input_folder):
        for file in files:
            local_file_path = os.path.join(root, file)
            parsed = parse_filename(file)
            model_scenario_ensemble = f"{parsed['Model']}_{parsed['Scenario']}_{parsed['Ensemble']}"

            if model_scenario_ensemble not in model_scenario_ensemble_files:
                model_scenario_ensemble_files[model_scenario_ensemble] = []
            model_scenario_ensemble_files[model_scenario_ensemble].append(local_file_path)

    # Process Output files
    for root, _, files in os.walk(output_folder):
        for file in files:
            local_file_path = os.path.join(root, file)
            parsed = parse_filename(file)
            model_scenario_ensemble = f"{parsed['Model']}_{parsed['Scenario']}_{parsed['Ensemble']}"

            if model_scenario_ensemble not in model_scenario_ensemble_files:
                model_scenario_ensemble_files[model_scenario_ensemble] = []
            model_scenario_ensemble_files[model_scenario_ensemble].append(local_file_path)

    return model_scenario_ensemble_files

def convert_time(obj, output='compact'):
    if isinstance(obj, str):  # Handle ctime (string)
        dt_obj = datetime.strptime(obj, '%a %b %d %H:%M:%S %Y')
    elif isinstance(obj, np.datetime64):  # Handle datetime64
        dt_obj = pd.Timestamp(obj).to_pydatetime()
    elif isinstance(obj, pd.Timestamp):  # Handle pandas Timestamp explicitly
        dt_obj = obj.to_pydatetime()
    elif isinstance(obj, datetime):  # Handle Python datetime objects
        dt_obj = obj
    elif isinstance(
        obj,
        (
            cftime.DatetimeNoLeap,
            cftime.DatetimeAllLeap,
            cftime.Datetime360Day,
            cftime.DatetimeJulian,
        ),
    ):
        dt_obj = datetime(obj.year, obj.month, obj.day, obj.hour, obj.minute, obj.second)
    elif isinstance(obj, (int, float)):
        if obj > 1e18:  # Assume nanoseconds timestamp
            dt_obj = datetime.fromtimestamp(obj / 1e9)
        elif obj > 1e10:  # Assume milliseconds timestamp
            dt_obj = datetime.fromtimestamp(obj / 1000)
        else:  # Assume seconds timestamp
            dt_obj = datetime.fromtimestamp(obj)
    else:
        return obj  # Return as-is if the type is unrecognized

    if output == 'iso':
        return dt_obj.isoformat()
    elif output == 'datetime':
        return dt_obj
    elif output == 'compact':
        return int(dt_obj.strftime('%Y%m%d%H%M%S'))
    elif output == 'unix':
        return dt_obj.timestamp()

def convert_longitude(lon):
    """
    Converts longitude values from 0-360 to -180 to 180.
    This ensures compatibility with NetCDF data that uses either range.
    """
    lon = np.array(lon)
    lon[lon > 180] -= 360  # If lon > 180, convert it to the -180 to 180 range.
    return lon

def extract_netcdf_data(geojson_file='input.geojson', netcdf_files=['input.nc'], sliding_variable='time', 
                        x_variable='lon', y_variable='lat', output_json='mergednetcdf.json'):
    """Extracts NetCDF data for each feature in the GEOJSON file and merges multiple NetCDF files by time index."""

    # Load GeoJSON
    gdf = gpd.read_file(geojson_file)

    output_data = {}

    for _, feature in gdf.iterrows():
        feature_id = str(feature.get("Plant_Code", feature.get("id", _)))  # Ensure feature_id is a string
        x, y = feature.geometry.centroid.x, feature.geometry.centroid.y
        
        # Convert longitude if necessary (0-360 to -180 to 180)
        x = convert_longitude(x)
        
        # Storage for merged data
        merged_data = {"time": []}
        variable_descriptions = {}
        variable_names = []
        for netcdf_file in netcdf_files:
            ds = xr.open_dataset(netcdf_file)
            
            # Ensure necessary variables exist
            if sliding_variable not in ds or x_variable not in ds or y_variable not in ds:
                raise ValueError(f"One or more specified variables not found in {netcdf_file}.")

            # Find nearest grid cell
            x_idx = np.abs(ds[x_variable] - x).argmin().item()
            y_idx = np.abs(ds[y_variable] - y).argmin().item()
            
            for var in ds.data_vars:
                if sliding_variable in ds[var].dims:
                    df = ds[var].isel({x_variable: x_idx, y_variable: y_idx}).to_pandas()
                    
                    # Check if the variable is a DataFrame
                    if isinstance(df, pd.DataFrame) and sliding_variable in df.columns:
                        # Convert time to UNIX time (seconds) and update the header
                        df[sliding_variable] = df[sliding_variable].apply(lambda t: convert_time(t, 'unix'))
                        df.rename(columns={sliding_variable: 'unix_time'}, inplace=True)
                    elif isinstance(df, pd.Series) and sliding_variable in df.index:
                        # Convert time in Series if present
                        df = df.apply(lambda t: convert_time(t, 'unix'))
                        df.name = 'unix_time'
                    
                    var_name = f"{var}"  # Append filename to differentiate variables
                    variable_names.append(var_name)
                    # Extract description from NetCDF metadata
                    description = ds[var].attrs.get("long_name") or ds[var].attrs.get("standard_name") or "No description available"
                    variable_descriptions[var_name] = description

                    # Merge time index
                    if not merged_data["time"]:
                        merged_data["time"] = sorted(df.index)
                    
                    # Use 'unix_time' as the index for reindexing
                    merged_data[var_name] = df.reindex(merged_data["time"]).dropna().tolist()

        # Convert to structured format
        headers = list(merged_data.keys())
        headers[headers.index("time")] = "unix_time"

        data_obj = {
            "name": f"merged_data_{feature_id}",
            "description": "Merged NetCDF data from multiple sources",
            "type": "_".join(variable_names),
            "header": headers,
            "rows": [list(row) for row in zip(*merged_data.values())]
        }

        # Convert pandas Timestamps to a serializable format
        for row in data_obj["rows"]:
            for idx, value in enumerate(row):
                row[idx] = convert_time(value, 'unix')

        # Generate summary stats
        summary = {}
        for column_name, values in zip(data_obj["header"], zip(*data_obj["rows"])):
            values = np.array(values, dtype=object)
            if isinstance(values[0], (int, float)) or np.issubdtype(values.dtype, np.number) and not np.isnan(values).all():
                summary[column_name] = {
                    "type": "number",
                    "min": float(np.nanmin(values)),
                    "max": float(np.nanmax(values)),
                    "description": variable_descriptions.get(column_name, "No description available")
                }
            else:
                unique_values = set(filter(pd.notna, values))
                summary[column_name] = {
                    "type": "string",
                    "description": variable_descriptions.get(column_name, "No description available")
                }
                if len(unique_values) < 100:
                    summary[column_name]["unique_values"] = list(unique_values)

        data_obj["summary"] = summary
        output_data[feature_id] = [data_obj]

    # Save output to JSON file
    with open(output_json, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Extraction complete. Output saved to {output_json}")

@click.command()
@click.argument('input_folder', type=click.Path(exists=True))
@click.argument('output_folder', type=click.Path(exists=True))
@click.argument('geojson_matcher', default="TVAPowerPlants.geojson", type=click.Path(exists=True))
@click.option('--output-file', default='model_scenario_ensemble_listing.json', help='Output file to save the listing of model, scenario, and ensemble.')
def main(input_folder, output_folder, geojson_matcher, output_file):
    # Generate the listing of Model, Scenario, and Ensemble from input and output folders
    model_scenario_ensemble_files = generate_model_scenario_ensemble_listing(input_folder, output_folder)

    # Save the listing to a JSON file
    with open(output_file, 'w') as f:
        json.dump(model_scenario_ensemble_files, f, indent=4)
    
    total = len(model_scenario_ensemble_files.keys())
    count = 0
    for item in model_scenario_ensemble_files.keys():
        output_name = f'{output_folder}/PowerPlant_{item}_tabular.json'
        print(f'Processing: {item} - {count} of {total}')
        extract_netcdf_data(geojson_matcher, netcdf_files=model_scenario_ensemble_files[item], output_json=output_name)
        count += 1

if __name__ == '__main__':
    main()
