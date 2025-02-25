from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from uvdat.core.models import NetCDFLayer, RasterMapLayer, VectorMapLayer


class MetadataFilterViewSet(viewsets.GenericViewSet):
    # Custom action to handle metadata filtering (GET request)
    @action(detail=False, methods=['get'])
    def get_filters(self, request, *args, **kwargs):
        models = [RasterMapLayer, VectorMapLayer, NetCDFLayer]

        filters = {}

        for model in models:
            layers = model.objects.all()

            for layer in layers:
                if layer.metadata is None:
                    continue
                metadata = layer.metadata.get('tags', {}).get('filters', {})
                for key, value in metadata.items():
                    if value is not None:
                        if key not in filters:
                            filters[key] = set()
                        filters[key].update(value if (isinstance(value, list) and len(value)) else [value])

        # Convert sets to lists for JSON response
        filters = {key: list(value) for key, value in filters.items()}
        return Response(filters)

    # Custom action to handle filtering layers based on provided filters (POST request)
    @action(detail=False, methods=['post'])
    def filter_layers(self, request, *args, **kwargs):
        filters = request.data  # DRF will automatically parse the JSON body

        # Collecting all models
        models = [RasterMapLayer, VectorMapLayer, NetCDFLayer]
        matching_ids = []
        type_mapper = {'RasterMapLayer': 'raster', 'VectorMapLayer': 'vector', 'NetCDFLayer': 'netcdf'}
        for model in models:
            layers = model.objects.all()

            for layer in layers:
                if layer.metadata is None:
                    continue
                metadata = layer.metadata.get('tags', {}).get('filters', {})
                match = True
                matches = {}
                for key, values in filters.items():
                    if key in metadata:
                        for value in values:
                            if (value not in metadata[key]):
                                match = False
                                break
                            else:
                                matches[key] = value


                if match:
                    matching_ids.append({
                        'id': layer.id,
                        'name': layer.name,
                        'type': type_mapper[model.__name__],
                        'matches': matches
                    })
        return Response(matching_ids)
