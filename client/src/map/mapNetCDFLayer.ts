import { Ref, ref } from 'vue';
import { ImageSource } from 'maplibre-gl';
import UVdatApi from '../api/UVDATApi';
import MapStore from '../MapStore';
import { MapLibreCoordinates, NetCDFImageWorking, NetCDFLayer } from '../types';

const visibleNetCDFLayers: Ref<NetCDFImageWorking[]> = ref([]);
const internalMap: Ref<maplibregl.Map | null> = ref(null);

const setNetCDFInternalMap = (map: Ref<maplibregl.Map>) => {
  internalMap.value = map.value;
};

const toggleNetCDFMapLayers = async (map: maplibregl.Map) => {
  const addLayers: NetCDFLayer[] = [];
  MapStore.selectedNetCDFMapLayers.value.forEach((layer) => {
    if (MapStore.visibleMapLayers.value.has(`${layer.type}_${layer.id}`)) {
      addLayers.push(layer as NetCDFLayer);
    }
  });
  for (let i = 0; i < addLayers.length; i += 1) {
    const addLayer = addLayers[i];
    const index = visibleNetCDFLayers.value.findIndex((item) => item.netCDFLayer === addLayer.id);
    if (index === -1) {
      // eslint-disable-next-line no-await-in-loop
      const newData = await UVdatApi.getNetCDFLayerImages(addLayer.id);
      const modifiedData = {
        ...newData, currentIndex: 0, opacity: 0.75, name: addLayer.name,
      };
      visibleNetCDFLayers.value.push(modifiedData);
      // Coordinates need to be top-left then clockwise
      const baseCoordinates = modifiedData.parent_bounds[0].slice(0, 4);
      const coordinates = [baseCoordinates[3], baseCoordinates[2], baseCoordinates[1], baseCoordinates[0]] as MapLibreCoordinates;
      map.addSource(`NetCDFSource_${modifiedData.netCDFLayer}`, {
        type: 'image',
        url: modifiedData.images[modifiedData.currentIndex],
        coordinates,
      });
      map.addLayer({
        id: `NetCDFLayer_${modifiedData.netCDFLayer}`,
        type: 'raster',
        source: `NetCDFSource_${modifiedData.netCDFLayer}`,
        paint: {
          'raster-fade-duration': 0,
          'raster-opacity': modifiedData.opacity,
        },
      });
    }
  }
  // Remove any extra items that are no longer visible
  for (let i = 0; i < visibleNetCDFLayers.value.length; i += 1) {
    const visibleLayer = visibleNetCDFLayers.value[i];
    const index = addLayers.findIndex((item) => visibleLayer.netCDFLayer === item.id);
    if (index === -1) {
      visibleNetCDFLayers.value.splice(i, 1);
      map.removeLayer(`NetCDFLayer_${visibleLayer.netCDFLayer}`);
      map.removeSource(`NetCDFSource_${visibleLayer.netCDFLayer}`);
    }
  }
};

const updateNetCDFLayer = (layer: number, newindex?: number, newOpacity?: number) => {
  const foundLayer = visibleNetCDFLayers.value.find((item) => item.netCDFLayer === layer);
  if (foundLayer && internalMap.value) {
    if (newindex !== undefined) {
      const source = internalMap.value.getSource(`NetCDFSource_${layer}`);
      const newURL = foundLayer.images[newindex];
      const baseCoordinates = foundLayer.parent_bounds[0].slice(0, 4);
      const coordinates = [baseCoordinates[3], baseCoordinates[2], baseCoordinates[1], baseCoordinates[0]] as MapLibreCoordinates;
      if (source && newURL) {
        (source as ImageSource).updateImage({
          url: newURL,
          coordinates,
        });
      }
      foundLayer.currentIndex = newindex;
    }
    if (newOpacity !== undefined) {
      internalMap.value.setPaintProperty(`NetCDFLayer_${layer}`, 'raster-opacity', newOpacity);
    }
  }
  visibleNetCDFLayers.value = visibleNetCDFLayers.value.map((item) => item);
};

export {
  toggleNetCDFMapLayers, updateNetCDFLayer, setNetCDFInternalMap, visibleNetCDFLayers,
};
