<script lang="ts">
import {
  Ref, computed, defineComponent, onMounted, ref,
} from 'vue';
import UVdatApi from '../../api/UVDATApi';
import MapStore from '../../MapStore';
import {
  AvailablePropertyDisplay,
} from '../../types';

interface PropertyDisplayTable {
  selected: boolean;
  display?: boolean; // display when selected
  tooltip?: boolean; // display in tooltip
  displayName: string;
  key: string;
  description?: string;
  type: 'string' | 'number' | 'bool';
  valueCount: number;
  notes: {
    searchable?: boolean;
    static?: boolean;
    range?: { min?: number; max?: number };
    unique?: number;
  };
  values?: string[];
}
export default defineComponent({
  components: {},
  props: {
    layerId: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const loading = ref(false);
    const search = ref('');

    const customSearch = (
      value: string,
      query: string,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      item?: any,
    ) => Object.values(item).some((v) => v && v.toString().toLowerCase().includes(query.toLowerCase()));
    const headers = ref([
      { title: 'Selected', key: 'selected', width: '20px' },
      { title: 'Display', key: 'display', width: '20px' },
      { title: 'Tooltip', key: 'tooltip', width: '20px' },
      { title: 'Name', key: 'displayName', width: '40%' },
      { title: 'Type', key: 'type', width: '20px' },
      { title: 'Count', key: 'valueCount', width: '20px' },
      { title: 'Notes', key: 'notes', width: '80px' },
      { title: 'Values', key: 'values', width: '20px' },
    ]);
    const getLayerAvailableProperties = () => {
      const found = MapStore.selectedVectorMapLayers.value.find(
        (item) => item.id === props.layerId,
      );
      if (found?.default_style?.layers) {
        const availableProperties = found?.default_style?.properties?.availableProperties;
        if (availableProperties) {
          return availableProperties;
        }
      }
      return {};
    };
    const availableProperties = computed(() => getLayerAvailableProperties());
    const displaySummaryTable: Ref<PropertyDisplayTable[]> = ref([]);
    onMounted(async () => {
      loading.value = true;
      const results = await UVdatApi.getLayerPropertySummary(props.layerId);
      // convert into a better format for each item
      displaySummaryTable.value = [];
      Object.entries(results).forEach(([key, val]) => {
        let displayName = key;
        let selected = false;
        let description = '';
        let tooltip = false;
        let display = false;
        if (availableProperties.value[key] !== undefined) {
          selected = true;
          displayName = availableProperties.value[key].displayName;
          description = availableProperties.value[key].description || '';
          display = !!availableProperties.value[key].display;
          tooltip = !!availableProperties.value[key].tooltip;
        }
        displaySummaryTable.value.push({
          selected,
          displayName,
          display,
          tooltip,
          key,
          description,
          type: val.type,
          valueCount: val.value_count,
          notes: {
            searchable: val.searchable,
            static: val.static,
            unique: val.unique,
            range:
              val.min !== undefined || val.max !== undefined
                ? {
                  min: val.min,
                  max: val.max,
                }
                : undefined,
          },
          values: val.values,
        });
      });
      loading.value = false;
    });

    const pushMetadata = () => {
      const selected = displaySummaryTable.value.filter(
        (item) => item.selected,
      );

      const newAvailableProps: Record<string, AvailablePropertyDisplay> = {};
      selected.forEach((item) => {
        const newProp = {
          key: item.key,
          displayName: item.displayName,
          display: item.display,
          tooltip: item.tooltip,
          description: item.description,
          type: item.type,
          static: item.notes.static,
          searchable: item.notes.searchable,
          min: item.notes.range?.min,
          max: item.notes.range?.max,
          unique: item.notes.unique,
          values: item.values,
        };
        newAvailableProps[item.key] = newProp;
      });
      const found = MapStore.selectedVectorMapLayers.value.find(
        (item) => item.id === props.layerId,
      );
      if (found) {
        if (!found.default_style) {
          found.default_style = {
            properties: {
              availableProperties: {},
            },
          };
        }
        if (!found.default_style.properties) {
          found.default_style.properties = {
            availableProperties: {},
          };
        }
        if (found.default_style.properties?.availableProperties) {
          found.default_style.properties.availableProperties = newAvailableProps;
        }
      }
    };

    const updateMetadata = (
      key: string,
      selected: boolean,
      display: boolean,
      tooltip: boolean,
      name: string,
      description: string | undefined,
      item: PropertyDisplayTable,
    ) => {
      const found = MapStore.selectedVectorMapLayers.value.find(
        (subitem) => subitem.id === props.layerId,
      );
      if (found) {
        if (!found.default_style) {
          found.default_style = {
            properties: {
              availableProperties: {},
            },
          };
        }
        if (found?.default_style?.properties?.availableProperties && selected) {
          found.default_style.properties.availableProperties[key] = {
            key,
            displayName: name,
            display,
            tooltip,
            description,
            type: item.type,
            static: item.notes.static,
            searchable: item.notes.searchable,
            min: item.notes.range?.min,
            max: item.notes.range?.max,
            values: item.values,
          };
          // Also need to update local table view
          const foundLocal = displaySummaryTable.value.findIndex(
            (subitem) => subitem.key === key,
          );
          if (foundLocal !== -1) {
            const updated = displaySummaryTable.value[foundLocal];
            updated.selected = selected;
            updated.display = display;
            updated.tooltip = tooltip;
            updated.displayName = name;
            updated.description = description;
            displaySummaryTable.value.splice(foundLocal, 1, updated);
          }
        } else if (
          found?.default_style?.properties?.availableProperties
          && !selected
        ) {
          if (found.default_style.properties.availableProperties[key]) {
            delete found.default_style.properties.availableProperties[key];
          }
        }
      }
    };
    return {
      headers,
      displaySummaryTable,
      updateMetadata,
      pushMetadata,
      loading,
      search,
      customSearch,
    };
  },
});
</script>

