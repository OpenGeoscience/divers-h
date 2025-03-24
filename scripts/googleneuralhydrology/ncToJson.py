import click
import xarray as xr
import json
import numpy as np
import os
import pandas as pd

def summarize_data(ds, diff_values, percentage_off):
    """Generate a summary of the dataset with min/max values for numerical variables."""
    summary = {}

    for var in ds.data_vars:
        data = ds[var].values.flatten()  # Convert to 1D array
        if np.issubdtype(data.dtype, np.number):  # Check if it's numeric
            summary[var] = {
                "type": "number",
                "min": np.nanmin(data).item() if np.any(~np.isnan(data)) else None,
                "max": np.nanmax(data).item() if np.any(~np.isnan(data)) else None
            }

    # Add the new computed values to the summary
    summary["Obs - Sim"] = {
        "type": "number",
        "min": np.nanmin(diff_values).item() if np.any(~np.isnan(diff_values)) else None,
        "max": np.nanmax(diff_values).item() if np.any(~np.isnan(diff_values)) else None
    }

    summary["Percentage Off"] = {
        "type": "number",
        "min": np.nanmin(percentage_off).item() if np.any(~np.isnan(percentage_off)) else None,
        "max": np.nanmax(percentage_off).item() if np.any(~np.isnan(percentage_off)) else None
    }

    summary["columns"] = list(ds.data_vars.keys()) + ["Obs - Sim", "Percentage Off"]

    if 'date' in ds:
        time_values = ds['date'].values
        start_time = pd.to_datetime(time_values.min())
        end_time = pd.to_datetime(time_values.max())
        unique_dates = np.unique(time_values)

        summary["time"] = {
            "type": "string",
            "start": start_time.strftime("%Y-%m-%d"),
            "end": end_time.strftime("%Y-%m-%d"),
            "value_count": len(unique_dates)
        }
        
        # Convert to Unix time (seconds since the Unix epoch)
        summary["unix_time"] = {
            "type": "number",
            "min": start_time.value // 10**9,  # Convert to seconds
            "max": end_time.value // 10**9,     # Convert to seconds
            "value_count": len(unique_dates)
        }

    return summary

def convert_netcdf_to_json(nc_file):
    """Load NetCDF file and convert it to JSON format."""
    ds = xr.open_dataset(nc_file, engine="netcdf4")  # Open NetCDF file

    # Extract key variables
    time = ds["date"].values  # Extract dates
    obs_values = ds["QObs(mm/d)_obs"].values.flatten()
    sim_values = ds["QObs(mm/d)_sim"].values.flatten()

    # Compute differences and percentage differences
    diff_values = obs_values - sim_values
    percentage_off = np.where(obs_values != 0, (diff_values / obs_values) * 100, np.nan)  # Avoid division by zero

    # Format time correctly and convert to UNIX time
    if "units" in ds["date"].attrs and "since" in ds["date"].attrs["units"]:
        time_origin = ds["date"].attrs["units"].split("since")[1].strip()
        time = pd.to_datetime(time, origin=time_origin, unit="D")
    else:
        time = pd.to_datetime(time)

    # Convert time to UNIX time
    unix_time = time.astype(int) // 10**9  # Convert to seconds

    # Format time as strings
    time_str = time.strftime("%Y-%m-%d").tolist()

    # Construct rows with the new columns
    rows = [
        [time_str[i], int(unix_time[i]), float(obs_values[i]), float(sim_values[i]), float(diff_values[i]), float(percentage_off[i])]
        for i in range(len(time))
    ]

    # Generate summary including new values
    summary = summarize_data(ds, diff_values, percentage_off)

    # Construct final JSON output
    output_json = {
        "summary": summary,
        "rows": rows
    }

    return output_json

def process_folder(folder_path):
    """Process all .nc files in a folder and generate a combined JSON object."""
    json_output = {}

    # Loop through all .nc files in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith(".nc"):
            base_filename = os.path.splitext(filename)[0]  # Get base filename without extension
            nc_file = os.path.join(folder_path, filename)

            # Convert NetCDF to JSON format
            json_data = convert_netcdf_to_json(nc_file)

            # Create the structure for each file
            json_output[base_filename] = [{
                "name": f"{base_filename}_daily",
                "description": "This is a table of the daily values",
                "type": f"GoogleNeuralHydrology",
                "summary": {
                    "time": json_data["summary"].get("time", {}),
                    "unix_time": json_data["summary"].get("unix_time", {}),
                    "QObs(mm/d)_obs": json_data["summary"].get("QObs(mm/d)_obs", {}),
                    "QObs(mm/d)_sim": json_data["summary"].get("QObs(mm/d)_sim", {}),
                    "Obs - Sim": json_data["summary"].get("Obs - Sim", {}),
                    "Percentage Off": json_data["summary"].get("Percentage Off", {}),
                },
                "header": ["time", "unix_time", "QObs(mm/d)_obs", "QObs(mm/d)_sim", "Obs - Sim", "Percentage Off"],
                "rows": json_data["rows"]
            }]

    return json_output

@click.command()
@click.argument("folder", type=click.Path(exists=True))
@click.argument("output", default='ncToJSONOutput.json')
def convert_netcdf(folder, output):
    """CLI tool to convert a NetCDF (.nc) file to JSON format."""
    json_data = process_folder(folder)

    # Save JSON
    with open(output, "w") as json_file:
        json.dump(json_data, json_file, indent=4)

    click.echo(f"Converted {folder} to {output}")

if __name__ == "__main__":
    convert_netcdf()
