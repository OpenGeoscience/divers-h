from django.db import models

from uvdat.core.models import VectorFeature, VectorMapLayer


class VectorFeatureTableData(models.Model):
    vector_feature = models.ForeignKey(VectorFeature, on_delete=models.CASCADE)
    map_layer = models.ForeignKey(VectorMapLayer, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    type = models.TextField(blank=True, default='')
    description = models.TextField(blank=True, null=True)
    columns = models.JSONField(blank=True, null=True)
    summary = models.JSONField(blank=True, null=True)


class VectorFeatureRowData(models.Model):
    vector_feature_table = models.ForeignKey(VectorFeatureTableData, on_delete=models.CASCADE)
    row_data = models.JSONField(blank=True, null=True)
