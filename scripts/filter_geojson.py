import click
import geopandas as gpd
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.argument('geojson_file1', type=click.Path(exists=True))
@click.argument('geojson_file2', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
def filter_intersections(geojson_file1, geojson_file2, output_file):
    """
    A script to filter features from the first GeoJSON file that intersect with features
    from the second GeoJSON file and save the filtered features into a new GeoJSON file.
    """
    # Load the GeoJSON files using GeoPandas
    logger.info(f"Loading GeoJSON files: {geojson_file1}, {geojson_file2}")
    gdf1 = gpd.read_file(geojson_file1)
    gdf2 = gpd.read_file(geojson_file2)

    # Ensure both datasets use the same coordinate reference system (CRS)
    if gdf1.crs != gdf2.crs:
        logger.info("CRS mismatch, reprojecting GeoJSON 2 to match GeoJSON 1.")
        gdf2 = gdf2.to_crs(gdf1.crs)

    # Prepare a list to store the intersecting features
    logger.info("Finding intersecting features...")
    filtered_features = []

    # Loop through each feature in the first GeoDataFrame
    for _, row1 in gdf1.iterrows():
        # Check if the feature from gdf1 intersects with any feature from gdf2
        intersecting_features = gdf2[gdf2.geometry.intersects(row1['geometry'])]

        # If any intersection exists, add the feature to the filtered list
        if not intersecting_features.empty:
            # Convert the feature to GeoJSON format (including geometry)
            feature_geojson = {
                'type': 'Feature',
                'geometry': row1['geometry'].__geo_interface__,
                'properties': row1.drop('geometry').to_dict()
            }
            filtered_features.append(feature_geojson)

    # Save the filtered features to a new GeoJSON file
    logger.info(f"Saving filtered features to {output_file}")
    with open(output_file, 'w') as f:
        geojson = {"type": "FeatureCollection", "features": filtered_features}
        json.dump(geojson, f)

    logger.info("Filtering complete.")

if __name__ == '__main__':
    filter_intersections()
