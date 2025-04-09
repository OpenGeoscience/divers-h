<script lang="ts">
import * as d3 from 'd3';
import {
  computed,
  defineComponent,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from 'vue';
import { throttle } from 'lodash';
import UVdatApi from '../../api/UVDATApi';
import { FeatureGraphData } from '../../types';
import { getStringBBox } from '../../map/mapLayers';
import MapStore from '../../MapStore';
import { renderVectorFeatureGraph } from '../FeatureSelection/vectorFeatureGraphUtils';

export default defineComponent({
  name: 'MapLayerTableGraph',
  setup() {
    const selectedLayer = ref<number | null>(null);
    const selectedChart = ref<number | null>(null);
    const graphContainer = ref<SVGSVGElement | null>(null);
    const graphData = ref<FeatureGraphData | null>(null);
    const loading = ref<boolean>(false);
    const hideBaseData = ref(false);
    const trendLine = ref(false);
    const confidenceIntervalEnabled = ref(false);
    const confidenceLevel = ref(95);
    const aggregate = ref(true);
    const movingAverageEnabled = ref(false);
    const movingAverageValue = ref(12);
    // eslint-disable-next-line vue/max-len
    const availableLayers = computed(() => MapStore.mapLayerFeatureGraphs.value.map((item) => ({ title: item.name, value: item.id })));

    const maxMovingAverage = computed(() => {
      if (graphData.value) {
        if (graphData.value?.graphs) {
          const values = Object.values(graphData.value.graphs);
          let max = -Infinity;
          for (let i = 0; i < values.length; i += 1) {
            max = Math.max(max, Math.floor(values[i].data.length / 4));
          }
          return max;
        }
      }
      return 50;
    });

    const availableCharts = computed(() => {
      if (availableLayers.value && selectedLayer.value) {
        const found = MapStore.mapLayerFeatureGraphs.value.find((item) => item.id === selectedLayer.value);
        if (found) {
          return found.graphs.map((item, index) => ({ title: item.name, value: index }));
        }
      }
      return [];
    });

    // Watch for layer change and reset selected chart
    watch(selectedLayer, () => {
      selectedChart.value = availableCharts.value.length > 0 ? availableCharts.value[0].value : null;
      graphData.value = null;
    });

    const onLineHover = (vectorFeatureId: number) => {
      if (!MapStore.hoveredFeatures.value.includes(vectorFeatureId)) {
        MapStore.hoveredFeatures.value.push(vectorFeatureId);
      }
    };
    const onLineExit = (vectorFeatureId: number) => {
      const foundIndex = MapStore.hoveredFeatures.value.findIndex((item) => item === vectorFeatureId);
      if (foundIndex !== -1) {
        MapStore.hoveredFeatures.value.splice(foundIndex, 1);
      }
    };
    // Fetch chart data based on selected layer and chart
    const fetchMapLayerFeatureGraphData = async () => {
      if (selectedLayer.value === null || selectedChart.value === null) return;

      const bbox = getStringBBox();
      const found = MapStore.mapLayerFeatureGraphs.value.find((item) => item.id === selectedLayer.value);
      const graph = found?.graphs[selectedChart.value];

      if (!graph) return;

      const display: ('data' | 'trendLine' | 'confidenceInterval' | 'movingAverage')[] = ['data'];
      if (aggregate.value) {
        if (trendLine.value) {
          display.push('trendLine');
        }
        if (confidenceIntervalEnabled.value) {
          display.push('confidenceInterval');
        }
        if (movingAverageEnabled.value) {
          display.push('movingAverage');
        }
      } else {
        hideBaseData.value = false;
      }

      try {
        loading.value = true;
        const data = await UVdatApi.getMapLayerFeatureGraphData(
          graph.type,
          selectedLayer.value,
          graph.xAxis,
          graph.yAxis,
          graph.indexer,
          bbox,
          display,
          confidenceLevel.value,
          aggregate.value,
          movingAverageValue.value,
        );
        graphData.value = data;

        if (graphContainer.value) {
          const colorMapping = renderVectorFeatureGraph(
            data,
            graphContainer.value,
            {
              xAxisIsTime: graph.xAxis === 'unix_time',
              onLineHover,
              onLineExit,
              xAxisLabel: graph.xAxisLabel,
              yAxisLabel: graph.yAxisLabel,
              hideBaseData: hideBaseData.value,
              showTrendline: trendLine.value,
              showConfidenceInterval: confidenceIntervalEnabled.value,
              showMovingAverage: movingAverageEnabled.value,
            },
            300,
          );
          MapStore.mapLayerFeatureColorMapping.value = colorMapping;
        }
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('Error fetching feature graph data:', error);
      } finally {
        loading.value = false;
      }
    };

    // Automatically select the first available layer and chart on mount
    onMounted(() => {
      if (availableLayers.value.length > 0) {
        selectedLayer.value = availableLayers.value[0].value;
      }
    });

    // Watch for chart selection change and fetch data automatically
    watch([selectedChart], fetchMapLayerFeatureGraphData);

    const reversePathHover = (vectorFeatureId: number) => {
      d3.selectAll('path') // Select all paths
        .attr('opacity', 0.3); // Dim all lines
      d3.selectAll('path')
        .filter((d, i, nodes) => d3.select(nodes[i]).attr('vectorFeatureId') === vectorFeatureId.toString())
        .attr('stroke-width', 4).attr('opacity', 1.0);
    };

    watch(MapStore.hoveredFeatures, () => {
      if (MapStore.hoveredFeatures.value.length === 0) {
        d3.selectAll('path') // Select all paths
          .attr('opacity', 1.0)
          .attr('stroke-width', 2);
      } else {
        MapStore.hoveredFeatures.value.forEach((vectorFetureId) => {
          reversePathHover(vectorFetureId);
        });
      }
    }, { deep: true });

    onUnmounted(() => {
      MapStore.enabledMapLayerFeatureColorMapping.value = false;
      MapStore.mapLayerFeatureColorMapping.value = {};
      MapStore.clearHoveredFeatures();
    });

    const throttledUpateGraph = throttle(fetchMapLayerFeatureGraphData, 500);
    watch([
      aggregate,
      hideBaseData,
      trendLine,
      confidenceIntervalEnabled,
      confidenceLevel,
      movingAverageEnabled,
      movingAverageValue,
    ], throttledUpateGraph);

    return {
      selectedLayer,
      selectedChart,
      availableLayers,
      availableCharts,
      graphContainer,
      fetchMapLayerFeatureGraphData,
      loading,
      enabledColorMapping: MapStore.enabledMapLayerFeatureColorMapping,
      hideBaseData,
      trendLine,
      confidenceIntervalEnabled,
      confidenceLevel,
      movingAverageEnabled,
      movingAverageValue,
      aggregate,
      maxMovingAverage,
    };
  },
});
</script>

<template>
  <v-card class="full-width-card">
    <v-card-text class="pa-0">
      <v-container fluid class="pa-0">
        <v-row no-gutters dense align="center">
          <v-col cols="3">
            <v-select
              v-model="selectedLayer"
              density="compact"
              :items="availableLayers"
              item-text="title"
              item-value="value"
              label="Select Layer"
              hide-details
              dense
              outlined
            />
          </v-col>

          <v-col cols="3">
            <v-select
              v-model="selectedChart"
              density="compact"
              :disabled="selectedLayer === null"
              :items="availableCharts"
              item-text="title"
              item-value="value"
              label="Select Chart"
              hide-details
              dense
              outlined
            />
          </v-col>
          <v-tooltip text="Map Colors from graph to vector features">
            <template #activator="{ props }">
              <v-icon
                v-bind="props"
                :color="enabledColorMapping ? 'primary' : 'light-gray'"
                size="x-large"
                class="pb-4"
                :disabled="aggregate"
                @click="enabledColorMapping = !enabledColorMapping"
              >
                mdi-palette
              </v-icon>
            </template>
          </v-tooltip>
          <v-tooltip text="Average all Values">
            <template #activator="{ props }">
              <v-icon
                v-bind="props"
                :color="aggregate ? 'primary' : 'light-gray'"
                size="x-large"
                class="pb-4"
                @click="aggregate = !aggregate"
              >
                mdi-set-all
              </v-icon>
            </template>
          </v-tooltip>

          <v-tooltip
            v-if="selectedChart !== null"
            text="Reload graph data based on current Map View"
          >
            <template #activator="{ props }">
              <v-btn
                v-bind="props"
                color="primary"
                :disabled="loading"
                class="mb-4 ml-4"
                @click="fetchMapLayerFeatureGraphData"
              >
                Reload <v-icon>mdi-refresh</v-icon>
              </v-btn>
            </template>
          </v-tooltip>
        </v-row>
        <v-row v-if="aggregate" dense>
          <v-col>
            <v-checkbox v-model="hideBaseData" density="compact" hide-details label="Hide Data" />
          </v-col>
          <v-col>
            <v-checkbox v-model="trendLine" density="compact" hide-details label="TrendLine" />
          </v-col>
          <v-col>
            <v-checkbox v-model="confidenceIntervalEnabled" density="compact" hide-details label="Confidence" />
            <v-slider
              v-if="confidenceIntervalEnabled"
              v-model="confidenceLevel"
              color="primary"
              :min="50"
              step="1"
              :max="99"
              :label="`${confidenceLevel.toFixed(1)}%`"
              hide-details
            />
          </v-col>
          <v-col>
            <v-checkbox v-model="movingAverageEnabled" density="compact" hide-details label="Moving Average" />
            <v-slider
              v-if="movingAverageEnabled"
              v-model="movingAverageValue"
              color="primary"
              :min="2"
              step="1"
              :max="maxMovingAverage"
              :label="movingAverageValue.toFixed(0)"
              hide-details
            />
          </v-col>
        </v-row>

        <v-row no-gutters justify="center">
          <v-spacer />
          <v-progress-circular
            v-if="loading"
            indeterminate
            color="primary"
            size="256"
            width="32"
            style="position:absolute"
          />
          <v-spacer />
        </v-row>

        <v-row no-gutters>
          <v-col>
            <svg
              ref="graphContainer"
              height="300px"
              class="selectedFeatureSVG"
              :style="loading ? 'opacity: 0.2;' : 'opacity: 1.0' "
            />
          </v-col>
        </v-row>
      </v-container>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.selectedFeatureSVG {
  width: 100%;
  height: auto;
}

.line {
  fill: none;
  stroke: steelblue;
  stroke-width: 1.5;
}

.axis path,
.axis line {
  fill: none;
  shape-rendering: crispEdges;
}

.x.axis text,
.y.axis text {
  font-size: 12px;
}
</style>
