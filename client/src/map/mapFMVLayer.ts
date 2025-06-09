/* eslint-disable @typescript-eslint/no-unused-vars */
import { Ref, ref } from 'vue';
import {
  DataDrivenPropertyValueSpecification,
  FilterSpecification,
  VideoSource,
} from 'maplibre-gl';
import { difference, union } from 'lodash';
import { AnnotationTypes, FMVLayer } from '../types';
import MapStore from '../MapStore';
import { getLayerDefaultFilter } from './mapFilters';
import { subLayerMapping } from './mapHeatmap';
import { FMVStore, getFMVStore } from './fmvStore';

const addedLayers: Ref<FMVLayer[]> = ref([]);
const defaultAnnotationColor = 'black';
const internalMap: Ref<maplibregl.Map | null> = ref(null);

const fmvStoreMap : Record<number, FMVStore> = {};

const setLayerFilter = (map: maplibregl.Map, layerId: string, filter: FilterSpecification | null) => {
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
  MapStore.selectedFMVMapLayers.value.forEach((layer) => {
    console.log('need to implement selection coloring toggling');
  });
};

const baseVectorSource = new URL(
  (import.meta.env.VUE_APP_API_ROOT as string || 'http://localhost:8000/api/v1'),
  window.location.origin,
);

const setFMVInternalMap = (map: Ref<maplibregl.Map>) => {
  internalMap.value = map.value;
};

