import { Ref, ref } from 'vue';
import {
  DataDrivenPropertyValueSpecification,
  FilterSpecification,
} from 'maplibre-gl';
import { AnnotationTypes, VectorMapLayer } from '../types';
import MapStore from '../MapStore';
import { calculateColors } from './mapColors';
import { updateProps } from './mapProperties';
import { getLayerDefaultFilter, updateFilters } from './mapFilters';
import { subLayerMapping, updateHeatmap } from './mapHeatmap';
import { getVectorLayerDisplayConfig } from '../utils';

const addedLayers: Ref<VectorMapLayer[]> = ref([]);
const defaultAnnotationColor = 'black';

const internalMap: Ref<maplibregl.Map | null> = ref(null);

const setLayerFilter = (map: maplibregl.Map, layerId: string, filter: FilterSpecification) => {
  if (map.getLayer(layerId)) {
    map.setFilter(layerId, filter);
  }
};

const getSelected = () => {
  const result = [];
  result.push('case');
  result.push(['in', ['get', 'vectorfeatureid'], ['literal', MapStore.selectedIds.value]]);
  result.push('cyan');
  result.push(['has', 'colors']);
  result.push([
    'let',
    'firstColor',
    ['slice', ['get', 'colors'], 0, 7], // assuming each color is in the format '#RRGGBB'
    ['to-color', ['var', 'firstColor']],
  ]);

  // Check if the 'color' field exists and match specific values
  result.push(['has', 'color']);
  result.push([
    'match',
    ['get', 'color'],
    'light blue',
    '#ADD8E6',
    'dark blue',
    '#00008B',
    // add other color mappings here
    ['get', 'color'], // if the color is already in a valid format
  ]);
  result.push(defaultAnnotationColor);
  return result as DataDrivenPropertyValueSpecification<string>;
};

const getLineWidth = () => {
  const result = [];
  result.push('interpolate');
  result.push(['linear']);
  result.push(['zoom']);
  result.push(5);
  result.push(10);
  result.push(7);
  result.push(3);
  result.push(10);
  result.push(1);
  result.push(14);
  result.push(1);

  return result as DataDrivenPropertyValueSpecification<number>;
};

const getFillOpacity = () => {
  const result = 0.8;
  return result as DataDrivenPropertyValueSpecification<number>;
};

const getCircleRadius = () => {
  const result = [];
  result.push('interpolate');
  result.push(['linear']);
  result.push(['zoom']);
  result.push(5);
  result.push(10);
  result.push(7);
  result.push(7);
  result.push(10);
  result.push(7);
  result.push(14);
  result.push(3);

  return result as DataDrivenPropertyValueSpecification<number>;
};

// As selectedIds change we modify how they are drawn
const updateSelected = (map: maplibregl.Map) => {
  MapStore.selectedVectorMapLayers.value.forEach((layer) => {
    calculateColors(map, layer);
  });
};

const baseVectorSource = new URL(
  (import.meta.env.VUE_APP_API_ROOT as string || 'http://localhost:8000/api/v1'),
  window.location.origin,
);

const setVectorInternalMap = (map: Ref<maplibregl.Map>) => {
  internalMap.value = map.value;
};

const toggleVisibility = (map: maplibregl.Map, layer_type: AnnotationTypes, visible: boolean) => {
  MapStore.selectedVectorMapLayers.value.forEach((layer) => {
    const layerMap = {
      circle: `Layer_${layer.id}_circle`,
      line: `Layer_${layer.id}_line`,
      fill: `Layer_${layer.id}_fill`,
      'fill-extrusion': `Layer_${layer.id}_fill-extrusion`,
      text: `Layer_${layer.id}_text`,
    };
    const layerName = layerMap[layer_type];
    if (map.getLayer(layerName)) {
      map.setLayoutProperty(layerName, 'visibility', visible ? 'visible' : 'none');
    }
  });
};
const setLayerProperty = (
  map: maplibregl.Map,
  layerId: number,
  layer_type: AnnotationTypes,
  property: string,
  val: string | number,
  val2?: string | number,
) => {
  const layerMap = {
    circle: `Layer_${layerId}_circle`,
    line: `Layer_${layerId}_line`,
    fill: `Layer_${layerId}_fill`,
    'fill-extrusion': `Layer_${layerId}_fill-extrusion`,
    text: `Layer_${layerId}_text`,
    heatmap: `Layer_${layerId}_heatmap`,
  };
  const layerName = layerMap[layer_type];
  if (map.getLayer(layerName)) {
    if (property === 'zoom') map.setLayerZoomRange(layerName, val as number, (val2 as number) || 24);
  }
};

