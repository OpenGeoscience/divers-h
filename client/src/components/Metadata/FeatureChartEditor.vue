<script lang="ts">
import {
  computed, defineComponent, onMounted, ref, watch,
} from 'vue';
import draggable from 'vuedraggable'; // Import vuedraggable
import { FeatureChart } from '../../types';
import MapStore from '../../MapStore';
import { drawBarChart } from './drawChart'; // Separate drawChart function
import { colorGenerator } from '../../map/mapColors';
import RenderFeatureChart from '../FeatureSelection/RenderFeatureChart.vue';

export default defineComponent({
  name: 'FeatureChartEditor',
  components: {
    draggable,
    RenderFeatureChart,
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
    editFeatureChart: {
      type: Object as () => FeatureChart | null,
      default: null,
    },
  },
  emits: ['save', 'cancel'],
  setup(props, { emit }) {
    const chart = ref<FeatureChart>({
      name: 'New Feature Chart',
      type: 'bar',
      sort: 'static',
      keys: [],
      display: {
        expanded: false,
        keyStaticLabels: true,
        keyHighlightLabels: false,
      },
    });

    const selectedKey = ref(''); // Track selected key from dropdown

    const availableProperties = computed(() => {
      const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.layerId);
      if (found && found.default_style.properties?.availableProperties) {
        // Filter properties to only allow those that are numerical
        const properties = Object.values(found.default_style.properties.availableProperties).filter(
          (item) => !item.searchable && !item.static && item.type === 'number',
        );
        // Exclude already selected keys
        return properties.filter((property) => !chart.value.keys.map((k) => k.key).includes(property.key));
      }
      return [];
    });

    // eslint-disable-next-line vue/max-len
    const propertyMap = computed(() => MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.layerId)?.default_style.properties?.availableProperties || {});

    const addSelectedKey = () => {
      if (selectedKey.value && !chart.value.keys.some((k) => k.key === selectedKey.value)) {
        chart.value.keys.push({ key: selectedKey.value, color: colorGenerator(selectedKey.value) });
        selectedKey.value = ''; // Reset after adding
      }
    };

    const removeKey = (key: string) => {
      chart.value.keys = chart.value.keys.filter((item) => item.key !== key);
    };

    // Computed property to generate the data with random values between 0 and 100
    const generatedData = computed(() => chart.value.keys.map((item) => ({
      key: propertyMap.value[item.key]?.displayName || item.key,
      value: Math.floor(Math.random() * 101), // Random value between 0-100
      color: item.color || 'steelblue',
    })));

    const save = () => {
      emit('save', chart.value);
    };

    const cancel = () => {
      emit('cancel');
    };

    // Watch for chart changes to re-render the D3 chart, but only if there are keys
    watch([generatedData, () => chart.value.sort, () => chart.value.display], () => {
      if (chart.value.keys.length > 0) {
        drawBarChart(
          'featureBarChart',
          generatedData.value,
          chart.value.sort,
          chart.value.display.keyStaticLabels,
          chart.value.display.keyHighlightLabels,
          500,
        );
      }
    }, { deep: true });

    watch(() => props.editFeatureChart, (newVal) => {
      if (newVal) {
        chart.value = { ...newVal };
      } else {
        chart.value = {
          name: '',
          type: 'bar',
          sort: 'static',
          keys: [],
          display: {
            expanded: true,
            keyStaticLabels: true,
            keyHighlightLabels: false,
          },
        };
      }
    }, { immediate: true });

    onMounted(() => {
      if (chart.value.keys.length > 0) {
        drawBarChart(
          'featureBarChart',
          generatedData.value,
          chart.value.sort,
          chart.value.display.keyStaticLabels,
          chart.value.display.keyHighlightLabels,
          500,
        );
      }
    });

    return {
      chart,
      availableProperties,
      generatedData,
      selectedKey,
      addSelectedKey,
      removeKey,
      propertyMap,
      save,
      cancel,
    };
  },
});
</script>

