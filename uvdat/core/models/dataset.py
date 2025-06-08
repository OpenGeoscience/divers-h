from itertools import chain

from django.db import models
from django_extensions.db.models import TimeStampedModel


class Dataset(TimeStampedModel):

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=25)
    processing = models.BooleanField(default=False)
    metadata = models.JSONField(blank=True, null=True)
    created = models.TimeField(default=None, null=True)

    def is_in_context(self, context_id):
        from uvdat.core.models import Context

        context = Context.objects.get(id=context_id)
        return context.datasets.filter(id=self.id).exists()

    def spawn_conversion_task(
        self,
        style_options=None,
        network_options=None,
        region_options=None,
        asynchronous=True,
    ):
        from uvdat.core.tasks.dataset import convert_dataset

        if asynchronous:
            convert_dataset.delay(self.id, style_options, network_options, region_options)
        else:
            convert_dataset(self.id, style_options, network_options, region_options)

    def get_size(self):
        from uvdat.core.models import FileItem

        size = 0
        for file_item in FileItem.objects.filter(dataset=self):
            if file_item.file_size is not None:
                size += file_item.file_size
        return size

    def get_regions(self):
        from uvdat.core.models import SourceRegion

        return SourceRegion.objects.filter(dataset=self)

    def get_map_layers(self):
        return chain(
            self.rastermaplayer_set.all(), self.vectormaplayer_set.all(), self.netcdfdata_set.all(), self.fmvlayer_set.all()
        )
