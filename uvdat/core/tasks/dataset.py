import json
import logging

from celery import shared_task

from uvdat.celery import app
from uvdat.core.models import Dataset, FileItem, ProcessingTask
from uvdat.core.tasks.map_layers import save_vector_features

from .csv_to_heatmap import process_file_item_to_heatmap
from .map_layers import (
    create_raster_map_layer,
    create_vector_map_layer,
    process_geopackage,
    process_tabular_vector_feature_data,
)
from .fmv import create_fmv_layer
from .netcdf import create_netcdf_data_layer
from .networks import create_network
from .regions import create_source_regions

logger = logging.getLogger(__name__)


valid_video_format = (
    "mp4",
    "webm",
    "avi",
    "mov",
    "wmv",
    "mpg",
    "mpeg",
    "mp2",
    "ogg",
    "flv",
)

@shared_task
def convert_dataset(
    dataset_id,
    style_options=None,
    network_options=None,
    region_options=None,
):
    dataset = Dataset.objects.get(id=dataset_id)
    dataset.processing = True
    dataset.save()
    base_style_options = style_options
    for file_to_convert in FileItem.objects.filter(dataset=dataset):
        file_name = file_to_convert.file.name.lower()
        file_metadata = file_to_convert.metadata
        style_options = file_metadata.get('default_style', base_style_options)
        if file_name.endswith('.gpkg'):
            raster_map_layers, vector_map_layers = process_geopackage(
                file_to_convert, style_options
            )
            for item in raster_map_layers:
                item.set_bounds()
        elif file_name.endswith(('.zip', '.geojson', '.json', '.csv')):
            if file_metadata.get('processing', False) == 'csvToHeatmap' and file_name.endswith(
                '.csv'
            ):
                process_file_item_to_heatmap(file_to_convert, style_options)
                continue

            # Handle Vector files
            tags = file_metadata.get('tags', False)
            metadata_modified = {}
            if tags:
                metadata_modified = {'tags': tags}
            vector_map_layers = create_vector_map_layer(
                file_to_convert,
                style_options=style_options,
                name=file_to_convert.name,
                metadata=metadata_modified,
            )
            for vector_map_layer in vector_map_layers:
                if network_options:
                    create_network(vector_map_layer, network_options)
                elif region_options:
                    create_source_regions(vector_map_layer, region_options)

                # Create vector tiles after geojson_data may have been altered
                save_vector_features(vector_map_layer=vector_map_layer)
                if 'tabular' in file_metadata.keys():  # Process additional metadata item
                    tabular_info = file_metadata.get('tabular', {})
                    tabular_file_item_id = tabular_info.get('fileItemId')
                    tabular_matcher = tabular_info.get('featurePropertyMatcher')
                    if tabular_file_item_id is not None:
                        tabular_file_item = FileItem.objects.get(pk=tabular_file_item_id)
                        tabular_geojson = json.load(tabular_file_item.file.open())
                        process_tabular_vector_feature_data(
                            vector_map_layer.pk, tabular_geojson, tabular_matcher
                        )
                vector_map_layer.set_bounds()
        elif file_name.endswith(valid_video_format):
            create_fmv_layer(file_to_convert, style_options, file_name, file_metadata)
        elif file_name.endswith(('.tif', '.tiff')):
            # Handle Raster files
            raster_map_layer = create_raster_map_layer(
                file_to_convert,
                style_options=style_options,
            )
            raster_map_layer.set_bounds()
        elif file_name.endswith('.nc'):  # convert netcdf into a netcdf Data model
            create_netcdf_data_layer(
                file_to_convert,
                file_metadata,
            )
        else:
            # Handle unsupported file types
            print(f'Unsupported file type: {file_name}')

    dataset.processing = False
    dataset.save()


@app.task(bind=True)
def process_file_item(self, file_item_id):
    """Process an individual FileItem based on its type and metadata."""
    file_item = FileItem.objects.get(id=file_item_id)
    file_name = file_item.file.name.lower()
    file_metadata = file_item.metadata
    base_style_options = file_item.dataset.metadata.get('default_style', None)
    style_options = file_metadata.get('default_style', base_style_options)
    dataset = file_item.dataset
    dataset.processing = True
    dataset.save()
    logger.info(f'Processing file: {file_item.file.name}')
    logger.info(f'Getting Celery Id:  {self.request.id}')
    processing_task = ProcessingTask.objects.filter(celery_id=self.request.id)
    raster_map_layers = []
    vector_map_layers = []
    netcdf_map_layers = []
    fmv_map_layers = []
    processing_task.update(status=ProcessingTask.Status.RUNNING)
    try:
        if file_name.endswith('.gpkg'):
            gpkg_raster_map_layers, gpkg_vector_map_layers = process_geopackage(
                file_item, style_options
            )
            raster_map_layers += gpkg_raster_map_layers
            vector_map_layers += gpkg_vector_map_layers
        elif file_name.endswith(('.zip', '.geojson', '.json', '.csv')):
            if file_metadata.get('processing', False) == 'csvToHeatmap' and file_name.endswith(
                '.csv'
            ):
                raster_map_layer = process_file_item_to_heatmap(file_item, style_options)
                raster_map_layers.append(raster_map_layer)

            # Handle Vector files
            new_vector_map_layers = create_vector_map_layer(
                file_item, style_options=style_options, name=file_item.name
            )
            for vector_map_layer in new_vector_map_layers:
                save_vector_features(vector_map_layer=vector_map_layer)
                vector_map_layer.set_bounds()
                vector_map_layers.append(vector_map_layer)

        elif file_name.endswith(valid_video_format):
            fmv_map_layer = create_fmv_layer(file_item, style_options, file_name, file_metadata)
            fmv_map_layers.append(fmv_map_layer)
        elif file_name.endswith(('.tif', '.tiff')):
            # Handle Raster files
            raster_map_layer = create_raster_map_layer(
                file_item,
                style_options=style_options,
            )
            raster_map_layers.append(raster_map_layer)
        elif file_name.endswith('.nc'):  # convert netcdf into a netcdf Data model
            netcdf_map_layer = create_netcdf_data_layer(
                file_item,
                file_metadata,
            )
            netcdf_map_layers.append(netcdf_map_layer.pk)
        else:
            # Handle unsupported file types
            logger.info(f'Unsupported file type: {file_name}')
            processing_task.update(
                status=ProcessingTask.Status.ERROR, error=str(f'Unsupported file type: {file_name}')
            )

        for item in raster_map_layers:
            item.set_bounds()
    except Exception as e:
        processing_task.update(status=ProcessingTask.Status.ERROR, error=str(e))
        dataset.processing = False
        dataset.save()
        raise e
    else:
        processing_task.update(
            status=ProcessingTask.Status.COMPLETE,
            output_metadata={
                'output_layers': {
                    'raster_map_layers': [rml.id for rml in raster_map_layers],
                    'vector_map_layers': [vml.id for vml in vector_map_layers],
                    'net_cdf_map_layers': netcdf_map_layers,
                    'fmv_map_layers': [fmv.id for fmv in fmv_map_layers]
                }
            },
        )
    finally:
        dataset.processing = False
        dataset.save()
