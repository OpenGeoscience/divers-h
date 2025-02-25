<!-- eslint-disable vue/max-len -->
<script lang="ts">
import {
  Ref, computed, defineComponent, nextTick, ref, watch,
} from 'vue';
import * as d3 from 'd3';
import {
  AnnotationTypes,
  AvailablePropertyDisplay,
  ColorCategoricalNumber,
  ColorCategoricalString,
  ColorLinearNumber,
  KeyProcessedLayer,
  KeyProcessedType,
  NetCDFLayer,
  RasterMapLayer,
  VectorLayerDisplay,
  VectorLayerDisplayConfig,
  VectorMapLayer,
} from '../../types'; // Import your defined types
import { createColorNumberPairs, formatNumPrecision, getLayerAvailableProperties } from '../../utils';
import MapStore from '../../MapStore';

export default defineComponent({
  name: 'ColorKey',
  props: {
    vectorLayers: {
      type: Array as () => VectorMapLayer[],
      required: true,
    },
    netcdfLayers: {
      type: Array as () => NetCDFLayer[],
      required: true,
    },
    rasterLayers: {
      type: Array as () => RasterMapLayer[],
      required: true,
    },
  },
  setup(props) {
    // Process the layers and colors

    const iconMapper: Ref<Record<string, string>> = ref({
      line: 'mdi-vector-line',
      fill: 'mdi-pentagon',
      circle: 'mdi-circle-outline',
      'fill-extrusion': 'mdi-domain',
      text: 'mdi-format-title',
      heatmap: 'mdi-heat-wave',
    });
    const attributeValues = computed(() => {
      const attributeMapping: Record<number, Record<string, AvailablePropertyDisplay>> = {};
      props.vectorLayers.forEach((layer) => {
        attributeMapping[layer.id] = getLayerAvailableProperties(layer.id);
      });
      return attributeMapping;
    });
    const processedLayers = computed(() => {
      const annotationTypes: AnnotationTypes[] = [
        'line',
        'fill',
        'circle',
        'fill-extrusion',
        'text',
        'heatmap',
      ];
      const tempProcessLayers: KeyProcessedLayer[] = [];
      props.vectorLayers.forEach((layer) => {
        const tempProcessLayer: KeyProcessedLayer = {
          id: layer.id,
          type: layer.type,
          name: layer.name,
          keyTypes: [],
        };
        // Compute Vector Layer Keys
        annotationTypes.forEach((type) => {
          const layerDisplay: VectorLayerDisplay | undefined = layer.default_style?.layers && layer.default_style.layers[type];
          if (
            layerDisplay === undefined
            || layerDisplay === true
            || layerDisplay === false
          ) {
            return;
          }
          const keyType: KeyProcessedType = {
            type,
            colors: [],
          };
          const layerDisplayConfig = layerDisplay as VectorLayerDisplayConfig;

          if (layerDisplayConfig?.color && layerDisplayConfig.enabled && layerDisplayConfig.legend) {
            if (type !== 'heatmap') {
              if (typeof layerDisplayConfig.color === 'string') {
                keyType.colors.push({
                  type: 'solid',
                  color: layerDisplayConfig.color,
                });
              } else if (
                layerDisplayConfig.color.type === 'ColorCategoricalString'
              ) {
                keyType.colors.push({
                  type: 'categorical',
                  attribute: (layerDisplayConfig.color as ColorCategoricalString).attribute,
                  pairs: Object.entries(
                    (layerDisplayConfig.color as ColorCategoricalString)
                      .colorPairs,
                  ).map(([key, value]) => ({ value: key, color: value })),
                });
              } else if (
                layerDisplayConfig.color.type === 'ColorCategoricalNumber'
              ) {
                keyType.colors.push({
                  type: 'categorical',
                  attribute: (layerDisplayConfig.color as ColorCategoricalNumber).attribute,
                  pairs: (
                    layerDisplayConfig.color as ColorCategoricalNumber
                  ).numberColorPairs.map((item) => ({
                    value: `< ${item.value}`,
                    color: item.color,
                  })),
                });
              } else if (layerDisplayConfig.color.type === 'ColorLinearNumber') {
                keyType.colors.push({
                  type: 'linear',
                  attribute: (layerDisplayConfig.color as ColorLinearNumber).attribute,
                  colors: layerDisplayConfig.color.numberColorPairs,
                  name: `gradientImage-${layer.id}-${keyType.type}`,
                });
              }
            }
            if (type === 'heatmap' && layerDisplayConfig?.heatmap
            && layerDisplayConfig.enabled && layerDisplayConfig.heatmap.color) {
              keyType.colors.push({
                type: 'heatmap',
                colors: layerDisplayConfig.heatmap.color,
                name: `gradientImage-${layer.id}-${keyType.type}`,
              });
            }
            tempProcessLayer.keyTypes.push(keyType);
          }
        });
        if (tempProcessLayer.keyTypes.length) {
          tempProcessLayers.push(tempProcessLayer);
        }
      });
      // Compute NetCDF Layer Keys
      props.netcdfLayers.forEach((layer) => {
        const tempProcessLayer: KeyProcessedLayer = {
          id: layer.id,
          type: layer.type,
          name: layer.name,
          keyTypes: [],
        };
        // Generate the color pairs based on the min/max values
        const {
          min, max, longName, standardName, variable,
        } = layer.parameters.main_variable;
        const { colorScheme } = layer.parameters;
        const colorPairs = createColorNumberPairs(min, max, colorScheme);
        tempProcessLayer.keyTypes.push({
          type: 'netCDF',
          colors: [{
            type: 'linearNetCDF',
            colors: colorPairs,
            name: `gradientImage-${layer.id}-netCDF`,
            min,
            max,
            value: longName || standardName || variable,
          }],
        });
        tempProcessLayers.push(tempProcessLayer);
      });

      // Raster Layer Computed:
      props.rasterLayers.forEach((layer) => {
        const bands = layer.default_style?.largeImageStyle?.bands || [];
        const minMaxMapper = layer.default_style?.largeImageStyle?.minMaxMapper || {};
        const tempProcessLayer: KeyProcessedLayer = {
          id: layer.id,
          type: layer.type,
          name: layer.name,
          keyTypes: [],
        };
        bands.forEach((band, bandIndex) => {
          if (band.enabled && Array.isArray(band.palette) && band.palette.length) {
            const bandMinMax = minMaxMapper[bandIndex + 1] || { min: 0, max: 1 };
            const { min, max } = bandMinMax;
            const bandPaletteLength = Array.isArray(band.palette) ? band.palette.length : 1;
            const colorType = band.scheme === 'linear' || band.scheme === undefined ? 'linear-raster' : 'categorical-raster';
            if (colorType === 'linear-raster') {
              tempProcessLayer.keyTypes.push({
                type: `raster-band-${bandIndex + 1}`,
                colors: [{
                  type: colorType,
                  colors: band.palette.map((item, index) => ({ value: min + index * ((max - min) / bandPaletteLength), color: item })),
                  name: `gradientImage-${layer.id}-raster-band-${bandIndex + 1}`,
                  min,
                  max,
                  value: `Band ${bandIndex}`,
                } as { type: 'linear-raster'; colors: ColorLinearNumber['numberColorPairs'], name: string, min: number, max: number, value: string }],
              });
            } else if (colorType === 'categorical-raster') {
              tempProcessLayer.keyTypes.push({
                type: 'raster-band',
                colors: [{
                  type: colorType,
                  pairs: band.palette.map((item, index) => ({ value: min + index * ((max - min) / bandPaletteLength), color: item })),
                  value: `Band ${bandIndex}`,
                } as { name: string, type: 'categorical-raster'; pairs: { value: number | string; color: string }[], value:string }],
              });
            }
          }
        });
        tempProcessLayers.push(tempProcessLayer);
      });
      // Sort the layers in the based on the layer order
      const orderMap = new Map(MapStore.selectedMapLayers.value.map((item, index) => [item.id, index]));
      tempProcessLayers.sort((a, b) => {
        const indexA = orderMap.get(a.id) ?? Infinity;
        const indexB = orderMap.get(b.id) ?? Infinity;
        return indexA - indexB;
      });
      console.log(tempProcessLayers);
      return tempProcessLayers;
    });

    const linearGradients = computed(() => {
      const linearGradientsList: {
        type: 'linear' | 'heatmap' | 'linearNetCDF' | 'linear-raster';
        colors: ColorLinearNumber['numberColorPairs'];
        name: string;
      }[] = [];
      processedLayers.value.forEach((processedLayer) => {
        processedLayer.keyTypes.forEach((keyType) => {
          keyType.colors.forEach((color) => {
            if (color.type === 'linear' || color.type === 'heatmap' || color.type === 'linearNetCDF' || color.type === 'linear-raster') {
              linearGradientsList.push(color);
            }
          });
        });
      });
      return linearGradientsList;
    });
    const recalculateGradient = (linearGradientConfig: {
      type: 'linear' | 'heatmap' | 'linearNetCDF';
      colors: ColorLinearNumber['numberColorPairs'];
      name: string;
    }) => {
      const { name } = linearGradientConfig;
      const linearGradient = d3.select(`#color-gradient_${name}`);
      const domain = Object.values(linearGradientConfig.colors).map(
        (item) => item.value,
      );
      const colors = Object.values(linearGradientConfig.colors).map(
        (item) => item.color,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ) as any[];
      const colorScale = d3
        .scaleLinear()
        .domain(domain)
        // D3 allows color strings but says it requires numbers for type definitions
        .range(colors);
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
    const drawGradients = () => {
      for (let i = 0; i < linearGradients.value.length; i += 1) {
        const item = linearGradients.value[i];
        const svg = d3.select(`#${item.name}`);
        svg
          .append('defs')
          .append('linearGradient')
          .attr('id', `color-gradient_${item.name}`)
          .attr('x1', '0%')
          .attr('y1', '0%')
          .attr('x2', '100%')
          .attr('y2', '0%');
        svg
          .append('rect')
          .attr('width', 125)
          .attr('height', 20)
          .style('fill', `url(#color-gradient_${item.name})`);
        recalculateGradient(item);
      }
    };
    watch(linearGradients, () => {
      nextTick(() => drawGradients());
    });

    const drawDelay = () => {
      setTimeout(() => drawGradients(), 100);
    };

    const capitalize = (s: string) => (s.length > 0 ? `${s[0].toLocaleUpperCase()}${s.slice(1)}` : s);
    const expandedPanels: Ref<number[]> = ref([]);
    watch(processedLayers, () => {
      const opened: number[] = [];
      processedLayers.value.forEach((item, index) => {
        if (item.keyTypes.length === 1) {
          opened.push(index);
        }
      });
      expandedPanels.value = opened;
      setTimeout(() => drawGradients(), 100);
    }, { immediate: true });
    return {
      capitalize,
      processedLayers,
      attributeValues,
      drawGradients,
      formatNumPrecision,
      drawDelay,
      iconMapper,
      expandedPanels,
    };
  },
});
</script>

<template>
  <v-expansion-panels
    v-model="expandedPanels"
    multiple
    @update:model-value="drawDelay()"
  >
    <v-expansion-panel
      v-for="layer in processedLayers"
      :key="layer.id"
    >
      <v-expansion-panel-title>
        <span class="text-subtitle-2">{{ layer.name }}</span>
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <div
          v-for="keyType in layer.keyTypes"
          :key="`${layer.id}_${keyType.type}`"
        >
          <v-row
            v-if="
              keyType.colors.length === 1 && keyType.colors[0].type === 'solid'
            "
            dense
            no-gutters
            class="py-1"
            align="center"
            justify="center"
            style="font-size:0.75em"
          >
            <v-col>
              <div class="text-body-2">
                {{ capitalize(keyType.type) }}
              </div>
            </v-col>
            <v-col cols="1">
              <div
                class="color-icon"
                :style="{ backgroundColor: keyType.colors[0].color }"
              />
            </v-col>
          </v-row>
          <div v-else-if="layer.keyTypes.length === 1">
            <span
              v-for="(colorConfig, index) in keyType.colors"
              :key="`${layer.id}_${keyType.type}_${index}`"
            >
              <v-row class="pb-2">
                <v-spacer />
                <b v-if="colorConfig.type === 'linearNetCDF'">{{ capitalize(colorConfig.value) }}</b>
                <b v-else-if="['categorical', 'linear'].includes(colorConfig.type)">
                  {{ attributeValues[layer.id][colorConfig.attribute].displayName }}
                </b>
                <v-spacer />
              </v-row>
              <div v-if="colorConfig.type === 'categorical'">
                <v-row
                  v-for="pair in colorConfig.pairs"
                  :key="pair.value"
                  dense
                  no-gutters
                  class="py-1"
                  align="center"
                  justify="center"
                >
                  <v-col>
                    <span>{{ pair.value }}: </span>
                  </v-col>
                  <v-col cols="1">
                    <div
                      class="color-icon"
                      :style="{ backgroundColor: pair.color }"
                    />
                  </v-col>
                </v-row>
              </div>
              <div v-else-if="colorConfig.type === 'linear'">
                <v-row
                  dense
                  no-gutters
                  class="py-1"
                  align="center"
                  justify="center"
                >
                  <v-col cols="3">
                    <span>{{ formatNumPrecision((attributeValues[layer.id][colorConfig.attribute].min || 0)) }}</span>
                  </v-col>
                  <v-col
                    class="d-flex justify-center align-center"
                  >
                    <svg
                      :id="`gradientImage-${layer.id}-${keyType.type}`"
                      width="125"
                      height="20"
                    />
                  </v-col>
                  <v-col cols="3">
                    <span>{{ formatNumPrecision((attributeValues[layer.id][colorConfig.attribute].max || 100)) }}</span>
                  </v-col>
                </v-row>
              </div>
              <div v-else-if="colorConfig.type === 'heatmap'">
                <v-row
                  dense
                  no-gutters
                  class="py-1"
                  align="center"
                  justify="center"
                >
                  <v-spacer />
                  <v-col
                    class="d-flex justify-center align-center"
                  >
                    <svg
                      :id="`gradientImage-${layer.id}-${keyType.type}`"
                      width="125"
                      height="20"
                    />
                  </v-col>
                  <v-spacer />
                </v-row>
              </div>
              <div v-else-if="colorConfig.type === 'linearNetCDF' || colorConfig.type === 'linear-raster'">
                <v-row
                  dense
                  no-gutters
                  class="py-1"
                  align="center"
                  justify="center"
                >
                  <v-col cols="3">
                    <span>{{ formatNumPrecision((colorConfig.min || 0)) }}</span>
                  </v-col>
                  <v-col
                    align
                    class="d-flex justify-center align-center"
                  >
                    <svg
                      :id="`gradientImage-${layer.id}-${keyType.type}`"
                      width="125"
                      height="20"
                    />
                  </v-col>
                  <v-col cols="3">
                    <span>{{ formatNumPrecision((colorConfig.max || 100)) }}</span>
                  </v-col>
                </v-row>
              </div>
            </span>
          </div>
          <div v-else>
            <v-expansion-panels
              @update:model-value="drawDelay()"
            >
              <v-expansion-panel
                v-for="(colorConfig, index) in keyType.colors"
                :key="`${layer.id}_${keyType.type}_${index}`"
              >
                <v-expansion-panel-title style="font-size:0.75em">
                  <span v-if="!['netCDF', 'raster'].includes(keyType.type)"><v-icon v-if="iconMapper[keyType.type]" class="pr-2"> {{ iconMapper[keyType.type] }}</v-icon>{{ capitalize(keyType.type) }}</span>
                  <span v-else-if="colorConfig.type === 'linearNetCDF'">{{ capitalize(colorConfig.value) }}</span>
                  <span v-if="['categorical', 'linear'].includes(colorConfig.type)">:
                    {{ attributeValues[layer.id][colorConfig.attribute].displayName }}
                  </span>
                </v-expansion-panel-title>
                <v-expansion-panel-text style="font-size:0.75em">
                  <div
                    v-if="colorConfig.type === 'solid'"
                    class="color-icon"
                    :style="{ backgroundColor: colorConfig.color }"
                  />
                  <div v-else-if="colorConfig.type === 'categorical'">
                    <v-row
                      v-for="pair in colorConfig.pairs"
                      :key="pair.value"
                      dense
                      no-gutters
                      class="py-1"
                      align="center"
                      justify="center"
                    >
                      <v-col>
                        <span>{{ pair.value }}: </span>
                      </v-col>
                      <v-col cols="1">
                        <div
                          class="color-icon"
                          :style="{ backgroundColor: pair.color }"
                        />
                      </v-col>
                    </v-row>
                  </div>
                  <div v-else-if="colorConfig.type === 'linear'">
                    <v-row
                      dense
                      no-gutters
                      class="py-1"
                      align="center"
                      justify="center"
                    >
                      <v-col cols="2">
                        <span>{{ formatNumPrecision((attributeValues[layer.id][colorConfig.attribute].min || 0)) }}</span>
                      </v-col>
                      <v-col
                        class="d-flex justify-center align-center"
                      >
                        <svg
                          :id="`gradientImage-${layer.id}-${keyType.type}`"
                          width="125"
                          height="20"
                        />
                      </v-col>
                      <v-col cols="2">
                        <span>{{ formatNumPrecision((attributeValues[layer.id][colorConfig.attribute].max || 100)) }}</span>
                      </v-col>
                    </v-row>
                  </div>
                  <div v-else-if="colorConfig.type === 'heatmap'">
                    <v-row
                      dense
                      no-gutters
                      class="py-1"
                      align="center"
                      justify="center"
                    >
                      <v-spacer />
                      <v-col
                        class="d-flex justify-center align-center"
                      >
                        <svg
                          :id="`gradientImage-${layer.id}-${keyType.type}`"
                          width="125"
                          height="20"
                        />
                      </v-col>
                      <v-spacer />
                    </v-row>
                  </div>
                  <div v-else-if="colorConfig.type === 'linearNetCDF' || colorConfig.type === 'linear-raster'">
                    <v-row
                      dense
                      no-gutters
                      class="py-1"
                      align="center"
                      justify="center"
                    >
                      <v-col cols="2">
                        <span>{{ formatNumPrecision((colorConfig.min || 0)) }}</span>
                      </v-col>
                      <v-col>
                        <svg
                          :id="`gradientImage-${layer.id}-${keyType.type}`"
                          width="125"
                          height="20"
                        />
                      </v-col>
                      <v-col cols="2">
                        <span>{{ formatNumPrecision((colorConfig.max || 100)) }}</span>
                      </v-col>
                    </v-row>
                  </div>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>
        </div>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<style scoped>
.color-icon {
  width: 15px;
  height: 15px;
  border: 1px solid gray;
}
</style>