const toggleVectorMapLayers = (map: maplibregl.Map) => {
  const addLayers: VectorMapLayer[] = [];
  const removeLayers: VectorMapLayer[] = [];
  MapStore.selectedVectorMapLayers.value.forEach((layer) => {
    if (MapStore.visibleMapLayers.value.has(`${layer.type}_${layer.id}`)) {
      addLayers.push(layer as VectorMapLayer);
    }
  });
  const layerTypes: AnnotationTypes[] = ['fill', 'fill-extrusion', 'circle', 'line', 'text', 'heatmap'];
  // Secondary pass to remove anything in Added that is not found in the system.
  addedLayers.value.forEach((item) => {
    if (
      !addLayers.includes(item)
      && map.getSource(`VectorTile_${item.id}`)
      && (
        !MapStore.selectedVectorMapLayers.value.includes(item)
        || !MapStore.visibleMapLayers.value.has(`${item.type}_${item.id}`)
      )
    ) {
      removeLayers.push(item);
    }
  });
  removeLayers.forEach((layer) => {
    layerTypes.forEach((layerType) => {
      if (map.getLayer(`Layer_${layer.id}_${layerType}`)) {
        map.removeLayer(`Layer_${layer.id}_${layerType}`);
      }
    });
    map.removeSource(`VectorTile_${layer.id}`);
  });
  // Now we add the sources that are included
  addLayers.forEach((layer) => {
    if (map.getSource(`VectorTile_${layer.id}`)) {
      return;
    }
    map.addSource(`VectorTile_${layer.id}`, {
      tiles: [`${baseVectorSource}/vectors/${layer.id}/tiles/{z}/{x}/{y}/`],
      type: 'vector',
    });
    map.addLayer({
      id: `Layer_${layer.id}_circle`,
      type: 'circle',
      source: `VectorTile_${layer.id}`,
      'source-layer': 'default',
      filter: getLayerDefaultFilter('circle', layer),
      paint: {
        'circle-color': getSelected(),
        'circle-radius': getCircleRadius(),
        'circle-opacity': 0.5,
        'circle-stroke-width': 1,
        'circle-stroke-color': getSelected(),
      },
    });
    map.addLayer({
      id: `Layer_${layer.id}_line`,
      type: 'line',
      source: `VectorTile_${layer.id}`,
      'source-layer': 'default',
      filter: getLayerDefaultFilter('line'),
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-width': getLineWidth(),
      },
    });
    map.addLayer({
      id: `Layer_${layer.id}_fill`,
      type: 'fill',
      source: `VectorTile_${layer.id}`,
      'source-layer': 'default',
      filter: getLayerDefaultFilter('fill'),
      paint: {
        // "fill-color": getAnnotationColor(),
        'fill-color': 'blue',
        'fill-opacity': getFillOpacity(),
      },
    });

    map.addLayer({
      id: `Layer_${layer.id}_fill-extrusion`,
      source: `VectorTile_${layer.id}`,
      'source-layer': 'default',
      type: 'fill-extrusion',
      filter: getLayerDefaultFilter('fill-extrusion'),
      paint: {
        // "fill-extrusion-color": getAnnotationColor(),
        'fill-extrusion-color': '#888888',
        'fill-extrusion-height': [
          'interpolate',
          ['linear'],
          ['zoom'],
          0,
          0, // Default height at lower zoom levels
          12,
          ['*', ['get', 'render_height'], 2], // Apply twice the render_height at zoom level 16 and above
        ],
      },
    });
    map.addLayer({
      id: `Layer_${layer.id}_text`,
      type: 'symbol',
      source: `VectorTile_${layer.id}`,
      'source-layer': 'default',
      layout: {
        'text-anchor': 'center',
        'text-font': ['Roboto Regular'],
        'text-max-width': 5,
        'text-size': 12,
        'text-allow-overlap': true,
      },
      paint: {
        'text-color': 'black',
      },
    });

    delete subLayerMapping[`Layer_${layer.id}_heatmap`];

    map.addLayer({
      id: `Layer_${layer.id}_heatmap`,
      type: 'heatmap',
      source: `VectorTile_${layer.id}`,
      'source-layer': 'default',
      paint: {
        'heatmap-color': [
          'interpolate',
          ['linear'],
          ['heatmap-density'],
          0,
          'rgba(33,102,172,0)',
          0.2,
          'rgb(103,169,207)',
          0.4,
          'rgb(209,229,240)',
          0.6,
          'rgb(253,219,199)',
          0.8,
          'rgb(239,138,98)',
          1,
          'rgb(178,24,43)',
        ],
      },
    });
  });

  addedLayers.value = addLayers;
  MapStore.selectedVectorMapLayers.value.forEach((layer) => {
    if (MapStore.visibleMapLayers.value.has(`${layer.type}_${layer.id}`)) {
      // eslint-disable-next-line @typescript-eslint/no-use-before-define
      updateVectorLayer(layer);
      if (layer?.default_style.searchableVectorFeatureData) {
        if (layer.default_style.searchableVectorFeatureData.display.autoOpenSideBar) {
          if (MapStore.activeSideBarCard.value !== 'searchableVectors') {
            MapStore.toggleContext('searchableVectors');
          }
        }
      }
    }
  });
};

