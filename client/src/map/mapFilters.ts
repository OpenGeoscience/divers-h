/* eslint-disable no-case-declarations */
/* eslint-disable @typescript-eslint/no-explicit-any */
import { FilterSpecification } from 'maplibre-gl';
import {
  AnnotationTypes,
  BooleanEqualsFilter,
  ColorFilters,
  Filter,
  NumberBetweenFilter,
  NumberComparisonFilter,
  StringContainsFilter,
  StringInArrayFilter,
  StringMatchFilter,
  VectorLayerDisplayConfig,
  VectorMapLayer,
} from '../types';
import MapStore from '../MapStore';

const getLayerDefaultFilter = (type: AnnotationTypes, layer?: VectorMapLayer) => {
  let drawPoints = false;
  if (type === 'circle' && layer?.default_style?.layers && layer.default_style.layers.line) {
    if (layer.default_style.layers.line !== true) {
      drawPoints = !!layer.default_style.layers.line.drawPoints;
    }
  }
  if (['fill', 'fill-extrusion'].includes(type)) {
    return ['==', ['geometry-type'], 'Polygon'] as FilterSpecification;
  }
  if (!drawPoints && ['circle'].includes(type)) {
    return ['==', ['geometry-type'], 'Point'] as FilterSpecification;
  }

  return true as FilterSpecification;
};

function filterToMapLibreExpression(filter: Filter): any[] {
  switch (filter.type) {
    case 'number':
      if (filter.operator === 'between') {
        const numberBetweenFilter = filter as NumberBetweenFilter;
        return [
          'all',
          ['>=',
            ['get', filter.key],
            numberBetweenFilter.minValue],
          ['<=', ['get', filter.key], numberBetweenFilter.maxValue],
        ];
      }
      const numberFilter = filter as NumberComparisonFilter;
      return [numberFilter.operator, ['get', filter.key], numberFilter.value];

    case 'string':
      if (filter.operator === 'in') {
        const stringInArrayFilter = filter as StringInArrayFilter;
        return ['in', ['get', filter.key], ['literal', stringInArrayFilter.values]];
      } if (filter.operator === '==') {
        const stringMatchFilter = filter as StringMatchFilter;
        return ['==', ['get', filter.key], stringMatchFilter.value];
      } if (filter.operator === 'contains') {
        const stringContainsFilter = filter as StringContainsFilter;
        return ['match', ['get', filter.key], [stringContainsFilter.value], true, false];
      }
      break;
    case 'bool':
      const booleanFilter = filter as BooleanEqualsFilter;
      return ['==', ['get', filter.key], booleanFilter.value];
    // case 'any':
    //   const anyFilter = filter as LogicalFilter;
    //   return ['any', ...anyFilter.filters.map(f => filterToMapLibreExpression(f))];
    // case 'all':
    //   const allFilter = filter as LogicalFilter;
    //   return ['all', ...allFilter.filters.map(f => filterToMapLibreExpression(f))];
    // case 'and':
    //   const andFilter = filter as LogicalFilter;
    //   return ['all', ...andFilter.filters.map(f => filterToMapLibreExpression(f))];
    // case 'or':
    //   const orFilter = filter as LogicalFilter;
    //   return ['any', ...orFilter.filters.map(f => filterToMapLibreExpression(f))];
    default:
      return [];
  }
  return [];
}

const colorFilterToExpression = (filter: ColorFilters) => {
  const expression = ['!', ['in', ['get', filter.key], ['literal', Array.from(filter.values)]]];
  return expression;
};

const updateFilters = (map: maplibregl.Map, layer: VectorMapLayer) => {
  const colorFilter = MapStore.vectorColorFilters.value.find((item) => item.layerId === layer.id);
  if (layer.default_style?.filters || colorFilter) {
    const annotationFilters: Record<AnnotationTypes, any[]> = {
      line: [],
      fill: [],
      circle: [],
      'fill-extrusion': [],
      text: [],
      heatmap: [],
    };
    if (layer.default_style?.filters) {
      for (let i = 0; i < layer.default_style.filters.length; i += 1) {
        const filter = layer.default_style.filters[i];
        const layerTypes = filter.layers;
        if (filter.enabled) {
          const expression = filterToMapLibreExpression(filter);
          layerTypes.forEach((layerType) => {
            if (annotationFilters[layerType] === undefined) {
              annotationFilters[layerType] = [];
            }
            annotationFilters[layerType].push(expression);
          });
        } else {
          layerTypes.forEach((layerType) => {
            const layerName = `Layer_${layer.id}_${layerType}`;
            map.setFilter(layerName, null);
          });
        }
      }
    }
    if (colorFilter) {
      if (colorFilter.layerType === 'all') {
        (Object.keys(annotationFilters) as AnnotationTypes[]).forEach((key) => {
          const expression = colorFilterToExpression(colorFilter);
          annotationFilters[key].push(expression);
        });
      }
    }
    // Now we assign filters to each layer
    (Object.keys(annotationFilters) as AnnotationTypes[]).forEach((key) => {
      if (layer.default_style?.layers && typeof layer.default_style.layers[key] !== 'boolean') {
        if (!(layer.default_style.layers[key] as VectorLayerDisplayConfig).enabled) {
          return;
        }
        const layerConfig = (layer.default_style.layers[key] as VectorLayerDisplayConfig);
        const layerName = `Layer_${layer.id}_${key}`;
        const typeFilters = annotationFilters[key];
        if (typeFilters.length === 0 && !layerConfig.drawPoints) {
          return;
        }
        const lineFilter = [];
        if (['fill', 'fill-extrusion'].includes(key)) {
          lineFilter.push(['==', ['geometry-type'], 'Polygon'] as FilterSpecification);
        }
        if (['circle'].includes(key)) {
          lineFilter.push(['==', ['geometry-type'], 'Point'] as FilterSpecification);
        }
        if (typeFilters.length) {
          let filterSpecification = typeFilters.length > 0 ? ['all'] : [];
          if (lineFilter.length) {
            filterSpecification = filterSpecification.concat(lineFilter);
          }
          const outputFilter = filterSpecification.concat(typeFilters);
          if (outputFilter.length) {
            map.setFilter(layerName, outputFilter as FilterSpecification);
          }
        } else {
          let filterSpecification = [];
          if (lineFilter.length) {
            filterSpecification = filterSpecification.concat(lineFilter);
          }
          if (filterSpecification.length) {
            map.setFilter(layerName, filterSpecification as FilterSpecification);
          }
        }
      }
    });
  } else {
    const annotationTypes: AnnotationTypes[] = ['fill', 'line', 'circle', 'fill-extrusion', 'text'];
    annotationTypes.forEach((item) => {
      const layerName = `Layer_${layer.id}_${item}`;
      const filterSpecification = getLayerDefaultFilter(item, layer);
      map.setFilter(layerName, filterSpecification as FilterSpecification);
    });
  }
};
export { filterToMapLibreExpression, updateFilters, getLayerDefaultFilter };
