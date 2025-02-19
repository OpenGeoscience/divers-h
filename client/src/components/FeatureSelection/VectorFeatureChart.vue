<script lang="ts">
import {
  PropType, defineComponent, nextTick, ref, watch,
} from 'vue';
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

    // Fetch feature graph data when component is mounted or props change
    const fetchFeatureGraphData = async () => {
      noGraphData.value = false;
      try {
        const data = await UVdatApi.getFeatureGraphData(
          props.graphInfo.type, // Use graphInfo.type (tableType) instead of mapLayerId
          props.vectorFeatureId,
          props.graphInfo.xAxis,
          props.graphInfo.yAxis,
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
            },
          );
        }
      });
    };

    return {
      graphContainer,
      graphDialogContainer,
      graphData,
      dialogVisible,
      openDialog,
      noGraphData,
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
    <v-dialog v-model="dialogVisible" max-width="800px">
      <v-card>
        <v-card-title>
          <v-row>
            <v-spacer />
            <span class="headline">{{ graphInfo.name }}</span>
            <v-spacer />
          </v-row>
        </v-card-title>
        <v-card-text>
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
