<script lang="ts">
import {
  Ref, computed,
  defineComponent,
  ref,
  watch,
} from 'vue';
import MapStore from '../../MapStore';
import AddEditChart from './AddEditChart.vue';
import { CustomChart, VectorMapLayer } from '../../types';
import ChartRenderer from './ChartRenderer.vue';
import UVdatApi from '../../api/UVDATApi';

export default defineComponent({
  components: {
    AddEditChart,
    ChartRenderer,
  },
  setup() {
    const configuredChartsByMap = computed(() => {
      const visible = MapStore.selectedVectorMapLayers.value.filter(
        (item) => MapStore.visibleMapLayers.value.has(`${item.type}_${item.id}`),
      );
      const mapChartList: Record<number, { map: VectorMapLayer, charts: CustomChart[] }> = {};
      visible.filter((item) => item?.default_style?.charts?.length).forEach((item) => {
        if (mapChartList[item.id] === undefined && item.default_style.charts?.length) {
          mapChartList[item.id] = {
            map: item, charts: item.default_style.charts,
          };
        }
      });
      return mapChartList;
    });
    const mapsEnabled = computed(
      () => MapStore.selectedVectorMapLayers.value.filter(
        (item) => MapStore.visibleMapLayers.value.has(`${item.type}_${item.id}`),
      ).length,
    );
    const enabledMapPanels: Ref<number[]> = ref([]);
    const enabledChartPanels: Ref<Record<number, number[]>> = ref({});
    const addingEditingChart = ref(false);
    const editingChart: Ref<CustomChart | null> = ref(null);
    const editingChartIndex = ref(-1);
    const addEditChart = (editing: CustomChart | null, index = -1) => {
      addingEditingChart.value = true;
      editingChart.value = editing;
      editingChartIndex.value = index;
    };

    const cancelEditChart = () => {
      editingChart.value = null;
      addingEditingChart.value = false;
      editingChartIndex.value = -1;
    };
    watch(configuredChartsByMap, () => {
      enabledMapPanels.value = [];
      Object.values(configuredChartsByMap.value).forEach((item) => {
        enabledMapPanels.value.push(item.map.id);
        enabledChartPanels.value[item.map.id] = [];
        item.charts.forEach((chart, index) => {
          if (chart.expanded) {
            enabledChartPanels.value[item.map.id].push(index);
          }
        });
      });
    });
    const saveEditChart = (chartData: CustomChart) => {
      const foundLayer = MapStore.selectedMapLayers.value.find((item) => item.id === chartData.mapLayer);
      if (foundLayer) {
        if (foundLayer.default_style && !foundLayer.default_style?.charts) {
          foundLayer.default_style.charts = [];
        }
        if (foundLayer.default_style?.charts && editingChartIndex.value === -1) {
          foundLayer.default_style.charts.push(chartData);
        } else if (foundLayer.default_style?.charts) {
          foundLayer.default_style.charts.splice(editingChartIndex.value, 1, chartData);
        }
      }
      cancelEditChart();
    };
    const deleteChart = (mapLayer: number, index: number) => {
      const foundLayer = MapStore.selectedMapLayers.value.find((item) => item.id === mapLayer);
      if (foundLayer) {
        if (foundLayer.default_style && foundLayer.default_style?.charts) {
          foundLayer.default_style.charts.splice(index, 1);
        }
      }
    };

    const saveAllCharts = async () => {
      const visibleLayers = MapStore.selectedVectorMapLayers.value.filter(
        (item) => MapStore.visibleMapLayers.value.has(`${item.type}_${item.id}`),
      );
      for (let i = 0; i < visibleLayers.length; i += 1) {
        if (visibleLayers[i].default_style.charts) {
          const layerId = visibleLayers[i].id;
          const layerType = visibleLayers[i].type;
          const layerRepId = visibleLayers[i].layerRepresentationId;
          if (layerRepId === undefined || layerRepId === -1) {
            UVdatApi.patchVectorLayer(layerId, visibleLayers[i].default_style);
          } else {
            // eslint-disable-next-line no-await-in-loop
            const reps = await UVdatApi.getLayerRepresentations(layerId, layerType);
            const layerReps = reps.filter((item) => (MapStore.proMode.value ? item.enabled : true));
            if (layerRepId > -1) {
              UVdatApi.patchLayerRepresentation(
                layerRepId,
                {
                  ...layerReps[layerRepId],
                  default_style: visibleLayers[i].default_style,
                  type: visibleLayers[i].type,
                  layer_id: layerId,
                },
              );
            }
          }
        }
      }
    };
    return {
      proMode: MapStore.proMode,
      configuredChartsByMap,
      addingEditingChart,
      editingChart,
      addEditChart,
      cancelEditChart,
      saveEditChart,
      deleteChart,
      mapsEnabled,
      enabledMapPanels,
      enabledChartPanels,
      saveAllCharts,
    };
  },
});
</script>
<template>
  <v-container>
    <v-row v-if="proMode">
      <p>
        Charts are attached to a Map Layer's styling or Layer Representation.
        When adding a new chart it will be saved to the styling
      </p>
    </v-row>
    <v-row v-if="proMode && mapsEnabled" class="my-4">
      <v-spacer />
      <v-btn
        color="success"
        :disabled="addingEditingChart"
        @click="addEditChart(null)"
      >
        Add Chart
      </v-btn>
      <v-icon
        color="success"
        :disabled="addingEditingChart"
        class="ml-2"
        @click="saveAllCharts()"
      >
        mdi-content-save
      </v-icon>
    </v-row>
    <add-edit-chart
      v-if="addingEditingChart"
      :edit-chart="editingChart"
      @cancel="cancelEditChart()"
      @save="saveEditChart($event)"
    />
    <div v-else>
      <v-expansion-panels v-model="enabledMapPanels" multiple>
        <v-expansion-panel
          v-for="mapLayer in configuredChartsByMap"
          :key="mapLayer.map.id"
          :value="mapLayer.map.id"
        >
          <v-expansion-panel-title>
            {{ mapLayer.map.name }} Charts
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-expansion-panels
              v-model="enabledChartPanels[mapLayer.map.id]"
              multiple
            >
              <v-expansion-panel
                v-for="(chart, index) in mapLayer.charts"
                :key="`${mapLayer.map.id}_chart_${index}`"
                :value="index"
              >
                <v-expansion-panel-title>
                  <v-row v-if="proMode" align="center" justify="center">
                    <v-icon class="pr-2">
                      {{ chart.chartType === 'histogram' ? 'mdi-chart-bar' : 'mdi-chart-arc' }}
                    </v-icon>
                    {{ chart.title }}
                    <v-spacer />
                    <div class="mr-6">
                      <v-tooltip text="Edit Collection" location="top">
                        <template #activator="{ props }">
                          <v-icon
                            v-bind="props"
                            color="warning"
                            @click.stop="addEditChart(chart, index)"
                          >
                            mdi-pencil
                          </v-icon>
                        </template>
                      </v-tooltip>
                      <v-tooltip text="Delete Collection" location="top">
                        <template #activator="{ props }">
                          <v-icon
                            v-bind="props"
                            color="error"
                            @click.stop="deleteChart(mapLayer.map.id, index)"
                          >
                            mdi-delete
                          </v-icon>
                        </template>
                      </v-tooltip>
                    </div>
                  </v-row>
                  <v-row v-else justify="center" align="center">
                    <v-icon class="pr-2">
                      {{ chart.chartType === 'histogram' ? 'mdi-chart-bar' : 'mdi-chart-arc' }}
                    </v-icon>
                    {{ chart.title }}
                    <v-spacer />
                  </v-row>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-row v-if="chart.description">
                    <b class="mr-2">Description:</b>{{ chart.description }}
                  </v-row>
                  <chart-renderer :chart-config="chart" :map-layer-id="mapLayer.map.id" />
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </div>
  </v-container>
</template>
<style scoped>
</style>
