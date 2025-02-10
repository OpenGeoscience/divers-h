import logging
import geopandas as gpd
import pandas as pd
from celery import shared_task
from uvdat.core.models import VectorMapLayer, Dataset, FileItem
import json
from typing import List, Optional, Literal
from django.core.files.base import ContentFile

# Configure logging
logger = logging.getLogger(__name__)

def save_geojson_to_dataset(dataset_name: str, geojson_data: dict):
    dataset, _ = Dataset.objects.get_or_create(name=dataset_name, defaults={'category': 'generated'})
    geojson_content = json.dumps(geojson_data, indent=2)
    file_item = FileItem.objects.create(
        name=f'{dataset_name}.geojson',
        dataset=dataset,
        file_type='geojson',
        file_size=len(geojson_content.encode('utf-8')),
    )
    file_item.file.save(f'{dataset_name}.geojson', ContentFile(geojson_content.encode()), save=True)
    return file_item

@shared_task
def merge_vector_layer_data(
    base_layer_id: int,
    other_layer_ids: List[int],
    dataset_name: str,
    operation: Literal['intersection', 'contains'] = 'intersection',
    exclude_non_overlapping: bool = True,
    properties_to_merge: Optional[List[str]] = None,
    flatten: bool = True,  # Default to flattening
    use_first_value: bool = False  # first value from merged properties
) -> dict:
    logger.info(f'Starting merge_vector_layer_data task for base_layer_id: {base_layer_id}')

    try:
        # Load the base layer GeoDataFrame
        base_layer = VectorMapLayer.objects.get(id=base_layer_id)
        base_gdf = gpd.GeoDataFrame.from_features(base_layer.read_geojson_data().get('features', []))

        # Load the secondary layers and store their properties
        other_gdfs = []
        for layer_id in other_layer_ids:
            layer = VectorMapLayer.objects.get(id=layer_id)
            layer_gdf = gpd.GeoDataFrame.from_features(layer.read_geojson_data().get('features', []))
            other_gdfs.append(layer_gdf)

        if not other_gdfs:
            logger.warning('No valid other layers found. Skipping merge.')
            return {'status': 'error', 'message': 'No valid other layers provided.'}

        # Merge all secondary layers into a single GeoDataFrame
        other_gdf = pd.concat(other_gdfs, ignore_index=True)

        # Ensure both layers use the same CRS
        if base_gdf.crs != other_gdf.crs:
            logger.info('Reprojecting other layers to match base layer CRS...')
            other_gdf = other_gdf.to_crs(base_gdf.crs)

        # Prepare list to collect the merged features
        output_features = []

        # Loop through each feature in the base layer
        logger.info(f"Processing {len(base_gdf)} features from the base layer.")
        for _, base_row in base_gdf.iterrows():
            # Find features in the other layers that intersect or completely overlap the current base layer feature
            intersecting_features = []
            for _, other_row in other_gdf.iterrows():
                if operation == 'intersection' and base_row['geometry'].intersects(other_row['geometry']):
                    intersecting_features.append(other_row)
                elif operation == 'contains' and base_row['geometry'].contains(other_row['geometry']):
                    intersecting_features.append(other_row)

            # If exclude_non_overlapping is True and no intersection or complete overlap is found, skip this base feature
            if exclude_non_overlapping and not intersecting_features:
                continue

            # Prepare the properties for the current feature
            feature_properties = base_row.drop('geometry')

            # Merge properties from the intersecting features
            merged_properties = []
            for other_row in intersecting_features:
                other_props = other_row.drop('geometry').to_dict()

                # If properties_to_merge is provided, only merge those
                if properties_to_merge:
                    filtered_props = {key: value for key, value in other_props.items() if key in properties_to_merge}
                    merged_properties.append(filtered_props)
                else:
                    merged_properties.append(other_props)

            # Flatten or use first intersecting value for properties
            if flatten:
                new_vals = {}
                for prop in merged_properties:
                    for key, value in prop.items():
                        if f'intersecting_{key}' not in new_vals:
                            new_vals[f'intersecting_{key}'] = []
                        new_vals[f'intersecting_{key}'].append(value)

                if use_first_value:
                    for key, value in feature_properties.items():
                        if isinstance(value, list):
                            feature_properties[key] = value[0]
                else:
                    for key, value in new_vals.items():
                        feature_properties[key] = ', '.join(map(str, value))
            else:
                feature_properties['merged_properties'] = merged_properties

            # Convert the feature to a GeoJSON feature
            feature_geojson = {
                'type': 'Feature',
                'geometry': base_row['geometry'].__geo_interface__,  # Convert geometry to GeoJSON format
                'properties': feature_properties  # Add properties to the GeoJSON feature
            }

            # Append the feature to the output list
            output_features.append(feature_geojson)

        # Save the output features as a new GeoJSON file
        logger.info(f"Saving the result to {dataset_name}.geojson")
        geojson = {"type": "FeatureCollection", "features": output_features}
        save_geojson_to_dataset(dataset_name, geojson)

        return {'status': 'success', 'message': 'Vector processing completed and dataset created.'}

    except VectorMapLayer.DoesNotExist:
        logger.error(f'Base layer with ID {base_layer_id} not found.')
        return {'status': 'error', 'message': 'Base layer not found.'}
    except Exception as e:
        logger.error(f'Error in merge_vector_layer_data: {str(e)}')
        return {'status': 'error', 'message': str(e)}
