import json

from django.db.models import Count
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from uvdat.core.models import (
    Dataset,
    FileItem,
    FMVLayer,
    NetCDFData,
    NetworkEdge,
    NetworkNode,
    RasterMapLayer,
    VectorMapLayer,
)
from uvdat.core.rest import serializers as uvdat_serializers
from uvdat.core.tasks.chart import add_gcc_chart_datum

from .permissions import DefaultPermission


class DatasetViewSet(ModelViewSet):
    serializer_class = uvdat_serializers.DatasetSerializer
    filterset_fields = ['name']
    permission_classes = [DefaultPermission]

    def get_queryset(self):
        context_id = self.request.query_params.get('context')
        unconnected = self.request.query_params.get('unconnected')
        if context_id:
            return Dataset.objects.filter(context__id=context_id).order_by('created', 'modified')
        elif unconnected and unconnected != 'false':
            # Filter datasets that are not linked to any context
            return Dataset.objects.filter(context=None).order_by('created', 'modified')
        else:
            return (
                Dataset.objects.all()
                .annotate(contextCount=Count('context'))
                .order_by('created', 'modified')
            )

    @action(detail=True, methods=['get'])
    def file_items(self, request, **kwargs):
        dataset = self.get_object()
        file_items = FileItem.objects.filter(dataset=dataset)
        serializer = uvdat_serializers.FileItemSerializer(file_items, many=True)
        return Response(serializer.data, status=200)

    @action(detail=True, methods=['get'])
    def map_layers(self, request, **kwargs):
        dataset: Dataset = self.get_object()
        map_layers = list(dataset.get_map_layers())

        # Combine both Raster and Vector map layers in a single list
        raster_layers = uvdat_serializers.RasterMapLayerSerializer(
            [layer for layer in map_layers if isinstance(layer, RasterMapLayer)], many=True
        ).data

        vector_layers = uvdat_serializers.VectorMapLayerSerializer(
            [layer for layer in map_layers if isinstance(layer, VectorMapLayer)], many=True
        ).data

        netcdf_data = uvdat_serializers.NetCDFDataSerializer(
            [layer for layer in map_layers if isinstance(layer, NetCDFData)], many=True
        ).data

        fmv_layers = uvdat_serializers.FMVLayerSerializer(
            [layer for layer in map_layers if isinstance(layer, FMVLayer)], many=True
        ).data

        # Combine both serialized data
        combined_layers = raster_layers + vector_layers + netcdf_data + fmv_layers

        # Return response with combined data
        return Response(combined_layers, status=200)

    @action(detail=False, methods=['get'], url_path='map_layers')
    def map_layers_from_datasets(self, request, **kwargs):
        dataset_ids = request.query_params.getlist('datasetIds', [])
        datasets = Dataset.objects.filter(id__in=dataset_ids)
        total_layers = []
        for dataset in datasets:
            map_layers = list(dataset.get_map_layers())

            # Combine both Raster and Vector map layers in a single list
            raster_layers = uvdat_serializers.RasterMapLayerSerializer(
                [layer for layer in map_layers if isinstance(layer, RasterMapLayer)], many=True
            ).data

            vector_layers = uvdat_serializers.VectorMapLayerSerializer(
                [layer for layer in map_layers if isinstance(layer, VectorMapLayer)], many=True
            ).data

            netcdf_data = uvdat_serializers.NetCDFDataSerializer(
                [layer for layer in map_layers if isinstance(layer, NetCDFData)], many=True
            ).data

            fmv_layers = uvdat_serializers.FMVLayerSerializer(
                [layer for layer in map_layers if isinstance(layer, FMVLayer)], many=True
            ).data

            # Combine both serialized data
            combined_layers = raster_layers + vector_layers + netcdf_data + fmv_layers
            total_layers += combined_layers

        # Return response with combined data
        return Response(total_layers, status=200)

    @action(detail=True, methods=['get'])
    def convert(self, request, **kwargs):
        dataset = self.get_object()
        dataset.spawn_conversion_task()
        return HttpResponse(status=200)

    @action(detail=True, methods=['get'])
    def network(self, request, **kwargs):
        dataset = self.get_object()
        networks = []
        for network in dataset.networks.all():
            networks.append(
                [
                    {
                        'nodes': [
                            uvdat_serializers.NetworkNodeSerializer(n).data
                            for n in NetworkNode.objects.filter(network=network)
                        ],
                        'edges': [
                            uvdat_serializers.NetworkEdgeSerializer(e).data
                            for e in NetworkEdge.objects.filter(network=network)
                        ],
                    }
                ]
            )
        return HttpResponse(json.dumps(networks), status=200)

    @action(detail=True, methods=['get'])
    def gcc(self, request, **kwargs):
        dataset = self.get_object()
        context_id = request.query_params.get('context')
        exclude_nodes = request.query_params.get('exclude_nodes', [])
        exclude_nodes = exclude_nodes.split(',')
        exclude_nodes = [int(n) for n in exclude_nodes if len(n)]

        # TODO: improve this for datasets with multiple networks;
        # this currently returns the gcc for the network with the most excluded nodes
        results = []
        for network in dataset.networks.all():
            excluded_node_names = [n.name for n in network.nodes.all() if n.id in exclude_nodes]
            gcc = network.get_gcc(exclude_nodes)
            results.append(dict(excluded=excluded_node_names, gcc=gcc))
        if len(results):
            results.sort(key=lambda r: len(r.get('excluded')), reverse=True)
            gcc = results[0].get('gcc')
            excluded = results[0].get('excluded')
            add_gcc_chart_datum(dataset, context_id, excluded, len(gcc))
            return HttpResponse(json.dumps(gcc), status=200)
