from rest_framework.viewsets import ModelViewSet

from uvdat.core.models import Network, NetworkEdge, NetworkNode
from uvdat.core.rest.serializers import (
    NetworkEdgeSerializer,
    NetworkNodeSerializer,
    NetworkSerializer,
)

from .permissions import DefaultPermission


class NetworkViewSet(ModelViewSet):
    queryset = Network.objects.all()
    serializer_class = NetworkSerializer
    permission_classes = [DefaultPermission]


class NetworkNodeViewSet(ModelViewSet):
    queryset = NetworkNode.objects.all()
    serializer_class = NetworkNodeSerializer
    permission_classes = [DefaultPermission]


class NetworkEdgeViewSet(ModelViewSet):
    queryset = NetworkEdge.objects.all()
    serializer_class = NetworkEdgeSerializer
    permission_classes = [DefaultPermission]
