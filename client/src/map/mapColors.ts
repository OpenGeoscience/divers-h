/* eslint-disable @typescript-eslint/default-param-last */
/* eslint-disable @typescript-eslint/no-explicit-any */

import * as d3 from 'd3';
import { ColorSpecification, DataDrivenPropertyValueSpecification } from 'maplibre-gl';
import MapStore from '../MapStore';
import {
  AnnotationTypes,
  ColorAttributeValue,
  ColorBoolean,
  ColorCategoricalNumber,
  ColorCategoricalString,
  ColorLinearNumber,
  VectorLayerDisplayConfig,
  VectorMapLayer,
} from '../types';

function generateColors(numColors: number) {
  const colorList = [];
  for (let i = 0; i < numColors; i += 1) {
    // We are using a rainbow but we want to skip the cyan area so number will be reduced
    const pos = i * (1 / numColors);
    if (pos > 0.58 && pos < 0.63) {
      break;
    }
    const baseColor = d3.color(d3.interpolateRainbow(pos))?.hex();
    if (baseColor) {
      const hueColor = d3.hsl(baseColor);
      hueColor.s = 1.0;
      hueColor.l = 0.5;
      colorList.push(hueColor.hex());
      hueColor.s = 0.5;
      hueColor.l = 0.35;
      colorList.push(hueColor.hex());
      hueColor.s = 1.0;
      hueColor.l = 0.75;
      colorList.push(hueColor.hex());
    }
  }

  // Mix up colors in a uniform way so reloads have the same types associated with the same colors
  let seed = 0.28;
  colorList.sort(() => {
    seed += seed;
    return Math.cos(seed);
  });
  return colorList;
}

const colorGenerator = d3.scaleOrdinal<string>().range(generateColors(10));

const chainSelected = (result: any[] = [], color = 'cyan', defaultColor = '') => {
  result.push('case');
  result.push(['in', ['get', 'vectorfeatureid'], ['literal', MapStore.selectedIds.value]]);
  result.push(color);
  if (MapStore.mapLayerFeatureGraphsVisible.value || MapStore.activeSideBarCard.value === 'searchableVectors') {
    result.push(['in', ['get', 'vectorfeatureid'], ['literal', MapStore.hoveredFeatures.value]]);
    result.push(color);
  }
  if (MapStore.enabledMapLayerFeatureColorMapping.value) {
    Object.entries(MapStore.mapLayerFeatureColorMapping.value).forEach(([vectorfeatureId, mappedColor]) => {
      result.push(['==', ['get', 'vectorfeatureid'], parseInt(vectorfeatureId, 10)]);
      result.push(mappedColor);
    });
  }
  if (defaultColor) {
    result.push(defaultColor);
  }
  return result as DataDrivenPropertyValueSpecification<ColorSpecification>;
};

const colorCategoricalString = (result: any[] = [], data: ColorCategoricalString) => {
  // For right now I don't know the attribute values so I can't generate an ordinal color scale
  const { defaultColor, attribute, colorPairs } = data;
  // You would look inside the metadata for the attribute to get a
  // list of possible values and use that as a color generate
  if (result.length === 0) {
    result.push('case');
  }

  Object.entries(colorPairs).forEach(([label, color]) => {
    result.push(['==', ['get', attribute], label]);
    result.push(color);
  });
  result.push(defaultColor);

  return result as DataDrivenPropertyValueSpecification<ColorSpecification>;
};

const colorAttributeValue = (result: any[] = [], data: ColorAttributeValue) => {
  const { defaultColor, attributeValues } = data;
  for (let i = 0; i < attributeValues.length; i += 1) {
    const attribute = attributeValues[i];
    if (result.length === 0) {
      result.push('case');
    }
    result.push(['has', attribute]);
    result.push([
      'let',
      'firstColor',
      ['slice', ['get', attribute], 0, 7], // assuming each color is in the format '#RRGGBB'
      ['to-color', ['var', 'firstColor']],
    ]);
    result.push(['has', 'color']);
    result.push([
      'match',
      ['get', attribute],
      'light blue',
      '#ADD8E6',
      'dark blue',
      '#00008B',
      // add other color mappings here
      ['get', attribute], // if the color is already in a valid format
    ]);
  }
  result.push(defaultColor);
  return result as DataDrivenPropertyValueSpecification<string>;
};

