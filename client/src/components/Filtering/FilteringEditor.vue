<script lang="ts">
import {
  Ref, computed, defineComponent, onMounted,
  ref,
} from 'vue';
import MapStore from '../../MapStore';
import {
  AnnotationTypes,
  BaseFilter,
  Filter,
  NumberBetweenFilter,
  NumberComparisonFilter,
  NumberFilters,
  StringContainsFilter,
  StringFilters,
  StringInArrayFilter,
  VectorMapLayer,
} from '../../types';
import { getLayerAvailableProperties, getLayerFilters } from '../../utils';
import AddingFilter from './AddingFilter.vue';

interface FilterDisplayTable {
  interactable: boolean;
  name: string;
  key: string;
  filter: Filter;
  description?: string;
  type: BaseFilter['type'];
  layers?: AnnotationTypes[];
  details: {
    operator: NumberFilters['operator'] | StringFilters['operator'];
    value?: number | string;
    values?: string[];
    minValue?: number;
    maxValue?: number;
  };
}
export default defineComponent({
  components: {
    AddingFilter,
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const loading = ref(false);
    const headers = ref([
      { title: 'Name', key: 'name' },
      { title: 'Key', key: 'key' },
      { title: 'Interactable', key: 'interactable', width: '20px' },
      { title: 'Type', key: 'type', width: '20px' },
      { title: 'Description', key: 'description' },
      { title: 'Layers', key: 'layers', width: '200px' },
      { title: 'Delete', value: 'delete', width: '20px' },
    ]);
    const availableProperties = computed(() => getLayerAvailableProperties(props.layerId));
    const displaySummaryTable: Ref<FilterDisplayTable[]> = ref([]);
    onMounted(async () => {
      loading.value = true;
      const filters = getLayerFilters(props.layerId);
      displaySummaryTable.value = [];
      filters.forEach((filter) => {
        displaySummaryTable.value.push({
          name: filter.name,
          filter,
          key: availableProperties.value[filter.key].displayName || filter.key,
          interactable: filter.interactable,
          type: filter.type,
          description: filter.description,
          layers: filter.layers,
          details: {
            operator: filter.operator,
            value: (filter as NumberComparisonFilter | StringContainsFilter)
              ?.value,
            values: (filter as StringInArrayFilter)?.values,
            minValue: (filter as NumberBetweenFilter)?.minValue,
            maxValue: (filter as NumberBetweenFilter)?.maxValue,
          },
        });
      });
      loading.value = false;
    });

    const pushFilters = () => {
      const found = MapStore.selectedVectorMapLayers.value.find(
        (item: VectorMapLayer) => item.id === props.layerId,
      );
      const filters = displaySummaryTable.value.map((filterDisplay) => {
        const baseFilter = filterDisplay.filter;
        baseFilter.name = filterDisplay.name;
        baseFilter.layers = filterDisplay.layers || [];
        baseFilter.interactable = filterDisplay.interactable;
        return baseFilter;
      });
      if (found && found.default_style) {
        found.default_style.filters = filters;
      }
    };

    const addingFilter = ref(false);

    const addFilter = (filter: Filter) => {
      displaySummaryTable.value.push({
        name: filter.name,
        filter,
        key: availableProperties.value[filter.key].displayName || filter.key,
        interactable: filter.interactable,
        type: filter.type,
        description: filter.description,
        layers: filter.layers,
        details: {
          operator: filter.operator,
          value: (filter as NumberComparisonFilter | StringContainsFilter)
            ?.value,
          values: (filter as StringInArrayFilter)?.values,
          minValue: (filter as NumberBetweenFilter)?.minValue,
          maxValue: (filter as NumberBetweenFilter)?.maxValue,
        },
      });
      addingFilter.value = false;
    };
    const deleteFilter = (deletingFilter: Filter) => {
      const index = displaySummaryTable.value.findIndex(
        (filter) => filter.type === deletingFilter.type && filter.name === deletingFilter.name,
      );
      if (index !== -1) {
        displaySummaryTable.value.splice(index, 1);
      }
    };

    const updateFilter = (
      index: number,
      name: string,
      interactable: boolean,
      description: string,
      layers: AnnotationTypes[],
    ) => {
      displaySummaryTable.value[index] = {
        ...displaySummaryTable.value[index],
        name,
        interactable,
        description,
        layers,
        filter: {
          ...displaySummaryTable.value[index].filter,
          name,
          interactable,
          description,
          layers,
        },
      };
    };

    const toggleLayerFilter = (index: number, layerType: AnnotationTypes) => {
      const { layers } = displaySummaryTable.value[index];
      if (layers) {
        if (layers.includes(layerType)) {
          const subIndex = layers.findIndex((item) => item === layerType);
          layers.splice(subIndex);
        } else {
          layers.push(layerType);
        }
        displaySummaryTable.value[index].layers = layers;
      }
    };

    const deleteItem = (index: number) => {
      if (displaySummaryTable.value[index]) {
        displaySummaryTable.value.splice(index, 1);
      }
    };

    return {
      headers,
      displaySummaryTable,
      pushFilters,
      loading,
      addingFilter,
      addFilter,
      deleteFilter,
      updateFilter,
      toggleLayerFilter,
      deleteItem,
    };
  },
});
</script>

