/* eslint-disable @typescript-eslint/no-explicit-any */
// Opacity, minZoom/maxZoom settings for the layers

import { DataDrivenPropertyValueSpecification, FormattedSpecification } from 'maplibre-gl';
import {
  AnnotationTypes, SizeLinear, SizeTypes, SizeZoom, VectorLayerDisplayConfig, VectorMapLayer,
} from '../types';

const sizeMapping: Record<AnnotationTypes, string | null> = {
  circle: 'circle-radius',
  line: 'line-width',
  text: 'text-size',
  fill: null,
  'fill-extrusion': null,
};

const sizeZoom = (data: SizeZoom) => {
  const result: any[] = [];
  result.push('interpolate');
  result.push(['linear']);
  result.push(['zoom']);
  const sorted = data.zoomLevels.sort((a, b) => a[0] - b[0]);
  sorted.forEach((zoomLevel) => {
    result.push(zoomLevel[0]);
    result.push(zoomLevel[1]);
  });
  return result as DataDrivenPropertyValueSpecification<number>;
};

const sizeLinear = (data: SizeLinear) => {
  const result: any[] = [];
  result.push('interpolate');
  result.push(['linear']);
  result.push(['get', data.attribute]);
  const sorted = data.linearLevels.sort((a, b) => a[0] - b[0]);
  sorted.forEach((level) => {
    result.push(level[0]);
    result.push(level[1]);
  });
  return result as DataDrivenPropertyValueSpecification<number>;
};

const processSize = (
  map: maplibregl.Map,
  layerName: string,
  type: AnnotationTypes,
  size: SizeTypes,
) => {
  const prop = sizeMapping[type];
  if (typeof size === 'number' && prop) {
    if (type === 'text') {
      map.setLayoutProperty(layerName, prop, size);
    } else {
      map.setPaintProperty(layerName, prop, size);
    }
    // mapFunc(layerName, prop, size);
  } else if (typeof size === 'object' && prop) {
    if (size.type === 'SizeZoom') {
      if (type === 'text') {
        map.setLayoutProperty(layerName, prop, sizeZoom(size));
      } else {
        map.setPaintProperty(layerName, prop, sizeZoom(size));
      }
    } else if (size.type === 'SizeLinear') {
      if (type === 'text') {
        map.setLayoutProperty(layerName, prop, sizeLinear(size));
      } else {
        map.setPaintProperty(layerName, prop, sizeLinear(size));
      }
    }
  }
};

const getTextField = (attributeKey: string) => {
  const result = [];
  result.push('case');
  result.push(['has', attributeKey]);
  result.push(['get', attributeKey]);
  result.push('Default');
  return result;
  result.push([
    'number-format',
    ['get', attributeKey],
    { 'min-fraction-digits': 1, 'max-fraction-digits': 1 },
  ]);
  result.push('');
  return result as DataDrivenPropertyValueSpecification<FormattedSpecification>;
};

const updateProps = (map: maplibregl.Map, layer: VectorMapLayer) => {
  const layerTypes: AnnotationTypes[] = ['fill', 'fill-extrusion', 'circle', 'line', 'text', 'heatmap'];

  const layerConfigs = layer.default_style?.layers;
  for (let i = 0; i < layerTypes.length; i += 1) {
    const layerType = layerTypes[i];
    const subLayerName = `Layer_${layer.id}_${layerType}`;
    if (layerConfigs && layerConfigs[layerType] && layerConfigs[layerType] !== true) {
      const layerDisplayConfig = layerConfigs[layerType] as VectorLayerDisplayConfig;
      if (layerDisplayConfig.zoom) {
        const minZoom = layerDisplayConfig.zoom.min || 0;
        const maxZoom = layerDisplayConfig.zoom.max || 24;
        map.setLayerZoomRange(subLayerName, minZoom, maxZoom);
      }
      map.setPaintProperty(
        subLayerName,
        `${layerType}-opacity`,
        layerDisplayConfig.opacity !== undefined ? layerDisplayConfig.opacity : null,
      );
      if (layerDisplayConfig.size !== undefined) {
        processSize(map, subLayerName, layerType, layerDisplayConfig.size);
      }
      if (layerDisplayConfig.text !== undefined && layerType === 'text') {
        map.setLayoutProperty(subLayerName, 'text-field', getTextField(layerDisplayConfig.text.key));
      }
    }
  }
};

// eslint-disable-next-line import/prefer-default-export
export { updateProps, sizeLinear, sizeZoom };
