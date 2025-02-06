from celery.result import AsyncResult
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from uvdat.core.models import ProcessingTask
from uvdat.core.rest.serializers import ProcessingTaskSerializer

from .permissions import DefaultPermission


class ProcessingTaskView(GenericViewSet, mixins.ListModelMixin):
    queryset = ProcessingTask.objects.all()
    serializer_class = ProcessingTaskSerializer
    permission_classes = [DefaultPermission]

    @action(detail=False, methods=['get'], url_path='filtered')
    def filtered(self, request, *args, **kwargs):
        status_filter = request.query_params.get('status', None)

        if status_filter is None or status_filter not in ProcessingTask.Status.values:
            return Response(
                {
                    'error': f'Invalid status value. Allowed values are {ProcessingTask.Status.values}.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        tasks = (
            ProcessingTask.objects.filter(status=status_filter)
            if status_filter
            else ProcessingTask.objects.all()
        )

        # Paginate the queryset
        page = self.paginate_queryset(tasks)
        if page is not None:
            serializer = ProcessingTaskSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Serialize the tasks
        serializer = ProcessingTaskSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path=r'(?P<task_id>[^/.]+)/details')
    def details(self, request, *args, **kwargs):
        task_id = request.query_params.get('task_id')

        if not task_id:
            return Response({'error': "'task_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        task = get_object_or_404(ProcessingTask, pk=task_id)
        celery_task = AsyncResult(task.celery_id)
        celery_data = {
            'state': celery_task.state,
            'status': celery_task.status,
            'info': celery_task.info if not isinstance(celery_task.info, Exception) else None,
            'error': str(celery_task.info) if isinstance(celery_task.info, Exception) else None,
        }

        return Response({'task': task.name, 'celery_data': celery_data})

    @action(detail=False, methods=['post'], url_path=r'(?P<task_id>[^/.]+)/cancel')
    def cancel_task(self, request, *args, **kwargs):
        task_id = request.query_params.ge.get('task_id')

        if not task_id:
            return Response({'error': "'task_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        task = get_object_or_404(ProcessingTask, pk=task_id)
        with transaction.atomic():
            task.delete()
            celery_task = AsyncResult(task.celery_id)
            if celery_task:
                # Terminate true will revoke the task and truly end the process
                celery_task.revoke(terminate=True)
            return Response(
                {'message': 'Task successfully canceled.'}, status=status.HTTP_202_ACCEPTED
            )

        return Response({'error': 'Task not found.'}, status=status.HTTP_404_NOT_FOUND)
