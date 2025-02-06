import json

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.serializers import geojson
from rest_framework import serializers

from uvdat.core.models import (
    Chart,
    Context,
    Dataset,
    DerivedRegion,
    FileItem,
    LayerCollection,
    LayerRepresentation,
    NetCDFData,
    NetCDFLayer,
    Network,
    NetworkEdge,
    NetworkNode,
    ProcessingTask,
    RasterMapLayer,
    SimulationResult,
    SourceRegion,
    VectorFeatureRowData,
    VectorFeatureTableData,
    VectorMapLayer,
)


class ContextSerializer(serializers.ModelSerializer):
    default_map_center = serializers.SerializerMethodField('get_center')

    def get_center(self, obj):
        # Web client expects Lon, Lat
        if obj.default_map_center:
            return [obj.default_map_center.y, obj.default_map_center.x]

    class Meta:
        model = Context
        fields = '__all__'


class DatasetSerializer(serializers.ModelSerializer):
    contextCount = serializers.IntegerField(read_only=True)  # noqa: N815 Numer of Linked Contexts

    class Meta:
        model = Dataset
        fields = '__all__'


class FileItemSerializer(serializers.ModelSerializer):
    processing_tasks = serializers.SerializerMethodField()

    class Meta:
        model = FileItem
        fields = '__all__'

    def get_processing_tasks(self, obj):
        tasks = ProcessingTask.objects.filter(
            file_items=obj,
            status__in=[
                ProcessingTask.Status.QUEUED,
                ProcessingTask.Status.RUNNING,
                ProcessingTask.Status.ERROR,
            ],
            metadata={'type': 'file processing'},
        ).order_by('-created')
        if tasks.count() == 0:
            return None
        return ProcessingTaskSerializer(tasks, many=True).data


class ChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chart
        fields = '__all__'


class ProcessingTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingTask
        fields = '__all__'


def get_file_item_ids(obj: VectorMapLayer | RasterMapLayer | NetCDFData):
    if obj.dataset is None:
        return []
    ids = []
    for file_item in obj.dataset.source_files.all():
        ids.append(file_item.id)
    return ids


class AbstractMapLayerSerializer(serializers.Serializer):
    name = serializers.SerializerMethodField('get_name')
    type = serializers.SerializerMethodField('get_type')
    dataset_id = serializers.SerializerMethodField('get_dataset_id')
    file_item = serializers.SerializerMethodField('get_file_item')
    processing_tasks = serializers.SerializerMethodField('get_processing_tasks')

    def get_name(self, obj: VectorMapLayer | RasterMapLayer | NetCDFData):
        if obj.name:
            return obj.name
        if obj.dataset:
            for file_item in obj.dataset.source_files.all():
                if file_item.index == obj.index:
                    return file_item.name
            return f'{obj.dataset.name} Layer {obj.index}'
        return None

    def get_type(self, obj: VectorMapLayer | RasterMapLayer | NetCDFData):
        if isinstance(obj, VectorMapLayer):
            return 'vector'
        if isinstance(obj, RasterMapLayer):
            return 'raster'
        if isinstance(obj, NetCDFData):
            return 'netcdf'
        return 'none'

    def get_dataset_id(self, obj: VectorMapLayer | RasterMapLayer | NetCDFData):
        if obj.dataset:
            return obj.dataset.id
        return None

    def get_file_item(self, obj: VectorMapLayer | RasterMapLayer | NetCDFData):
        if obj.dataset is None:
            return None
        for file_item in obj.dataset.source_files.all():
            if file_item.index == obj.index:
                return {
                    'id': file_item.id,
                    'name': file_item.name,
                }

    def get_processing_tasks(self, obj):
        file_item_ids = get_file_item_ids(obj)
        if not file_item_ids:
            return None
        tasks = ProcessingTask.objects.filter(
            file_items__id__in=file_item_ids,
            status__in=[
                ProcessingTask.Status.QUEUED,
                ProcessingTask.Status.RUNNING,
            ],
        ).order_by('-created')
        if not tasks.exists():
            return None
        return ProcessingTaskSerializer(tasks, many=True).data


class RasterMapLayerSerializer(serializers.ModelSerializer, AbstractMapLayerSerializer):
    class Meta:
        model = RasterMapLayer
        fields = '__all__'


class VectorMapLayerSerializer(serializers.ModelSerializer, AbstractMapLayerSerializer):
    class Meta:
        model = VectorMapLayer
        exclude = ['geojson_file']


class NetCDFLayerSerializer(serializers.ModelSerializer):
    bounds = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    class Meta:
        model = NetCDFLayer
        fields = '__all__'

    def get_type(self, obj):
        return 'netcdf'

    def get_bounds(self, obj):
        """Convert bounds of PolygonField into a JSON {xmin, ymin, xmax, ymax}."""
        if obj.bounds:
            bbox = obj.bounds.extent  # Returns (xmin, ymin, xmax, ymax)
            return {
                'xmin': bbox[0],
                'ymin': bbox[1],
                'xmax': bbox[2],
                'ymax': bbox[3],
            }
        return None


