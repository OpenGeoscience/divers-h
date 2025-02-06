from django.core.management import call_command
import pytest

from uvdat.core.models import (
    Chart,
    Context,
    Dataset,
    FileItem,
    NetCDFData,
    NetCDFImage,
    NetCDFLayer,
    Network,
    NetworkEdge,
    NetworkNode,
    RasterMapLayer,
    SimulationResult,
    SourceRegion,
    VectorFeature,
    VectorMapLayer,
)


@pytest.mark.django_db
def test_ingest_data():
    call_command(
        'ingest_data',
        './test.json',
    )

    assert Chart.objects.all().count() == 0
    assert Context.objects.all().count() == 7
    assert Dataset.objects.all().count() == 11
    assert FileItem.objects.all().count() == 16
    assert Network.objects.all().count() == 0
    assert NetworkEdge.objects.all().count() == 0
    assert NetworkNode.objects.all().count() == 0
    assert RasterMapLayer.objects.all().count() == 7
    assert SimulationResult.objects.all().count() == 0
    assert SourceRegion.objects.all().count() == 0
    assert VectorMapLayer.objects.all().count() == 11
    assert VectorFeature.objects.count() == 35103
    # Testing that layer/file-item index and naming is working properly
    assert VectorMapLayer.objects.filter(name='Chicago Vectors ShapeFile').count() == 1
    assert VectorMapLayer.objects.filter(name='Second Chicago Vectors Shapefile').count() == 1
    # Testing NetCDF Data
    assert NetCDFData.objects.count() == 2
    assert NetCDFLayer.objects.count() == 2
    assert NetCDFImage.objects.count() == 1330
