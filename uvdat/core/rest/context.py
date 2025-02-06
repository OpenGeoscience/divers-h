from django.contrib.gis.geos import Point
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from uvdat.core.models import Context
from uvdat.core.rest.serializers import ContextSerializer
from uvdat.core.tasks.osmnx import load_roads

from .permissions import DefaultPermission


class ContextViewSet(ModelViewSet):
    queryset = Context.objects.all()
    serializer_class = ContextSerializer
    permission_classes = [DefaultPermission]

    def create(self, request, *args, **kwargs):
        name = request.data.get('name')
        default_map_zoom = request.data.get('default_map_zoom')
        datasets = request.data.get('datasets')
        default_map_center = request.data.get('default_map_center')

        point = Point(default_map_center[1], default_map_center[0])
        context = Context.objects.create(
            name=name,
            default_map_zoom=default_map_zoom,
            default_map_center=point,
        )
        context.datasets.set(datasets)

        # Serialize the created file item
        serializer = self.get_serializer(context)

        return Response(serializer.data, status=201)

    @action(detail=True, methods=['patch'], url_path='all')
    def update_all_fields(self, request, pk=None):
        instance = self.get_object()

        # Get fields from the request
        name = request.data.get('name', instance.name)
        default_map_zoom = request.data.get('default_map_zoom', instance.default_map_zoom)
        datasets = request.data.get('datasets', None)
        default_map_center = request.data.get('default_map_center', None)

        # Update fields only if they are present in the request
        if name:
            instance.name = name
        if default_map_zoom:
            instance.default_map_zoom = default_map_zoom
        if default_map_center:
            point = Point(default_map_center[1], default_map_center[0])
            instance.default_map_center = point
        if datasets is not None:
            instance.datasets.set(datasets)

        # Save the instance
        instance.save()

        # Serialize the updated instance
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def regions(self, request, **kwargs):
        context = self.get_object()
        regions = context.derived_regions.all()
        return HttpResponse(regions, status=200)

    @action(detail=True, methods=['get'])
    def simulation_results(self, request, **kwargs):
        context = self.get_object()
        simulation_results = context.simulation_results.all()
        return HttpResponse(simulation_results, status=200)

    @action(
        detail=True,
        methods=['get'],
        url_path=r'load_roads/(?P<location>.+)',
    )
    def load_roads(self, request, location, **kwargs):
        context = self.get_object()
        load_roads.delay(context.id, location)
        return HttpResponse('Task spawned successfully.', status=200)
