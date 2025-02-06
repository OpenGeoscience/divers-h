import base64
from datetime import datetime
from io import BytesIO
import logging
from pathlib import Path
import re
import tempfile

from PIL import Image
from celery import current_task, shared_task
from django.contrib.gis.geos import Polygon
from django.contrib.gis.geos.error import GEOSException
from django.core.files.base import ContentFile
from matplotlib import cm
import numpy as np
import xarray as xr

from uvdat.core.models import NetCDFData, NetCDFImage, NetCDFLayer, ProcessingTask

logger = logging.getLogger(__name__)


def create_netcdf_data_layer(file_item, metadata):
    with tempfile.TemporaryDirectory() as temp_dir:
        raw_data_path = Path(temp_dir, 'netcdf.nc')
        with open(raw_data_path, 'wb') as raw_data:
            with file_item.file.open('rb') as raw_data_archive:
                raw_data.write(raw_data_archive.read())

        ds = xr.open_dataset(raw_data_path)

        description = {
            'dimensions': {
                dim: int(len(ds[dim])) for dim in ds.dims
            },  # Ensure values are standard Python integers
            'variables': {},
            'attributes': {
                key: str(value) for key, value in ds.attrs.items()
            },  # Convert attributes to strings if needed
        }

        for var_name, variable in ds.variables.items():
            var_info = {
                'dimensions': list(variable.dims),
                'dtype': str(variable.dtype),
                'attributes': {key: str(value) for key, value in variable.attrs.items()},
            }

            # Calculate min and max values if the variable has numeric data
            try:
                var_min = float(variable.min().values) if variable.size > 0 else None
                var_max = float(variable.max().values) if variable.size > 0 else None
                if 'datetime' in str(variable.dtype):
                    var_info['startDate'] = str(variable.min().values)
                    var_info['endDate'] = str(variable.max().values)
                var_info['min'] = var_min
                var_info['max'] = var_max
                if var_name in description['dimensions'].keys():
                    var_info['steps'] = description['dimensions'][var_name]
                if re.search(r'\blat\b|\blatitude\b', var_name, re.IGNORECASE):
                    if -90 <= var_min <= 90 and -90 <= var_max <= 90:
                        var_info['geospatial'] = 'latitude'
                elif re.search(r'\blon\b|\blongitude\b', var_name, re.IGNORECASE):
                    if -180 <= var_min <= 180 and -180 <= var_max <= 180:
                        var_info['geospatial'] = 'longitude'
                    elif 0 <= var_min <= 360 and 0 <= var_max <= 360:
                        var_info['geospatial'] = 'longitude360'
            except Exception:
                var_info['min'] = 0
                var_info['max'] = variable.size

            description['variables'][var_name] = var_info

        # Create the NetCDF Layer Item
        created_netcdf = NetCDFData.objects.create(
            dataset=file_item.dataset,
            name=file_item.dataset.name,
            file_item=file_item,
            metadata=description,
            default_style={},
            index=0,
        )
        generate = metadata.get('generate', [])

        for item in generate:
            create_netcdf_slices(
                netcdf_data_id=created_netcdf.pk,
                name=item.get('name', 'Default Layer'),
                variable=item.get('variable'),
                x_variable=item.get('x_variable'),
                y_variable=item.get('y_variable'),
                sliding_variable=item.get('sliding_variable'),
                description=item.get('description', ''),
                additional_vars=item.get('additional_var', ''),
                x_range=item.get('xRange', None),
                y_range=item.get('yRange', None),
                slicer_range=item.get('slicerRange', None),
            )
    return created_netcdf


