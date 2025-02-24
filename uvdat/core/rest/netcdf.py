from datetime import datetime

from rest_framework import mixins, status
from rest_framework.decorators import action, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from uvdat.core.models.netcdf import NetCDFData, NetCDFImage, NetCDFLayer
from uvdat.core.models.processing_task import ProcessingTask
from uvdat.core.tasks.netcdf import create_netcdf_slices, preview_netcdf_slice


class NetCDFDataView(GenericViewSet, mixins.ListModelMixin, mixins.CreateModelMixin):

    # POST endpoint for previewing the NetCDF slice
    @action(detail=False, methods=['post'], url_path='preview')
    def preview(self, request, *args, **kwargs):
        # Extract parameters from the request data
        netcdf_data_id = request.data.get('netcdf_data_id')
        variable = request.data.get('variable')
        sliding_variable = request.data.get('sliding_variable', 'time')
        x_variable = request.data.get('x_variable', 'latitude')
        y_variable = request.data.get('y_variable', 'longitude')
        color_map = request.data.get('color_map', 'viridis')
        additional_vars = request.data.get('additional_vars', '')
        x_range = request.data.get('xRange', None)
        y_range = request.data.get('yRange', None)
        slicer_range = request.data.get('slicerRange', None)
        i = int(request.data.get('i', 0))

        # Validate required parameters
        if not netcdf_data_id or not variable:
            return Response(
                {'error': "Both 'netcdf_data_id' and 'variable' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get Base64 image from the preview function
            base64_image = preview_netcdf_slice(
                netcdf_data_id=netcdf_data_id,
                variable=variable,
                sliding_variable=sliding_variable,
                x_variable=x_variable,
                y_variable=y_variable,
                color_map=color_map,
                i=i,
                additional_vars=additional_vars,
                x_range=x_range,
                y_range=y_range,
                slicer_range=slicer_range,
            )
            return Response({'image': base64_image}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # GET endpoint for fetching bounds and image URLs for a NetCDFLayer
    @action(detail=False, methods=['get'], url_path='layer/(?P<netcdf_layer_id>[^/.]+)/images')
    def images(self, request, *args, **kwargs):
        # Extract the netCDFLayer ID from the URL parameter
        netcdf_layer_id = kwargs.get('netcdf_layer_id')

        if not netcdf_layer_id:
            return Response(
                {'error': "'netcdf_layer_id' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract the 'details' parameter from the query parameters (default to False)
        details = request.query_params.get('details', 'false').lower() == 'true'

        try:
            # Fetch the NetCDFLayer by ID
            netcdf_layer = NetCDFLayer.objects.get(id=netcdf_layer_id)

            # Query for NetCDFImage objects with related parent bounds, sorted by slider_index
            # Only include bounds if 'details' is true
            netcdf_images = NetCDFImage.objects.filter(netcdf_layer=netcdf_layer).order_by(
                'slider_index'
            )

            # Prepare the response data with image URLs and parent bounds
            sliding_dim = netcdf_layer.parameters.get('sliding_dimension', None)
            step_count = netcdf_layer.parameters.get('stepCount', None)
            if sliding_dim and step_count:
                if sliding_dim.get('startDate', False) and sliding_dim.get('endDate', False):
                    startDate = sliding_dim.get('startDate')
                    endDate = sliding_dim.get('endDate')
                    min = datetime.fromisoformat(startDate[:26]).timestamp()
                    max = datetime.fromisoformat(endDate[:26]).timestamp()
                    sliding_data = {
                        'min': min,
                        'max': max,
                        'variable': sliding_dim.get('variable', 'time'),
                    }
                else:
                    sliding_data = {
                        'min': sliding_dim.get('min', 0),
                        'max': sliding_dim.get('max', step_count),
                        'variable': sliding_dim.get('variable', 'time'),
                    }
                sliding_data['step'] = (sliding_data['max'] - sliding_data['min']) / (
                    step_count - 1
                )
            response_data = {
                'netCDFLayer': int(netcdf_layer_id),
                'parent_bounds': netcdf_layer.bounds.envelope.coords,  # 4-tuple for the parent layer bounds
                'sliding': sliding_data,
                'images': [image.image.url for image in netcdf_images],  # Only return the image URL
            }

            # If 'details' is true, include the bounds for each image
            if details:
                for image_data, image in zip(response_data['images'], netcdf_images):
                    image_data['bounds'] = image.bounds.envelope.coords

            return Response(response_data, status=status.HTTP_200_OK)

        except NetCDFLayer.DoesNotExist:
            return Response(
                {'error': f'NetCDFLayer with ID {netcdf_layer_id} not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='generate-layer')
    def generate_layer(self, request, *args, **kwargs):
        # Extract parameters from the request data
        netcdf_data_id = request.data.get('netcdf_data_id')
        variable = request.data.get('variable')
        name = request.data.get('name', 'Default Name')
        sliding_variable = request.data.get('sliding_variable', 'time')
        x_variable = request.data.get('x_variable', 'latitude')
        y_variable = request.data.get('y_variable', 'longitude')
        color_map = request.data.get('color_map', 'viridis')
        additional_vars = request.data.get('additional_vars', '')
        start = request.data.get('start', 0)
        end = request.data.get('end', None)
        description = request.data.get('description', '')
        x_range = request.data.get('xRange', None)
        y_range = request.data.get('yRange', None)
        slicer_range = request.data.get('slicerRange', None)

        task = create_netcdf_slices.delay(
            netcdf_data_id=netcdf_data_id,
            name=name,
            variable=variable,
            sliding_variable=sliding_variable,
            x_variable=x_variable,
            y_variable=y_variable,
            color_map=color_map,
            start=start,
            end=end,
            description=description,
            additional_vars=additional_vars,
            x_range=x_range,
            y_range=y_range,
            slicer_range=slicer_range,
        )
        processing_task = ProcessingTask.objects.create(
            name=f'Creating NetCDF Layer called {name}',
            status=ProcessingTask.Status.QUEUED,
            metadata={'type': 'netCDF layer creation'},
            celery_id=task.id,
        )
        netcdf_data = NetCDFData.objects.get(id=netcdf_data_id)
        processing_task.file_items.add(netcdf_data.file_item)
        processing_task.save()

        return Response(
            {'message': 'Task created successfully.', 'taskId': task.id},
            status=status.HTTP_201_CREATED,
        )

    # DELETE endpoint for deleting a NetCDFLayer
    @permission_classes([IsAuthenticated])
    @action(
        detail=False, methods=['delete'], url_path='layer/(?P<netcdf_layer_id>[^/.]+)/delete-layer'
    )
    def delete_layer(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied('You must be logged in to delete a dataset.')

        # Extract the netCDFLayer ID from the URL parameter
        netcdf_layer_id = kwargs.get('netcdf_layer_id')

        if not netcdf_layer_id:
            return Response(
                {'error': "'netcdf_layer_id' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Fetch the NetCDFLayer by ID
            netcdf_layer = NetCDFLayer.objects.get(id=netcdf_layer_id)

            # Delete the NetCDFLayer
            netcdf_layer.delete()

            return Response(
                {'message': f'NetCDFLayer with ID {netcdf_layer_id} deleted successfully.'},
                status=status.HTTP_200_OK,
            )

        except NetCDFLayer.DoesNotExist:
            return Response(
                {'error': f'NetCDFLayer with ID {netcdf_layer_id} not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
