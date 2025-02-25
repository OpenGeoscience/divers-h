<script lang="ts">
import { computed, defineComponent } from 'vue';
import MapStore from '../../MapStore';
import { updateLayerFilter } from '../../map/mapVectorLayers';
import {
  AvailablePropertyDisplay,
  Filter,
  VectorMapLayer,
} from '../../types'; // Import your defined types
import { getLayerAvailableProperties } from '../../utils';
import FilteringInteraction from '../Filtering/FilteringInteraction.vue';

export default defineComponent({
  name: 'FilterKey',
  components: {
    FilteringInteraction,
  },
  props: {
    layers: {
      type: Array as () => VectorMapLayer[],
      required: true,
    },
  },
  setup(props) {
    // Process the layers and colors
    const attributeValues = computed(() => {
      const attributeMapping: Record<number, Record<string, AvailablePropertyDisplay>> = {};
      props.layers.forEach((layer) => {
        attributeMapping[layer.id] = getLayerAvailableProperties(layer.id);
      });
      return attributeMapping;
    });

    const filterList = computed(() => {
      const localFilterList: { name: string, id: number, filters: { index: number, value: Filter }[] }[] = [];
      props.layers.forEach((layer) => {
        if (layer.default_style?.filters) {
          const { filters } = layer.default_style;
          localFilterList.push({ name: layer.name, id: layer.id, filters: [] });
          filters.forEach((filter, index) => {
            if (filter.userEnabled) {
              localFilterList[localFilterList.length - 1].filters.push({ value: filter, index });
            }
          });
        }
      });
      return localFilterList;
    });
    const updateEnabled = (filter: Filter, layerId: number) => {
      // eslint-disable-next-line no-param-reassign
      filter.enabled = !filter.enabled;
      const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === layerId);
      if (found) {
        updateLayerFilter(found);
      }
    };

    return {
      filterList,
      attributeValues,
      updateEnabled,
    };
  },
});
</script>

<template>
  <v-expansion-panels
    :model-value="[0]"
    multiple
  >
    <v-expansion-panel
      v-for="filterLayer in filterList"
      :key="filterLayer.name"
    >
      <v-expansion-panel-title>
        {{ filterLayer.name }}
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <div
          v-for="(filter) in filterLayer.filters"
          :key="`${filterLayer.name}_${filter.value.index}`"
        >
          <v-row dense>
            <v-col>
              <v-icon
                size="small"
                @click="updateEnabled(filter.value, filterLayer.id)"
              >
                {{
                  filter.value.enabled ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline' }}
              </v-icon>
            </v-col>
            <v-col>{{ filter.value.name }}:</v-col>
            <v-col>{{ attributeValues[filterLayer.id][filter.value.key].displayName }}</v-col>
            <v-col>{{ filter.value.operator }}</v-col>
            <v-col>{{ filter.value.value }}</v-col>
          </v-row>

          <v-row dense>
            <filtering-interaction
              :layer-id="filterLayer.id"
              :filter="filter.value"
              :filter-index="filter.index"
            />
          </v-row>
        </div>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>
