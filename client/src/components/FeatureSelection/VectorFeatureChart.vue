<script lang="ts">
import {
  PropType, computed, defineComponent, nextTick, ref, watch,
} from 'vue';
import { throttle } from 'lodash';
import UVdatApi from '../../api/UVDATApi';
import { FeatureGraphData, VectorFeatureTableGraph } from '../../types';
import { renderVectorFeatureGraph } from './vectorFeatureGraphUtils';

export default defineComponent({
  name: 'FeatureGraph',
  props: {
    graphInfo: {
      type: Object as PropType<VectorFeatureTableGraph>,
      required: true,
    },
    vectorFeatureId: {
      type: Number as PropType<number>,
      required: true,
    },
    mapLayerId: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const graphContainer = ref<SVGSVGElement | null>(null);
    const graphDialogContainer = ref<SVGSVGElement | null>(null);
    const graphData = ref<FeatureGraphData | null>(null);
    const dialogVisible = ref(false);
    const noGraphData = ref(false);
    const hideBaseData = ref(false);
    const trendLine = ref(false);
    const confidenceIntervalEnabled = ref(false);
    const confidenceLevel = ref(95);
    const movingAverageEnabled = ref(false);
    const movingAverageValue = ref(12);

    const maxMovingAverage = computed(() => {
      if (graphData.value) {
        const keys = Object.keys(graphData.value?.graphs || []);
        if (keys.length === 1 && graphData.value?.graphs) {
          const dataLength = graphData.value.graphs[parseInt(keys[0], 10)].data.length;
          return Math.floor(dataLength / 4);
        }
      }
      return 50;
    });
    // Fetch feature graph data when component is mounted or props change
    const fetchFeatureGraphData = async () => {
      noGraphData.value = false;
      try {
        const display: ('data' | 'trendLine' | 'confidenceInterval' | 'movingAverage')[] = ['data', 'trendLine'];
        if (confidenceIntervalEnabled.value) {
          display.push('confidenceInterval');
        }
        if (movingAverageEnabled.value) {
          display.push('movingAverage');
        }
        const data = await UVdatApi.getFeatureGraphData(
          props.graphInfo.type, // Use graphInfo.type (tableType) instead of mapLayerId
          props.vectorFeatureId,
          props.graphInfo.xAxis,
          props.graphInfo.yAxis,
          display,
          confidenceLevel.value,
          false,
          movingAverageValue.value,

        );
        if (data.graphs && Object.keys(data.graphs).length === 0) {
          noGraphData.value = true;
          return;
        }
        graphData.value = data;
        if (graphContainer.value) {
          nextTick(() => {
            if (graphContainer.value) {
              renderVectorFeatureGraph(
                data,
                graphContainer.value,
                {
                  specificGraphKey: props.vectorFeatureId,
                  xAxisIsTime: props.graphInfo.xAxis === 'unix_time',
                  xAxisVerticalLabels: true,
                },
              );
            }
          });
        }
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('Error fetching feature graph data:', error);
      }
    };

    // Watch for prop changes and refetch data
    watch(
      () => [props.graphInfo, props.vectorFeatureId],
      () => fetchFeatureGraphData(),
    );
    watch(graphContainer, () => {
      fetchFeatureGraphData();
    });

    // Open the dialog to display a larger graph
    const openDialog = () => {
      dialogVisible.value = true;
      nextTick(() => {
        if (graphData.value && graphDialogContainer.value) {
          renderVectorFeatureGraph(
            graphData.value,
            graphDialogContainer.value,
            {
              specificGraphKey: props.vectorFeatureId,
              xAxisIsTime: props.graphInfo.xAxis === 'unix_time',
              showXYValuesOnHover: true,
              xAxisLabel: props.graphInfo.xAxisLabel,
              yAxisLabel: props.graphInfo.yAxisLabel,
              hideBaseData: hideBaseData.value,
              showTrendline: trendLine.value,
              showConfidenceInterval: confidenceIntervalEnabled.value,
            },
          );
        }
      });
    };

    const updateDialogGraph = async () => {
      await fetchFeatureGraphData();
      if (graphData.value && graphDialogContainer.value && dialogVisible.value) {
        renderVectorFeatureGraph(
          graphData.value,
          graphDialogContainer.value,
          {
            specificGraphKey: props.vectorFeatureId,
            xAxisIsTime: props.graphInfo.xAxis === 'unix_time',
            showXYValuesOnHover: true,
            xAxisLabel: props.graphInfo.xAxisLabel,
            yAxisLabel: props.graphInfo.yAxisLabel,
            hideBaseData: hideBaseData.value,
            showTrendline: trendLine.value,
            showConfidenceInterval: confidenceIntervalEnabled.value,
            showMovingAverage: movingAverageEnabled.value,
          },
        );
      }
    };

    const throttledUpateDialogGraph = throttle(updateDialogGraph, 500);
    watch([
      hideBaseData,
      trendLine,
      confidenceIntervalEnabled,
      confidenceLevel,
      movingAverageEnabled,
      movingAverageValue,
    ], throttledUpateDialogGraph);

    return {
      graphContainer,
      graphDialogContainer,
      graphData,
      dialogVisible,
      openDialog,
      noGraphData,
      hideBaseData,
      trendLine,
      confidenceIntervalEnabled,
      confidenceLevel,
      movingAverageEnabled,
      movingAverageValue,
      maxMovingAverage,
    };
  },
});
</script>

<template>
  <div>
    <div v-if="noGraphData">
      <v-alert type="warning">
        No Data to Graph
      </v-alert>
    </div>
    <div v-if="graphData">
      <v-btn color="primary" size="x-small" @click="openDialog">
        View Larger Graph
      </v-btn>
    </div>
    <svg ref="graphContainer" width="100%" :height="graphData ? 400 : 0" class="selectedFeatureSVG" />
    <v-dialog v-model="dialogVisible" max-width="1200px">
      <v-card>
        <v-card-title>
          <v-row dense>
            <v-spacer />
            <span class="headline">{{ graphInfo.name }}</span>
            <v-spacer />
          </v-row>
        </v-card-title>
        <v-card-text>
          <v-row>
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
          <svg ref="graphDialogContainer" width="100%" height="400" />
        </v-card-text>
        <v-card-actions>
          <v-btn @click="dialogVisible = false">
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
  .selectedFeatureSVG {
    max-width: 250px;
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