<template>
  <v-row dense>
    <v-spacer />
    <v-btn
      color="success"
      :disabled="loading"
      @click="pushMetadata()"
    >
      Push Changes
    </v-btn>
  </v-row>
  <v-row
    v-if="!loading"
    dense
    class="mb-2"
  >
    <v-text-field
      v-model="search"
      label="Search"
      prepend-inner-icon="mdi-magnify"
      variant="outlined"
      hide-details
      single-line
    />
  </v-row>
  <v-data-table-virtual
    v-if="!loading"
    :headers="headers"
    fixed-header
    :items="displaySummaryTable"
    :search="search"
    :custom-filter="customSearch"
    height="700"
    item-value="key"
  >
    <template #[`item.selected`]="{ item }">
      <v-checkbox v-model="item.selected" />
    </template>
    <template #[`item.display`]="{ item }">
      <v-checkbox v-model="item.display" />
    </template>
    <template #[`item.tooltip`]="{ item }">
      <v-checkbox v-model="item.tooltip" />
    </template>
    <template #[`item.displayName`]="{ item }">
      <div>
        <span style="font-size: 0.75em">{{ item.key }}</span>
      </div>
      <v-text-field
        v-model="item.displayName"
        :disabled="!item.selected"
        class="mt-2"
        density="compact"
        label="Name"
      />
      <v-text-field
        v-model="item.description"
        :disabled="!item.selected"
        density="compact"
        label="Description"
      />
    </template>
    <template #[`item.notes`]="{ item }">
      <v-chip
        v-if="item.notes.searchable"
        color="primary"
      >
        Searchable
      </v-chip>
      <v-chip
        v-if="item.notes.static"
        color="primary"
      >
        Static
      </v-chip>
      <div v-if="item.notes.range">
        <b>Range: </b>
        <span>{{ item.notes.range.min }}</span>
        <span> to </span>
        <span>{{ item.notes.range.max }}</span>
      </div>
      <div v-if="item.notes.unique !== undefined">
        <b>Unique: </b>
        <span>{{ item.notes.unique }}</span>
      </div>
    </template>
    <template #[`item.values`]="{ item }">
      <v-tooltip :text="item.values?.join(',')">
        <template #activator="{ props }">
          <v-icon
            v-if="item.values"
            class="pl-3"
            v-bind="props"
          >
            mdi-text-long
          </v-icon>
        </template>
      </v-tooltip>
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
</template>

<style scoped></style>
