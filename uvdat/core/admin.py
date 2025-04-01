from django.contrib import admin

from uvdat.core.models import (
    Chart,
    Context,
    Dataset,
    DerivedRegion,
    DisplayConfiguration,
    FileItem,
    LayerCollection,
    LayerRepresentation,
    NetCDFData,
    NetCDFImage,
    NetCDFLayer,
    Network,
    NetworkEdge,
    NetworkNode,
    ProcessingTask,
    RasterMapLayer,
    SimulationResult,
    SourceRegion,
    VectorFeature,
    VectorFeatureRowData,
    VectorFeatureTableData,
    VectorMapLayer,
)


class ContextAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


class DatasetAdmin(admin.ModelAdmin):
    list_display = ['id', 'created', 'modified', 'name', 'category']


class FileItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'get_relationship']

    def get_relationship(self, obj):
        if obj.dataset is not None:
            return obj.dataset.name
        if obj.chart is not None:
            return obj.chart.name
        return 'None'


class ChartAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'editable']


class RasterMapLayerAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'get_dataset_name', 'index', 'bounds']

    def get_dataset_name(self, obj):
        return obj.dataset.name


class VectorMapLayerAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'get_dataset_name', 'index', 'geojson_file', 'bounds']

    def get_dataset_name(self, obj):
        return obj.dataset.name


class VectorFeatureAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_dataset_name', 'get_map_layer_index']

    def get_dataset_name(self, obj):
        return obj.map_layer.dataset.name

    def get_map_layer_index(self, obj):
        return obj.map_layer.index


class SourceRegionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'get_dataset_name']

    def get_dataset_name(self, obj):
        return obj.dataset.name


class DerivedRegionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'get_context_name', 'operation', 'get_source_region_names']

    def get_context_name(self, obj):
        return obj.context.name

    def get_source_region_names(self, obj):
        return ', '.join(r.name for r in obj.source_regions.all())


class NetworkAdmin(admin.ModelAdmin):
    list_display = ['id', 'category', 'get_dataset_name']

    def get_dataset_name(self, obj):
        return obj.dataset.name


class NetworkEdgeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'get_network_id', 'get_dataset_name']

    def get_network_id(self, obj):
        return obj.network.id

    def get_dataset_name(self, obj):
        return obj.network.dataset.name


class NetworkNodeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'get_network_id', 'get_dataset_name', 'get_adjacent_node_names']

    def get_network_id(self, obj):
        return obj.network.id

    def get_dataset_name(self, obj):
        return obj.network.dataset.name

    def get_adjacent_node_names(self, obj):
        return ', '.join(n.name for n in obj.get_adjacent_nodes())


class SimulationResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'simulation_type', 'input_args']


class LayerRepresentationAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'map_type', 'object_id', 'default_style']
    search_fields = ['name', 'description']
    list_filter = ['map_type']


class LayerCollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'configuration']
    search_fields = ['name', 'description']


class NetCDFDataAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'get_dataset_name', 'index', 'file_item']

    def get_dataset_name(self, obj):
        return obj.dataset.name


class NetCDFLayerAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'netcdf_data',
        'name',
        'parameters',
        'metadata',
        'description',
        'color_scheme',
        'bounds',
    ]


class NetCDFImageAdmin(admin.ModelAdmin):
    list_display = ['image', 'slider_index', 'bounds']


class ProcessingTaskAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'status',
        'created',
        'modified',
        'celery_id',
        'metadata',
        'output_metadata',
    )
    list_filter = ('status', 'created', 'modified')
    search_fields = ('name', 'celery_id', 'metadata', 'output_metadata', 'error')
    ordering = ('-created',)
    readonly_fields = ('created', 'modified')
    fieldsets = (
        (None, {'fields': ('name', 'status', 'celery_id', 'error')}),
        (
            'Metadata',
            {
                'classes': ('collapse',),
                'fields': ('metadata', 'output_metadata'),
            },
        ),
        (
            'Timestamps',
            {
                'fields': ('created', 'modified'),
            },
        ),
    )


class VectorFeatureTableDataAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'vector_feature',
        'get_map_layer_name',
        'map_layer',
        'name',
        'type',
        'description',
        'columns',
        'summary',
    ]

    def get_map_layer_name(self, obj):
        return obj.map_layer.name


class VectorFeatureRowDataAdmin(admin.ModelAdmin):
    list_display = ['id', 'vector_feature_table', 'row_data']


class DisplayConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        'enabled_ui',
        'default_tab',
        'default_displayed_layers',
    ]


admin.site.register(Context, ContextAdmin)
admin.site.register(Dataset, DatasetAdmin)
admin.site.register(FileItem, FileItemAdmin)
admin.site.register(Chart, ChartAdmin)
admin.site.register(RasterMapLayer, RasterMapLayerAdmin)
admin.site.register(VectorMapLayer, VectorMapLayerAdmin)
admin.site.register(VectorFeature, VectorFeatureAdmin)
admin.site.register(SourceRegion, SourceRegionAdmin)
admin.site.register(DerivedRegion, DerivedRegionAdmin)
admin.site.register(Network, NetworkAdmin)
admin.site.register(NetworkNode, NetworkNodeAdmin)
admin.site.register(NetworkEdge, NetworkEdgeAdmin)
admin.site.register(SimulationResult, SimulationResultAdmin)
admin.site.register(LayerRepresentation, LayerRepresentationAdmin)
admin.site.register(LayerCollection, LayerCollectionAdmin)
admin.site.register(NetCDFData, NetCDFDataAdmin)
admin.site.register(NetCDFLayer, NetCDFLayerAdmin)
admin.site.register(NetCDFImage, NetCDFImageAdmin)
admin.site.register(ProcessingTask, ProcessingTaskAdmin)
admin.site.register(VectorFeatureTableData, VectorFeatureTableDataAdmin)
admin.site.register(VectorFeatureRowData, VectorFeatureRowDataAdmin)
admin.site.register(DisplayConfiguration, DisplayConfigurationAdmin)
