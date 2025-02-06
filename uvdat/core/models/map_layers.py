import json
from pathlib import Path
import tempfile

from django.contrib.gis.db import models as geomodels
from django.core.files.base import ContentFile
from django.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel
import large_image
from s3_file_field import S3FileField

from .dataset import Dataset


class AbstractMapLayer(TimeStampedModel):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, null=True)
    metadata = models.JSONField(blank=True, null=True)
    default_style = models.JSONField(blank=True, null=True)
    index = models.IntegerField(null=True)
    name = models.CharField(max_length=255, unique=False, blank=True)

    def is_in_context(self, context_id):
        return self.dataset.is_in_context(context_id)

    class Meta:
        abstract = True


class RasterMapLayer(AbstractMapLayer):
    cloud_optimized_geotiff = S3FileField()

    def get_image_data(self, resolution: float = 1.0):
        with tempfile.TemporaryDirectory() as tmp:
            raster_path = Path(tmp, 'raster')
            with open(raster_path, 'wb') as raster_file:
                raster_file.write(self.cloud_optimized_geotiff.read())
            source = large_image.open(raster_path)
            data, data_format = source.getRegion(format='numpy')
            data = data[:, :, 0]
            if resolution != 1.0:
                step = int(1 / resolution)
                data = data[::step][::step]
            return data.tolist()

    def get_bbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            raster_path = Path(tmp, 'raster')
            with open(raster_path, 'wb') as raster_file:
                raster_file.write(self.cloud_optimized_geotiff.read())
            source = large_image.open(raster_path)
            bounds = source.getBounds('epsg:4326')
            return bounds


@receiver(models.signals.pre_delete, sender=RasterMapLayer)
def delete_raster_content(sender, instance, **kwargs):
    if instance.cloud_optimized_geotiff:
        instance.cloud_optimized_geotiff.delete(save=False)


class VectorMapLayer(AbstractMapLayer):
    geojson_file = S3FileField(null=True)

    def write_geojson_data(self, content: str | dict):
        if isinstance(content, str):
            data = content
        elif isinstance(content, dict):
            data = json.dumps(content)
        else:
            raise Exception(f'Invalid content type supplied: {type(content)}')

        self.geojson_file.save('vectordata.geojson', ContentFile(data.encode()))

    def read_geojson_data(self) -> dict:
        """Read and load the data from geojson_file into a dict."""
        return json.load(self.geojson_file.open())


@receiver(models.signals.pre_delete, sender=VectorMapLayer)
def delete__vectorcontent(sender, instance, **kwargs):
    if instance.geojson_file:
        instance.geojson_file.delete(save=False)


class VectorFeature(models.Model):
    map_layer = models.ForeignKey(VectorMapLayer, on_delete=models.CASCADE)
    geometry = geomodels.GeometryField()
    properties = models.JSONField()
