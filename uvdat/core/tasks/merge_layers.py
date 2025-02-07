from celery import shared_task
from django.contrib.gis.geos import GEOSGeometry
from uvdat.core.models import VectorMapLayer
import json
from typing import List, Optional, Literal


@shared_task
def merge_vector_layer_data(
    base_layer_id: int,
    other_layer_ids: List[int],
    operation: Literal['intersection', 'complete_overlap'] = 'intersection',
    exclude_non_overlapping: bool = False,
    properties_to_merge: Optional[List[str]] = None
) -> dict:
    try:
        base_layer = VectorMapLayer.objects.get(id=base_layer_id)
        base_geojson = base_layer.read_geojson_data()
        # Extract base features
        base_features = base_geojson.get('features', [])
        filtered_features = []
        # Fetch specified vector map layers
        other_layers = VectorMapLayer.objects.filter(id__in=other_layer_ids)
        for base_feature in base_features:
            base_geom = GEOSGeometry(json.dumps(base_feature['geometry']))
            base_feature['overlapping_properties'] = []
            has_overlap = False
            for layer in other_layers:
                layer_geojson = layer.read_geojson_data()
                for feature in layer_geojson.get('features', []):
                    feature_geom = GEOSGeometry(json.dumps(feature['geometry']))
                    if operation == 'intersection' and base_geom.intersects(feature_geom):
                        properties = feature['properties']
                        if properties_to_merge:
                            properties = {k: v for k, v in properties.items() if k in properties_to_merge}
                        base_feature['overlapping_properties'].append(properties)
                        has_overlap = True
                    elif operation == 'complete_overlap' and base_geom.covers(feature_geom):
                        properties = feature['properties']
                        if properties_to_merge:
                            properties = {k: v for k, v in properties.items() if k in properties_to_merge}
                        base_feature['overlapping_properties'].append(properties)
                        has_overlap = True
            if not exclude_non_overlapping or has_overlap:
                filtered_features.append(base_feature)

        # Save the updated GeoJSON
        updated_geojson = {'type': 'FeatureCollection', 'features': filtered_features}
        base_layer.write_geojson_data(updated_geojson)
        return {'status': 'success', 'message': 'Vector processing completed.'}

    except VectorMapLayer.DoesNotExist:
        return {'status': 'error', 'message': 'Base layer not found.'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
