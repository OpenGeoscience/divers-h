<script lang="ts">
import {
  Ref, computed, defineComponent, onMounted, ref, watch,
} from 'vue';
import MapStore from '../../MapStore';
import { FeatureChart, VectorMapLayer } from '../../types';
import SelectedFeatureCharts from './SelectedFeatureCharts.vue'; // Import the previously created component
import { getLayerAvailableProperties } from '../../utils';

export default defineComponent({
  components: {
    SelectedFeatureCharts,
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const selectedFeatureCharts: Ref<FeatureChart[]> = ref([]);

    onMounted(() => {
      const found = MapStore.selectedVectorMapLayers.value.find((item: VectorMapLayer) => item.id === props.layerId);
      if (found?.default_style?.selectedFeatureCharts) {
        selectedFeatureCharts.value = found.default_style.selectedFeatureCharts;
      } else {
        // Initialize as empty array if undefined
        selectedFeatureCharts.value = [];
        if (found && found.default_style) {
          found.default_style.selectedFeatureCharts = selectedFeatureCharts.value;
        }
      }
    });

    const availablePropsMap = computed(() => {
      const properties = getLayerAvailableProperties(props.layerId);
      return properties;
    });
    // Watch for changes to the selected vector map layers and update the selectedFeatureCharts
    watch(MapStore.selectedVectorMapLayers, () => {
      const found = MapStore.selectedVectorMapLayers.value.find((item: VectorMapLayer) => item.id === props.layerId);
      if (found?.default_style?.selectedFeatureCharts) {
        selectedFeatureCharts.value = found.default_style.selectedFeatureCharts;
      } else {
        // Initialize as empty array if undefined
        selectedFeatureCharts.value = [];
        if (found && found.default_style) {
          found.default_style.selectedFeatureCharts = selectedFeatureCharts.value;
        }
      }
    }, { deep: true });

    const editChartsDialog = ref(false);

    return {
      selectedFeatureCharts,
      editChartsDialog,
      availablePropsMap,
    };
  },
});
</script>

<template>
  <!-- Row for Selected Feature Charts header and settings icon -->
  <v-row
    dense
    align="center"
    justify="center"
  >
    <h3>Selected Feature Charts</h3>
    <v-spacer />
    <!-- Cog icon to open dialog for editing -->
    <v-icon @click="editChartsDialog = true">
      mdi-cog
    </v-icon>
  </v-row>

  <!-- Row for displaying list of selected feature charts -->
  <v-row
    dense
    align="center"
    justify="center"
  >
    <v-col cols="6">
      <span>Name</span>
    </v-col>
    <v-col cols="3">
      <span>Type</span>
    </v-col>
    <v-col cols="3">
      <span>Info</span>
    </v-col>
  </v-row>

  <!-- Loop through selectedFeatureCharts and display each chart's name, type, and description -->
  <v-row
    v-for="chart in selectedFeatureCharts"
    :key="chart.name"
    dense
    align="center"
    justify="center"
  >
    <v-col cols="6">
      <span>{{ chart.name }}</span>
    </v-col>
    <v-col cols="3">
      <span>{{ chart.type }}</span>
    </v-col>
    <v-col cols="3">
      <v-tooltip>
        <template #activator="{ props }">
          <v-icon v-bind="props">
            mdi-information-outline
          </v-icon>
        </template>
        <v-card>
          <v-card-title>
            Selected Properties
          </v-card-title>
          <v-card-text>
            <v-row v-for="item in chart.keys" :key="`${chart.name}_${item.key}`" dense>
              <v-col style="font-size:8px">
                {{ availablePropsMap[item.key].displayName }}
              </v-col>
              <v-col cols="3">
                <div
                  class="color-square"
                  :style="{ backgroundColor: item.color }"
                />
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-tooltip>
    </v-col>
  </v-row>

  <!-- Dialog for editing feature charts using SelectedFeatureCharts.vue -->
  <v-dialog
    v-model="editChartsDialog"
    width="800"
  >
    <v-card>
      <v-card-title>Edit Feature Charts</v-card-title>
      <v-card-text>
        <!-- Pass layerId and selectedFeatureCharts to the SelectedFeatureCharts component -->
        <SelectedFeatureCharts :layer-id="layerId" :feature-charts="selectedFeatureCharts" />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.color-square {
  width: 10px;
  height: 10px;
  border: 1px solid #000;
  cursor: pointer;
}
</style>
