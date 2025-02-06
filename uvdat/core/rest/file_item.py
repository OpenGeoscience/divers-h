import os

from django.core import signing
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from uvdat.core.models import Dataset, FileItem, ProcessingTask
from uvdat.core.rest.serializers import FileItemSerializer
from uvdat.core.tasks.dataset import process_file_item

from .permissions import DefaultPermission

VALID_FILE_TYPES = {'geojson', 'json', 'tiff', 'tif', 'zip', 'gpkg', 'nc'}


class FileItemViewSet(ModelViewSet):
    queryset = FileItem.objects.all()
    serializer_class = FileItemSerializer
    permission_classes = [DefaultPermission]

    def create(self, request, *args, **kwargs):
        name = request.data.get('name')
        metadata = request.data.get('metadata')
        index = request.data.get('index')
        dataset_id = request.data.get('dataset')
        file_key = request.data.get('fileKey')

        # Decode the fileKey
        try:
            file_key_data = signing.loads(file_key)
            file_key = file_key_data.get('object_key')
        except signing.BadSignature:
            return Response({'detail': 'Invalid file key'}, status=400)

        # Assuming that dataset_id refers to an existing Dataset object
        try:
            dataset = Dataset.objects.get(id=dataset_id)
        except Dataset.DoesNotExist:
            return Response({'detail': 'Dataset not found'}, status=404)

        _, extension = os.path.splitext(file_key)
        extension = extension.lower().strip('.')

        if extension in VALID_FILE_TYPES:
            if extension == 'json':
                file_type = 'geojson'
            elif extension == 'nc':
                file_type = 'netcdf'
            else:
                file_type = extension
        else:
            return Response({'detail': f'Unsupported file type: {extension}'}, status=400)

        # Create a new FileItem
        file_item = FileItem.objects.create(
            name=name,
            metadata=metadata,
            index=index,
            dataset=dataset,
            file=file_key,  # Store the S3 file path
            file_type=file_type,  # Set the file type
        )

        task_id = process_file_item.delay(file_item.id)

        processing_task = ProcessingTask.objects.create(
            name=f'Processing {file_item.name}',
            status=ProcessingTask.Status.QUEUED,
            metadata={'type': 'file processing'},
            celery_id=task_id,
        )
        processing_task.file_items.add(file_item)
        processing_task.save()

        # Serialize the created file item
        serializer = self.get_serializer(file_item)

        return Response(serializer.data, status=201)
