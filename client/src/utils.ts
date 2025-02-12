/* eslint-disable vue/max-len */
import * as d3 from 'd3';
import MapStore from './MapStore';
import {
  AnnotationTypes, AvailablePropertyDisplay, Filter, RasterMapLayer, VectorLayerDisplayConfig, VectorMapLayer,
} from './types';

const getVectorLayerDisplayConfig = (
  layerId: number,
  layerType: AnnotationTypes,
):
{ layer?: VectorMapLayer, displayConfig: boolean | VectorLayerDisplayConfig, enabled: boolean } => {
  const found = MapStore.selectedMapLayers.value.find(
    (item) => item.id === layerId,
  ) as VectorMapLayer;
  if (found?.default_style?.layers) {
    const layerTypeVal = found?.default_style?.layers[layerType];
    if (layerTypeVal !== false && layerTypeVal !== true) {
      return {
        layer: found,
        displayConfig: layerTypeVal as VectorLayerDisplayConfig,
        enabled: layerTypeVal?.enabled !== false,
      };
    }
    return { layer: found, displayConfig: false, enabled: false };
  }
  return { layer: found, displayConfig: false, enabled: false };
};
const getRasterLayerDisplayConfig = (layerId: number) : {
  layer?: RasterMapLayer,
  displayConfig: false | RasterMapLayer['default_style'],
} => {
  const found = MapStore.selectedMapLayers.value.find((item) => item.id === layerId) as RasterMapLayer;
  if (found?.default_style) {
    return {
      layer: found,
      displayConfig: found.default_style as RasterMapLayer['default_style'],
    };
  }
  return { layer: found, displayConfig: false };
};

const getLayerFilters = (layerId: number): Filter[] => {
  const found = MapStore.selectedVectorMapLayers.value.find(
    (item: VectorMapLayer) => item.id === layerId,
  );
  if (found?.default_style?.filters) {
    return found.default_style.filters;
  }
  return [];
};

const getLayerAvailableProperties = (layerId: number): Record<string, AvailablePropertyDisplay> => {
  const found = MapStore.selectedVectorMapLayers.value.find(
    (item: VectorMapLayer) => item.id === layerId,
  );
  if (found?.default_style?.layers) {
    const availableProperties = found?.default_style?.properties?.availableProperties;
    if (availableProperties) {
      return availableProperties;
    }
  }
  return {};
};

const recalculateGradient = (colors: string[], gradientId: string) => {
  const linearGradient = d3.select(`#color-gradient_${gradientId}`);
  const domain = Array.from({ length: colors.length + 1 }, (_, i) => i);
  const colorScale = d3
    .scaleLinear()
    .domain(domain)
    // D3 allows color strings but says it requires numbers for type definitions
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    .range(colors as any[]);
  // Recalculate percentage of width for gradient
  const max = domain[domain.length - 1];
  const percent = domain.map((item) => (max === 0 ? 0 : item / max));
  // Append multiple color stops using data/enter step
  linearGradient.selectAll('stop').remove();
  linearGradient
    .selectAll('stop')
    .data(colorScale.range())
    .enter()
    .append('stop')
    .attr('offset', (d, i) => percent[i])
    .attr('stop-color', (d) => d);
};
const drawGradients = (colors: string[], gradientId: string, width = 125, height = 20) => {
  const svg = d3.select(`#gradientImage-${gradientId}`);
  svg
    .append('defs')
    .append('linearGradient')
    .attr('id', `color-gradient_${gradientId}`)
    .attr('x1', '0%')
    .attr('y1', '0%')
    .attr('x2', '100%')
    .attr('y2', '0%');
  svg
    .append('rect')
    .attr('width', width)
    .attr('height', height)
    .style('fill', `url(#color-gradient_${gradientId})`);
  recalculateGradient(colors, gradientId);
};

function isWithinPercent(
  target: number,
  value: number,
  percent: number = 1,
): boolean {
  const tolerance = target * (percent / 100); // Calculate the tolerance based on the provided percentage
  return value >= (target - tolerance) && value <= (target + tolerance);
}