<template>
  <v-row dense>
    <v-spacer />
    <v-btn
      color="primary"
      @click="addingFilter = true"
    >
      Add Filter
    </v-btn>
    <v-btn
      color="success"
      :disabled="loading"
      class="ml-2"
      @click="pushFilters()"
    >
      Push Changes
    </v-btn>
  </v-row>
  <v-data-table-virtual
    v-if="!loading"
    :headers="headers"
    :items="displaySummaryTable"
    height="700"
    item-value="key"
  >
    <template #[`item.name`]="{ item }">
      <v-text-field
        v-model="item.name"
        density="compact"
        label="Name"
      />
    </template>

    <template #[`item.interactable`]="{ item }">
      <v-checkbox v-model="item.interactable" />
    </template>
    <template #[`item.layers`]="{ item, index }">
      <v-row
        v-if="item.layers"
        dense
        style="max-width:300px"
        align="center"
        justify="center"
      >
        <v-tooltip text="Line Display">
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              :color="item.layers.includes('line') ? 'primary' : ''"
              size="x-small"
              class="icon-center"
              @click="toggleLayerFilter(index, 'line')"
            >
              mdi-vector-line
            </v-icon>
          </template>
        </v-tooltip>
        <v-tooltip text="Polygon Display">
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              :color="item.layers.includes('fill') ? 'primary' : ''"
              size="x-small"
              class="icon-center"
              @click="toggleLayerFilter(index, 'fill')"
            >
              mdi-pentagon
            </v-icon>
          </template>
        </v-tooltip>
        <v-tooltip text="Point Display">
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              :color="item.layers.includes('circle') ? 'primary' : ''"
              size="x-small"
              class="icon-center"
              @click="toggleLayerFilter(index, 'circle')"
            >
              mdi-circle-outline
            </v-icon>
          </template>
        </v-tooltip>
        <v-tooltip text="Building Display">
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              :color="
                item.layers.includes('fill-extrusion') ? 'primary' : ''
              "
              size="x-small"
              class="icon-center"
              @click="toggleLayerFilter(index, 'fill-extrusion')"
            >
              mdi-domain
            </v-icon>
          </template>
        </v-tooltip>
        <v-tooltip text="Text Display">
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              :color="item.layers.includes('text') ? 'primary' : ''"
              size="x-small"
              class="icon-center"
              @click="toggleLayerFilter(index, 'text')"
            >
              mdi-format-text
            </v-icon>
          </template>
        </v-tooltip>
      </v-row>
    </template>
    <template #[`item.delete`]="{ index }">
      <v-btn
        color="error"
        @click="deleteItem(index)"
      >
        Delete
      </v-btn>
    </template>
  </v-data-table-virtual>
  <div v-if="loading">
    <v-row dense>
      <v-spacer />
      <h3>Loading...</h3>
      <v-spacer />
    </v-row>
    <v-row dense>
      <v-progress-linear
        indeterminate
        :height="12"
      />
    </v-row>
  </div>
  <v-dialog
    v-model="addingFilter"
    width="800"
  >
    <adding-filter
      :layer-id="layerId"
      @cancel="addingFilter = false"
      @add="addFilter($event)"
    />
  </v-dialog>
</template>

<style scoped>
.tab {
  border: 1px solid lightgray;
}

.tab:hover {
  cursor: pointer;
}
.icon-center {
  width:35px;
  height:35px;
  border: 1px solid lightgray;
  display: flex;
  align-items: center;
  justify-content: center;
}

</style>
