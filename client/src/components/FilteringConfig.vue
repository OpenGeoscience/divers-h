<script lang="ts">
import {
  Ref, defineComponent, ref, watch,
} from 'vue';
import MapStore from '../MapStore';
import { Filter, VectorMapLayer } from '../types';
import FilteringEditor from './Filtering/FilteringEditor.vue';
import { getLayerFilters } from '../utils';
import { updateLayerFilter } from '../map/mapVectorLayers';
import FilteringInteraction from './Filtering/FilteringInteraction.vue';

export default defineComponent({
  components: {
    FilteringEditor,
    FilteringInteraction,
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const filters: Ref<Filter[]> = ref(getLayerFilters(props.layerId));
    watch(MapStore.selectedVectorMapLayers, () => {
      const found = MapStore.selectedVectorMapLayers.value.find((item: VectorMapLayer) => item.id === props.layerId);
      if (found?.default_style?.filters) {
        filters.value = found?.default_style?.filters || [];
      } else {
        filters.value = [];
      }
    }, { deep: true });

    const editFilters = ref(false);

    const updateUserEnabled = (filter: Filter) => {
      // eslint-disable-next-line no-param-reassign
      filter.userEnabled = !filter.userEnabled;
      const found = MapStore.selectedVectorMapLayers.value.find((item: VectorMapLayer) => item.id === props.layerId);
      if (found) {
        updateLayerFilter(found);
      }
    };

    const interactableDialog = ref(false);
    const interactableIndex = ref(0);
    const interactableFilter: Ref<Filter | undefined> = ref();
    const interactFilter = (index: number, filter: Filter) => {
      interactableIndex.value = index;
      interactableFilter.value = filter;
      interactableDialog.value = true;
    };
    return {
      filters,
      editFilters,
      updateUserEnabled,
      interactableDialog,
      interactableIndex,
      interactableFilter,
      interactFilter,
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
    <h3>Available Filters</h3>
    <v-spacer />
    <v-icon @click="editFilters = true">
      mdi-cog
    </v-icon>
  </v-row>
  <v-row
    dense
    align="center"
    justify="center"
  >
    <v-col cols="6">
      <span>Display Name</span>
    </v-col>
    <v-col cols="3">
      <span>Type</span>
    </v-col>
    <v-col cols="3">
      <span>Details</span>
    </v-col>
  </v-row>
  <v-row
    v-for="(filter, index) in filters"
    :key="filter.key"
    dense
    align="center"
    justify="center"
  >
    <v-col cols="5">
      <v-icon
        size="x-small"
        @click="updateUserEnabled(filter)"
      >
        {{
          filter.userEnabled ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline' }}
      </v-icon>

      <span>{{ filter.name }}</span>
    </v-col>
    <v-col cols="3">
      <span>{{ filter.type }}</span>
    </v-col>
    <v-col cols="3">
      <v-tooltip :text="filter.description">
        <template #activator="{ props }">
          <v-icon
            v-if="filter.description"
            class="pl-3"
            v-bind="props"
          >
            mdi-text-long
          </v-icon>
        </template>
      </v-tooltip>
      <v-tooltip text="Edit Value">
        <template #activator="{ props }">
          <v-icon
            v-if="filter.interactable"
            class="pl-3"
            v-bind="props"
            @click="interactFilter(index, filter)"
          >
            mdi-pencil
          </v-icon>
        </template>
      </v-tooltip>
    </v-col>
  </v-row>
  <v-dialog
    v-model="editFilters"
    width="1200"
  >
    <v-card>
      <v-card-title>Filtering Editor</v-card-title>
      <v-card-text>
        <FilteringEditor :layer-id="layerId" />
      </v-card-text>
    </v-card>
  </v-dialog>
  <v-dialog
    v-model="interactableDialog"
    width="300"
  >
    <v-card>
      <v-card-title>Interact Filter</v-card-title>
      <v-card-text v-if="interactableFilter">
        <FilteringInteraction
          :layer-id="layerId"
          :filter-index="interactableIndex"
          :filter="interactableFilter"
        />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped></style>
