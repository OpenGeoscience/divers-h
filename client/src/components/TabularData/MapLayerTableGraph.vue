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

    // eslint-disable-next-line vue/max-len
    const availableLayers = computed(() => MapStore.mapLayerFeatureGraphs.value.map((item) => ({ title: item.name, value: item.id })));

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

      try {
        loading.value = true;
        const data = await UVdatApi.getMapLayerFeatureGraphData(
          graph.type,
          selectedLayer.value,
          graph.xAxis,
          graph.yAxis,
          graph.indexer,
          bbox,
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
    return {
      selectedLayer,
      selectedChart,
      availableLayers,
      availableCharts,
      graphContainer,
      fetchMapLayerFeatureGraphData,
      loading,
      enabledColorMapping: MapStore.enabledMapLayerFeatureColorMapping,
    };
  },
});
</script>

<template>
  <v-card class="full-width-card">
    <v-card-text class="pa-0">
      <v-container fluid class="pa-0">
        <v-row no-gutters align="center">
          <v-col cols="3">
            <v-select
              v-model="selectedLayer"
              density="compact"
              :items="availableLayers"
              item-text="title"
              item-value="value"
              label="Select Layer"
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
                @click="enabledColorMapping = !enabledColorMapping"
              >
                mdi-palette
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

        <v-row no-gutters justify="center">
          <v-col cols="12" class="text-center">
            <v-progress-circular
              v-if="loading"
              indeterminate
              color="primary"
              size="32"
            />
          </v-col>
        </v-row>

        <v-row no-gutters>
          <v-col>
            <svg ref="graphContainer" height="300px" class="selectedFeatureSVG" />
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
