<script lang="ts">
import {
  PropType,
  Ref, computed,
  defineComponent,
  nextTick,
  onMounted,
  ref,
  watch,
} from 'vue';
import MapStore from '../../MapStore';
import ChartRenderer from './ChartRenderer.vue';
import { CustomChart, HistogramChart, PieChart } from '../../types';

export default defineComponent({
  name: 'AddEditChart',
  components: {
    ChartRenderer,
  },
  props: {
    editChart: {
      type: Object as PropType<CustomChart | null>,
      default: () => null,
    },
  },
  emits: ['cancel', 'save'],
  setup(props, { emit }) {
    const mapLayers = computed(() => {
      const visible = MapStore.selectedVectorMapLayers.value.filter(
        (item) => MapStore.visibleMapLayers.value.has(`${item.type}_${item.id}`),
      );
      return visible.map((item) => ({ id: item.id, name: item.name }));
    });
    const chartTitle = ref(props.editChart?.title || 'Custom Chart Title');
    const chartDescription = ref(props.editChart?.description || '');
    const chartType: Ref<CustomChart['chartType'] | null> = ref(null);
    const chartSources = ref([
      {
        title: 'Pie Chart', value: 'pie', subtitle: 'Pie Chart of Count of a single Categorical String property', type: 'string',
      },
      {
        title: 'Histogram', value: 'histogram', subtitle: 'Histogram of of a single numerical property', type: 'number',
      },
    ]);

    const sourceArea: Ref<'global' | 'bbox'> = ref('global');
    const enableBbox = ref(props.editChart?.enableBbox !== undefined ? props.editChart.enableBbox : true);
    const expanded = ref(props.editChart?.expanded !== undefined ? props.editChart.expanded : false);
    const selectedMapLayer: Ref<number | null > = ref(null);
    const selectedPropertyKey: Ref<string | null> = ref(null);
    const chartData: Ref<null | CustomChart['chartData']> = ref(null);
    const availableProperties = computed(() => {
      if (selectedMapLayer.value) {
        const found = MapStore.selectedVectorMapLayers.value.find((item) => (item.id === selectedMapLayer.value));
        if (found && found.default_style.properties?.availableProperties) {
          // We only return properties that are categorical or numerical;
          const results = Object.values(
            found.default_style.properties.availableProperties,
          ).filter((item) => (!item.searchable && !item.static));
          return results;
        }
      }
      return [];
    });
    const chartTypeProps = computed(() => {
      const chartProp = chartSources.value.find((item) => item.value === chartType.value);
      if (chartType.value !== null && chartProp) {
        const chartPropType = chartProp.type;
        return availableProperties.value.filter((item) => item.type === chartPropType);
      }
      return [];
    });
    const filteredChartSources = computed(() => {
      if (availableProperties.value.length) {
        const typeSet = new Set();
        availableProperties.value.forEach((item) => typeSet.add(item.type));
        const sources = chartSources.value.filter((item) => typeSet.has(item.type));
        return sources;
      }
      return [];
    });

    const initialize = () => {
      if (props.editChart !== null) {
        selectedMapLayer.value = props.editChart.mapLayer;
        chartType.value = props.editChart.chartType;
        chartTitle.value = props.editChart.title;
        // waits a tick to calculate available properties
        nextTick(() => {
          if (props.editChart !== null) {
            selectedPropertyKey.value = props.editChart.chartData.keys ? props.editChart.chartData.keys[0] : null;
          }
        });
        chartDescription.value = props.editChart.description;
        sourceArea.value = props.editChart.sourceArea;
        chartData.value = props.editChart.chartData;
        enableBbox.value = props.editChart?.enableBbox !== undefined ? props.editChart.enableBbox : true;
        expanded.value = props.editChart?.expanded !== undefined ? props.editChart.expanded : false;
      }
    };
    watch([mapLayers, availableProperties], () => {
      const foundMapLayer = mapLayers.value.find((item) => item.id === selectedMapLayer.value);
      const foundProperty = availableProperties.value.find((item) => item.key === selectedPropertyKey.value);
      if (!foundMapLayer) {
        selectedMapLayer.value = null;
        selectedPropertyKey.value = null;
      } else if (!foundProperty) {
        selectedPropertyKey.value = null;
      }
    });
    onMounted(() => initialize());
    const editData: Ref<CustomChart | null> = computed(() => {
      if (props.editChart) {
        const val: CustomChart = {
          ...props.editChart,
        };
        if (chartType.value) {
          val.chartType = chartType.value;
        }
        if (selectedPropertyKey.value?.length) {
          val.chartData.keys = [selectedPropertyKey.value];
        }
        val.enableBbox = enableBbox.value;
        val.expanded = expanded.value;
        return val;
      }
      if (selectedMapLayer.value !== null && selectedPropertyKey.value !== null) {
        const calcChartData = {
          keys: [selectedPropertyKey.value],
          mapLayer: selectedMapLayer.value,
          type: chartType.value,
          staticLabels: chartType.value === 'pie' ? true : undefined,
          highlightLabels: chartType.value === 'pie' ? false : undefined,
          bins: chartType.value === 'histogram' ? 10 : undefined,
          xAxisLabel: chartType.value === 'histogram' ? '' : undefined,
          yAxisLabel: chartType.value === 'histogram' ? '' : undefined,
        };
        return {
          title: 'static', // static for purposes of editData for Renderer
          description: 'static', // static for purposes of editData for Renderer
          chartType: chartType.value,
          mapLayer: selectedMapLayer.value,
          sourceArea: 'global',
          enableBbox: enableBbox.value,
          expanded: expanded.value,
          chartData: calcChartData as HistogramChart | PieChart,
        } as CustomChart;
      }
      return null;
    });
    watch(chartType, () => {
      selectedPropertyKey.value = null;
    });
    const updateChartData = (data: { xAxisLabel: string,
      yAxisLabel: string,
      bins: number,
      sourceArea: 'global' | 'bbox',
      staticLabels: boolean,
      highlightLabels: boolean,
    }) => {
      if (selectedMapLayer.value && selectedPropertyKey.value) {
        sourceArea.value = data.sourceArea;
        if (chartType.value === 'pie') {
          chartData.value = {
            keys: [selectedPropertyKey.value],
            type: chartType.value,
            staticLabels: data.staticLabels,
            highlightLabels: data.highlightLabels,
          } as PieChart;
        } else if (chartType.value === 'histogram') {
          chartData.value = {
            keys: [selectedPropertyKey.value],
            type: chartType.value,
            xAxisLabel: data.xAxisLabel,
            yAxisLabel: data.yAxisLabel,
            bins: data.bins,
          } as HistogramChart;
        }
      }
    };
    const saveChart = () => {
      // Now we save the chart to the map layer
      if (selectedMapLayer.value && selectedPropertyKey.value && chartData.value && chartType.value) {
        const baseChart: CustomChart = {
          title: chartTitle.value,
          description: chartDescription.value,
          chartType: chartType.value,
          mapLayer: selectedMapLayer.value,
          sourceArea: sourceArea.value,
          enableBbox: enableBbox.value,
          expanded: expanded.value,
          chartData: chartData.value,
        };
        emit('save', baseChart);
      }
    };
    return {
      availableProperties,
      chartTypeProps,
      selectedMapLayer,
      mapLayers,
      selectedPropertyKey,
      chartTitle,
      chartDescription,
      enableBbox,
      expanded,
      editData,
      updateChartData,
      saveChart,
      filteredChartSources,
      chartType,
    };
  },
});
</script>

