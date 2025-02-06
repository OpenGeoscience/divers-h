import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from uvdat.core.models import LayerRepresentation, RasterMapLayer, VectorMapLayer
from uvdat.core.rest.serializers import LayerRepresentationSerializer

from .permissions import DefaultPermission

logger = logging.getLogger(__name__)


class LayerRepresentationViewSet(ModelViewSet):
    serializer_class = LayerRepresentationSerializer
    queryset = LayerRepresentation.objects.all()  # Default queryset
    permission_classes = [DefaultPermission]

    @action(detail=False, methods=['get'], url_path='map-layer/(?P<layer_id>[^/.]+)')
    def map_layer(self, request, layer_id=None):
        layer_type = request.query_params.get('type')
        try:
            # Try to retrieve the corresponding MapLayer (Raster or Vector)
            map_layer = None
            if layer_type == 'raster':
                map_layer = RasterMapLayer.objects.get(id=layer_id)
            else:
                map_layer = VectorMapLayer.objects.get(id=layer_id)

            # Filter LayerRepresentation objects by the object_id (MapLayer ID)
            layer_representations = LayerRepresentation.objects.filter(object_id=layer_id)

            # Prepare the response data
            data = self._add_type_to_representations(layer_representations)

            # Create the default representation
            default_representation = {
                'id': -1,
                'name': 'Default',
                'description': 'Default Styling',
                'default_style': map_layer.default_style,  # Get the default_style from the MapLayer
                'type': layer_type,
                'enabled': True,
            }

            # Check if any layer representations exist
            if data:
                # Append the default representation only if there are existing representations
                data.insert(0, default_representation)
            else:
                # If no layer representations exist, return just the default representation
                data = [default_representation]

            return Response(data, status=status.HTTP_200_OK)

        except ValueError:
            return Response(
                {'detail': 'Invalid MapLayer ID format.'}, status=status.HTTP_400_BAD_REQUEST
            )

    def _add_type_to_representations(self, layer_representations):
        serializer = self.get_serializer(layer_representations, many=True)
        data = serializer.data

        # Prepend the basic default_style:
        for item in data:
            # If there is a different field to check, update here.
            item_type = 'vector' if item.get('map_type') == 'vector' else 'raster'
            item['type'] = item_type

        return data
