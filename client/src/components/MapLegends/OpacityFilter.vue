<script lang="ts">
import {
  computed, defineComponent,
} from 'vue';
import {
  AnnotationTypes,
  NetCDFLayer,
  RasterMapLayer,
  VectorLayerDisplay,
  VectorLayerDisplayConfig,
  VectorMapLayer,
} from '../../types'; // Import your defined types
import MapStore from '../../MapStore';
import { updateNetCDFLayer, visibleNetCDFLayers } from '../../map/mapNetCDFLayer';
import { getVectorLayerDisplayConfig } from '../../utils';
import { updateLayer } from '../../map/mapLayers';

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
      visibleNetCDFLayers.value.forEach((item) => {
        const found = props.netcdfLayers.find((layer) => layer.id === item.netCDFLayer);
        if (found) {
          const { opacity } = item;
          mapLayerOpacityMap[`netcdf_${found.id}`] = opacity !== undefined ? opacity : 1.0;
        }
      });

      props.rasterLayers.forEach((layer) => {
        mapLayerOpacityMap[`raster_${layer.id}`] = layer?.default_style?.opacity !== undefined ? layer.default_style.opacity : 1.0;
      });
      const order: { id: number, opacity: number, name: string, type: 'netcdf' | 'vector' | 'raster' } [] = [];
      MapStore.selectedMapLayers.value.forEach((layer) => {
        if (layer.type === 'netcdf') {
          if (mapLayerOpacityMap[`netcdf_${layer.id}`] !== undefined) {
            order.push({
              id: layer.id, opacity: mapLayerOpacityMap[`netcdf_${layer.id}`], name: layer.name, type: layer.type,
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
        const found = visibleNetCDFLayers.value.find((layer) => item.id === layer.netCDFLayer);
        if (found) {
          found.opacity = val;
          updateNetCDFLayer(item.id, undefined, val);
        }
      }
    };
    return {
      processedLayers,
      iconMapper,
      updateOpacity,
    };
  },
});
</script>

<template>
  <v-card
    v-for="(item, index) in processedLayers"
    :key="`opacity_${index}`"
    class="mb-2 rounded-lg shadow-sm"
    elevation="2"
    density="compact"
  >
    <!-- Compact Card Title -->

    <!-- Compact Opacity Slider -->
    <v-card-text class="py-1 px-2">
      <span class="py-1 px-2 d-flex align-center">
        <v-icon size="16" class="mr-1" color="primary">
          {{ iconMapper[item.type] }}
        </v-icon>
        <span class="text-sm">{{ item.name }}</span>
      </span>

      <v-row align="center" no-gutters>
        <v-col cols="9">
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
    </v-card-text>
  </v-card>
</template>

<style scoped>
</style>
