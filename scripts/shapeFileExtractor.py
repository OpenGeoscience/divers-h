import click
import zipfile
import tempfile
from collections import defaultdict
from pathlib import Path
import shapefile
import geopandas 
import logging
import os

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_zip_to_geojson(zip_file_path, output_dir):
    """Process a ZIP file containing shapefiles and save GeoJSON files to output_dir."""
    if not zipfile.is_zipfile(zip_file_path):
        logger.error(f"{zip_file_path} is not a valid ZIP file.")
        return

    with zipfile.ZipFile(zip_file_path) as zip_archive:
        filenames = zip_archive.namelist()

        shapefile_exts = ['.shp', '.shx', '.dbf', '.prj']
        shapefile_groups = defaultdict(list)
        for filename in filenames:
            base_name = Path(filename).stem
            for ext in shapefile_exts:
                if ext in filename:
                    shapefile_groups[base_name].append(filename)
        # Process each shapefile group
        for base_name, files in shapefile_groups.items():
            shp_file = next((f for f in files if f.endswith('.shp')), None)
            dbf_file = next((f for f in files if f.endswith('.dbf')), None)
            prj_file = next((f for f in files if f.endswith('.prj')), None)

            if not shp_file:
                logger.warning(f'Shapefile {base_name}.shp not found, skipping.')
                continue
            if not dbf_file:
                logger.warning(f'DBF file {base_name}.dbf is missing, skipping.')
                continue
            # Create file-like options that can be read
            shp_data = zip_archive.open(shp_file)
            dbf_data = zip_archive.open(dbf_file)
            if prj_file:
                prj_data = zip_archive.open(prj_file)
            sf = shapefile.Reader(shp=shp_data, dbf=dbf_data)
            features = sf.__geo_interface__['features']

            # Extract geometry and properties
            geometries = [
                feature['geometry'] for feature in features if feature['geometry']
            ]

            if not geometries:
                logger.warning(f'Shapefile {base_name}.shp has no valid geometries, skipping.')
                continue

            # Create GeoDataFrame
            features = sf.__geo_interface__['features']
            geodata = geopandas.GeoDataFrame.from_features(features)
            if prj_data:
                source_projection = prj_data.read().decode('utf-8')
                geodata = geodata.set_crs(source_projection, allow_override=True)

            # Convert to WGS84
            geodata = geodata.to_crs(4326)

            # Write to GeoJSON
            output_path = Path(output_dir, f"{base_name}.geojson")
            geodata.to_file(output_path, driver='GeoJSON')
            logger.info(f"Saved GeoJSON: {output_path}")
            shp_data.close()
            dbf_data.close()
            if prj_data:
                prj_data.close()


@click.command()
@click.argument('zip_file', type=click.Path(exists=True, dir_okay=False))
@click.option(
    '--output-dir', 
    type=click.Path(file_okay=False, writable=True), 
    default='./output', 
    help='Directory to save GeoJSON files (default: ./output)'
)
def main(zip_file, output_dir):
    """
    Process a ZIP_FILE containing shapefiles and save GeoJSON files to OUTPUT_DIR.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    process_zip_to_geojson(zip_file, output_dir)

if __name__ == "__main__":
    main()
