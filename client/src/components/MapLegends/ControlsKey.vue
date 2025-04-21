<!-- eslint-disable vue/max-len -->
<script lang="ts">
import {
  computed, defineComponent,
  watch,
} from 'vue';
import { throttle } from 'lodash';
import GlobalTime from './GlobalTime.vue';
import {
  AnnotationTypes,
  NetCDFLayer,
  RasterMapLayer,
  VectorLayerDisplay,
  VectorLayerDisplayConfig,
  VectorMapLayer,
} from '../../types'; // Import your defined types
import MapStore from '../../MapStore';
import { updateNetCDFLayer } from '../../map/mapNetCDFLayer';
import { getRasterLayerDisplayConfig, getVectorLayerDisplayConfig } from '../../utils';
import { updateLayer } from '../../map/mapLayers';

export default defineComponent({
  name: 'ControlsKey',
  components: {
    GlobalTime,
  },
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
    const iconMapper = {
      netcdf: 'mdi-grid',
      vector: 'mdi-map-marker-outline',
      raster: 'mdi-image-outline',
    };
    const annotationTypes: AnnotationTypes[] = [
      'line',
      'fill',
      'circle',
      'fill-extrusion',
      'text',
      'heatmap',
    ];
    const processedLayers = computed(() => {
      const mapLayerOpacityMap: Record<string, number> = {};
      props.vectorLayers.forEach((layer) => {
        annotationTypes.forEach((type) => {
          const layerDisplay: VectorLayerDisplay | undefined = layer.default_style?.layers && layer.default_style.layers[type];
          if (
            layerDisplay === undefined
            || layerDisplay === true
            || layerDisplay === false
          ) {
            return;
          }
          const layerDisplayConfig = layerDisplay as VectorLayerDisplayConfig;
          if (layerDisplayConfig.enabled) {
            if (layerDisplayConfig.opacity !== undefined && layerDisplayConfig.opacity < 1.0) {
              mapLayerOpacityMap[`vector_${layer.id}`] = Math.min(layerDisplayConfig.opacity, (mapLayerOpacityMap[`vector_${layer.id}`] || Infinity));
            } else {
              mapLayerOpacityMap[`vector_${layer.id}`] = 1.0;
            }
          }
        });
      });
      // Compute NetCDF Layer Keys
      const stepIndexMap: Record<string, { length: number, currentIndex: number }> = {};
      const resamplingMap: Record<string, 'linear' | 'nearest'> = {};
      MapStore.visibleNetCDFLayers.value.forEach((item) => {
        const found = props.netcdfLayers.find((layer) => layer.id === item.netCDFLayer);
        if (found) {
          const { opacity } = item;
          resamplingMap[`netcdf_${found.id}`] = item.resampling === 'nearest' ? 'nearest' : 'linear';
          mapLayerOpacityMap[`netcdf_${found.id}`] = opacity !== undefined ? opacity : 1.0;
          stepIndexMap[`netcdf_${found.id}`] = {
            length: item.images.length,
            currentIndex: item.currentIndex,
          };
        }
      });

      props.rasterLayers.forEach((layer) => {
        mapLayerOpacityMap[`raster_${layer.id}`] = layer?.default_style?.opacity !== undefined ? layer.default_style.opacity : 1.0;
      });
      const order: { id: number, opacity: number, name: string, type: 'netcdf' | 'vector' | 'raster', length?: number, currentIndex?: number, resampling?: 'linear' | 'nearest' } [] = [];
      MapStore.selectedMapLayers.value.forEach((layer) => {
        if (layer.type === 'netcdf') {
          if (mapLayerOpacityMap[`netcdf_${layer.id}`] !== undefined) {
            let length: undefined | number;
            let currentIndex: undefined | number;
            if (stepIndexMap[`netcdf_${layer.id}`]) {
              const data = stepIndexMap[`netcdf_${layer.id}`];
              length = data.length;
              currentIndex = data.currentIndex;
            }
            order.push({
              id: layer.id, opacity: mapLayerOpacityMap[`netcdf_${layer.id}`], name: layer.name, type: layer.type, length, currentIndex, resampling: resamplingMap[`netcdf_${layer.id}`],
            });
          }
        } else if (layer.type === 'raster') {
          if (mapLayerOpacityMap[`raster_${layer.id}`] !== undefined) {
            order.push({
              id: layer.id, opacity: mapLayerOpacityMap[`raster_${layer.id}`], name: layer.name, type: layer.type,
            });
          }
        } else if (layer.type === 'vector') {
          if (mapLayerOpacityMap[`vector_${layer.id}`] !== undefined) {
            order.push({
              id: layer.id, opacity: mapLayerOpacityMap[`vector_${layer.id}`], name: layer.name, type: layer.type,
            });
          }
        }
      });
      return order;
    });

    const stepMapping = computed(() => {
      const mappedStepMapping: Record<string, Record<number, string | number>> = {};
      MapStore.visibleNetCDFLayers.value.forEach((item) => {
        const foundLayer = props.netcdfLayers.find((layer) => layer.id === item.netCDFLayer);
        mappedStepMapping[`netcdf_${foundLayer?.id}`] = {};
        const mapSlicer: Record<number, string | number> = {};
        let unixTimeStamp = true;
        if (item?.sliding) {
          for (let i = 0; i < item.images.length; i += 1) {
            mapSlicer[i] = item.sliding.min + i * item.sliding.step;
            if (item.sliding.variable === 'time') {
              // convert unix timestamp to human readable date YYYY-MM-DD
              try {
                const date = new Date((mapSlicer[i] as number) * 1000);
                // eslint-disable-next-line prefer-destructuring
                mapSlicer[i] = date.toISOString().split('T')[0];
              } catch (e) {
                unixTimeStamp = false;
                break;
              }
            }
          }
          if (unixTimeStamp) {
            mappedStepMapping[`netcdf_${foundLayer?.id}`] = mapSlicer;
          }
        } else {
          for (let i = 0; i < item.images.length; i += 1) {
            mapSlicer[i] = i;
          }
          mappedStepMapping[`netcdf_${foundLayer?.id}`] = mapSlicer;
        }
      });
      return mappedStepMapping;
    });

    const updateIndex = (layerId: number, currentIndex: number) => {
      updateNetCDFLayer(layerId, { index: currentIndex });
    };
    const throttledUpdateNetCDFLayer = throttle(updateIndex, 50);

    const updateOpacity = (item: { id: number, opacity: number, name: string, type: 'netcdf' | 'vector' | 'raster' }, val: number) => {
      if (item.type === 'vector') {
        annotationTypes.forEach((annotationType) => {
          const { layer, displayConfig } = getVectorLayerDisplayConfig(item.id, annotationType);
          if (displayConfig !== false && displayConfig !== true && displayConfig?.enabled) {
            displayConfig.opacity = val;
            if (layer) {
              updateLayer(layer);
            }
          }
        });
      }
      if (item.type === 'netcdf') {
        const found = MapStore.visibleNetCDFLayers.value.find((layer) => item.id === layer.netCDFLayer);
        if (found) {
          found.opacity = val;
          updateNetCDFLayer(item.id, { opacity: val });
        }
      }
      if (item.type === 'raster') {
        const { layer, displayConfig } = getRasterLayerDisplayConfig(
          item.id,
        );
        if (displayConfig) {
          displayConfig.opacity = val;
          if (layer) {
            updateLayer(layer);
          }
        }
      }
    };

    const toggleResampling = (id: number) => {
      const found = MapStore.visibleNetCDFLayers.value.find((layer) => id === layer.netCDFLayer);
      if (found) {
        const val = found.resampling === 'linear' ? 'nearest' : 'linear';
        found.resampling = val;
        updateNetCDFLayer(id, { resampling: val });
      }
    };

    watch(MapStore.globalTime, (newVal) => {
      if (!MapStore.timeLinked.value) {
        return;
      }
      props.netcdfLayers.forEach((netcdfLayer) => {
        const found = MapStore.visibleNetCDFLayers.value.find((layer) => layer.netCDFLayer === netcdfLayer.id);
        if (found) {
          // now we need to find the closest index to the current time
          const { min } = found.sliding;
          const stepSize = found.sliding.step;
          const currentIndex = Math.round((newVal - min) / stepSize);
          if (currentIndex >= 0 && currentIndex < found.images.length) {
            found.currentIndex = currentIndex;
            throttledUpdateNetCDFLayer(netcdfLayer.id, currentIndex);
          }
        }
      });
    });

    const globalTimeEnabled = computed(() => {
      let enabled = false;
      if (props.netcdfLayers.length > 0) {
        enabled = props.netcdfLayers.some((layer) => layer.sliding !== undefined && layer.sliding.variable === 'time');
      }
      if (MapStore.vectorFeatureTableGraphVisible.value || MapStore.mapLayerFeatureGraphsVisible.value) {
        enabled = true;
      }
      return enabled;
    });
    return {
      processedLayers,
      iconMapper,
      updateOpacity,
      throttledUpdateNetCDFLayer,
      stepMapping,
      toggleResampling,
      globalTimeEnabled,
    };
  },
});
</script>