const toggleLayerTypeVisibility = (
  map: maplibregl.Map,
  layerId: number,
  layer_type: AnnotationTypes,
  visible: boolean,
) => {
  const layerMap = {
    circle: `Layer_${layerId}_circle`,
    line: `Layer_${layerId}_line`,
    fill: `Layer_${layerId}_fill`,
    'fill-extrusion': `Layer_${layerId}_fill-extrusion`,
    text: `Layer_${layerId}_text`,
    heatmap: `Layer_${layerId}_heatmap`,
  };
  const layerName = layerMap[layer_type];
  if (map.getLayer(layerName)) {
    map.setLayoutProperty(layerName, 'visibility', visible ? 'visible' : 'none');
    if (layer_type === 'heatmap' && !visible) {
      delete subLayerMapping[layerName];
    }
  }
};

const updateVectorLayer = (layer: VectorMapLayer) => {
  const layerTypes: AnnotationTypes[] = ['fill', 'fill-extrusion', 'circle', 'line', 'text', 'heatmap'];
  if (!internalMap.value) {
    return;
  }
  layerTypes.forEach((layerType) => {
    if (layer.default_style?.layers) {
      if (!layer.default_style.layers[layerType]) {
        toggleLayerTypeVisibility(internalMap.value as maplibregl.Map, layer.id, layerType, false);
      } else {
        const layerDisplayConfig = layer.default_style.layers[layerType];
        if (layerDisplayConfig !== true && layerDisplayConfig !== undefined) {
          toggleLayerTypeVisibility(
            internalMap.value as maplibregl.Map,
            layer.id,
            layerType,
            layerDisplayConfig?.enabled !== false,
          );
          if (layerDisplayConfig?.zoom) {
            if (
              layerDisplayConfig.zoom.min !== undefined
              || layerDisplayConfig.zoom.max !== undefined
            ) {
              setLayerProperty(
                internalMap.value as maplibregl.Map,
                layer.id,
                layerType,
                'zoom',
                layerDisplayConfig.zoom.min || 0,
                layerDisplayConfig.zoom.max || 0,
              );
            }
          }
          if (!layerDisplayConfig.drawPoints && layerType === 'line' && !layer.default_style.filters?.length) {
            setLayerFilter(
              internalMap.value as maplibregl.Map,
              `Layer_${layer.id}_circle`,
              ['==', ['geometry-type'], 'Point'] as FilterSpecification,
            );
          } else if (layerType === 'line') {
            setLayerFilter(internalMap.value as maplibregl.Map, `Layer_${layer.id}_circle`, true as FilterSpecification);
          }
        } else {
          toggleLayerTypeVisibility(internalMap.value as maplibregl.Map, layer.id, layerType, false);
        }
      }
    }
  });
  calculateColors(internalMap.value as maplibregl.Map, layer);
  updateProps(internalMap.value as maplibregl.Map, layer);
  updateHeatmap(internalMap.value as maplibregl.Map, layer);
};

const centerAndZoom = (center: number[], zoom: number, flyTo = false) => {
  if (internalMap.value !== null) {
    if (!flyTo) {
      internalMap.value.setCenter(center as [number, number]);
      internalMap.value.setZoom(zoom);
    } else {
      internalMap.value.flyTo({
        center: center as [number, number],
        zoom,
      });
    }
  }
};

const updateLayerFilter = (layer: VectorMapLayer) => {
  if (internalMap.value !== null) {
    updateFilters(internalMap.value, layer);
  }
};

export {
  setVectorInternalMap,
  toggleVectorMapLayers,
  toggleVisibility,
  toggleLayerTypeVisibility,
  setLayerProperty,
  setLayerFilter,
  updateSelected,
  updateVectorLayer,
  updateLayerFilter,
  centerAndZoom,
};
