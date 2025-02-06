<script lang="ts">
import { PropType, computed, defineComponent } from 'vue';
import { throttle } from 'lodash';
import {
  Filter, NumberBetweenFilter, NumberComparisonFilter, StringFilters, StringInArrayFilter,
} from '../../types';
import { getLayerAvailableProperties, getLayerFilters, getVectorLayerDisplayConfig } from '../../utils';
import { updateLayerFilter } from '../../map/mapVectorLayers';

export default defineComponent({
  components: {
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
    filter: {
      type: Object as PropType<Filter>,
      required: true,
    },
    filterIndex: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const attribute = computed(() => {
      const availabeAttributes = getLayerAvailableProperties(props.layerId);
      return availabeAttributes[props.filter.key];
    });

    const possibleValues = computed(() => {
      if (props.filter.type === 'string') {
        const availabeAttributes = Object.values(getLayerAvailableProperties(props.layerId));
        const found = availabeAttributes.find((item) => item.key === (props.filter as StringFilters).key);
        if (found?.type === 'string' && !found.searchable && found.values) {
          return found.values;
        }
      }
      return [];
    });

    const getFilter = () => getLayerFilters(props.layerId)[props.filterIndex] as Filter | undefined;

    const throttledUpdateLayerFilter = throttle(updateLayerFilter, 10);

    const updateFilterValue = (value: number | number[] | string | string[] | boolean) => {
      const baseFilter = getFilter();
      const { layer } = getVectorLayerDisplayConfig(props.layerId, 'circle');
      if (baseFilter && layer) {
        if (props.filter.type === 'number' && ['>', '<', '>=', '<=', '=='].includes(props.filter.operator)) {
          const numberVal = value as number;
          (baseFilter as NumberComparisonFilter).value = numberVal;
          throttledUpdateLayerFilter(layer);
        } else if (props.filter.type === 'number' && props.filter.operator === 'between') {
          const numberVal = value as number[];
          [(baseFilter as NumberBetweenFilter).minValue, (baseFilter as NumberBetweenFilter).maxValue] = numberVal;
          throttledUpdateLayerFilter(layer);
        } else if (props.filter.type === 'string' && props.filter.operator === 'in') {
          const values = value as string[];
          (baseFilter as StringInArrayFilter).values = values;
          throttledUpdateLayerFilter(layer);
        }
      }
    };

    return {
      attribute,
      updateFilterValue,
      possibleValues,
    };
  },
});
</script>

<template>
  <v-row
    dense
    align="center"
    justify="center"
  >
    <div v-if="filter.type === 'number'">
      <div v-if="['>', '<', '>=', '<=', '=='].includes(filter.operator)">
        <v-slider
          width="200"
          :model-value="filter.value"
          :min="attribute.min || 0"
          :max="(attribute.max || 100) + 1"
          :step="(attribute.max || 100) >= 100 ? 1 : 0.1"
          thumb-label="always"
          @update:model-value="updateFilterValue($event)"
        />
      </div>
      <div v-else-if="filter.operator === 'between'">
        <v-range-slider
          width="200"
          :model-value="[filter.minValue, filter.maxValue]"
          :min="attribute.min || 0"
          :max="(attribute.max || 100) + 1"
          :step="(attribute.max || 100) >= 100 ? 1 : 0.1"
          thumb-label="always"
          @update:model-value="updateFilterValue($event)"
        />
      </div>
    </div>
    <div v-if="filter.type === 'string'">
      <div v-if="filter.operator === 'in'">
        <v-combobox
          :model-value="filter.values"
          chips
          multiple
          label="Values"
          :items="possibleValues"
          @update:model-value="updateFilterValue($event)"
        />
      </div>
    </div>
  </v-row>
</template>

<style scoped></style>
