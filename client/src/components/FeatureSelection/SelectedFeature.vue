<script lang="ts">
import {
  PropType, Ref, computed, defineComponent, onMounted, ref,
} from 'vue';
import MapStore from '../../MapStore';
import { ClickedProps, FeatureChartWithData } from '../../types';
import { colorGenerator } from '../../map/mapColors';
import RenderFeatureChart from './RenderFeatureChart.vue';

export default defineComponent({
  components: {
    RenderFeatureChart,
  },
  props: {
    data: {
      type: Object as PropType<ClickedProps>,
      required: true,
    },
  },
  setup(props) {
    const deselectFeature = () => {
      MapStore.removeSelectedFeature(props.data.id as number);
    };
    const defaultProps = ref(props.data.properties);
    const displayFeatureId = ref(true);
    const customData: Ref<{ view: boolean; edit: boolean; add: boolean; delete: boolean; } | false> = ref(false);
    const featureCharts: Ref<FeatureChartWithData[]> = ref([]);
    const mapLayerId = ref(props.data.layerId);
    const featureId = ref(props.data.id as number);
    const enabledChartPanels: Ref<number[]> = ref([]);
    const processLayerProps = () => {
      const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.data.layerId);
      if (found?.default_style.properties) {
        const { availableProperties } = found.default_style.properties;
        if (found?.default_style?.properties?.selectionDisplay) {
          // Process and only display available props;
          displayFeatureId.value = found.default_style.properties.displayFeatureId !== false;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const sampleProps: Record<string, any> = {};
          Object.keys(props.data.properties).forEach((key) => {
            if (availableProperties && availableProperties[key] && availableProperties[key].display) {
              sampleProps[availableProperties[key].displayName] = props.data.properties[key];
            }
          });
          defaultProps.value = sampleProps;
        } else {
          defaultProps.value = props.data.properties;
        }
        if (found?.default_style.selectedFeatureCharts?.length && availableProperties) {
          found?.default_style.selectedFeatureCharts.forEach((featureChart, index) => {
            const data: ({ key: string, value: number, color: string })[] = [];
            featureChart.keys.forEach((keyObj) => {
              if (props.data.properties[keyObj.key] !== undefined) {
                data.push({
                  key: availableProperties[keyObj.key].displayName,
                  value: props.data.properties[keyObj.key],
                  color: keyObj.color || colorGenerator(keyObj.key),
                });
              }
            });
            featureCharts.value.push({ ...featureChart, data });
            if (featureChart.display.expanded) {
              enabledChartPanels.value.push(index);
            }
          });
        }
      }
    };
    onMounted(() => processLayerProps());

    const selectedFeatureExpanded = computed(() => (MapStore.selectedFeatureExpanded.value ? 'expanded' : null));
    const toggleFeatureExpaned = () => {
      MapStore.selectedFeatureExpanded.value = !MapStore.selectedFeatureExpanded.value;
    };
    return {
      deselectFeature,
      defaultProps,
      displayFeatureId,
      customData,
      mapLayerId,
      featureId,
      featureCharts,
      enabledChartPanels,
      selectedFeatureExpanded,
      toggleFeatureExpaned,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      <v-row>
        <span v-if="displayFeatureId">Feature Id: {{ data.id }}</span>
        <v-spacer />
        <v-icon
          size="x-small"
          @click="deselectFeature()"
        >
          mdi-close
        </v-icon>
      </v-row>
    </v-card-title>
    <v-card-text>
      <v-expansion-panels :model-value="selectedFeatureExpanded" @click="toggleFeatureExpaned()">
        <v-expansion-panel value="expanded">
          <v-expansion-panel-title>
            <v-icon class="pr-2">
              mdi-list-box-outline
            </v-icon> Data
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-row
              v-for="(item, key) in defaultProps"
              :key="`${data.id}_${key}`"
            >
              <v-col>
                {{ key }}
              </v-col>
              <v-col>
                {{ item }}
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
      <v-expansion-panels v-if="featureCharts.length" v-model="enabledChartPanels" multiple>
        <v-expansion-panel
          v-for="featureChart, index in featureCharts"
          :key="`${featureChart.name}_${index}`"
          :value="index"
        >
          <v-expansion-panel-title>
            <v-icon class="pr-2">
              mdi-chart-bar
            </v-icon> {{ featureChart.name }}
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <render-feature-chart :feature-chart="featureChart" />
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
  </v-card>
</template>

<style scoped>
</style>
