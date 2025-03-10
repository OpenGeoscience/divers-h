import { Ref, ref } from 'vue';
import { setRasterInternalMap, toggleRasterMapLayers, updateRasterLayer } from './mapRasterLayers';
import { setVectorInternalMap, toggleVectorMapLayers, updateVectorLayer } from './mapVectorLayers';
import {
  AbstractMapLayer, AnnotationTypes, Bounds, NetCDFLayer, RasterMapLayer, VectorMapLayer,
} from '../types';
import { setPopupEvents } from './mouseEvents';
import MapStore from '../MapStore';
import { setNetCDFInternalMap, toggleNetCDFMapLayers } from './mapNetCDFLayer';

const internalMap: Ref<maplibregl.Map | null> = ref(null);
const setInternalMap = (map: Ref<maplibregl.Map>) => {
  internalMap.value = map.value;
  if (map.value) {
    setVectorInternalMap(map);
    setRasterInternalMap(map);
    setNetCDFInternalMap(map);
  }
};

const reorderMapLayers = () => {
  const map = internalMap.value;
  // Define the sub-layer types to be reordered
  const layerTypes: AnnotationTypes[] = ['fill', 'fill-extrusion', 'circle', 'line', 'heatmap', 'text'];
  // Loop through each selected layer in the desired order
  MapStore.selectedMapLayers.value.forEach(
    (layer: VectorMapLayer | RasterMapLayer | NetCDFLayer) => {
      // Get the base ID for the current layer
      const layerBaseId = layer.id;

      const layerNames = [];
      if (layer.type === 'vector') {
        layerTypes.forEach((layerType) => {
          layerNames.push(`Layer_${layerBaseId}_${layerType}`);
        });
      } else if (layer.type === 'raster') {
        layerNames.push(`Layer_${layerBaseId}_raster`);
      } else if (layer.type === 'netcdf') {
        layerNames.push(`NetCDFLayer_${layerBaseId}`);
      }

      layerNames.forEach((layerName) => {
        if (map && map.getLayer(layerName)) {
          map.moveLayer(layerName);
        }
      });
    },
  );
};

const toggleMapLayers = () => {
  if (internalMap.value) {
    toggleVectorMapLayers(internalMap.value);
    toggleRasterMapLayers(internalMap.value);
    toggleNetCDFMapLayers(internalMap.value);
    reorderMapLayers();
  }
};

const updateLayer = (layer: AbstractMapLayer) => {
  if (layer.type === 'vector') {
    updateVectorLayer(layer as VectorMapLayer);
  } else if (layer.type === 'raster') {
    updateRasterLayer(layer as RasterMapLayer);
  }
  setPopupEvents(internalMap.value as maplibregl.Map);
};

const zoomToBounds = (bbox: Bounds) => {
  if (internalMap.value) {
    internalMap.value.fitBounds(
      [
        [bbox.xmin, bbox.ymin],
        [bbox.xmax, bbox.ymax],
      ],
      {
        padding: 20,
        offset: [0, 0],
      },
    );
  }
};

const getStringBBox = () => {
  if (internalMap.value) {
    const bounds = internalMap.value.getBounds();
    return bounds.toArray().join(',');
  }
  return '';
};

const toggleLayerVisibility = (layer: VectorMapLayer | RasterMapLayer | NetCDFLayer, visibility: boolean) => {
  if (visibility) {
    MapStore.visibleMapLayers.value.add(`${layer.type}_${layer.id}`);
  } else {
    MapStore.visibleMapLayers.value.delete(`${layer.type}_${layer.id}`);
  }
  toggleMapLayers();
};

const toggleLayerSelection = (layer: VectorMapLayer | RasterMapLayer | NetCDFLayer) => {
  const foundIndex = MapStore.selectedMapLayers.value.findIndex((item) => (item.id === layer.id));
  if (foundIndex !== -1) {
    MapStore.selectedMapLayers.value.splice(foundIndex, 1);
    toggleLayerVisibility(layer, false);
  } else {
    MapStore.selectedMapLayers.value = [...MapStore.selectedMapLayers.value, layer];
    toggleLayerVisibility(layer, true);
    setPopupEvents(internalMap.value as maplibregl.Map);
  }
};

const getCenterAndZoom = () => {
  if (internalMap.value) {
    const val = internalMap.value.getCenter();
    const center = [val.lng, val.lat] as [number, number];
    const zoom = internalMap.value.getZoom();
    return {
      center,
      zoom,
    };
  }
  return {
    center: [-75.5, 43.0] as [number, number], // Coordinates for the center of New York State
    zoom: 7, // Initial zoom level
  };
};

export {
  toggleMapLayers,
  setInternalMap,
  updateLayer,
  reorderMapLayers,
  zoomToBounds,
  getStringBBox,
  toggleLayerSelection,
  toggleLayerVisibility,
  getCenterAndZoom,
  internalMap,
};
