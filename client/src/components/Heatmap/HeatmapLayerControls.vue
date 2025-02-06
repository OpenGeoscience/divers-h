<!-- eslint-disable vue/max-len -->
<script lang="ts">
import {
  PropType, Ref, computed, defineComponent, nextTick, onMounted, ref,
} from 'vue';
import { cloneDeep } from 'lodash';
import {
  AnnotationTypes, HeatMapConfig, VectorLayerDisplayConfig,
} from '../../types';

import { updateLayer } from '../../map/mapLayers';
import { drawGradients, getVectorLayerDisplayConfig } from '../../utils';
import HeatmapColorEditor from './HeatmapColorEditor.vue';
import HeatmapWeightIntensity from './HeatmapWeightIntensity.vue';

export default defineComponent({
  components: {
    HeatmapColorEditor,
    HeatmapWeightIntensity,
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
    layerType: {
      type: String as PropType<AnnotationTypes>,
      required: true,
    },
  },
  setup(props) {
    const heatMapConfig: Ref<HeatMapConfig | null> = ref(null);

    const calculateGradient = () => {
      nextTick(() => {
        const colors = heatMapConfig.value?.color?.map((item) => item.color) || [];
        drawGradients(colors, 'heatmap', 175);
      });
    };
    const initializeConfg = () => {
      const { layer, displayConfig } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      if (displayConfig === undefined) {
        if (layer?.default_style.layers) {
          heatMapConfig.value = {
            radius: 30,
            weight: 1,
            intensity: 1,
            color: [
              { value: 0, color: '#0000FF' },
              { value: 0.1, color: '#4169e1' },
              { value: 0.3, color: '#00ffff' },
              { value: 0.5, color: '#00ff00' },
              { value: 0.7, color: '#ffff00' },
              { value: 1.0, color: '#ff0000' },
            ],
          };
          layer.default_style.layers.heatmap = {
            enabled: false,
            heatmap: heatMapConfig.value,
          };
        }
        calculateGradient();
        return;
      }

      if (displayConfig !== true && displayConfig !== false) {
        if (displayConfig.heatmap) {
          heatMapConfig.value = cloneDeep(displayConfig.heatmap);
        } else {
          heatMapConfig.value = {
            radius: 30,
            weight: 1,
            intensity: 1,
            color: [
              { value: 0, color: '#0000FF' },
              { value: 0.1, color: '#4169e1' },
              { value: 0.3, color: '#00ffff' },
              { value: 0.5, color: '#00ff00' },
              { value: 0.7, color: '#ffff00' },
              { value: 1.0, color: '#ff0000' },
            ],
          };
        }
      }
      calculateGradient();
    };
    onMounted(() => initializeConfg());

    const isNumber = computed(() => {
      const vals: Record<'radius' | 'weight' | 'intensity', boolean> = {
        radius: typeof heatMapConfig.value?.radius === 'number',
        weight: typeof heatMapConfig.value?.weight === 'number',
        intensity: typeof heatMapConfig.value?.intensity === 'number',
      };
      return vals;
    });
    const saveUpdate = () => {
      const { layer } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      const { layerType } = props;
      if (
        heatMapConfig.value
        && layer?.default_style?.layers
        && layer.default_style.layers[layerType as 'heatmap'] !== false
        && layer.default_style.layers[layerType as 'heatmap'] !== true
      ) {
        (layer.default_style.layers[layerType as 'heatmap'] as VectorLayerDisplayConfig).heatmap = heatMapConfig.value;
        updateLayer(layer);
      }
    };

    const heatmapColorListing = computed(() => {
      if (heatMapConfig.value && heatMapConfig.value.color) {
        return heatMapConfig.value.color;
      }
      return [];
    });

    const updateHeatmapValue = (type: 'radius' | 'weight' | 'intensity', value: number) => {
      if (heatMapConfig.value) {
        if (type === 'radius') {
          heatMapConfig.value.radius = value;
        }
        if (type === 'weight') {
          heatMapConfig.value.weight = value;
        }
        if (type === 'intensity') {
          heatMapConfig.value.intensity = value;
        }
      }
      saveUpdate();
    };

    const updateColor = (colors: { value: number, color: string }[]) => {
      if (heatMapConfig.value) {
        heatMapConfig.value.color = colors;
      }
      saveUpdate();
      calculateGradient();
    };
    const heatmapColorDialog = ref(false);
    const heatmapWeightDialog = ref(false);
    const heatmapIntensityDialog = ref(false);

    interface StaticUpdate {
      type:'static';
      value: number;
    }
    interface WeightUpdate {
      type:'linear';
      attribute:string;
      numberPairs: [number, number][];
    }
    interface ZoomUpdate {
      type:'zoom';
      numberPairs: [number, number][];
    }
    type WeightIntensityUpdate = StaticUpdate | WeightUpdate | ZoomUpdate;

    const updateWeightIntensity = (type: 'weight' | 'intensity', data: WeightIntensityUpdate) => {
      if (heatMapConfig.value) {
        if (data.type === 'static' && type === 'weight') {
          heatMapConfig.value.weight = data.value;
        } else if (data.type === 'static' && type === 'intensity') {
          heatMapConfig.value.intensity = data.value;
        } else if (data.type === 'zoom' && type === 'intensity') {
          heatMapConfig.value.intensity = {
            type: 'SizeZoom',
            zoomLevels: data.numberPairs,
          };
        } else if (data.type === 'linear' && type === 'weight') {
          heatMapConfig.value.weight = {
            type: 'SizeLinear',
            attribute: data.attribute,
            linearLevels: data.numberPairs,
          };
        }
        saveUpdate();
      }
    };

    return {
      heatMapConfig,
      updateHeatmapValue,
      isNumber,
      heatmapColorListing,
      updateColor,
      heatmapColorDialog,
      heatmapWeightDialog,
      heatmapIntensityDialog,
      updateWeightIntensity,
    };
  },
});
</script>

