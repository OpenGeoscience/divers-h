import { Map, MapLayerMouseEvent, Popup } from 'maplibre-gl';
import {
  App, Ref, ShallowRef, nextTick, ref,
} from 'vue';
import { isEqual } from 'lodash';
import MapStore from '../MapStore';
import createPopup from '../main';
import { AnnotationTypes, FeatureProps } from '../types';

let app: App | null = null;
const map: ShallowRef<null | Map> = ref(null);
let popup: Popup;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const popUpProps: Ref<Record<string, any>[]> = ref([]);
let hoverPopup = false;
let attemptClosePopUp = false;
let timeout: NodeJS.Timeout | null = null;

// Onetime function to configure the popup
const popupLogic = async (mapArg: ShallowRef<null | Map>) => {
  popup = new Popup({
    closeButton: false,
    closeOnClick: false,
    maxWidth: '1200px',
  });
  map.value = mapArg.value;
};

const hoveredInfo: Ref<FeatureProps[]> = ref([]);

const mouseenter = async (e: MapLayerMouseEvent) => {
  if (e.features && MapStore.toolTipsEnabled.value) {
    const coordinates = e.lngLat;
    const data: FeatureProps[] = [];
    for (let i = 0; i < e.features.length; i += 1) {
      const props = e.features[i]?.properties;
      if (props) {
        data.push(props);
      }
    }
    hoveredInfo.value = data;
    popUpProps.value = hoveredInfo.value;
    // eslint-disable-next-line @typescript-eslint/no-use-before-define
    createPopupComponent(coordinates, popUpProps.value);
  }
};

const mouseleave = async (e: MapLayerMouseEvent) => {
  if (e.features) {
    for (let i = 0; i < e.features.length; i += 1) {
      const props = e.features[i]?.properties;
      if (props) {
        const foundIndex = hoveredInfo.value.findIndex((item) => isEqual(item, props));
        if (foundIndex !== -1) {
          hoveredInfo.value.splice(foundIndex, 1);
        }
      }
    }
    popUpProps.value = hoveredInfo.value;
  }
  if (timeout !== null) {
    clearTimeout(timeout);
  }
  // eslint-disable-next-line @typescript-eslint/no-use-before-define
  timeout = setTimeout(() => unmountPopup(), 100);
};

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const clickOutside = (_e: MapLayerMouseEvent) => {
  // console.log(e)
};

const click = async (e: MapLayerMouseEvent) => {
  if (e.features?.length) {
    for (let i = 0; i < e.features?.length; i += 1) {
      const feature = e.features[i];
      if (feature.properties) {
        const data = {
          id: feature.properties?.vectorfeatureid as number,
          layerId: feature.properties?.map_layer_id as number,
          properties: feature.properties,
        };
        MapStore.addSelectedFeature(data);
      }
    }
  }
};

const singleClick = async (e: MapLayerMouseEvent) => {
  if (e.features?.length) {
    for (let i = 0; i < e.features?.length; i += 1) {
      const feature = e.features[i];
      if (feature.properties) {
        const data = {
          id: feature.properties?.vectorfeatureid as number,
          layerId: feature.properties?.map_layer_id as number,
          properties: feature.properties,
        };
        MapStore.selectedFeatures.value = [data];
      }
    }
  }
};

