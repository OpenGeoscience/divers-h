from django.db import models
from django_extensions.db.models import TimeStampedModel

from .file_item import FileItem


class ProcessingTask(TimeStampedModel):
    class Status(models.TextChoices):
        COMPLETE = 'Complete'
        RUNNING = 'Running'
        ERROR = 'Error'
        QUEUED = 'Queued'

    name = models.CharField(max_length=255)

    file_items = models.ManyToManyField(FileItem, blank=True)
    metadata = models.JSONField(blank=True, null=True)  # description and details about the task
    status = models.CharField(
        max_length=255,  # If we need future states
        blank=True,
        help_text='Processing Status',
        choices=Status.choices,
    )
    celery_id = models.CharField(
        max_length=255,  # If we need future states
        blank=True,
        help_text='Celery Task Id',
    )
    output_metadata = models.JSONField(
        blank=True, null=True
    )  # description and details about the task output (file_items/layers)

    error = models.TextField(blank=True, help_text='Error text if an error occurs')
