from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django_extensions.db.models import TimeStampedModel


class LayerRepresentation(TimeStampedModel):

    map_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    map_layer = GenericForeignKey('map_type', 'object_id')
    default_style = models.JSONField(blank=True, null=True)
    name = models.CharField(max_length=255, unique=False, blank=True)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['map_type', 'object_id']),
        ]
