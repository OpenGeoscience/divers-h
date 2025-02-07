import os

import requests

from IPython.display import display



# Configuration

output_dir = "/work/sds-lab/Puja/P-E/"



# Base URL pattern

base_url = "https://esgf-data1.llnl.gov/thredds/fileServer/css03_data/CMIP6/ScenarioMIP/NCAR/CESM2/ssp{scenario}/r11i1p1f1/Amon/{variable}/gn/v20200528/{variable}_Amon_CESM2_ssp{scenario}_r11i1p1f1_gn_201501-206412.nc"





variables = ["tas", "pr", "evspsbl"]

scenarios = ["585", "245", "126"]



# Function to download file

def download_file(url, output_path):

    try:

        response = requests.get(url, stream=True)

        response.raise_for_status()



        with open(output_path, 'wb') as f:

            for chunk in response.iter_content(chunk_size=8192):

                f.write(chunk)



        display(f"Downloaded: {output_path}")

    except Exception as e:

        display(f"Failed to download {url}: {e}")



# Loop through all combinations

for variable in variables:

    for scenario in scenarios:

        # Construct URL and output file path

        file_url = base_url.format(scenario=scenario, variable=variable)

        file_name = f"{variable}_Amon_CESM2_ssp{scenario}_r11i1p1f1_gn_201501-206412.nc"

        output_path = os.path.join(output_dir, file_name)



        # Download the file

        download_file(file_url, output_path)

import os

import requests

from IPython.display import display



# Configuration

output_dir = "/work/sds-lab/Puja/P-E/"



# Base URL pattern

base_url = "https://esgf-data1.llnl.gov/thredds/fileServer/css03_data/CMIP6/ScenarioMIP/NCAR/CESM2/ssp{scenario}/r10i1p1f1/Amon/{variable}/gn/v20200528/{variable}_Amon_CESM2_ssp{scenario}_r10i1p1f1_gn_201501-206412.nc"





variables = ["tas", "pr", "evspsbl"]

scenarios = ["585", "245", "126"]



# Function to download file

def download_file(url, output_path):

    try:

        response = requests.get(url, stream=True)

        response.raise_for_status()



        with open(output_path, 'wb') as f:

            for chunk in response.iter_content(chunk_size=8192):

                f.write(chunk)



        display(f"Downloaded: {output_path}")

    except Exception as e:

        display(f"Failed to download {url}: {e}")



# Loop through all combinations

for variable in variables:

    for scenario in scenarios:

        # Construct URL and output file path

        file_url = base_url.format(scenario=scenario, variable=variable)

        file_name = f"{variable}_Amon_CESM2_ssp{scenario}_r10i1p1f1_gn_201501-206412.nc"

        output_path = os.path.join(output_dir, file_name)



        # Download the file

        download_file(file_url, output_path)

import os

import requests

from IPython.display import display



# Configuration

output_dir = "/work/sds-lab/Puja/P-E/"



# Base URL pattern

base_url = "https://esgf-data1.llnl.gov/thredds/fileServer/css03_data/CMIP6/ScenarioMIP/NCAR/CESM2/ssp{scenario}/r4i1p1f1/Amon/{variable}/gn/v20200528/{variable}_Amon_CESM2_ssp{scenario}_r4i1p1f1_gn_201501-206412.nc"



variables = ["tas", "pr", "evspsbl"]

scenarios = ["585", "245", "126"]



# Function to download file

def download_file(url, output_path):

    try:

        response = requests.get(url, stream=True)

        response.raise_for_status()



        with open(output_path, 'wb') as f:

            for chunk in response.iter_content(chunk_size=8192):

                f.write(chunk)



        display(f"Downloaded: {output_path}")

    except Exception as e:

        display(f"Failed to download {url}: {e}")



# Loop through all combinations

for variable in variables:

    for scenario in scenarios:

        # Construct URL and output file path

        file_url = base_url.format(scenario=scenario, variable=variable)

        file_name = f"{variable}_Amon_CESM2_ssp{scenario}_r4i1p1f1_gn_201501-206412.nc"

        output_path = os.path.join(output_dir, file_name)



        # Download the file

        download_file(file_url, output_path)