const colorSchemes = [
  { name: 'd3.cividis', colors: ['#002051', '#0a326a', '#2b446e', '#4d566d', '#696970', '#7f7c75', '#948f78', '#ada476', '#caba6a', '#ead156', '#fdea45'] },
  { name: 'd3.viridis', colors: ['#440154', '#482475', '#414487', '#355f8d', '#2a788e', '#21918c', '#22a884', '#44bf70', '#7ad151', '#bddf26', '#fde725'] },
  { name: 'd3.inferno', colors: ['#000004', '#160b39', '#420a68', '#6a176e', '#932667', '#bc3754', '#dd513a', '#f37819', '#fca50a', '#f6d746', '#fcffa4'] },
  { name: 'd3.magma', colors: ['#000004', '#140e36', '#3b0f70', '#641a80', '#8c2981', '#b73779', '#de4968', '#f7705c', '#fe9f6d', '#fecf92', '#fcfdbf'] },
  { name: 'd3.plasma', colors: ['#0d0887', '#41049d', '#6a00a8', '#8f0da4', '#b12a90', '#cc4778', '#e16462', '#f2844b', '#fca636', '#fcce25', '#f0f921'] },
  { name: 'd3.warm', colors: ['#6e40aa', '#963db3', '#bf3caf', '#e4419d', '#fe4b83', '#ff5e63', '#ff7847', '#fb9633', '#e2b72f', '#c6d63c', '#aff05b'] },
  { name: 'd3.cool', colors: ['#6e40aa', '#6054c8', '#4c6edb', '#368ce1', '#23abd8', '#1ac7c2', '#1ddfa3', '#30ef82', '#52f667', '#7ff658', '#aff05b'] },
  { name: 'd3.turbo', colors: ['#23171b', '#4a58dd', '#2f9df5', '#27d7c4', '#4df884', '#95fb51', '#dedd32', '#ffa423', '#f65f18', '#ba2208', '#900c00'] },
  { name: 'd3.BuGn', colors: ['#f7fcfd', '#e8f6f9', '#d5efed', '#b7e4da', '#8fd3c1', '#68c2a3', '#49b17f', '#2f9959', '#157f3c', '#036429', '#00441b'] },
  { name: 'd3.BuPu', colors: ['#f7fcfd', '#e4eef5', '#ccddec', '#b2cae1', '#9cb3d5', '#8f95c6', '#8c74b5', '#8952a5', '#852d8f', '#730f71', '#4d004b'] },
  { name: 'd3.GnBu', colors: ['#f7fcf0', '#e5f5df', '#d3eece', '#bde5bf', '#9ed9bb', '#7bcbc4', '#58b7cd', '#399cc6', '#1d7eb7', '#0b60a1', '#084081'] },
  { name: 'd3.OrRd', colors: ['#fff7ec', '#feebcf', '#fddcaf', '#fdca94', '#fdb07a', '#fa8e5d', '#f16c49', '#e04530', '#c81d13', '#a70403', '#7f0000'] },
  { name: 'd3.PuBuGn', colors: ['#fff7fb', '#efe7f2', '#dbd8ea', '#bec9e2', '#98b9d9', '#69a8cf', '#4096c0', '#19879f', '#037877', '#016353', '#014636'] },
  { name: 'd3.PuBu', colors: ['#fff7fb', '#efeaf4', '#dbdaeb', '#bfc9e2', '#9bb9d9', '#72a8cf', '#4394c3', '#1a7db6', '#0667a1', '#045281', '#023858'] },
  { name: 'd3.PuRd', colors: ['#f7f4f9', '#eae3f0', '#dcc9e2', '#d0aad2', '#d08ac2', '#dd63ae', '#e33890', '#d71c6c', '#b70b4f', '#8f023a', '#67001f'] },
  { name: 'd3.RdPu', colors: ['#fff7f3', '#fde4e1', '#fccfcc', '#fbb5bc', '#f993b0', '#f369a3', '#e03e98', '#c01788', '#99037c', '#700174', '#49006a'] },
  { name: 'd3.YlGnBu', colors: ['#ffffd9', '#eff9bd', '#d5eeb3', '#a9ddb7', '#73c9bd', '#45b4c2', '#2897bf', '#2073b2', '#234ea0', '#1c3185', '#081d58'] },
  { name: 'd3.YlGn', colors: ['#ffffe5', '#f7fcc4', '#e4f4ac', '#c7e89b', '#a2d88a', '#78c578', '#4eaf63', '#2f944e', '#15793f', '#036034', '#004529'] },
  { name: 'd3.YlOrBr', colors: ['#ffffe5', '#fff8c4', '#feeaa1', '#fed676', '#feba4a', '#fb992c', '#ee7918', '#d85b0a', '#b74304', '#8f3204', '#662506'] },
  { name: 'd3.YlOrRd', colors: ['#ffffcc', '#fff0a9', '#fee087', '#fec965', '#feab4b', '#fd893c', '#fa5c2e', '#ec3023', '#d31121', '#af0225', '#800026'] },
];