const setPopupHoverOn = () => {
  hoverPopup = true;
};
const setPopupHoverOff = () => {
  hoverPopup = false;
  if (attemptClosePopUp && !MapStore.toolTipMenuOpen) {
    // eslint-disable-next-line @typescript-eslint/no-use-before-define
    unmountPopup();
  }
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const createPopupComponent = (coordinates: any, props: FeatureProps[]) => {
  if (!map.value) {
    return;
  }
  popup.setLngLat(coordinates).setHTML('<div id="popup-content"></div>').addTo(map.value);
  nextTick(() => {
    const div = document.getElementById('popup-content');
    if (div) {
      div.addEventListener('mouseenter', setPopupHoverOn);
      div.addEventListener('mouseleave', setPopupHoverOff);
    }
    if (app !== null) {
      if (timeout !== null) {
        clearTimeout(timeout);
      }
      app.unmount();
      app = null;
    }
    app = createPopup(props);
    app.mount('#popup-content');
  });
};

const unmountPopup = () => {
  // We check to see if the mouse is still within the bounds of the popup
  if (hoverPopup) {
    attemptClosePopUp = true;
    return;
  }
  const div = document.getElementById('popup-content');
  if (div) {
    div.removeEventListener('mouseenter', setPopupHoverOn);
    div.removeEventListener('mouseleave', setPopupHoverOff);
  }
  popUpProps.value = [];
  if (app !== null) {
    app.unmount();
    app = null;
  }
  if (map.value) {
    map.value.getCanvas().style.cursor = '';
  }
  popup.remove();
};
let loadedFunctions: {
  id: number,
  mouseenter: (e: MapLayerMouseEvent) => Promise<void>;
  mouseleave: (e: MapLayerMouseEvent) => Promise<void>;
  click: (e: MapLayerMouseEvent) => Promise<void>;
}[] = [];
const setPopupEvents = (localMap: Map) => {
  const annotationTypes: (AnnotationTypes | 'raster')[] = ['line', 'circle', 'fill', 'fill-extrusion', 'raster'];
  if (localMap) {
    for (let i = 0; i < loadedFunctions.length; i += 1) {
      const data = loadedFunctions[i];
      // Remove events for all layers
      // Doesn't matter if it exists or not
      annotationTypes.forEach((annotationType) => {
        localMap.off('mouseenter', `Layer_${data.id}_${annotationType}`, data.mouseenter);
        localMap.off('mouseleave', `Layer_${data.id}_${annotationType}`, data.mouseleave);
        localMap.off('click', `Layer_${data.id}_${annotationType}`, data.click);
      });
      localMap.off('click', clickOutside);
    }
    localMap.off('click', clickOutside);
    loadedFunctions = [];
    for (let i = 0; i < MapStore.selectedRasterMapLayers.value.length; i += 1) {
      const layer = MapStore.selectedRasterMapLayers.value[i];
      const { id } = layer;
      const configDisplay = layer.default_style;
      let clickFunc = click;
      if (configDisplay) {
        if (configDisplay.selectable) {
          clickFunc = configDisplay.selectable === 'singleSelect' ? singleClick : click;
          localMap.on('click', `Layer_${id}_raster`, clickFunc);
        }
        if (configDisplay.hoverable) {
          localMap.on('mouseenter', `Layer_${id}_raster`, mouseenter);
          localMap.on('mouseleave', `Layer_${id}_raster`, mouseleave);
        }
      } else {
        localMap.off('click', `Layer_${id}_raster`, click);
        localMap.off('mouseenter', `Layer_${id}_raster`, mouseenter);
        localMap.off('mouseleave', `Layer_${id}_raster`, mouseleave);
        localMap.off('click', clickOutside);
      }
      loadedFunctions.push({
        id,
        mouseenter,
        mouseleave,
        click: clickFunc,
      });
    }

    for (let i = 0; i < MapStore.selectedVectorMapLayers.value.length; i += 1) {
      const layer = MapStore.selectedVectorMapLayers.value[i];
      const { id } = layer;
      const configDisplay = layer.default_style?.layers;
      if (configDisplay) {
        // Other layers select and hover is used based on config
        annotationTypes.forEach((annotationType) => {
          if (configDisplay && annotationType !== 'raster' && configDisplay[annotationType]) {
            const annotationDisplayType = configDisplay[annotationType];
            if (typeof annotationDisplayType === 'object') {
              let clickFunc = click;
              if (annotationDisplayType.selectable) {
                clickFunc = annotationDisplayType.selectable === 'singleSelect' ? singleClick : click;
                localMap.on('click', `Layer_${id}_${annotationType}`, clickFunc);
              }
              if (annotationDisplayType.hoverable) {
                localMap.on('mouseenter', `Layer_${id}_${annotationType}`, mouseenter);
                localMap.on('mouseleave', `Layer_${id}_${annotationType}`, mouseleave);
              }
            }
          }
        });
      } else {
        annotationTypes.forEach((annotationType) => {
          localMap.off('mouseenter', `Layer_${id}_${annotationType}`, mouseenter);
          localMap.off('mouseleave', `Layer_${id}_${annotationType}`, mouseleave);
          localMap.off('click', `Layer_${id}_${annotationType}`, click);
        });
        localMap.off('click', clickOutside);
      }
      localMap.on('click', clickOutside);
      loadedFunctions.push({
        id,
        mouseenter,
        mouseleave,
        click,
      });
    }
  }
};

export { setPopupEvents, popupLogic };