<template>
  <v-card v-if="globalTimeEnabled" class="pa-0 ma-0 mb-2">
    <v-card-text class="pa-0 ma-0">
      <global-time />
    </v-card-text>
  </v-card>
  <v-card
    v-for="(item, index) in processedLayers"
    :key="`opacity_${index}`"
    class="mb-2 rounded-lg shadow-sm"
    elevation="2"
    density="compact"
  >
    <v-card-text class="py-1 px-2">
      <span class="py-1 px-2 d-flex align-center">
        <v-tooltip v-if="item.type === 'netcdf'" text="Image Scaling (Nearest vs Linear)">
          <template #activator="{ props }">
            <v-icon size="16" v-bind="props" class="mr-1" color="primary" @click="toggleResampling(item.id)">
              {{ item.resampling === 'nearest' ? ' mdi-view-grid' : 'mdi-grid' }}
            </v-icon>
          </template>
        </v-tooltip>
        <v-icon v-else size="16" class="mr-1" color="primary">
          {{ iconMapper[item.type] }}
        </v-icon>
        <span class="text-sm">{{ item.name }}</span>
      </span>

      <v-row align="center" no-gutters>
        <v-col cols="1">
          <v-tooltip text="Opacity">
            <template #activator="{ props }">
              <v-icon
                class="pl-3"
                v-bind="props"
                color="primary"
              >
                mdi-square-opacity
              </v-icon>
            </template>
          </v-tooltip>
        </v-col>
        <v-col cols="8">
          <v-slider
            :model-value="item.opacity"
            min="0"
            max="1"
            step="0.01"
            hide-details
            thumb-size="12"
            track-size="4"
            color="primary"
            track-color="grey lighten-3"
            density="compact"
            @update:model-value="updateOpacity(item, $event)"
          />
        </v-col>
        <v-col
          cols="3"
          class="text-right pr-1"
        >
          <span class="text-xs">{{ Math.round(item.opacity * 100) }}%</span>
        </v-col>
      </v-row>
      <v-row v-if="item.length !== undefined && item.currentIndex !== undefined" align="center" no-gutters>
        <v-col cols="1">
          <v-tooltip text="NetCDF Layer index">
            <template #activator="{ props }">
              <v-icon
                class="pl-3"
                v-bind="props"
                color="primary"
              >
                mdi-timer-outline
              </v-icon>
            </template>
          </v-tooltip>
        </v-col>
        <v-col cols="6">
          <v-slider
            :model-value="item.currentIndex"
            min="0"
            :max="item.length"
            step="1"
            hide-details
            thumb-size="12"
            track-size="4"
            color="primary"
            track-color="grey lighten-3"
            density="compact"
            @update:model-value="throttledUpdateNetCDFLayer(item.id, $event)"
          />
        </v-col>
        <v-col
          cols="5"
          class="text-right pr-1"
        >
          <span class="text-xs">{{ stepMapping[`netcdf_${item.id}`][item.currentIndex] }}</span>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<style scoped>
</style>
