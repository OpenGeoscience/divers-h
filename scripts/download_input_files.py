import os
import requests
import click
import xarray as xr
import numpy as np

# Configuration
default_output_dir = "./outputs"
conus_dir = os.path.join(default_output_dir, "CONUS")

# Base URL patterns and filenames
base_urls = [
    {
        "url": "https://esgf-data1.llnl.gov/thredds/fileServer/css03_data/CMIP6/ScenarioMIP/NCAR/CESM2/ssp{scenario}/r11i1p1f1/Amon/{variable}/gn/v20200528/{variable}_Amon_CESM2_ssp{scenario}_r11i1p1f1_gn_201501-206412.nc",
        "filename": "{variable}_Amon_CESM2_ssp{scenario}_r11i1p1f1_gn_201501-206412.nc",
    },
    {
        "url": "https://esgf-data1.llnl.gov/thredds/fileServer/css03_data/CMIP6/ScenarioMIP/NCAR/CESM2/ssp{scenario}/r10i1p1f1/Amon/{variable}/gn/v20200528/{variable}_Amon_CESM2_ssp{scenario}_r10i1p1f1_gn_201501-206412.nc",
        "filename": "{variable}_Amon_CESM2_ssp{scenario}_r10i1p1f1_gn_201501-206412.nc",
    },
    {
        "url": "https://esgf-data1.llnl.gov/thredds/fileServer/css03_data/CMIP6/ScenarioMIP/NCAR/CESM2/ssp{scenario}/r4i1p1f1/Amon/{variable}/gn/v20200528/{variable}_Amon_CESM2_ssp{scenario}_r4i1p1f1_gn_201501-206412.nc",
        "filename": "{variable}_Amon_CESM2_ssp{scenario}_r4i1p1f1_gn_201501-206412.nc",
    },
    {
        "url": "https://aims3.llnl.gov/thredds/fileServer/css03_data/CMIP6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp{scenario}/r4i1p1f2/Amon/{variable}/gr/v20190410/{variable}_Amon_CNRM-CM6-1_ssp{scenario}_r4i1p1f2_gr_201501-210012.nc",
        "filename": "{variable}_Amon_CNRM-CM6-1_ssp{scenario}_r4i1p1f2_gr_201501-210012.nc",
    },
    {
        "url": "https://aims3.llnl.gov/thredds/fileServer/css03_data/CMIP6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp{scenario}/r6i1p1f2/Amon/{variable}/gr/v20190410/{variable}_Amon_CNRM-CM6-1_ssp{scenario}_r6i1p1f2_gr_201501-210012.nc",
        "filename": "{variable}_Amon_CNRM-CM6-1_ssp{scenario}_r6i1p1f2_gr_201501-210012.nc",
    },
]

variables = ["tas", "pr", "evspsbl"]
scenarios = ["585", "245", "126"]

def download_file(url, output_path):
    """Download a file if it does not exist."""
    if os.path.exists(output_path):
        print(f"File already exists: {output_path}, skipping download.")
        return True

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                    print(f"Downloading {output_path} - {progress:.2f}% completed", end='\r')

        print(f"\nDownloaded: {output_path}")
        return True
    except Exception as e:
        print(f"\nFailed to download {url}: {e}")
        return False

def process_conus(nc_path):
    """Clip the netCDF data to a rectangle around the Continental U.S."""
    if not os.path.exists(conus_dir):
        os.makedirs(conus_dir, exist_ok=True)

    output_conus_path = os.path.join(conus_dir, os.path.basename(nc_path))
    if os.path.exists(output_conus_path):
        print(f"CONUS-processed file already exists: {output_conus_path}, skipping.")
        return

    ds = xr.open_dataset(nc_path)

    # Identify first variable with 'time', 'lat', and 'lon'
    target_var = None
    for var in ds.data_vars:
        dims = ds[var].dims
        if all(dim in dims for dim in ['time', 'lat', 'lon']):
            target_var = var
            break

    if not target_var:
        print(f"Skipping {nc_path}, no valid variable found.")
        return

    # Convert longitude from [0, 360] to [-180, 180]
    ds = ds.assign_coords(lon=((ds.lon + 180) % 360) - 180)
    ds = ds.sortby(ds.lon)

    # Define CONUS bounds (approximate)
    lat_min, lat_max = 20, 50
    lon_min, lon_max = -130, -65
    ds.sortby(ds.lat, True)
    # Subset dataset for just the target variable
    ds_conus = ds[target_var].sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

    # Save to new netCDF file
    ds_conus.to_netcdf(output_conus_path)
    print(f"Processed CONUS file saved: {output_conus_path}")



@click.command()
@click.option('--output_dir', default=default_output_dir, help='Directory to save downloaded files')
def download_data(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    file_list = [(entry, variable, scenario) for entry in base_urls for variable in variables for scenario in scenarios]

    for entry, variable, scenario in file_list:
        file_url = entry["url"].format(scenario=scenario, variable=variable)
        file_name = entry["filename"].format(scenario=scenario, variable=variable)
        output_path = os.path.join(output_dir, file_name)

        if download_file(file_url, output_path):
            process_conus(output_path)

if __name__ == '__main__':
    download_data()