import os

import requests

from IPython.display import display



# Configuration

output_dir = "/work/sds-lab/Puja/P-E/"



base_url = "https://aims3.llnl.gov/thredds/fileServer/css03_data/CMIP6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp{scenario}/r4i1p1f2/Amon/{variable}/gr/v20190410/{variable}_Amon_CNRM-CM6-1_ssp{scenario}_r4i1p1f2_gr_201501-210012.nc"



variables = ["tas", "pr", "evspsbl"]

scenarios = ["126", "245", "585"]



# Function to download file

def download_file(url, output_path):

    try:

        response = requests.get(url, stream=True)

        response.raise_for_status()



        with open(output_path, 'wb') as f:

            for chunk in response.iter_content(chunk_size=8192):

                f.write(chunk)



        display(f"Downloaded: {output_path}")

    except Exception as e:

        display(f"Failed to download {url}: {e}")



# Loop through all combinations

for variable in variables:

    for scenario in scenarios:

        # Construct URL and output file path

        file_url = base_url.format(scenario=scenario, variable=variable)

        file_name = f"{variable}_Amon_CNRM-CM6-1_ssp{scenario}_r4i1p1f2_gr_201501-210012.nc"

        output_path = os.path.join(output_dir, file_name)



        # Download the file

        download_file(file_url, output_path)

import os

import requests

from IPython.display import display



# Configuration

output_dir = "/work/sds-lab/Puja/P-E/"



base_url = "https://aims3.llnl.gov/thredds/fileServer/css03_data/CMIP6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp{scenario}/r5i1p1f2/Amon/{variable}/gr/v20190410/{variable}_Amon_CNRM-CM6-1_ssp{scenario}_r5i1p1f2_gr_201501-210012.nc"



variables = ["tas", "pr", "evspsbl"]

scenarios = ["126", "245", "585"]



# Function to download file

def download_file(url, output_path):

    try:

        response = requests.get(url, stream=True)

        response.raise_for_status()



        with open(output_path, 'wb') as f:

            for chunk in response.iter_content(chunk_size=8192):

                f.write(chunk)



        display(f"Downloaded: {output_path}")

    except Exception as e:

        display(f"Failed to download {url}: {e}")



# Loop through all combinations

for variable in variables:

    for scenario in scenarios:

        # Construct URL and output file path

        file_url = base_url.format(scenario=scenario, variable=variable)

        file_name = f"{variable}_Amon_CNRM-CM6-1_ssp{scenario}_r5i1p1f2_gr_201501-210012.nc"

        output_path = os.path.join(output_dir, file_name)



        # Download the file

        download_file(file_url, output_path)

import os

import requests

from IPython.display import display



# Configuration

output_dir = "/work/sds-lab/Puja/P-E/"



ase_url = "https://aims3.llnl.gov/thredds/fileServer/css03_data/CMIP6/ScenarioMIP/CNRM-CERFACS/CNRM-CM6-1/ssp{scenario}/r6i1p1f2/Amon/{variable}/gr/v20190410/{variable}_Amon_CNRM-CM6-1_ssp{scenario}_r6i1p1f2_gr_201501-210012.nc"



variables = ["tas", "pr", "evspsbl"]

scenarios = ["126", "245", "585"]



# Function to download file

def download_file(url, output_path):

    try:

        response = requests.get(url, stream=True)

        response.raise_for_status()



        with open(output_path, 'wb') as f:

            for chunk in response.iter_content(chunk_size=8192):

                f.write(chunk)



        display(f"Downloaded: {output_path}")

    except Exception as e:

        display(f"Failed to download {url}: {e}")



# Loop through all combinations

for variable in variables:

    for scenario in scenarios:

        # Construct URL and output file path

        file_url = base_url.format(scenario=scenario, variable=variable)

        file_name = f"{variable}_Amon_CNRM-CM6-1_ssp{scenario}_r6i1p1f2_gr_201501-210012.nc"

        output_path = os.path.join(output_dir, file_name)



        # Download the file

        download_file(file_url, output_path)



