from typing import Any, Dict, List

from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import CharField, DictField, ListField, ModelSerializer

from uvdat.core.models import DisplayConfiguration


class DisplayConfigurationSerializer(ModelSerializer):
    enabled_ui = ListField(
        child=CharField(),
        help_text='List of enabled features: "Collections", "Datasets", "Metadata".',
    )
    default_tab = CharField(help_text='Default tab, must be one of the enabled features.')
    default_displayed_layers = ListField(
        child=DictField(child=CharField()),
        help_text='List of map layers: [{type: "netcdf"}, {type: "vector"}, {type: "raster"}].',
    )

    class Meta:
        model = DisplayConfiguration
        fields = ['enabled_ui', 'default_tab', 'default_displayed_layers']

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        '''Ensure `default_tab` is within `enabled_ui` and validate `default_displayed_layers`.'''
        enabled_ui = data.get('enabled_ui', [])
        default_tab = data.get('default_tab')
        default_displayed_layers = data.get('default_displayed_layers', [])

        if default_tab not in enabled_ui:
            raise ValidationError({'default_tab': 'The default tab must be one of the enabled features.'})

        if not all(isinstance(layer, dict) and 'type' in layer for layer in default_displayed_layers):
            raise ValidationError({'default_displayed_layers': 'Each entry must be a dictionary with a "type" field.'})

        return data


class DisplayConfigurationViewSet(viewsets.GenericViewSet):
    '''
    ViewSet for managing the single Display Configuration instance.

    - `GET /display_configuration/`: Retrieve the current configuration.
    - `PATCH /display_configuration/`: Partially update the configuration.
    - `PUT /display_configuration/`: Fully update the configuration.
    '''

    queryset = DisplayConfiguration.objects.all()
    serializer_class = DisplayConfigurationSerializer

    def get_object(self) -> DisplayConfiguration:
        '''Retrieve or create the single Configuration instance.'''
        return DisplayConfiguration.objects.first() or DisplayConfiguration.objects.create()

    @action(detail=False, methods=['get'], url_path='display-configuration')
    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        '''Retrieve the single Display Configuration.'''
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['put'], url_path='display-configuration')
    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        '''Fully replace the configuration (PUT request).'''
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'], url_path='display-configuration')
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        '''Partially update the configuration (PATCH request).'''
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
