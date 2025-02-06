<script lang="ts">
import {
  PropType,
  Ref, defineComponent, nextTick, onMounted, ref, watch,
} from 'vue';
import {
  HistogramData, StringData, renderBarChart, renderPieChart,
} from './chartUtils'; // Import the utility functions and types
import UVdatApi from '../../api/UVDATApi';
import { getStringBBox } from '../../map/mapLayers';
import { CustomChart, HistogramChart, PieChart } from '../../types';

interface NumericalStats {
  mean: number;
  min: number;
  max: number;
  median: number;
  std_dev: number;
}

export default defineComponent({
  props: {

    editMode: {
      type: Boolean,
      default: false,
    },
    mapLayerId: {
      type: Number,
      default: -1,
    },
    chartConfig: {
      type: Object as PropType<CustomChart>,
      required: true,
    },
  },
  emits: ['update'],
  setup(props, { emit }) {
    const chartType = ref<string | null>(null);
    const chartData = ref<HistogramData | StringData[] | null>(null);
    const numericalStats = ref<NumericalStats>({
      mean: 0,
      min: 0,
      max: 0,
      median: 0,
      std_dev: 0,
    });
    const bbox: Ref<string | undefined> = ref(undefined);
    const bins = ref(10);
    const mapLayerId: Ref<number> = ref(props.mapLayerId);
    const propertyKey: Ref<string | null> = ref(null);
    const xAxisLabel = ref('');
    const yAxisLabel = ref('');
    const staticLabels = ref(true);
    const highlightLabels = ref(false);
    const sourceArea: Ref<'global' | 'bbox'> = ref('global');
    const barChartRef = ref<HTMLDivElement | null>(null);
    const pieChartRef = ref<HTMLDivElement | null>(null);

    const fetchData = async () => {
      if (mapLayerId.value === -1 || propertyKey.value === null) {
        return;
      }
      const data = await UVdatApi.getPropertyStatistics(mapLayerId.value, propertyKey.value, bbox.value, bins.value);
      const selectedData = data[propertyKey.value];

      if (selectedData.type === 'number') {
        chartType.value = 'histogram';
        chartData.value = selectedData.histogram;

        numericalStats.value = {
          mean: selectedData.mean,
          min: selectedData.min,
          max: selectedData.max,
          median: selectedData.median,
          std_dev: selectedData.std_dev,
        };

        nextTick(() => renderBarChart(
          {
            chartElement: barChartRef.value,
            chartData: chartData.value as HistogramData,
            xAxisLabel: xAxisLabel.value,
            yAxisLabel: yAxisLabel.value,
          },
        ));
      } else if (selectedData.type === 'string') {
        chartType.value = 'pie';
        chartData.value = selectedData.values;
        nextTick(() => renderPieChart({
          chartElement: pieChartRef.value,
          chartData: chartData.value as StringData[],
          showLabels: staticLabels.value,
          showHoverLabel: highlightLabels.value,
        }));
      }
    };

    const updateData = () => {
      if (props.editMode) {
        emit('update', {
          xAxisLabel: xAxisLabel.value,
          yAxisLabel: yAxisLabel.value,
          bins: bins.value,
          sourceArea: sourceArea.value,
          staticLabels: staticLabels.value,
          highlightLabels: highlightLabels.value,
        });
      }
    };

    const initialize = async () => {
      sourceArea.value = props.chartConfig?.sourceArea || 'global';
      [propertyKey.value] = props.chartConfig.chartData.keys;
      if (props.chartConfig?.chartType === 'histogram') {
        const histogram = props.chartConfig.chartData as HistogramChart;
        xAxisLabel.value = histogram.xAxisLabel || '';
        yAxisLabel.value = histogram.yAxisLabel || '';
        bins.value = histogram.bins !== undefined ? histogram.bins : 10;
      } else if (props.chartConfig?.chartType === 'pie') {
        const pieChart = props.chartConfig.chartData as PieChart;
        staticLabels.value = pieChart.staticLabels;
        highlightLabels.value = pieChart.highlightLabels;
      }
      fetchData();
      updateData();
    };

    watch(() => props.chartConfig.chartData.keys, () => {
      if (props.chartConfig?.chartData.keys.length) {
        [propertyKey.value] = props.chartConfig.chartData.keys;
        bbox.value = undefined;
        fetchData();
      }
    });
    watch(() => props.mapLayerId, () => {
      if (props.mapLayerId) {
        mapLayerId.value = props.mapLayerId;
        bbox.value = undefined;
        fetchData();
      }
    });
    watch(bins, () => {
      fetchData();
      updateData();
    });

    watch([xAxisLabel, yAxisLabel], () => {
      updateData();
      fetchData();
    });
    watch([staticLabels, highlightLabels], () => {
      updateData();
      fetchData();
    });

    onMounted(() => initialize());

    const useGlobal = () => {
      bbox.value = undefined;
      sourceArea.value = 'global';
      fetchData();
      updateData();
    };
    const useBBox = () => {
      bbox.value = getStringBBox();
      sourceArea.value = 'bbox';
      fetchData();
      updateData();
    };
    watch(() => props.chartConfig.enableBbox, () => {
      if (props.editMode && !props.chartConfig.enableBbox) {
        useGlobal();
      }
    });
    return {
      chartType,
      chartData,
      numericalStats,
      barChartRef,
      pieChartRef,
      fetchData,
      useGlobal,
      useBBox,
      bbox,
      sourceArea,
      bins,
      xAxisLabel,
      yAxisLabel,
      staticLabels,
      highlightLabels,
    };
  },
});
</script>
<template>
  <v-row>
    <v-tooltip text="Use Global Values for Calculation" location="top">
      <template #activator="{ props }">
        <v-btn
          v-bind="props"
          icon="mdi-earth"
          variant="plain"
          density="compact"
          :color="sourceArea === 'global' ? 'primary' : 'gray'"
          @click="useGlobal()"
        />
      </template>
    </v-tooltip>
    <v-tooltip text="Use Current Viewport for Calculation" location="top">
      <template #activator="{ props }">
        <v-btn
          v-if="chartConfig.enableBbox"
          v-bind="props"
          icon="mdi-vector-square"
          variant="plain"
          density="compact"
          :color="sourceArea === 'bbox' ? 'primary' : 'gray'"
          @click="useBBox()"
        />
      </template>
    </v-tooltip>
    <v-col v-if="editMode && chartType === 'histogram'">
      <v-slider v-model="bins" label="bins" step="1" :min="10" :max="100" thumb-label="always" />
    </v-col>
  </v-row>
  <!-- Edit Mode Propertes -->
  <v-row v-if="editMode && chartType === 'histogram'">
    <v-text-field v-model="xAxisLabel" label="X-Axis" />
  </v-row>
  <v-row v-if="editMode && chartType === 'histogram'">
    <v-text-field v-model="yAxisLabel" label="Y-Axis" />
  </v-row>
  <v-row v-if="editMode && chartType === 'pie'">
    <v-switch v-model="staticLabels" :color="staticLabels ? 'primary' : ''" label="Show Static Labels" />
  </v-row>
  <v-row v-if="editMode && chartType === 'pie'">
    <v-switch v-model="highlightLabels" :color="highlightLabels ? 'primary' : ''" label="Highlight Labels" />
  </v-row>
  <v-row>
    <!-- Bar Chart -->
    <v-col v-if="chartType === 'histogram'" cols="12">
      <v-card class="mb-4">
        <v-expansion-panels>
          <v-expansion-panel>
            <v-expansion-panel-title>
              <strong>Statistics</strong>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-row dense align="center" justify="center">
                <v-col cols="3">
                  <strong>Mean</strong>
                </v-col>
                <v-col cols="3">
                  <strong>Median</strong>
                </v-col>
                <v-col cols="3">
                  <strong>Min<br>Max</strong>
                </v-col>
                <v-col cols="3">
                  <strong>Std Dev</strong>
                </v-col>
              </v-row>
              <v-row dense>
                <v-col cols="3">
                  <p>{{ numericalStats.mean.toFixed(2) }}</p>
                </v-col>
                <v-col cols="3">
                  <p>{{ numericalStats.median.toFixed(2) }}</p>
                </v-col>
                <v-col cols="3">
                  <p>{{ numericalStats.min.toFixed(2) }}<br>{{ numericalStats.max.toFixed(2) }}</p>
                </v-col>
                <v-col cols="3">
                  <p>{{ numericalStats.std_dev.toFixed(2) }}</p>
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card>
      <div ref="barChartRef" style="width: 100%; height: 400px;" />
    </v-col>

    <!-- Pie Chart -->
    <v-col v-if="chartType === 'pie'" cols="12">
      <div ref="pieChartRef" style="width: 100%; height: 400px;" />
    </v-col>
  </v-row>
</template>
  <style scoped>
  .bar {
    fill: steelblue;
  }
  </style>
