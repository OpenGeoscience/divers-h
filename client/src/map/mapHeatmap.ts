/* eslint-disable no-bitwise */
import { ExpressionSpecification } from 'maplibre-gl/dist/maplibre-gl';
import {
  AnnotationTypes, HeatMapConfig, SizeLinear, SizeZoom, VectorLayerDisplayConfig, VectorMapLayer,
} from '../types';
import { sizeLinear, sizeZoom } from './mapProperties';

function hexToRgba(hex: string, a: number | null = 1): string {
  // Remove the leading '#' if present
  // eslint-disable-next-line no-param-reassign
  hex = hex.replace(/^#/, '');

  // Convert 3-digit hex to 6-digit hex
  if (hex.length === 3) {
    // eslint-disable-next-line no-param-reassign
    hex = hex.split('').map((h) => h + h).join('');
  }

  // Ensure hex is valid
  if (hex.length !== 6) {
    throw new Error('Invalid hex color');
  }

  // Parse r, g, b values
  const bigint: number = parseInt(hex, 16);
  const r: number = (bigint >> 16) & 255;
  const g: number = (bigint >> 8) & 255;
  const b: number = bigint & 255;

  // Return rgba string with alpha value 0
  if (a === null) {
    return `rgb(${r}, ${g}, ${b})`;
  }
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

const heatmapRadius = (map: maplibregl.Map, subLayerName: string, radiusConfig: HeatMapConfig['radius']) => {
  map.setPaintProperty(subLayerName, 'heatmap-radius', radiusConfig);
};

const heatmapWeight = (map: maplibregl.Map, subLayerName: string, weightConfig: HeatMapConfig['weight']) => {
  if (typeof weightConfig === 'number') {
    map.setPaintProperty(subLayerName, 'heatmap-weight', weightConfig);
  } else {
    const config = weightConfig as SizeLinear;
    const result = sizeLinear(config);
    map.setPaintProperty(subLayerName, 'heatmap-weight', result);
  }
};

const heatmapIntensity = (map: maplibregl.Map, subLayerName: string, intensityConfig: HeatMapConfig['intensity']) => {
  if (typeof intensityConfig === 'number') {
    map.setPaintProperty(subLayerName, 'heatmap-intensity', intensityConfig);
  } else {
    const config = intensityConfig as SizeZoom | SizeLinear;
    if (config.type === 'SizeZoom') {
      const result = sizeZoom(config);
      map.setPaintProperty(subLayerName, 'heatmap-intensity', result);
    }
  }
};

const subLayerMapping: Record<string, string> = {};

const heatmapColor = (map: maplibregl.Map, layer: VectorMapLayer, subLayerName: string, colorConfig: HeatMapConfig['color']) => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const result: any[] = ['interpolate', ['linear'], ['heatmap-density']];
  if (colorConfig) {
    let firstColor = false;
    for (let i = 0; i < colorConfig?.length; i += 1) {
      if (!firstColor) {
        const rgbColor = hexToRgba(colorConfig[i].color, 0);
        result.push(colorConfig[i].value);
        result.push(rgbColor);
        firstColor = true;
      } else {
        result.push(colorConfig[i].value);
        result.push(hexToRgba(colorConfig[i].color, null));
      }
    }
  }
  /**
   * There is a weird issue where I can't directly use setPaintProperty for heatmap-color
   * So my best solution was to disable and re-ad the layer with the proper heatmap colors
   */
  if (subLayerMapping[subLayerName] !== JSON.stringify(colorConfig)) {
    // disable and renable the layer with the new settings
    if (map.getLayer(subLayerName)) {
      map.removeLayer(subLayerName);
      map.addLayer({
        id: subLayerName,
        type: 'heatmap',
        source: `VectorTile_${layer.id}`,
        'source-layer': 'default',
        paint: {
          'heatmap-color': result as ExpressionSpecification,
        },
      });
    }
  }
  subLayerMapping[subLayerName] = JSON.stringify(colorConfig);
};

const updateHeatmap = (map: maplibregl.Map, layer: VectorMapLayer) => {
  const layerTypes: AnnotationTypes[] = ['heatmap'];

  const layerConfigs = layer.default_style?.layers;
  for (let i = 0; i < layerTypes.length; i += 1) {
    const layerType = layerTypes[i];
    const subLayerName = `Layer_${layer.id}_${layerType}`;
    if (layerConfigs && layerConfigs[layerType] && layerConfigs[layerType] !== true) {
      const layerDisplayConfig = layerConfigs[layerType] as VectorLayerDisplayConfig;
      const heatMapConfig = layerDisplayConfig.heatmap;
      if (heatMapConfig && layerDisplayConfig.enabled) {
        if (heatMapConfig.color !== undefined) {
          heatmapColor(map, layer, subLayerName, heatMapConfig.color);
        }
        if (heatMapConfig.radius !== undefined) {
          heatmapRadius(map, subLayerName, heatMapConfig.radius);
        }
        if (heatMapConfig.weight !== undefined) {
          heatmapWeight(map, subLayerName, heatMapConfig.weight);
        }
        if (heatMapConfig.intensity !== undefined) {
          heatmapIntensity(map, subLayerName, heatMapConfig.intensity);
        }
      }
    }
  }
};

// eslint-disable-next-line import/prefer-default-export
export { updateHeatmap, subLayerMapping };
