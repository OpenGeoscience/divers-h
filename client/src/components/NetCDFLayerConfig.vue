<script lang="ts">
import {
  PropType, computed, defineComponent, onMounted, ref,
  watch,
} from 'vue';
import { throttle } from 'lodash';
import { NetCDFLayer } from '../types';
import { updateNetCDFLayer, visibleNetCDFLayers } from '../map/mapNetCDFLayer';

export default defineComponent({
  props: {
    layer: {
      type: Object as PropType<NetCDFLayer>,
      required: true,
    },
  },
  emits: ['toggleLayer', 'deselectLayer'],
  setup(props) {
    const layerOpacity = ref(0);
    const currentIndex = ref(0);
    onMounted(() => {
      const found = visibleNetCDFLayers.find((item) => item.netCDFLayer === props.layer.id);
      layerOpacity.value = found?.opacity || 0.75;
      currentIndex.value = found?.currentIndex || 0;
    });
    const totalIndex = computed(() => {
      const found = visibleNetCDFLayers.find((item) => item.netCDFLayer === props.layer.id);
      return found?.images.length || 0;
    });
    const updateIndex = () => {
      updateNetCDFLayer(props.layer.id, currentIndex.value);
    };
    const throttledUpdateLayerFilter = throttle(updateIndex, 50);

    watch([currentIndex], () => {
      throttledUpdateLayerFilter();
    });
    watch([layerOpacity], () => {
      updateNetCDFLayer(props.layer.id, undefined, layerOpacity.value);
    });

    return {
      layerOpacity,
      currentIndex,
      totalIndex,
    };
  },
});
</script>

<template>
  <v-card-title />
  <v-card-text>
    <v-row
      dense
      align="center"
      justify="center"
    >
      <v-col cols="2">
        <v-tooltip text="Opacity">
          <template #activator="{ props }">
            <v-icon
              class="pl-3"
              v-bind="props"
            >
              mdi-timer-outline
            </v-icon>
          </template>
        </v-tooltip>
      </v-col>
      <v-col>
        <v-icon>
          mdi-checkbox-marked
        </v-icon>
        <span class="pl-2">Step
          {{
            currentIndex
          }}</span>
      </v-col>
      <v-col>
        <v-slider
          v-model="currentIndex"
          density="compact"
          min="0"
          step="1"
          :max="totalIndex"
        />
      </v-col>
    </v-row>
    <v-row
      dense
      align="center"
      justify="center"
    >
      <v-col cols="2">
        <v-tooltip text="Opacity">
          <template #activator="{ props }">
            <v-icon
              class="pl-3"
              v-bind="props"
            >
              mdi-square-opacity
            </v-icon>
          </template>
        </v-tooltip>
      </v-col>
      <v-col>
        <v-icon>
          mdi-checkbox-marked
        </v-icon>
        <span class="pl-2">Opacity
          {{
            layerOpacity.toFixed(2)
          }}</span>
      </v-col>
      <v-col>
        <v-slider
          v-model="layerOpacity"
          density="compact"
          min="0"
          max="1.0"
        />
      </v-col>
    </v-row>
  </v-card-text>
</template>

<style scoped>

.icon-center {
  width: 35px;
  height: 35px;
  border: 1px solid lightgray;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
