import logging

from rest_framework.viewsets import ModelViewSet

from uvdat.core.models import LayerCollection
from uvdat.core.rest.serializers import LayerCollectionSerializer

from .permissions import DefaultPermission

logger = logging.getLogger(__name__)


class LayerCollectionViewSet(ModelViewSet):
    serializer_class = LayerCollectionSerializer
    queryset = LayerCollection.objects.all()  # Default queryset
    permission_classes = [DefaultPermission]