class NetCDFDataSerializer(serializers.ModelSerializer, AbstractMapLayerSerializer):
    layers = NetCDFLayerSerializer(many=True, read_only=True, source='netcdflayer_set')

    class Meta:
        model = NetCDFData
        fields = '__all__'


class VectorMapLayerDetailSerializer(serializers.ModelSerializer, AbstractMapLayerSerializer):
    derived_region_id = serializers.SerializerMethodField('get_derived_region_id')

    def get_derived_region_id(self, obj):
        dr = obj.derivedregion_set.first()
        if dr is None:
            return None
        return dr.id

    class Meta:
        model = VectorMapLayer
        exclude = ['geojson_file']


class LayerCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayerCollection
        fields = '__all__'


class LayerRepresentationSerializer(serializers.ModelSerializer):
    LAYER_TYPE_CHOICES = [
        ('raster', 'Raster'),
        ('vector', 'Vector'),
    ]

    type = serializers.ChoiceField(choices=LAYER_TYPE_CHOICES, write_only=True)
    layer_id = serializers.IntegerField(write_only=True)

    map_layer_id = serializers.SerializerMethodField(read_only=True)
    map_type = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = LayerRepresentation
        fields = [
            'id',
            'type',
            'layer_id',
            'description',
            'name',
            'default_style',
            'enabled',
            'map_layer_id',
            'map_type',  # Include map_type
        ]

    def validate(self, data):
        layer_type = data.get('type')
        layer_id = data.get('layer_id')

        if layer_type not in ['raster', 'vector']:
            raise serializers.ValidationError('Invalid type. Must be "raster" or "vector".')

        if layer_type == 'raster':
            model_class = RasterMapLayer
        elif layer_type == 'vector':
            model_class = VectorMapLayer
        else:
            raise serializers.ValidationError(
                f'layer type: {layer_type} is not a valid layer_type: raster | vector'
            )

        try:
            layer_instance = model_class.objects.get(id=layer_id)
        except model_class.DoesNotExist:
            raise serializers.ValidationError(
                f'{layer_type.capitalize()} layer with id {layer_id} does not exist.'
            )

        # Store the validated model and instance for use in create()
        data['layer_instance'] = layer_instance
        data['model_class'] = model_class
        return data

    def create(self, validated_data):
        layer_instance = validated_data['layer_instance']
        model_class = validated_data['model_class']
        description = validated_data['description']
        default_style = validated_data['default_style']
        name = validated_data['name']
        enabled = validated_data['enabled']

        layer_type = ContentType.objects.get_for_model(model_class)

        map_layer_reference = LayerRepresentation.objects.create(
            name=name,
            map_type=layer_type,
            object_id=layer_instance.id,
            description=description,
            default_style=default_style,
            enabled=enabled,
        )

        return map_layer_reference

    # Method to get the map_layer
    def get_map_layer_id(self, obj):
        return obj.map_layer.pk

    # Method to get the map_type
    def get_map_type(self, obj):
        return 'vector' if obj.map_type.model == 'vectormaplayer' else 'raster'


class SourceRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceRegion
        fields = '__all__'


class RegionFeatureCollectionSerializer(geojson.Serializer):
    # Override this method to ensure the pk field is a number instead of a string
    def get_dump_object(self, obj):
        val = super().get_dump_object(obj)
        val['properties']['id'] = int(val['properties'].pop('pk'))

        return val


class DerivedRegionListSerializer(serializers.ModelSerializer):
    map_layers = serializers.SerializerMethodField('get_map_layers')

    def get_map_layers(self, obj):
        return obj.get_map_layers()

    class Meta:
        model = DerivedRegion
        fields = [
            'id',
            'name',
            'context',
            'metadata',
            'source_regions',
            'operation',
            'map_layers',
        ]


class DerivedRegionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DerivedRegion
        fields = '__all__'

    boundary = serializers.SerializerMethodField()
    map_layers = serializers.SerializerMethodField('get_map_layers')

    def get_boundary(self, obj):
        return json.loads(obj.boundary.geojson)

    def get_map_layers(self, obj):
        return obj.get_map_layers()


class DerivedRegionCreationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DerivedRegion
        fields = [
            'name',
            'context',
            'regions',
            'operation',
        ]

    regions = serializers.ListField(child=serializers.IntegerField())
    operation = serializers.ChoiceField(choices=DerivedRegion.VectorOperation.choices)


class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = '__all__'

    name = serializers.SerializerMethodField('get_name')

    def get_name(self, obj):
        return obj.dataset.name


class NetworkNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkNode
        fields = '__all__'


class NetworkEdgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkEdge
        fields = '__all__'


class SimulationResultSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField('get_name')

    def get_name(self, obj):
        return obj.get_name()

    class Meta:
        model = SimulationResult
        fields = '__all__'


class VectorFeatureTableDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = VectorFeatureTableData
        fields = '__all__'


class VectorFeatureRowDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = VectorFeatureRowData
        fields = '__all__'