<template>
  <div v-if="heatMapConfig">
    <v-row
      dense
      align="center"
      justify="center"
    >
      <v-col cols="2">
        <v-tooltip text="Radius">
          <template #activator="{ props }">
            <v-icon
              class="pl-3"
              v-bind="props"
            >
              mdi-radius-outline
            </v-icon>
          </template>
        </v-tooltip>
      </v-col>
      <v-col v-if="isNumber.radius" cols="2">
        {{ heatMapConfig.radius.toFixed(0) }}
      </v-col>

      <v-col v-if="isNumber.radius">
        <v-slider
          density="compact"
          class="heatmap-slider"
          min="1"
          max="200"
          width="100"
          :step="1"
          :model-value="heatMapConfig.radius"
          @update:model-value="updateHeatmapValue('radius', $event)"
        />
      </v-col>
    </v-row>
    <v-row
      dense
      align="center"
      justify="center"
    >
      <v-col cols="2">
        <v-tooltip text="Weight">
          <template #activator="{ props }">
            <v-icon
              class="pl-3"
              v-bind="props"
            >
              mdi-weight
            </v-icon>
          </template>
        </v-tooltip>
      </v-col>
      <v-col v-if="isNumber.weight" cols="2">
        {{ heatMapConfig.weight.toFixed(0) }}
      </v-col>

      <v-col v-if="isNumber.weight">
        <v-slider
          density="compact"
          class="heatmap-slider"
          min="0"
          max="200"
          width="100"
          :step="1"
          :model-value="heatMapConfig.weight"
          @update:model-value="updateHeatmapValue('weight', $event)"
        />
      </v-col>
      <v-col v-else>
        <span>Linear Attribute</span>
      </v-col>
      <v-col>
        <v-icon @click="heatmapWeightDialog = true">
          mdi-pencil
        </v-icon>
      </v-col>
    </v-row>
    <v-row
      dense
    >
      <v-col cols="2">
        <v-tooltip text="Intensity">
          <template #activator="{ props }">
            <v-icon
              class="pl-3"
              v-bind="props"
            >
              mdi-format-line-weight
            </v-icon>
          </template>
        </v-tooltip>
      </v-col>
      <v-col v-if="isNumber.intensity" cols="2">
        {{ heatMapConfig.intensity.toFixed(2) }}
      </v-col>
      <v-col v-if="isNumber.intensity">
        <v-slider
          density="compact"
          class="heatmap-slider"
          min="0"
          max="50"
          width="100"
          :step="0.01"
          :model-value="heatMapConfig.intensity"
          @update:model-value="updateHeatmapValue('intensity', $event)"
        />
      </v-col>
      <v-col v-else>
        <span>Linear Zoom</span>
      </v-col>
      <v-col>
        <v-icon @click="heatmapIntensityDialog = true">
          mdi-pencil
        </v-icon>
      </v-col>
    </v-row>
    <v-row
      dense
      align="center"
      justify="center"
    >
      <v-col cols="2">
        <v-tooltip text="Heatmap Color">
          <template #activator="{ props }">
            <v-icon
              class="pl-3"
              v-bind="props"
            >
              mdi-brush
            </v-icon>
          </template>
        </v-tooltip>
      </v-col>
      <v-col>
        <svg
          :id="`gradientImage-heatmap`"
          width="175"
          height="20"
        />
      </v-col>
      <v-col>
        <v-icon @click="heatmapColorDialog = true">
          mdi-pencil
        </v-icon>
      </v-col>
    </v-row>
  </div>
  <v-dialog v-model="heatmapWeightDialog" width="600">
    <v-card>
      <v-card-title>Heatmap Weight Editor</v-card-title>
      <v-card-text>
        <heatmap-weight-intensity
          :layer-id="layerId"
          :layer-type="layerType"
          data-type="weight"
          @update="updateWeightIntensity('weight', $event)"
        />
      </v-card-text>
    </v-card>=
  </v-dialog>
  <v-dialog v-model="heatmapIntensityDialog" width="600">
    <v-card>
      <v-card-title>Heatmap Intensity Editor</v-card-title>
      <v-card-text>
        <heatmap-weight-intensity
          :layer-id="layerId"
          :layer-type="layerType"
          data-type="intensity"
          @update="updateWeightIntensity('intensity', $event)"
        />
      </v-card-text>
    </v-card>=
  </v-dialog>

  <v-dialog v-model="heatmapColorDialog" width="600">
    <v-card>
      <v-card-title>Heatmap Color Editor</v-card-title>
      <v-card-text>
        <heatmap-color-editor
          :color-listing="heatmapColorListing"
          @update-color="updateColor($event)"
        />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.heatmap-slider {
    height: 20px;
    margin-bottom: 15px;
}
</style>