def preview_netcdf_slice(
    netcdf_data_id: int,
    variable,
    sliding_variable='time',
    x_variable='latitude',
    y_variable='longitude',
    color_map='viridis',
    additional_vars='',  # var1,index1&var2,index2
    i=0,
    x_range=None,
    y_range=None,
    slicer_range=None,
):
    netcdf_data = NetCDFData.objects.get(pk=netcdf_data_id)
    with tempfile.TemporaryDirectory() as temp_dir:
        raw_data_path = Path(temp_dir, 'netcdf.nc')
        with open(raw_data_path, 'wb') as raw_data:
            with netcdf_data.file_item.file.open('rb') as raw_data_archive:
                raw_data.write(raw_data_archive.read())
        ds = xr.open_dataset(raw_data_path)

        # Check if the specified variable and dimension exist
        if variable not in ds:
            raise ValueError(f"Variable '{variable}' not found in the dataset.")
        if sliding_variable not in ds.dims:
            raise ValueError(f"Dimension '{sliding_variable}' not found in the dataset.")

        longitude360 = (
            netcdf_data.metadata.get('variables', {}).get(x_variable, {}).get('geospatial', '')
            == 'longitude360'
        )
        x_range_updated = x_range
        # This is a little complicated but we have latitude of -180 to 180 where 0 is greenwich
        # then there is the data in the system where it is 0 to 360 where 0 is greenwich
        # we can't do a simple mapping without reordering the data
        cross_zero = False
        if longitude360 and x_range:
            if x_range[0] < 0 and x_range[1] > 0:  # crossing the 0 degree range
                cross_zero = True
                # values below 0 need to be abs(x)+180 to get the proper value (180-360)
                # values above 0 can remain at their default 0 value (0-180)
                x_range_updated = [(x + 360) if x < 0 else x for x in x_range]
            # If both values are positive we can use the standard 0-180 latitude range
            elif x_range[0] > 0 and x_range[1] > 0:
                x_range_updated = [x for x in x_range]
            # If both values are negative we need to to convert to the 180-360 range
            else:
                x_range_updated = [x + 360 for x in x_range]
                x_range_updated.sort()

        # Validate and subset data if ranges are provided
        if x_range:
            x_min, x_max = ds[x_variable].values.min(), ds[x_variable].values.max()
            if not (x_min <= x_range_updated[0] <= x_max and x_min <= x_range_updated[1] <= x_max):
                raise ValueError(
                    f'x_range {x_range_updated} is outside the bounds of {x_min} to {x_max}.'
                )
            # if we cross the 0 boundary we need to keep the filtering but use an OR
            # this is to get the values about the 180 range and the values below
            if cross_zero:
                ds = ds.sel(
                    {
                        x_variable: ds[x_variable].where(
                            (ds[x_variable] >= x_range_updated[0])
                            | (ds[x_variable] <= x_range_updated[1]),
                            drop=True,
                        )
                    }
                )
                # We then need to reorder data so that the image looks like a proper preview
                part1 = ds.sel({x_variable: ds[x_variable].where(ds[x_variable] >= 180, drop=True)})
                part2 = ds.sel({x_variable: ds[x_variable].where(ds[x_variable] < 180, drop=True)})

                # Concatenate them so that the 180-360 values come before the 0-180 values
                ds = xr.concat([part1, part2], dim=x_variable)

            else:
                ds = ds.sel(
                    {
                        x_variable: ds[x_variable].where(
                            (ds[x_variable] >= x_range_updated[0])
                            & (ds[x_variable] <= x_range_updated[1]),
                            drop=True,
                        )
                    }
                )

        if y_range:
            y_min, y_max = ds[y_variable].values.min(), ds[y_variable].values.max()
            if not (y_min <= y_range[0] <= y_max and y_min <= y_range[1] <= y_max):
                raise ValueError(f'y_range {y_range} is outside the bounds of {y_min} to {y_max}.')
            ds = ds.sel(
                {
                    y_variable: ds[y_variable].where(
                        (ds[y_variable] >= y_range[0]) & (ds[y_variable] <= y_range[1]), drop=True
                    )
                }
            )

        if slicer_range:
            try:
                slide_min, slide_max = (
                    ds[sliding_variable].values.min(),
                    ds[sliding_variable].values.max(),
                )

                if np.issubdtype(ds[sliding_variable].dtype, np.datetime64):
                    # Convert slicer_range to datetime64 if sliding_variable is a datetime
                    slicer_range = [np.datetime64(int(ts), 'ms') for ts in slicer_range]

                # Check if slicer_range is a valid range of integers
                is_range_of_integers = (
                    isinstance(slicer_range, (list, tuple))
                    and len(slicer_range) == 2
                    and all(isinstance(x, int) for x in slicer_range)
                )

                if is_range_of_integers:
                    # Check if range is within the number of layers
                    num_layers = len(ds[sliding_variable])
                    if not (
                        0 <= slicer_range[0] < num_layers and 0 <= slicer_range[1] < num_layers
                    ):
                        raise ValueError(
                            f'slicer_range {slicer_range} is outside the valid layer range 0 to {num_layers - 1}.'
                        )
                    # Select using layer indices
                    ds = ds.isel({sliding_variable: slice(slicer_range[0], slicer_range[1] + 1)})
                else:
                    # Use slicer_range as values if it's not a range of integers
                    if not (
                        slide_min <= slicer_range[0] <= slide_max
                        and slide_min <= slicer_range[1] <= slide_max
                    ):
                        raise ValueError(
                            f'slicer_range {slicer_range} is outside the bounds of {slide_min} to {slide_max}.'
                        )
                    ds = ds.sel(
                        {
                            sliding_variable: ds[sliding_variable].where(
                                (ds[sliding_variable] >= slicer_range[0])
                                & (ds[sliding_variable] <= slicer_range[1]),
                                drop=True,
                            )
                        }
                    )
            except Exception as e:
                logger.warning(f'Slicer Range Exception: {e}')
                slicer_range = None

        data_var = ds.get(variable)
        variables = data_var.dims
        base_variables = (x_variable, y_variable, sliding_variable)

        extra_variables = []
        if additional_vars:
            for var_pair in additional_vars.split('&'):
                var, index = var_pair.split(',')
                extra_variables.append({'variable': var, 'index': int(index)})

        for internal_variable in variables:
            if internal_variable not in base_variables and not any(
                e['variable'] == internal_variable for e in extra_variables
            ):
                extra_variables.append({'variable': internal_variable, 'index': 0})
        # Get the colormap from matplotlib
        try:
            colormap = cm.get_cmap(color_map)
        except ValueError:
            raise ValueError(
                f"Invalid colormap '{color_map}'. Please use a valid matplotlib colormap."
            )
        indexers = {sliding_variable: i}
        for item in extra_variables:
            indexers[item['variable']] = item['index']
        slice_data = data_var.isel(indexers).values

        # Normalize data to 0-1 for colormap application
        slice_min = np.nanmin(slice_data)
        slice_max = np.nanmax(slice_data)
        normalized_data = (slice_data - slice_min) / (slice_max - slice_min)

        # Apply the colormap
        colored_data = colormap(normalized_data)  # Returns RGBA values
        colored_data = (colored_data[:, :, :3] * 255).astype(np.uint8)  # Drop alpha, scale to 0-255

        # Convert to an RGB image using PIL
        image = Image.fromarray(colored_data, mode='RGB')
        image_buffer = BytesIO()
        if longitude360:
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
        image.save(image_buffer, format='PNG')
        image_buffer.seek(0)
        base64_image = base64.b64encode(image_buffer.getvalue()).decode('utf-8')
        return base64_image


