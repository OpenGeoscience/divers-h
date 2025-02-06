from django.db import models
from django_extensions.db.models import TimeStampedModel


class LayerCollection(TimeStampedModel):

    name = models.CharField(max_length=255, unique=False, blank=True)
    description = models.TextField(blank=True)
    configuration = models.JSONField(blank=True, null=True)