const colorLinearNumber = (result: any[] = [], data: ColorLinearNumber) => {
  const { numberColorPairs, attribute } = data;
  const sorted = numberColorPairs.sort((a, b) => a.value - b.value);
  // If it is appened to a chain it needs to be it's own contained array
  if (result.length) {
    const newData: any[] = ['interpolate', ['linear'], ['get', attribute]];
    for (let i = 0; i < sorted.length; i += 1) {
      newData.push(sorted[i].value);
      newData.push(sorted[i].color);
    }
    result.push(newData);
  } else {
    // A root property needs to be at the root and not inside another array.
    result.push('interpolate');
    result.push(['linear']);
    result.push(['get', attribute]);
    for (let i = 0; i < sorted.length; i += 1) {
      result.push(sorted[i].value);
      result.push(sorted[i].color);
    }
  }
  return result as DataDrivenPropertyValueSpecification<string>;
};

const colorCategoricalNumber = (result: any[] = [], data: ColorCategoricalNumber) => {
  const { numberColorPairs, attribute } = data;
  if (result.length === 0) {
    result.push('case');
  }
  const sorted = numberColorPairs.sort((a, b) => a.value - b.value);
  for (let i = 0; i < sorted.length; i += 1) {
    result.push(['<=', ['get', attribute], sorted[i].value]);
    result.push(sorted[i].color);
  }

  // Add the last color for values above the last threshold
  result.push(sorted[0].color);
  return result as DataDrivenPropertyValueSpecification<string>;
};

const colorBoolean = (result: any[] = [], data: ColorBoolean) => {
  const { trueColor, falseColor, attribute } = data;
  result.push('case');
  result.push(['==', ['get', attribute], true]);
  result.push(trueColor);
  result.push(falseColor);

  return result as DataDrivenPropertyValueSpecification<string>;
};

const layerPropertyMapping: Record<AnnotationTypes, string> = {
  circle: 'circle-color',
  line: 'line-color',
  fill: 'fill-color',
  'fill-extrusion': 'fill-extrusion-color',
  text: 'text-color',
};

const colorFunctionMapping: Record<
| 'ColorAttributeValue'
| 'ColorCategoricalNumber'
| 'ColorLinearNumber'
| 'ColorBoolean'
| 'ColorCategoricalString',
(result: any[], data: any) => DataDrivenPropertyValueSpecification<ColorSpecification>
> = {
  ColorAttributeValue: colorAttributeValue,
  ColorCategoricalNumber: colorCategoricalNumber,
  ColorCategoricalString: colorCategoricalString,
  ColorLinearNumber: colorLinearNumber,
  ColorBoolean: colorBoolean,
};
const calculateColors = (map: maplibregl.Map, layer: VectorMapLayer) => {
  const layerTypes: AnnotationTypes[] = ['fill', 'fill-extrusion', 'circle', 'line', 'text'];
  const layerConfigs = layer.default_style?.layers;
  for (let i = 0; i < layerTypes.length; i += 1) {
    const layerType = layerTypes[i];
    if (layerConfigs && layerConfigs[layerType] && layerConfigs[layerType] !== true) {
      const layerName = `Layer_${layer.id}_${layerType}`;
      if (map.getLayer(layerName)) {
        const property = layerPropertyMapping[layerType];
        const currentLayerConfig = layerConfigs[layerType] as VectorLayerDisplayConfig;
        if (currentLayerConfig.color) {
          if (typeof currentLayerConfig.color === 'string') {
            let base;
            if (currentLayerConfig.selectColor) {
              base = chainSelected([], currentLayerConfig.selectColor, currentLayerConfig.color);
              map.setPaintProperty(layerName, property, base);
            } else {
              map.setPaintProperty(layerName, property, currentLayerConfig.color);
            }
          } else {
            const colorType = currentLayerConfig.color?.type;
            if (colorType && colorFunctionMapping[colorType]) {
              let base;
              if (currentLayerConfig.selectColor) {
                base = chainSelected([], currentLayerConfig.selectColor);
              }
              map.setPaintProperty(
                layerName,
                property,
                colorFunctionMapping[colorType]((base || []) as any[], currentLayerConfig.color),
              );
            }
          }
        }
      }
    }
  }
};

export { calculateColors, colorGenerator };