def convert_to_timestamp(obj):
    if isinstance(obj, str):  # Handle ctime (string)
        dt_obj = datetime.strptime(obj, '%a %b %d %H:%M:%S %Y')
        return dt_obj.timestamp()
    elif isinstance(obj, np.datetime64):  # Handle datetime64
        return (obj - np.datetime64('1970-01-01T00:00:00')) / np.timedelta64(1, 's')
    elif isinstance(obj, datetime):  # Handle Python datetime objects
        return obj.timestamp()
    else:
        return obj


@shared_task
def create_netcdf_slices(
    netcdf_data_id: int,
    name,
    variable,
    sliding_variable='time',
    x_variable='latitude',
    y_variable='longitude',
    color_map='viridis',
    start=0,
    end=None,
    description='',
    additional_vars='',  # New parameter for additional variables
    x_range=None,
    y_range=None,
    slicer_range=None,
    override_bounds=None,
):
    task_id = current_task.request.id  # Get the Celery task ID

    netcdf_data = NetCDFData.objects.get(pk=netcdf_data_id)
    # Try because ingestion wouldn't have a processing task
    try:
        processing_task = ProcessingTask.objects.filter(celery_id=task_id)
        if processing_task:
            processing_task.update(status=ProcessingTask.Status.RUNNING)
    except ProcessingTask.DoesNotExist:
        processing_task = None
    with tempfile.TemporaryDirectory() as temp_dir:
        raw_data_path = Path(temp_dir, 'netcdf.nc')
        with open(raw_data_path, 'wb') as raw_data:
            with netcdf_data.file_item.file.open('rb') as raw_data_archive:
                raw_data.write(raw_data_archive.read())
        ds = xr.open_dataset(raw_data_path)

        # Check if the specified variable and dimension exist
        if variable not in ds:
            raise ValueError(f"Variable '{variable}' not found in the dataset.")
        if sliding_variable not in ds.dims:
            raise ValueError(f"Dimension '{sliding_variable}' not found in the dataset.")

        longitude360 = (
            netcdf_data.metadata.get('variables', {}).get(x_variable, {}).get('geospatial', '')
            == 'longitude360'
        )
        # Handle the case of being 360 degrees and having no x_range
        if longitude360 and x_range is None:
            x_range = [ds[x_variable].values.min() - 180, ds[x_variable].values.max() - 180]

        x_range_updated = x_range
        # This is a little complicated but we have latitude of -180 to 180 where 0 is greenwich
        # then there is the data in the system where it is 0 to 360 where 0 is greenwich
        # we can't do a simple mapping without reordering the data
        cross_zero = False
        if longitude360 and x_range:
            if x_range[0] < 0 and x_range[1] > 0:  # crossing the 0 degree range
                cross_zero = True
                # values below 0 need to be abs(x)+180 to get the proper value (180-360)
                # values above 0 can remain at their default 0 value (0-180)
                x_range_updated = [(x + 360) if x < 0 else x for x in x_range]
            # If both values are positive we can use the standard 0-180 latitude range
            elif x_range[0] > 0 and x_range[1] > 0:
                x_range_updated = [x for x in x_range]
            # If both values are negative we need to to convert to the 180-360 range
            else:
                x_range_updated = [x + 360 for x in x_range]
                x_range_updated.sort()
        # Validate and subset data if ranges are provided
        if x_range:
            x_min, x_max = ds[x_variable].values.min(), ds[x_variable].values.max()
            if not (x_min <= x_range_updated[0] <= x_max and x_min <= x_range_updated[1] <= x_max):
                raise ValueError(
                    f'x_range {x_range_updated} is outside the bounds of {x_min} to {x_max}.'
                )
            # if we cross the 0 boundary we need to keep the filtering but use an OR
            # this is to get the values about the 180 range and the values below
            if cross_zero:
                ds = ds.sel(
                    {
                        x_variable: ds[x_variable].where(
                            (ds[x_variable] >= x_range_updated[0])
                            | (ds[x_variable] <= x_range_updated[1]),
                            drop=True,
                        )
                    }
                )
                # We then need to reorder data so that the image looks like a proper preview
                part1 = ds.sel({x_variable: ds[x_variable].where(ds[x_variable] >= 180, drop=True)})
                part2 = ds.sel({x_variable: ds[x_variable].where(ds[x_variable] < 180, drop=True)})

                # Concatenate them so that the 180-360 values come before the 0-180 values
                ds = xr.concat([part1, part2], dim=x_variable)

            else:
                ds = ds.sel(
                    {
                        x_variable: ds[x_variable].where(
                            (ds[x_variable] >= x_range_updated[0])
                            & (ds[x_variable] <= x_range_updated[1]),
                            drop=True,
                        )
                    }
                )

        if y_range:
            y_min, y_max = ds[y_variable].values.min(), ds[y_variable].values.max()
            if not (y_min <= y_range[0] <= y_max and y_min <= y_range[1] <= y_max):
                raise ValueError(f'y_range {y_range} is outside the bounds of {y_min} to {y_max}.')
            ds = ds.sel(
                {
                    y_variable: ds[y_variable].where(
                        (ds[y_variable] >= y_range[0]) & (ds[y_variable] <= y_range[1]), drop=True
                    )
                }
            )

        if slicer_range:
            try:
                slide_min, slide_max = (
                    ds[sliding_variable].values.min(),
                    ds[sliding_variable].values.max(),
                )

                if np.issubdtype(ds[sliding_variable].dtype, np.datetime64):
                    # Convert slicer_range to datetime64 if sliding_variable is a datetime
                    slicer_range = [np.datetime64(int(ts), 'ms') for ts in slicer_range]

                # Check if slicer_range is a valid range of integers
                is_range_of_integers = (
                    isinstance(slicer_range, (list, tuple))
                    and len(slicer_range) == 2
                    and all(isinstance(x, int) for x in slicer_range)
                )

                if is_range_of_integers:
                    # Check if range is within the number of layers
                    num_layers = len(ds[sliding_variable])
                    if not (
                        0 <= slicer_range[0] < num_layers and 0 <= slicer_range[1] < num_layers
                    ):
                        raise ValueError(
                            f'slicer_range {slicer_range} is outside the valid layer range 0 to {num_layers - 1}.'
                        )
                    # Select using layer indices
                    ds = ds.isel({sliding_variable: slice(slicer_range[0], slicer_range[1] + 1)})
                else:
                    # Use slicer_range as values if it's not a range of integers
                    if not (
                        slide_min <= slicer_range[0] <= slide_max
                        and slide_min <= slicer_range[1] <= slide_max
                    ):
                        raise ValueError(
                            f'slicer_range {slicer_range} is outside the bounds of {slide_min} to {slide_max}.'
                        )
                    ds = ds.sel(
                        {
                            sliding_variable: ds[sliding_variable].where(
                                (ds[sliding_variable] >= slicer_range[0])
                                & (ds[sliding_variable] <= slicer_range[1]),
                                drop=True,
                            )
                        }
                    )
            except Exception as e:
                if processing_task:
                    processing_task.update(status=ProcessingTask.Status.ERROR, error=str(e))

                logger.warning(f'Slicer Range Exception: {e}')
                slicer_range = None
        # Extract the data for the specified variable
        data_var = ds.get(variable)
        variables_data = data_var.dims
        dim_size = ds.dims.get(sliding_variable)
        end = dim_size if end is None else end

        base_variables = (x_variable, y_variable, sliding_variable)

        extra_variables = []

        if additional_vars:
            for var_pair in additional_vars.split('&'):
                var, index = var_pair.split(',')
                extra_variables.append({'variable': var, 'index': int(index)})

        for internal_variable in variables_data:
            if internal_variable not in base_variables and not any(
                e['variable'] == internal_variable for e in extra_variables
            ):
                extra_variables.append({'variable': internal_variable, 'index': 0})

        print(f'Extra Variables: {extra_variables}')

        # If the variable has more than 3 dimensions
        # we slice over the additional dimensions using the provided or default indices

        # Create output folder if it doesn't exist

        # Get the colormap from matplotlib
        try:
            colormap = cm.get_cmap(color_map)
        except ValueError:
            error = f"Invalid colormap '{color_map}'. Please use a valid matplotlib colormap."
            if processing_task:
                processing_task.update(status=ProcessingTask.Status.ERROR, error=str(error))
            raise ValueError(error)

        # check the metdata for a latitude/longitude and the min/max values of them
        netcdf_metdata = netcdf_data.metadata
        variables = netcdf_metdata.get('variables')
        bounds = None
        if slicer_range:
            slicer_range = [
                convert_to_timestamp(slicer_range[0]),
                convert_to_timestamp(slicer_range[1]),
            ]
        if variables:
            try:
                x_data = variables.get(x_variable, {})
                y_data = variables.get(y_variable, {})
                slide_data = variables.get(sliding_variable)
                variable_data = variables.get(variable)

                x_min, x_max = x_data.get('min'), x_data.get('max')
                if x_range:
                    x_min = x_range[0]
                    x_max = x_range[1]
                y_min, y_max = y_data.get('min'), y_data.get('max')
                if longitude360:
                    x_min = x_min - 180
                    x_max = x_max - 180
                if y_range:
                    y_min = y_range[0]
                    y_max = y_range[1]
                slide_min, slide_max = slide_data.get('min'), slide_data.get('max')
                if slicer_range:
                    slice_min = slicer_range[0]
                    slice_max = slicer_range[1]
                variable_min, variable_max = (
                    variable_data.get('min'),
                    variable_data.get('max'),
                )
                variable_attributes = variable_data.get('attributes', {})
                variable_longname, variable_standardname = variable_attributes.get(
                    'long_name', ''
                ), variable_attributes.get('standard_name', '')

                if None in (x_min, x_max, y_min, y_max):
                    raise ValueError(
                        "Incomplete bounds data. Ensure 'min' and 'max' are available for both x and y variables.",
                    )
                # Create a GEOS polygon
                x_bbox_range = [x_min, x_max]
                # Handles longitude360 values
                if x_range and longitude360:
                    x_bbox_range = [x_range[0], x_range[1]]
                bounds = Polygon.from_bbox((x_bbox_range[0], y_min, x_bbox_range[1], y_max))
            except GEOSException as geos_err:
                error = f'Error constructing polygon bounds: {geos_err}'
                if processing_task:
                    processing_task.update(status=ProcessingTask.Status.ERROR, error=str(error))
                raise ValueError(error)
            except Exception as e:
                error = f'Error processing bounds: {e}'
                if processing_task:
                    processing_task.update(status=ProcessingTask.Status.ERROR, error=str(error))
                raise ValueError(error)

        if not bounds and not override_bounds:
            error = (
                'Bounds could not be determined. Check metadata for latitude/longitude information.'
            )
            if processing_task:
                processing_task.update(status=ProcessingTask.Status.ERROR, error=str(error))
            raise ValueError(error)
        if override_bounds:
            bounds = Polygon.from_bbox(
                (override_bounds[0], override_bounds[1], override_bounds[2], override_bounds[3])
            )

        # Create the NetCDF Layer
        parameters = {
            'x': {'variable': x_variable, 'min': x_min, 'max': x_max},
            'y': {'variable': y_variable, 'min': y_min, 'max': y_max},
            'sliding_dimension': {
                'variable': sliding_variable,
                'min': slide_min,
                'max': slide_max,
            },
            'stepCount': end - start,
            'extra_variables': extra_variables,
            'main_variable': {
                'variable': variable,
                'min': variable_min,
                'max': variable_max,
                'longName': variable_longname,
                'standardName': variable_standardname,
            },
            'colorScheme': color_map,
            'xRange': x_range,
            'yRange': y_range,
            'SlidingRange': slicer_range,
        }
        netcdf_layer = NetCDFLayer.objects.create(
            netcdf_data=netcdf_data,
            name=name,
            color_scheme=color_map,
            description=description,
            parameters=parameters,
            bounds=bounds,
        )
        # Iterate through the dimension to create slices and save images
        for i in range(start, end):
            # Extract a slice along the specified dimension
            indexers = {sliding_variable: i}
            for item in extra_variables:
                indexers[item['variable']] = item['index']
            slice_data = data_var.isel(indexers).values

            # Normalize data to 0-1 for colormap application
            slice_min = np.nanmin(slice_data)
            slice_max = np.nanmax(slice_data)
            normalized_data = (slice_data - slice_min) / (slice_max - slice_min)

            # Apply the colormap
            colored_data = colormap(normalized_data)  # Returns RGBA values
            colored_data = (colored_data[:, :, :3] * 255).astype(
                np.uint8
            )  # Drop alpha, scale to 0-255

            # Convert to an RGB image using PIL
            image = Image.fromarray(colored_data, mode='RGB')
            image_buffer = BytesIO()
            if longitude360:
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
            image.save(image_buffer, format='PNG')
            image_buffer.seek(0)
            image_name = f'{variable}_{sliding_variable}_{i}.png'
            image_content = ContentFile(image_buffer.getvalue(), name=image_name)

            # Create the NetCDFImage object
            NetCDFImage.objects.create(
                netcdf_layer=netcdf_layer,
                image=image_content,  # Save the image to the S3 field
                slider_index=i,
                bounds=bounds,  # Reuse the bounds calculated earlier
            )
        if processing_task:
            processing_task.update(
                status=ProcessingTask.Status.COMPLETE,
                output_metadata={
                    'net_cdf_map_layers': [netcdf_layer.pk],
                },
            )
