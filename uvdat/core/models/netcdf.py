from django.contrib.gis.db import models as geomodels
from django.db import models
from django_extensions.db.models import TimeStampedModel
from s3_file_field import S3FileField

from .file_item import FileItem
from .map_layers import AbstractMapLayer


class NetCDFData(AbstractMapLayer):
    # It's an abstract map layer so it shows up properly under Datasets in the hierarchy
    # The user would then create an actua NetCDFLayer based on parameters.
    # a NetCDFData will provide a list of connected NetCDFLayers
    file_item = models.ForeignKey(FileItem, on_delete=models.CASCADE, null=True)


class NetCDFLayer(TimeStampedModel):
    # provides a listing of images associated with specific parameters for displaying
    netcdf_data = models.ForeignKey(NetCDFData, on_delete=models.CASCADE, null=False)
    name = models.CharField(max_length=255, unique=False, blank=True)
    parameters = models.JSONField()
    metadata = models.JSONField(blank=True, null=True)
    description = models.TextField(null=True, blank=True)
    color_scheme = models.CharField(max_length=255, unique=False, blank=True)
    bounds = geomodels.PolygonField(
        help_text='Bounds/Extents of NetCDFLayer',
        null=True,
        blank=True,
    )


class NetCDFImage(TimeStampedModel):
    image = S3FileField()
    netcdf_layer = models.ForeignKey(NetCDFLayer, on_delete=models.CASCADE, null=True)
    slider_index = models.IntegerField()
    bounds = geomodels.PolygonField(
        help_text='Bounds/Extents of NetCDFLayer',
        null=True,
        blank=True,
    )
