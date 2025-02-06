import os
from pathlib import Path
from subprocess import CalledProcessError, run
import sys
import tempfile

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from uvdat.core.models import FileItem

from .map_layers import create_raster_map_layer_from_file


class GridInterpolationParams:
    def __init__(
        self,
        csv_file: str,
        lon_field: str = 'lon',
        lat_field: str = 'lat',
        gradient_field: str = 'slope',  # Default 'slope'
        power: float = 2.0,
        smoothing: float = 0.3,
        output_size: tuple = (2000, 2000),
        nodata_value: float = -9999,
    ):
        self.csv_file = csv_file
        self.lon_field = lon_field
        self.lat_field = lat_field
        self.gradient_field = gradient_field  # Field representing terrain gradient
        self.power = power
        self.smoothing = smoothing
        self.output_size = output_size
        self.nodata_value = nodata_value


def csv_to_tif(file_item: FileItem, params: GridInterpolationParams, style_options=None):
    try:
        # Load the CSV file into a Pandas DataFrame
        if not os.path.exists(params.csv_file):
            print(f'Error: CSV file "{params.csv_file}" not found.', file=sys.stderr)
            return

        df = pd.read_csv(params.csv_file)

        # Check if necessary columns exist
        required_columns = [
            params.lon_field,
            params.lat_field,
            params.gradient_field,
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            print(
                f'Error: Missing columns in the CSV file: {", ".join(missing_columns)}',
                file=sys.stderr,
            )
            return

        # Filter out invalid values based on some threshold (example < 1e9)
        df = df[(df[params.gradient_field] < 1e9)]

        # Replace known invalid values with NaN
        df[params.gradient_field] = df[params.gradient_field].replace([2147483647], np.nan)

        # Check for empty dataframe after filtering
        if df.empty:
            print('Error: No valid data available after filtering invalid values.', file=sys.stderr)
            return

        # Create geometry using lon/lat
        geometry = [Point(xy) for xy in zip(df[params.lon_field], df[params.lat_field])]

        # Create a GeoDataFrame from the DataFrame
        gdf = gpd.GeoDataFrame(df, geometry=geometry)

        # Set the CRS (WGS84)
        gdf.set_crs(epsg=4326, inplace=True)

        # Create a temporary directory for the intermediate shapefile
        with tempfile.TemporaryDirectory() as tmpdirname:
            tmp_shp_path = os.path.join(tmpdirname, 'temp_shapefile.shp')

            # Save the temporary shapefile
            gdf.to_file(tmp_shp_path)

            # Construct the GDAL command using the temporary shapefile
            output_tif = os.path.join(tmpdirname, 'temp_output.tif')
            gdal_command = [
                'gdal_grid',
                '-zfield',
                params.gradient_field,  # The field to interpolate
                '-a',
                f'invdist:power={params.power}:smoothing={params.smoothing}:nodata={params.nodata_value}',
                '-of',
                'GTiff',  # Output format
                '-ot',
                'Float64',  # Data type
                '-outsize',
                str(params.output_size[0]),
                str(params.output_size[1]),  # Output size
                tmp_shp_path,  # Input shapefile
                output_tif,  # Output GeoTIFF file
            ]

            # Execute the GDAL command
            try:
                run(gdal_command, check=True)
            except CalledProcessError as e:
                print(f'Error during GDAL processing: {e}', file=sys.stderr)
                return
            print(f'GeoTIFF successfully saved to {output_tif}')

            new_map_layer = create_raster_map_layer_from_file(
                file_item, output_tif, style_options, name=f'{file_item.name} Heatmap Raster'
            )
            return new_map_layer

    except Exception as e:
        print(f'An unexpected error occurred: {e}', file=sys.stderr)


def process_file_item_to_heatmap(file_item: FileItem, style_options=None):
    if not file_item.metadata:
        raise ValueError(
            'CSV file does not have metadata to describe its params for csv_to_heatmap conversion'
        )
    metadata_params = file_item.metadata.get('params', {})

    with tempfile.TemporaryDirectory() as temp_dir:
        csv_path = Path(temp_dir, 'csv.csv')
        with open(csv_path, 'wb') as csv_file:
            content = file_item.file.open().read()
            csv_file.write(content)
        params = GridInterpolationParams(csv_file=csv_path, **metadata_params)
        return csv_to_tif(file_item, params, style_options)
