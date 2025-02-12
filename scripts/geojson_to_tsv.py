import click
import geopandas as gpd
import csv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.argument('geojson_file', type=click.Path(exists=True))
@click.argument('output_tsv_file', type=click.Path())
def geojson_to_tsv(geojson_file, output_tsv_file):
    """
    A script to convert a GeoJSON file into a TSV (Tab-Separated Values) file.
    Each feature in the GeoJSON becomes a row in the TSV, 
    with the feature properties as columns.
    """
    # Load GeoJSON file using GeoPandas
    logger.info(f"Loading GeoJSON file: {geojson_file}")
    gdf = gpd.read_file(geojson_file)

    # Prepare the data for TSV (excluding geometry)
    logger.info("Preparing the data for TSV conversion...")
    data = gdf.drop(columns='geometry')  # Drop geometry to focus on properties

    # Open the output TSV file and write the data
    logger.info(f"Saving the result to {output_tsv_file}")
    with open(output_tsv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data.columns, delimiter='\t')  # Set delimiter to tab
        writer.writeheader()  # Write the header row (columns)
        
        # Write each row as a dictionary
        for _, row in data.iterrows():
            writer.writerow(row.to_dict())

    logger.info("Processing complete.")

if __name__ == '__main__':
    geojson_to_tsv()