<template>
  <v-text-field
    v-model="chart.name"
    label="Name"
    required
  />
  <v-text-field
    v-model="chart.description"
    label="Description"
  />
  <v-row dense>
    <v-select
      v-model="selectedKey"
      :items="availableProperties"
      item-title="displayName"
      item-value="key"
      label="Select Property"
    >
      <template #item="{ props, item }">
        <v-list-item v-bind="props">
          <v-list-item-subtitle>
            {{ item.raw.description }}
          </v-list-item-subtitle>
        </v-list-item>
      </template>
    </v-select>

    <v-btn size="small" :disabled="!selectedKey" class="mx-2" @click="addSelectedKey">
      Add <v-icon class="ml-1">
        mdi-plus-thick
      </v-icon>
    </v-btn>
  </v-row>

  <!-- Draggable keys with colors -->
  <draggable
    :list="chart.keys"
    item-key="key"
    handle=".handle"
    class="list-group"
    ghost-class="ghost"
  >
    <template #item="{ element }">
      <v-list-item>
        <v-list-item-title>
          <v-row dense align="center" justify="center">
            <v-col
              title="Drag"
              cols="1"
              class="handle"
            >
              <v-icon
                size="large"
              >
                mdi-format-align-justify
              </v-icon>
            </v-col>
            <v-col>
              {{ propertyMap[element.key] && propertyMap[element.key].displayName }}
            </v-col>
            <v-spacer />
            <v-col cols="1">
              <v-menu
                :close-on-content-click="false"
                offset-y
              >
                <template #activator="{ props }">
                  <div
                    class="color-square"
                    :style="{ backgroundColor: element.color }"
                    v-bind="props"
                  />
                </template>
                <v-color-picker
                  v-model="element.color"
                  mode="hex"
                />
              </v-menu>
            </v-col>
            <v-col cols="1">
              <v-btn icon="mdi-delete" variant="plain" color="error" @click="removeKey(element.key)" />
            </v-col>
          </v-row>
        </v-list-item-title>
      </v-list-item>
    </template>
  </draggable>

  <v-select
    v-model="chart.sort"
    label="Sort By"
    :items="['static', 'value', 'name']"
  />

  <v-row>
    <v-col>
      <v-switch
        v-model="chart.display.expanded"
        :color="chart.display.expanded ? 'primary' : ''"
        label="Expanded"
      />
    </v-col>
    <v-col>
      <v-switch
        v-model="chart.display.keyStaticLabels"
        :color="chart.display.keyStaticLabels ? 'primary' : ''"
        label="Static Labels"
      />
    </v-col>
    <v-col>
      <v-switch
        v-model="chart.display.keyHighlightLabels"
        :color="chart.display.keyHighlightLabels ? 'primary' : ''"
        label="Highlight Labels"
      />
    </v-col>
  </v-row>

  <!-- Display the D3 chart -->
  <v-row>
    <p v-if="chart.keys.length">
      This is randomly generated sample data to visualize the chart
    </p>
  </v-row>
  <v-row>
    <v-expansion-panels :model-value="chart.display.expanded ? 'expanded' : null">
      <v-expansion-panel
        value="expanded"
      >
        <v-expansion-panel-title>
          <v-icon class="pr-2">
            mdi-chart-bar
          </v-icon> {{ chart.name }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <render-feature-chart :feature-chart="{ ...chart, data: generatedData }" :max-width="500" />
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-row>
  <v-row class="pt-4">
    <v-spacer />
    <v-btn color="error" class="mx-2" @click="cancel()">
      Cancel
    </v-btn>
    <v-btn
      :disabled="!chart.name || !chart.keys.length"
      type="submit"
      color="success"
      class="mx-2"
      @click="save()"
    >
      Save
    </v-btn>
  </v-row>
</template>

<style scoped>
#chart {
  margin-top: 20px;
}
.color-square {
  width: 25px;
  height: 25px;
  border: 1px solid #000;
  cursor: pointer;
}
</style>
