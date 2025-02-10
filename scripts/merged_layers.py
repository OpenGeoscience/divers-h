import click
import geopandas as gpd
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.argument('geojson_file1', type=click.Path(exists=True))
@click.argument('geojson_files', type=click.Path(exists=True), nargs=-1)  # Accept multiple secondary files
@click.argument('output_file', type=click.Path())
@click.option('--flatten', default=True, is_flag=True, help="Flatten the properties of the intersecting features into a single string.")
@click.option('--use_first_value', default=False, is_flag=True, help="Only take the first intersecting value for each property (do not flatten).")
def intersect_geojson(geojson_file1, geojson_files, output_file, flatten, use_first_value):
    """
    A script to find all intersecting features from a primary GeoJSON file and a list of secondary GeoJSON files.
    Each feature from the primary GeoJSON is converted into a GeoJSON feature,
    and properties from the intersecting features in the secondary GeoJSON files are added into a 'merged_properties' field as a comma-separated string.
    Only features with intersections are included in the output.
    The properties from the secondary files are excluded from the root 'properties' and moved into 'merged_properties' as a joined string.
    """
    # Load the primary GeoJSON file using GeoPandas
    logger.info(f"Loading primary GeoJSON file: {geojson_file1}")
    gdf1 = gpd.read_file(geojson_file1)

    # Prepare a list to hold the resulting features
    output_features = []

    # Loop through each secondary GeoJSON file
    for geojson_file2 in geojson_files:
        logger.info(f"Loading secondary GeoJSON file: {geojson_file2}")
        gdf2 = gpd.read_file(geojson_file2)

        # Ensure both datasets use the same coordinate reference system (CRS)
        if gdf1.crs != gdf2.crs:
            logger.info(f"CRS mismatch with {geojson_file2}, reprojecting.")
            gdf2 = gdf2.to_crs(gdf1.crs)

        # For each feature in the first GeoDataFrame, find intersecting features from the second GeoDataFrame
        logger.info(f"Calculating intersects with {geojson_file2}...")
        for _, row1 in gdf1.iterrows():
            # Find features in gdf2 that intersect the current feature from gdf1
            intersecting_features = gdf2[gdf2.geometry.intersects(row1['geometry'])]

            # Only proceed if there are intersecting features
            if not intersecting_features.empty:
                # Prepare the properties dictionary (include all original properties from gdf1)
                feature_properties = row1.drop('geometry')
                for _, row_dict in intersecting_features.iterrows():
                    for item in row_dict.to_dict().keys():
                        if feature_properties.get(item):
                            feature_properties = feature_properties.drop(item)
                feature_properties = feature_properties.to_dict()

                # Prepare 'merged_properties' and join intersecting feature properties as a comma-separated string
                merged_properties = []
                for _, row2 in intersecting_features.iterrows():
                    merged_properties.append(row2.drop('geometry').to_dict())

                if flatten and not use_first_value:
                    new_vals = {}
                    for i, prop in enumerate(merged_properties):
                        for key, value in prop.items():
                            if f'intersecting_{key}' not in new_vals:
                                new_vals[f'intersecting_{key}'] = []
                            new_vals[f'intersecting_{key}'].append(value)
                    for key, value in new_vals.items():
                        str_vals = [str(item) for item in value]
                        feature_properties[key] = ', '.join(str_vals)
                elif use_first_value:
                    # If use_first_value is True, only take the first value for each intersecting property
                    for prop in merged_properties:
                        for key, value in prop.items():
                            if f'intersecting_{key}' not in feature_properties:
                                feature_properties[f'intersecting_{key}'] = value
                    # No need to flatten or join as the first value is taken for each property

                else:
                    feature_properties['merged_properties'] = merged_properties

                # Convert the feature to a GeoJSON feature
                feature_geojson = {
                    'type': 'Feature',
                    'geometry': row1['geometry'].__geo_interface__,  # Convert geometry to GeoJSON format
                    'properties': feature_properties  # Add properties to the GeoJSON feature
                }

                # Append the feature to the output list
                output_features.append(feature_geojson)

    # Save the output features as a new GeoJSON file
    logger.info(f"Saving the result to {output_file}")
    with open(output_file, 'w') as f:
        geojson = {"type": "FeatureCollection", "features": output_features}
        json.dump(geojson, f)

    logger.info("Processing complete.")

if __name__ == '__main__':
    intersect_geojson()
