<script lang="ts">
import { computed, defineComponent, ref } from 'vue';
import { getLayerFilters } from '../../utils';

export default defineComponent({
  components: {
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
    filterIndex: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const filterTypes = ref([
      {
        type: 'none',
        name: 'No Filtering',
        typeRequirements: [],
        description: 'No Filtering',
      },

      {
        type: 'number',
        name: 'Numerical',
        description: 'Numerical Filtering',
      },
      {
        type: 'string',
        name: 'String',
        description:
          'Filtering based on String values',
      },
      {
        type: 'boolean',
        name: 'Boolean',
        description:
          'Filtering based on Boolean Values',
      },

    ]);

    const baseFilterType = computed(() => {
      const filters = getLayerFilters(props.layerId);
      if (filters.length) {
        if (filters[props.filterIndex]) {
          return filters[props.filterIndex].type;
        }
      }
      return 'none';
    });
    const selectedFilterType = ref(
      baseFilterType.value,
    );

    return {
      selectedFilterType,
      baseFilterType,
      filterTypes,
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
    <v-select
      v-model="selectedFilterType"
      :items="filterTypes"
      item-value="type"
      item-title="name"
      label="Color Type"
    >
      <template #item="{ props, item }">
        <v-list-item
          v-bind="props"
          :subtitle="item.raw.description"
        />
      </template>
    </v-select>
  </v-row>
  <div v-if="'number' === selectedFilterType">
    <span>number</span>
  </div>
  <div v-if="'string' === selectedFilterType">
    <span>string</span>
  </div>
</template>

<style scoped>
</style>