const createColorNumberPairs = (min: number, max: number, scheme: string) => {
  const found = colorSchemes.find((base) => base.name.includes(scheme));
  const colorPairs: { value: number, color: string }[] = [];
  if (found) {
    const divisions = (max - min) / found.colors.length;
    for (let i = 0; i < found.colors.length; i += 1) {
      const color = found.colors[i];
      const value = (i * divisions);
      colorPairs.push({ color, value });
    }
  }
  return colorPairs;
};

const formatNumPrecision = (num: number, range?: number) => {
  const strNum = num.toString();
  const decimalPart = strNum.split('.')[1] || '';

  // Count leading zeros in the decimal part
  const leadingZeros = decimalPart.match(/^0+/)?.[0]?.length || 0;

  // If it has leading zeros we add some precision to it.
  if (leadingZeros > 0) {
    return parseFloat(num.toFixed(leadingZeros + 2));
  }
  if (range && range > 50 && (num <= -1 || num >= 1)) {
    return Math.round(num);
  }

  // If number is between 0-1 and has more than 2 decimal places
  if (num < 1 && num > -1 && decimalPart.toString().length >= 2) {
    return parseFloat(num.toFixed(4));
  }
  if (decimalPart.length > 0) {
    return parseFloat(num.toFixed(2));
  }
  return num;
};

function convertTimestampNSToDatetimeString(timestamp: number, format = 'date'): string {
  // Convert the nanoseconds to milliseconds
  const seconds = Math.round(timestamp);
  // Create a Date object
  const date = new Date(seconds * 1000);
  // Extract the parts of the date in UTC
  const year = date.getUTCFullYear();
  const month = (date.getUTCMonth() + 1).toString().padStart(2, '0'); // Months are 0-indexed
  const day = date.getUTCDate().toString().padStart(2, '0');

  // Calculate the minutes and round to the nearest hour
  const hours = date.getUTCHours().toString().padStart(2, '0');
  const minutes = date.getUTCMinutes().toString().padStart(2, '0');
  // Format the date as YYYYMMDD HH:MM
  if (format === 'date') {
    return `${year}-${month}-${day}`;
  } if (format === 'year') {
    return `${year}`;
  }
  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

function formatISOToYYMMDD(dateString: string): string | null {
  const isoRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$/;

  if (!isoRegex.test(dateString)) {
    return null; // Not a valid ISO 8601 string
  }

  try {
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) {
      return null; // Invalid date
    }

    const yy = String(date.getFullYear()).slice(-2);
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');

    return `${yy}-${mm}-${dd}`;
  } catch {
    return null;
  }
}

function formatCompactToISO(compactNumber: number, format: 'date' | 'datetime' = 'date'): string | null {
  const compactStr = compactNumber.toString();

  if (!/^(\d{12}|\d{8})$/.test(compactStr)) {
    return null; // Invalid format
  }

  const year = compactStr.slice(0, 4);
  const month = compactStr.slice(4, 6);
  const day = compactStr.slice(6, 8);

  if (format === 'date') {
    return `${year}-${month}-${day}`;
  } if (compactStr.length === 12) {
    const hour = compactStr.slice(8, 10);
    const minute = compactStr.slice(10, 12);
    return `${year}-${month}-${day} ${hour}:${minute}`;
  }

  return `${year}-${month}-${day}`; // Default fallback
}

function convert360Longitude(longitude: number): number {
  return longitude - 180;
}

export {
  getVectorLayerDisplayConfig,
  getRasterLayerDisplayConfig,
  getLayerAvailableProperties,
  getLayerFilters,
  drawGradients,
  isWithinPercent,
  colorSchemes,
  formatNumPrecision,
  createColorNumberPairs,
  convertTimestampNSToDatetimeString,
  formatCompactToISO,
  formatISOToYYMMDD,
  convert360Longitude,
};
