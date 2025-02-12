<script lang="ts">
import {
  PropType, computed, defineComponent, nextTick, onMounted, watch,
} from 'vue';
import { FeatureChartWithData } from '../../types';
import { drawBarChart } from '../Metadata/drawChart';

// FeatureChart TypeScript interface (as provided)
export default defineComponent({
  name: 'PropertyFeatureChart',
  props: {
    featureChart: {
      type: Object as PropType<FeatureChartWithData>,
      required: true,
    },
    maxWidth: {
      type: Number,
      default: 250,
    },
  },
  setup(props) {
    // Computed property to generate a unique ID based on the chart title
    const chartId = computed(() => `feature-bar-chart-${props.featureChart.name.replace(/\s+/g, '-').toLowerCase()}`);

    // Function to render the chart
    const renderChart = () => {
      const { sort, display, data } = props.featureChart;
      nextTick(() => {
        drawBarChart(
          chartId.value,
          data,
          sort, // Use the sort option from featureChart
          display.keyStaticLabels,
          display.keyHighlightLabels,
          props.maxWidth,
        );
      });
    };

    // Watch for changes and re-render the chart
    watch(
      () => [props.featureChart],
      renderChart,
      { deep: true },
    );

    onMounted(() => {
      renderChart(); // Initial render
    });

    return { chartId };
  },
});
</script>

<template>
  <div class="feature-chart-container">
    <p v-if="featureChart.description">
      {{ featureChart.description }}
    </p>

    <!-- Bar chart container -->
    <div :id="chartId" />
  </div>
</template>

<style scoped>
.feature-chart-container {
  margin-bottom: 2rem;
}

h2 {
  margin-top: 0;
}

p {
  margin-bottom: 1rem;
}
</style>
