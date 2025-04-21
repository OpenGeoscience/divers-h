<script lang="ts">
import * as d3 from 'd3';
import {
  PropType,
  Ref,
  computed,
  defineComponent,
  onMounted,
  ref,
  watch,
} from 'vue';
import { first, throttle } from 'lodash';
import UVdatApi from '../../api/UVDATApi';
import { FeatureGraphData, FeatureGraphs, FeatureGraphsRequest } from '../../types';
import MapStore from '../../MapStore';
import { renderVectorFeatureGraph } from '../FeatureSelection/vectorFeatureGraphUtils';

const colorScale = d3.scaleOrdinal(d3.schemeCategory10);
export default defineComponent({
  name: 'VectorFeatureTableGraph',
  props: {
    vectorFeatureId: {
      type: Number as PropType<number>,
      required: true,
    },
    mapLayerId: {
      type: Number,
      required: true,
    },
    defaultGraphs: {
      type: Array as PropType<string[]>,
      default: () => [],
    },
  },

  setup(props) {
    const selectedGraphs: Ref<string[]> = ref([]);
    const graphColorMap = ref<Record<string, string>>({});
    const graphContainer = ref<SVGSVGElement | null>(null);
    const graphData = ref<FeatureGraphs[]>([]);
    const loading = ref<boolean>(false);
    const hideBaseData = ref(false);
    const trendLine = ref(false);
    const confidenceIntervalEnabled = ref(false);
    const confidenceLevel = ref(95);
    const aggregate = ref(true);
    const movingAverageEnabled = ref(false);
    const movingAverageValue = ref(12);
    // eslint-disable-next-line vue/max-len

    const maxMovingAverage = computed(() => {
      if (graphData.value) {
        let max = -Infinity;
        graphData.value.forEach((graphFeature) => {
          if (graphFeature.graphs.graphs) {
            Object.values(graphFeature.graphs.graphs).forEach((graph) => {
              const { data } = graph;
              for (let i = 0; i < data.length; i += 1) {
                max = Math.max(max, Math.floor(data[i].length / 4));
              }
            });
          }
        });
        return max;
      }
      return 50;
    });

    const availableVectorGraphs = computed(() => {
      const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.mapLayerId);
      if (found?.default_style.vectorFeatureTableGraphs) {
        return found.default_style.vectorFeatureTableGraphs;
      }
      return [];
    });
    const assignGraphColors = () => {
      graphColorMap.value = {};
      availableVectorGraphs.value.forEach((graph) => {
        if (!graphColorMap.value[graph.name]) {
          graphColorMap.value[graph.name] = colorScale(graph.name);
        }
      });
    };
    watch(availableVectorGraphs, () => assignGraphColors(), { immediate: true });
    // Fetch chart data based on selected layer and chart
    const fetchMapLayerFeatureGraphData = async () => {
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

      const baseRequestPayload: FeatureGraphsRequest = {
        tableTypes: [],
        vectorFeatureId: props.vectorFeatureId,
        xAxes: [],
        yAxes: [],
        indexers: [],
        display,
        confidenceLevel: confidenceLevel.value,
        aggregate: aggregate.value,
        movingAverage: movingAverageValue.value,

      };
      const graphNames: { name: string, type: string, xAxis: string, yAxis: string }[] = [];
      if (selectedGraphs.value.length === 0) {
        graphContainer.value?.setAttribute('style', 'display: none;');
        return;
      }
      graphContainer.value?.setAttribute('style', 'display: inline;');

      selectedGraphs.value.forEach((name) => {
        const data = availableVectorGraphs.value.find((graph) => graph.name === name);
        if (data) {
          baseRequestPayload.xAxes?.push(data.xAxis);
          baseRequestPayload.yAxes?.push(data.yAxis);
          if (data.indexer) {
            baseRequestPayload.indexers?.push(data.indexer);
          }
          baseRequestPayload.tableTypes.push(data.type);
          graphNames.push({
            name: data.name,
            type: data.type,
            xAxis: data.xAxis,
            yAxis: data.yAxis,
          });
        }
      });

      try {
        loading.value = true;
        const data = await UVdatApi.getFeatureGraphsData(baseRequestPayload);
        graphData.value = data;
        let minGraph = Infinity;
        let maxGraph = -Infinity;
        let minGraphY = Infinity;
        let maxGraphY = -Infinity;

        let steps = Infinity;
        data.forEach((featureGraph) => {
          Object.keys(featureGraph.graphs.graphs).forEach((key) => {
            const index = parseInt(key, 10);
            const [min, max] = featureGraph.graphs.xAxisRange;
            const [minY, maxY] = featureGraph.graphs.xAxisRange;

            minGraph = Math.min(minGraph, min);
            maxGraph = Math.max(maxGraph, max);
            minGraphY = Math.min(minGraphY, minY);
            maxGraphY = Math.max(maxGraphY, maxY);
            const stepChartSize = (max - min) / featureGraph.graphs.graphs[index].data.length;
            steps = Math.min(steps, stepChartSize);
          });
        });
        console.log('minGraph', minGraph, 'maxGraph', maxGraph, 'steps', steps);
        MapStore.updateChartsMinMax(minGraph, maxGraph, steps);
        const graphRenderData: FeatureGraphData = {
          table_name: 'Multiple Graphs',
          xAxisRange: [minGraph, maxGraph],
          yAxisRange: [minGraphY, maxGraphY],
          graphs: {},
        };
        let xAxisLabel = '';
        let yAxisLabel = '';
        data.forEach((featureGraph, index) => {
          const firstGraph = Object.values(featureGraph.graphs.graphs)[0];
          const { xAxis, yAxis, tableType } = featureGraph;
          const foundName = graphNames.find((name) => name.xAxis === xAxis && name.yAxis === yAxis && name.type === tableType);
          let name: string | number = index;
          if (foundName) {
            name = foundName.name;
          }
          graphRenderData.graphs[name] = firstGraph;
          xAxisLabel = featureGraph.xAxis;
          yAxisLabel = featureGraph.yAxis;
        });
        if (graphContainer.value) {
          const colorMapping = renderVectorFeatureGraph(
            graphRenderData,
            graphContainer.value,
            {
              xAxisIsTime: xAxisLabel === 'unix_time',
              xAxisLabel,
              yAxisLabel,
              colors: graphColorMap.value,
              hideBaseData: hideBaseData.value,
              showTrendline: trendLine.value,
              showConfidenceInterval: confidenceIntervalEnabled.value,
              showMovingAverage: movingAverageEnabled.value,
              useKeyTooltip: true,
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

    onMounted(() => {
      assignGraphColors();
      if (availableVectorGraphs.value.length > 0 && props.defaultGraphs.length > 0) {
        selectedGraphs.value = props.defaultGraphs;
      }
      fetchMapLayerFeatureGraphData();
    });

    watch(() => props.defaultGraphs, (newValue) => {
      if (newValue.length > 0) {
        selectedGraphs.value = newValue;
      }
      fetchMapLayerFeatureGraphData();
    }, { immediate: true });

    // Watch for chart selection change and fetch data automatically

    watch(selectedGraphs, () => {
      fetchMapLayerFeatureGraphData();
    }, { deep: true });

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

    const removeChip = (item: { raw: { name: string } }) => {
      const index = selectedGraphs.value.indexOf(item.raw.name);
      if (index > -1) {
        selectedGraphs.value.splice(index, 1);
      }
      fetchMapLayerFeatureGraphData();
    };

    const closeVectorFeatureGraph = () => {
      MapStore.clearVectorFeatureTableData();
    };

    return {
      selectedGraphs,
      availableVectorGraphs,
      graphColorMap,
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
      removeChip,
      closeVectorFeatureGraph,
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
              v-model="selectedGraphs"
              :items="availableVectorGraphs"
              item-value="name"
              item-title="name"
              label="Select Graphs"
              multiple
              chips
              closable-chips
              clearable
              dense
              outlined
              :menu-props="{ maxHeight: 400 }"
            >
              <template #chip="{ item }">
                <v-chip
                  :style="{ backgroundColor: graphColorMap[item.raw.name], color: 'white' }"
                  size="small"
                  label
                  @click:close="removeChip(item)"
                >
                  {{ item.raw.name }}
                </v-chip>
              </template>
            </v-select>
          </v-col>
          <v-spacer />
          <v-icon
            size="x-large"
            @click="closeVectorFeatureGraph()"
          >
            mdi-close
          </v-icon>
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
