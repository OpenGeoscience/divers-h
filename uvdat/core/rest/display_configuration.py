from typing import Any, Dict

from django.core.exceptions import ValidationError
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from uvdat.core.models import DisplayConfiguration


class LayerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dataset_id = serializers.IntegerField()
    type = serializers.CharField()
    name = serializers.CharField()


class DisplayConfigurationSerializer(serializers.ModelSerializer):
    enabled_ui = serializers.ListField(
        child=serializers.CharField(),
        help_text='List of enabled features: "Collections", "Datasets", "Metadata", "Scenarios".',
    )
    default_tab = serializers.CharField(
        help_text='Default tab, must be one of the enabled features.'
    )
    default_displayed_layers = serializers.ListField(child=LayerSerializer())
    default_map_settings = serializers.JSONField(
        help_text='Map settings, e.g., {"location": {"center": [x, y], "zoom": 5}}.'
    )

    class Meta:
        model = DisplayConfiguration
        fields = ['enabled_ui', 'default_tab', 'default_displayed_layers', 'default_map_settings']

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        enabled_ui = data.get('enabled_ui', [])
        default_tab = data.get('default_tab')
        default_displayed_layers = data.get('default_displayed_layers', [])

        if default_tab not in enabled_ui:
            raise ValidationError(
                {'default_tab': 'The default tab must be one of the enabled features.'}
            )

        if not all(
            isinstance(layer, dict) and 'type' in layer for layer in default_displayed_layers
        ):
            raise ValidationError(
                {'default_displayed_layers': 'Each entry must be a dictionary with a "type" field.'}
            )

        return data


class DisplayConfigurationViewSet(viewsets.GenericViewSet):

    queryset = DisplayConfiguration.objects.all()
    serializer_class = DisplayConfigurationSerializer

    def get_object(self) -> DisplayConfiguration:
        return DisplayConfiguration.objects.first() or DisplayConfiguration.objects.create()

    @action(detail=False, methods=['get'], url_path='display-configuration')
    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['put'], url_path='display-configuration')
    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'], url_path='display-configuration')
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
