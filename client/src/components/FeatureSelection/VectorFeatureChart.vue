<script lang="ts">
import {
  PropType, defineComponent, nextTick, ref, watch,
} from 'vue';
import * as d3 from 'd3';
import UVdatApi from '../../api/UVDATApi';
import { FeatureGraphData, VectorFeatureTableGraph } from '../../types';

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
  },
  setup(props) {
    const graphContainer = ref<SVGSVGElement | null>(null);
    const graphDialogContainer = ref<SVGSVGElement | null>(null);
    const graphData = ref<FeatureGraphData | null>(null);
    const dialogVisible = ref(false);

    // Render graph using D3
    const renderGraph = (data: FeatureGraphData, container = 'graphContainer') => {
      const localContainer = container === 'graphContainer' ? graphContainer : graphDialogContainer;
      if (!localContainer.value || !data) return;

      const svg = d3.select(localContainer.value);
      svg.selectAll('*').remove(); // Clear any existing content in the SVG

      const margin = {
        top: 20, right: container === 'graphContainer' ? 0 : 20, bottom: 40, left: 40,
      };

      // Set the maximum width to 250px
      const width = localContainer.value?.clientWidth || 250 - margin.left - margin.right;
      const height = 400 - margin.top - margin.bottom;

      const x = d3.scaleLinear().range([0, width]);
      const y = d3.scaleLinear().range([height, 0]);

      const line = d3.line()
        .x((d: [number, number]) => x(d[0]))
        .y((d: [number, number]) => y(d[1]));

      let dataForGraph: { data: [number, number][], filterVal?: string } | undefined;

      // Check for default data or apply filter if necessary
      if (data.graphs[props.vectorFeatureId]) {
        dataForGraph = data.graphs[props.vectorFeatureId];
      }

      if (!dataForGraph) {
        return; // Return if no data is available
      }

      // Set the domain for the axes, ensuring we handle empty arrays correctly
      const xExtent = d3.extent(dataForGraph.data.map((item) => item[0]));
      const yExtent = d3.extent(dataForGraph.data.map((item) => item[1]));

      // Fallback to zero if data is empty
      x.domain(xExtent[0] !== undefined ? xExtent : [0, 1]);
      y.domain(yExtent[0] !== undefined ? yExtent : [0, 1]);

      // Create the graph container
      const g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

      // Add the line path to the graph
      svg.append('path')
        .attr('fill', 'none')
        .attr('stroke', 'steelblue')
        .attr('stroke-width', 1.5)
        .attr('d', line(dataForGraph.data.sort((a, b) => a[0] - b[0])))
        .attr('transform', `translate(${margin.left},${margin.top})`);

      // Add the X-axis
      g.append('g')
        .attr('class', 'x axis')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x).ticks(5));

      // Add the Y-axis
      g.append('g')
        .attr('class', 'y axis')
        .call(d3.axisLeft(y));
    };

    // Fetch feature graph data when component is mounted or props change
    const fetchFeatureGraphData = async () => {
      try {
        const data = await UVdatApi.getFeatureGraphData(
          props.graphInfo.type, // Use graphInfo.type (tableType) instead of mapLayerId
          props.vectorFeatureId,
          props.graphInfo.xAxis,
          props.graphInfo.yAxis,
          props.graphInfo.indexer,
        );
        graphData.value = data;
        renderGraph(data);
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('Error fetching feature graph data:', error);
      }
    };

    // Watch for prop changes and refetch data
    watch(
      () => [props.graphInfo, props.vectorFeatureId],
      () => fetchFeatureGraphData(),
      { immediate: true },
    );

    // Open the dialog to display a larger graph
    const openDialog = () => {
      dialogVisible.value = true;
      nextTick(() => {
        if (graphData.value) {
          renderGraph(graphData.value, 'graphDialogContainer');
        }
      });
    };

    return {
      graphContainer,
      graphDialogContainer,
      graphData,
      dialogVisible,
      openDialog,
    };
  },
});
</script>

<template>
  <div>
    <!-- Button to open dialog -->
    <v-btn color="primary" @click="openDialog">
      View Larger Graph
    </v-btn>

    <!-- Graph container -->
    <svg ref="graphContainer" width="100%" height="400" class="selectedFeatureSVG" />

    <!-- Dialog for larger chart -->
    <v-dialog v-model="dialogVisible" max-width="800px">
      <v-card>
        <v-card-title>
          <span class="headline">Feature Graph</span>
        </v-card-title>
        <v-card-text>
          <svg ref="graphDialogContainer" width="100%" height="500" />
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