const toggleVisibility = (map: maplibregl.Map, layer_type: AnnotationTypes, visible: boolean) => {
  MapStore.selectedFMVMapLayers.value.forEach((layer) => {
    const layerMap = {
      circle: `FMVLayer_${layer.id}_circle`,
      line: `FMVLayer_${layer.id}_line`,
      fill: `FMVLayer_${layer.id}_fill`,
      'fill-extrusion': `FMVLayer_${layer.id}_fill-extrusion`,
      text: `FMVLayer_${layer.id}_text`,
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
    circle: `FMVLayer_${layerId}_circle`,
    line: `FMVLayer_${layerId}_line`,
    fill: `FMVLayer_${layerId}_fill`,
    'fill-extrusion': `FMVLayer_${layerId}_fill-extrusion`,
    text: `FMVLayer_${layerId}_text`,
    heatmap: `FMVLayer_${layerId}_heatmap`,
  };
  const layerName = layerMap[layer_type];
  if (map.getLayer(layerName)) {
    if (property === 'zoom') map.setLayerZoomRange(layerName, val as number, (val2 as number) || 24);
  }
};

const toggleFMVMapLayers = async (map: maplibregl.Map) => {
  const addLayers: FMVLayer[] = [];
  const removeLayers: FMVLayer[] = [];
  MapStore.selectedFMVMapLayers.value.forEach((layer) => {
    if (MapStore.visibleMapLayers.value.has(`${layer.type}_${layer.id}`)) {
      addLayers.push(layer as FMVLayer);
    }
  });
  const layerTypes: AnnotationTypes[] = ['fill', 'fill-extrusion', 'circle', 'line', 'text', 'heatmap'];
  // Secondary pass to remove anything in Added that is not found in the system.
  addedLayers.value.forEach((item) => {
    if (
      !addLayers.includes(item)
      && map.getSource(`FMVVectorTile_${item.id}`)
      && (
        !MapStore.selectedFMVMapLayers.value.includes(item)
        || !MapStore.visibleMapLayers.value.has(`${item.type}_${item.id}`)
      )
    ) {
      removeLayers.push(item);
    }
  });
  removeLayers.forEach((layer) => {
    layerTypes.forEach((layerType) => {
      if (map.getLayer(`FMVLayer_${layer.id}_${layerType}`)) {
        map.removeLayer(`FMVLayer_${layer.id}_${layerType}`);
      }
    });
    map.removeLayer(`FMVLayer_${layer.id}_video`);
    map.removeSource(`FMVVectorTile_${layer.id}`);
    map.removeSource(`FMVVideoSource_${layer.id}`);
  });
  // Now we add the sources that are included
  const stores = await Promise.all(addLayers.map((layer) => getFMVStore(layer.id)));
  addLayers.forEach((layer, idx) => {
    const fmvStore = stores[idx];
    fmvStoreMap[layer.id] = fmvStore;
    let skipVector = false;
    if (map.getSource(`FMVVectorTile_${layer.id}`)) {
      skipVector = true;
    }
    if (!skipVector) {
      map.addSource(`FMVVectorTile_${layer.id}`, {
        tiles: [`${baseVectorSource}/fmv-layer/${layer.id}/tiles/{z}/{x}/{y}/`],
        type: 'vector',
      });
      map.addLayer({
        id: `FMVLayer_${layer.id}_circle`,
        type: 'circle',
        source: `FMVVectorTile_${layer.id}`,
        'source-layer': 'default',
        paint: {
          'circle-color': getSelected(),
          'circle-radius': getCircleRadius(),
          'circle-opacity': 0.5,
          'circle-stroke-width': 1,
          'circle-stroke-color': getSelected(),
        },
      });
      map.addLayer({
        id: `FMVLayer_${layer.id}_line`,
        type: 'line',
        source: `FMVVectorTile_${layer.id}`,
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
        id: `FMVLayer_${layer.id}_fill`,
        type: 'fill',
        source: `FMVVectorTile_${layer.id}`,
        'source-layer': 'default',
        filter: getLayerDefaultFilter('fill'),
        paint: {
        // "fill-color": getAnnotationColor(),
          'fill-color': 'blue',
          'fill-opacity': getFillOpacity(),
        },
      });
      map.addLayer({
        id: `FMVLayer_${layer.id}_text`,
        type: 'symbol',
        source: `FMVVectorTile_${layer.id}`,
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
    }

    const coordinates = fmvStore.getBoundsAtFrame(0);
    map.addSource(`FMVVideoSource_${layer.id}`, {
      type: 'video',
      urls: [fmvStore.videoData.videoUrl],
      coordinates,
    });
    map.addLayer({
      id: `FMVLayer_${layer.id}_video`,
      type: 'raster',
      source: `FMVVideoSource_${layer.id}`,
      paint: {
        'raster-opacity': 1,
        'raster-fade-duration': 0,
      },
    });
    map.on('sourcedata', function handleVideoSourceLoad(e) {
      if (
        e.sourceId === `FMVVideoSource_${layer.id}`
    && e.isSourceLoaded
    && map.getSource(e.sourceId)
      ) {
        const videoSource = map.getSource(e.sourceId) as VideoSource;
        const video = videoSource.getVideo();
        fmvStore.setVideoSource(videoSource);

        if (video) {
          // Remove this listener after it's done
          map.off('sourcedata', handleVideoSourceLoad);
        }
      }
    });

    delete subLayerMapping[`FMVLayer_${layer.id}_heatmap`];
  });

  addedLayers.value = addLayers;
  MapStore.selectedFMVMapLayers.value.forEach((layer) => {
    if (MapStore.visibleMapLayers.value.has(`${layer.type}_${layer.id}`)) {
      // eslint-disable-next-line @typescript-eslint/no-use-before-define
      updateFMVLayer(layer);
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
    circle: `FMVLayer_${layerId}_circle`,
    line: `FMVLayer_${layerId}_line`,
    fill: `FMVLayer_${layerId}_fill`,
    'fill-extrusion': `FMVLayer_${layerId}_fill-extrusion`,
    text: `FMVLayer_${layerId}_text`,
    heatmap: `FMVLayer_${layerId}_heatmap`,
  };
  const layerName = layerMap[layer_type];
  if (map.getLayer(layerName)) {
    map.setLayoutProperty(layerName, 'visibility', visible ? 'visible' : 'none');
    if (layer_type === 'heatmap' && !visible) {
      delete subLayerMapping[layerName];
    }
  }
};

const updateFrameFilter = async (layer: FMVLayer) => {
  if (!internalMap.value) return;

  const fmvStore = fmvStoreMap[layer.id];
  const baseFilters: FilterSpecification[] = [];

  // Filter to specific frameId
  if (fmvStore.filterFrameStatus.value) {
    baseFilters.push(['any', ['==', ['get', 'fmvType'], 'ground_union'], ['==', ['get', 'frameId'], fmvStore.frameId.value]]);
  }

  // Filter to visible fmvTypes
  if (fmvStore.visibleProperties.value.length > 0) {
    baseFilters.push([
      'in',
      ['get', 'fmvType'],
      ['literal', fmvStore.visibleProperties.value],
    ]);
  }

  const layerTypes: AnnotationTypes[] = [
    'fill',
    'fill-extrusion',
    'circle',
    'line',
    'text',
    'heatmap',
  ];

  // eslint-disable-next-line no-restricted-syntax
  for (const layerType of layerTypes) {
    const layerName = `FMVLayer_${layer.id}_${layerType}`;
    const filters = [...baseFilters];

    // If it's a line layer, restrict geometry to LineString
    if (layerType === 'circle') {
      filters.push(['==', ['geometry-type'], 'Point']);
    }

    const finalFilter: FilterSpecification = filters.length === 1 ? filters[0] : ['all', ...filters];

    setLayerFilter(internalMap.value, layerName, finalFilter);
  }
};

type LatLon = [number, number]; // [longitude, latitude]
type Bounds = [LatLon, LatLon, LatLon, LatLon];

function boundsToBBoxWithMultiplier(
  bounds: [[number, number], [number, number], [number, number], [number, number]],
  sizeMultiplier: number = 1
): [number, number, number, number] {
  // Extract all lats and lons
  const lons = bounds.map(([lon, _]) => lon);
  const lats = bounds.map(([_, lat]) => lat);

  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);

  const centerLon = (minLon + maxLon) / 2;
  const centerLat = (minLat + maxLat) / 2;

  const halfWidth = (maxLon - minLon) / 2 * sizeMultiplier;
  const halfHeight = (maxLat - minLat) / 2 * sizeMultiplier;

  return [
    centerLon - halfWidth, // minLon
    centerLat - halfHeight, // minLat
    centerLon + halfWidth, // maxLon
    centerLat + halfHeight // maxLat
  ];
}

const updateFMVVideoMapping = (layer: FMVLayer) => {
  if (!internalMap.value) return;
  const fmvStore = fmvStoreMap[layer.id];
  if (fmvStore && fmvStore.videoData) {
    const coordinates = fmvStore.getBoundsAtFrame(fmvStore.frameId.value);
    const source = internalMap.value.getSource(`FMVVideoSource_${layer.id}`);
    if (source) {
      (source as maplibregl.VideoSource).setCoordinates(coordinates);
    }
    if (fmvStore.lockZoom.value) {
      const bounds = boundsToBBoxWithMultiplier(coordinates, fmvStore.zoomBounds.value);
      internalMap.value.fitBounds(bounds, { linear: false });
    }
  }
};

const updateFMVLayer = (layer: FMVLayer) => {
  const layerTypes: AnnotationTypes[] = ['fill', 'fill-extrusion', 'circle', 'line', 'text', 'heatmap'];
  if (!internalMap.value) {
    return;
  }
  layerTypes.forEach((layerType) => {
    if (layerType === 'line') {
      setLayerFilter(
        internalMap.value as maplibregl.Map,
        `FMVLayer_${layer.id}_circle`,
        ['==', ['geometry-type'], 'Point'] as FilterSpecification,
      );
    }
  });
  const fmvStore = fmvStoreMap[layer.id];
  if (fmvStore && internalMap.value) {
    const videoLayerName = `FMVLayer_${layer.id}_video`;
    if (!fmvStore.visibleProperties.value.includes('video')) {
      internalMap.value.setLayoutProperty(videoLayerName, 'visibility', 'none');
    } else {
      internalMap.value.setLayoutProperty(videoLayerName, 'visibility', 'visible');
      internalMap.value.setPaintProperty(videoLayerName, 'raster-opacity', fmvStore.opacity.value);
    }
  }
  updateFrameFilter(layer);
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

const getVideoSource = (layerId: number): VideoSource | null => {
  if (internalMap.value) {
    const source = internalMap.value.getSource(`FMVVideoSource_${layerId}`);
    if (source && source.type === 'video') {
      return source as VideoSource;
    }
  }
  return null;
};

export {
  setFMVInternalMap,
  toggleFMVMapLayers,
  toggleVisibility,
  toggleLayerTypeVisibility,
  setLayerProperty,
  updateSelected,
  updateFMVLayer,
  updateFrameFilter,
  centerAndZoom,
  updateFMVVideoMapping,
  getVideoSource,
};
