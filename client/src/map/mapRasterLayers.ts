import { Ref, ref } from 'vue';
import { cloneDeep } from 'lodash';
import { MapRasterParams, RasterMapLayer, StyleBands } from '../types';
import MapStore from '../MapStore';
import uvdatAPI from '../api/UVDATApi';

const addedLayers: Ref<RasterMapLayer[]> = ref([]);

const baseRasterSource = new URL(
  (import.meta.env.VUE_APP_API_ROOT as string)
  || 'http://localhost:8000/api/v1',
  window.location.origin,
);

const internalMap: Ref<maplibregl.Map | null> = ref(null);

const generateTileString = (layerId: number, style: MapRasterParams['style']) => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tileParams: Record<string, any> = {
    projection: 'EPSG:3857',
  };
  const tileParamString = new URLSearchParams(tileParams).toString();
  const clonedStyles = cloneDeep(style);
  if (clonedStyles?.bands) {
    clonedStyles.bands = clonedStyles.bands.filter(((item) => item.enabled));
  }
  const styleString = encodeURIComponent(JSON.stringify(clonedStyles));
  return `${baseRasterSource}/rasters/${layerId}/tiles/{z}/{x}/{y}.png/?${tileParamString}&style=${styleString}`;
};

const updateLargeImageStyling = (layer: RasterMapLayer) => {
  const sourceName = `RasterTile_${layer.id}`;
  if (layer.default_style?.largeImageStyle && internalMap.value) {
    const source = internalMap.value.getSource(sourceName);
    if (source) {
      const tileString = generateTileString(layer.id, layer.default_style.largeImageStyle);
      if (source.tiles && !source.tiles.includes(tileString)) {
        source.setTiles([tileString]);
      }
    }
  }
};

const updateRasterLayer = (layer: RasterMapLayer) => {
  const layerName = `Layer_${layer.id}_raster`;
  if (layer.default_style && internalMap.value) {
    if (layer.default_style.opacity !== undefined) {
      internalMap.value.setPaintProperty(layerName, 'raster-opacity', layer.default_style.opacity);
    } else {
      internalMap.value.setPaintProperty(layerName, 'raster-opacity', null);
    }
  }
  updateLargeImageStyling(layer);
};

const interpretationMap: Record<string, string> = {
  blue: '#0000FF',
  red: '#FF0000',
  green: '#00FF00',
};
const autoMinMax = async (layer: RasterMapLayer) => {
  const metadata = await uvdatAPI.getRasterMetadata(layer.id);
  const updatedStyle: MapRasterParams['style'] = { bands: [] };
  Object.entries(metadata.bands).forEach(([key, item]) => {
    if (updatedStyle.bands) {
      let palette: string | undefined;
      // Set default palette color if required
      if (interpretationMap[item.interpretation]) {
        palette = interpretationMap[item.interpretation];
      }
      updatedStyle.bands.push({
        band: key as StyleBands['band'],
        enabled: true,
        min: 'min',
        max: 'max',
        clamp: false, // Transparent outside of min.max
        palette,
      });
    }
  });
  // eslint-disable-next-line no-param-reassign
  layer.default_style = { ...layer.default_style, largeImageStyle: updatedStyle };
  updateRasterLayer(layer);
};

const setRasterInternalMap = (map: Ref<maplibregl.Map>) => {
  internalMap.value = map.value;
};

const toggleRasterMapLayers = (map: maplibregl.Map) => {
  const addLayers: RasterMapLayer[] = [];
  const removeLayers: RasterMapLayer[] = [];
  MapStore.selectedRasterMapLayers.value.forEach((layer) => {
    if (MapStore.visibleMapLayers.value.has(`${layer.type}_${layer.id}`)) {
      addLayers.push(layer as RasterMapLayer);
    }
  });
  // Secondary pass to remove anything in Added that is not found in the system.
  addedLayers.value.forEach((item) => {
    if (
      !addLayers.includes(item)
      && map.getSource(`RasterTile_${item.id}`)
      && (
        !MapStore.selectedRasterMapLayers.value.includes(item)
        || !MapStore.visibleMapLayers.value.has(`${item.type}_${item.id}`)
      )
    ) {
      removeLayers.push(item);
    }
  });

  removeLayers.forEach((layer) => {
    if (map.getLayer(`Layer_${layer.id}_raster`)) {
      map.removeLayer(`Layer_${layer.id}_raster`);
    }
    map.removeSource(`RasterTile_${layer.id}`);
  });

  // Now we add the sources that are included
  addLayers.forEach((layer) => {
    if (map.getSource(`RasterTile_${layer.id}`)) {
      return;
    }

    // eslint-disable-next-line @typescript-eslint/no-use-before-define
    const tileString = generateTileString(layer.id, layer?.default_style?.largeImageStyle || {});

    map.addSource(`RasterTile_${layer.id}`, {
      tiles: [tileString],
      type: 'raster',
      tileSize: 256,
    });
    map.addLayer({
      id: `Layer_${layer.id}_raster`,
      type: 'raster',
      source: `RasterTile_${layer.id}`,
      minzoom: 0,
      maxzoom: 22,
      paint: {
        'raster-opacity': 1,
      },
    });
  });
  addedLayers.value = addLayers;
  MapStore.selectedRasterMapLayers.value.forEach((layer) => {
    if (MapStore.visibleMapLayers.value.has(`${layer.type}_${layer.id}`)) {
      updateRasterLayer(layer);
    }
  });
};

export {
  toggleRasterMapLayers, setRasterInternalMap, updateRasterLayer, updateLargeImageStyling, autoMinMax,
};
