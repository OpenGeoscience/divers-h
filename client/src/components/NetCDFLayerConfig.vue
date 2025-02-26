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
      const found = visibleNetCDFLayers.value.find((item) => item.netCDFLayer === props.layer.id);
      layerOpacity.value = found?.opacity || 0.75;
      currentIndex.value = found?.currentIndex || 0;
    });
    const totalIndex = computed(() => {
      const found = visibleNetCDFLayers.value.find((item) => item.netCDFLayer === props.layer.id);
      return found?.images.length ? found.images.length - 1 : 0;
    });
    const stepMapping = computed(() => {
      const found = visibleNetCDFLayers.value.find((item) => item.netCDFLayer === props.layer.id);
      const mapSlicer: Record<number, string | number> = {};
      let unixTimeStamp = true;
      if (found) {
        if (found?.sliding) {
          for (let i = 0; i < found.images.length; i += 1) {
            mapSlicer[i] = found.sliding.min + i * found.sliding.step;
            if (found.sliding.variable === 'time') {
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
            return mapSlicer;
          }
        }
        for (let i = 0; i < found.images.length; i += 1) {
          mapSlicer[i] = i;
        }
      }
      return mapSlicer;
    });
    const updateIndex = () => {
      updateNetCDFLayer(props.layer.id, { index: currentIndex.value });
    };
    const throttledUpdateLayerFilter = throttle(updateIndex, 50);

    watch([currentIndex], () => {
      throttledUpdateLayerFilter();
    });
    watch([layerOpacity], () => {
      updateNetCDFLayer(props.layer.id, { opacity: layerOpacity.value });
    });

    return {
      layerOpacity,
      currentIndex,
      totalIndex,
      stepMapping,
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
        <v-slider
          v-model="currentIndex"
          density="compact"
          min="0"
          step="1"
          :max="totalIndex"
          hide-details
        >
          <template #prepend>
            <span class="pl-2">
              {{
                stepMapping[currentIndex]
              }}</span>
          </template>
        </v-slider>
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
        <v-slider
          v-model="layerOpacity"
          density="compact"
          min="0"
          max="1.0"
          hide-details
        >
          <template #prepend>
            <span class="pl-2">Opacity
              {{
                layerOpacity.toFixed(2)
              }}</span>
          </template>
        </v-slider>
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
