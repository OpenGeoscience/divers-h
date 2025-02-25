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
                metadata = layer.metadata.get('tags', {}).get('filters', {})
                for key, value in metadata.items():
                    if key not in filters:
                        filters[key] = set()
                    filters[key].update(value if isinstance(value, list) else [value])

        # Convert sets to lists for JSON response
        filters = {key: list(value) for key, value in filters.items()}
        return Response(filters)

    # Custom action to handle filtering layers based on provided filters (POST request)
    @action(detail=False, methods=['post'])
    def filter_layers(self, request, *args, **kwargs):
        filters = request.data  # DRF will automatically parse the JSON body

        # Collecting all models
        models = [RasterMapLayer, VectorMapLayer, NetCDFLayer]
        matching_ids = {'RasterMapLayer': [], 'VectorMapLayer': [], 'NetCDFLayer': []}

        for model in models:
            layers = model.objects.all()

            for layer in layers:
                metadata = layer.metadata.get('tags', {}).get('filters', {})
                match = True
                for key, values in filters.items():
                    if key in metadata:
                        if not any(value in metadata[key] for value in values):
                            match = False
                            break
                    else:
                        match = False
                        break
                if match:
                    matching_ids[model.__name__].append(layer.id)

        return Response(matching_ids)
