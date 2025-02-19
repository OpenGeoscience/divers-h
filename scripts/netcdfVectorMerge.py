import click
import xarray as xr
import geopandas as gpd
import json
import numpy as np
import pandas as pd
from datetime import datetime
import cftime

def convert_time(obj, output='compact'):
    if isinstance(obj, str):  # Handle ctime (string)
        dt_obj = datetime.strptime(obj, '%a %b %d %H:%M:%S %Y')
    elif isinstance(obj, np.datetime64):  # Handle datetime64
        dt_obj = pd.Timestamp(obj).to_pydatetime()
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
        if obj > 1e10:  # Assume milliseconds timestamp
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

@click.command()
@click.argument('geojson_file', type=click.Path(exists=True))
@click.argument('netcdf_files', nargs=-1, type=click.Path(exists=True))
@click.option('--sliding-variable', default='time', show_default=True, help="The variable representing time or another sliding dimension.")
@click.option('--x-variable', default='lon', show_default=True, help="The variable representing longitude.")
@click.option('--y-variable', default='lat', show_default=True, help="The variable representing latitude.")
@click.option('--output-json', default='mergednetcdf.json', show_default=True, help="Output JSON file name.")
def extract_netcdf_data(geojson_file, netcdf_files, sliding_variable, x_variable, y_variable, output_json):
    """Extracts NetCDF data for each feature in the GEOJSON file and merges multiple NetCDF files by time index."""

    # Load GeoJSON
    gdf = gpd.read_file(geojson_file)

    output_data = {}

    for _, feature in gdf.iterrows():
        feature_id = str(feature.get("Plant_Code", feature.get("id", _)))  # Ensure feature_id is a string
        x, y = feature.geometry.centroid.x, feature.geometry.centroid.y
        
        # Storage for merged data
        merged_data = {"time": []}
        variable_descriptions = {}

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
                    
                    var_name = f"{var}_{netcdf_file.split('/')[-1]}"  # Append filename to differentiate variables
                    
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
            "type": f"{sliding_variable}_{netcdf_file}",
            "header": headers,
            "rows": [list(row) for row in zip(*merged_data.values())]
        }

        # Convert pandas Timestamps to a serializable format
        for row in data_obj["rows"]:
            for idx, value in enumerate(row):
                if isinstance(value, pd.Timestamp):
                    row[idx] = value.timestamp()  # Convert to UNIX timestamp if it's a Timestamp

        # Generate summary stats
        summary = {}
        for column_name, values in zip(data_obj["header"], zip(*data_obj["rows"])):
            values = np.array(values, dtype=object)
            if np.issubdtype(values.dtype, np.number) and not np.isnan(values).all():
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
    
    click.echo(f"Extraction complete. Output saved to {output_json}")

if __name__ == '__main__':
    extract_netcdf_data()