<template>
  <v-row dense>
    <v-select
      v-model="selectedMapLayer"
      :items="mapLayers"
      item-value="id"
      item-title="name"
      label="Map Layer"
    />
  </v-row>
  <v-row v-if="selectedMapLayer !== null && filteredChartSources.length" dense>
    <v-select
      v-model="chartType"
      :items="filteredChartSources"
      item-value="value"
      item-title="title"
      label="Chart Type"
    >
      <template #item="{ props, item }">
        <v-list-item v-bind="props" :subtitle="item.raw.subtitle" />
      </template>
    </v-select>
  </v-row>
  <v-row v-else-if="selectedMapLayer !== null && filteredChartSources.length === 0" dense>
    <v-alert type="warning">
      Requires available properties of type number or string/categorical to create charts
    </v-alert>
  </v-row>

  <v-row v-if="selectedMapLayer !== null && chartType !== null" dense>
    <v-select
      v-model="selectedPropertyKey"
      :items="chartTypeProps"
      item-value="key"
      item-title="displayName"
      label="Property"
    />
  </v-row>
  <v-row dense>
    <v-text-field v-model="chartTitle" label="Title" />
  </v-row>
  <v-row dense>
    <v-text-field v-model="chartDescription" label="description" />
  </v-row>
  <v-row>
    <v-col>
      <v-switch v-model="enableBbox" :color="enableBbox ? 'primary' : ''" label="Enable BBox" />
    </v-col>
    <v-col>
      <v-switch v-model="expanded" :color="expanded ? 'primary' : ''" label="Expanded" />
    </v-col>
  </v-row>
  <chart-renderer
    v-if="selectedPropertyKey !== null && selectedMapLayer !== null && editData"
    edit-mode
    :chart-config="editData"
    :map-layer-id="selectedMapLayer"
    @update="updateChartData($event)"
  />
  <v-row dense>
    <v-spacer />
    <v-btn color="error" class="mx-2" @click="$emit('cancel')">
      Cancel
    </v-btn>
    <v-btn
      color="success"
      :disabled="
        chartTitle && selectedPropertyKey === null || selectedMapLayer === null || !editData"
      class="mx-2"
      @click="saveChart()"
    >
      Save
    </v-btn>
  </v-row>
</template>

<style scoped>

</style>
