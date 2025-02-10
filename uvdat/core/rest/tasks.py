from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from rest_framework.serializers import Serializer, IntegerField, CharField, BooleanField, ListField
from uvdat.core.tasks.merge_layers import merge_vector_layer_data
from .permissions import DefaultPermission

class MergeVectorLayerSerializer(Serializer):
    base_layer_id = IntegerField()
    other_layer_ids = ListField(child=IntegerField())
    dataset_name = CharField(max_length=255)
    operation = CharField(default='intersection')
    exclude_non_overlapping = BooleanField(default=True)
    properties_to_merge = ListField(child=CharField(), required=False, allow_null=True)

class TasksAPIView(ViewSet):
    permission_classes = [DefaultPermission]

    @extend_schema(request=MergeVectorLayerSerializer)
    @action(detail=False, methods=['post'], url_path='merge-vector-layer')
    def post(self, request, *args, **kwargs):
        serializer = MergeVectorLayerSerializer(data=request.data)
        if serializer.is_valid():
            merge_vector_layer_data.delay(
                base_layer_id=serializer.validated_data['base_layer_id'],
                other_layer_ids=serializer.validated_data['other_layer_ids'],
                dataset_name=serializer.validated_data['dataset_name'],
                operation=serializer.validated_data['operation'],
                exclude_non_overlapping=serializer.validated_data['exclude_non_overlapping'],
                properties_to_merge=serializer.validated_data.get('properties_to_merge')
            )
            return Response({'status': 'success', 'message': 'Task has been initiated.'}, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)