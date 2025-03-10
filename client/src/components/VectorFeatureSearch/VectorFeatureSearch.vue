<script lang="ts">
import {
  Ref,
  computed, defineComponent, ref, watch,
} from 'vue';
import UVdatApi from '../../api/UVDATApi';
import MapStore from '../../MapStore';
import { SearchableVectorDataRequest, SearchableVectorFeatureResponse } from '../../types';
import { getStringBBox, internalMap } from '../../map/mapLayers';

export default defineComponent({
  name: 'VectorFeatureSearch',
  setup() {
    const search = ref('');
    const filterBBox = ref(false);
    const showFilters = ref(false);
    const selectedLayer = ref<number | null>(null);
    const availableLayers = computed(
      () => MapStore.mapLayerVectorSearchable.value.map((item) => ({ title: item.name, value: item.id })),
    );
    const selectedSearchSettings = computed(() => {
      if (selectedLayer.value !== null) {
        return MapStore.mapLayerVectorSearchable.value.find((item) => item.id === selectedLayer.value)?.searchSettings;
      }
      return undefined;
    });
    const searchResults: Ref<SearchableVectorFeatureResponse[]> = ref([]);

    const updateSearch = async () => {
      if (selectedSearchSettings.value && selectedLayer.value !== null) {
        const data: SearchableVectorDataRequest = {
          mapLayerId: selectedLayer.value as number,
          mainTextSearchFields: selectedSearchSettings.value.mainTextSearchFields,
          search: search.value,
          bbox: filterBBox.value ? getStringBBox() : undefined,
          titleKey: selectedSearchSettings.value.display.titleKey,
          subtitleKeys: selectedSearchSettings.value.display.subtitleKeys,
          detailStrings: selectedSearchSettings.value.display.detailStrings,
        };
        searchResults.value = await UVdatApi.searchVectorFeatures(data);
      }
    };
    let movementTimeout: NodeJS.Timeout | null = null;
    const onMapMoveEnd = () => {
      if (movementTimeout) clearTimeout(movementTimeout);
      movementTimeout = setTimeout(updateSearch, 500);
    };

    const onMapMove = () => {
      if (movementTimeout) {
        clearTimeout(movementTimeout);
      }
    };

    watch(filterBBox, () => {
      if (filterBBox.value && internalMap.value) {
        internalMap.value.on('moveend', onMapMoveEnd);
        internalMap.value.on('move', onMapMove);
      } else if (internalMap.value) {
        internalMap.value.off('moveend', onMapMoveEnd);
        internalMap.value.off('move', onMapMove);
      }
      updateSearch();
    });

    watch([search, selectedLayer, filterBBox], () => {
      updateSearch();
    });

    return {
      search,
      filterBBox,
      showFilters,
      selectedLayer,
      availableLayers,
      selectedSearchSettings,
      searchResults,
    };
  },
});
</script>

<template>
  <v-container>
    <v-row no-gutters dense align="center">
      <v-select
        v-model="selectedLayer"
        density="compact"
        :items="availableLayers"
        item-text="title"
        item-value="value"
        label="Select Layer"
        hide-details
        dense
        outlined
      />
    </v-row>

    <!-- Search Bar and Filter Toggle -->
    <v-row class="mb-2 align-center">
      <v-text-field
        v-model="search"
        label="Search layers..."
        dense
        hide-details
        clearable
        prepend-inner-icon="mdi-magnify"
      />
      <v-tooltip text="Filter by current Map View">
        <template #activator="{ props }">
          <v-icon :color="filterBBox ? 'primary' : ''" v-bind="props" @click="filterBBox = !filterBBox">
            mdi-vector-square
          </v-icon>
        </template>
      </v-tooltip>
      <v-tooltip text="View metadata filters">
        <template #activator="{ props }">
          <v-icon :color="showFilters ? 'primary' : ''" v-bind="props" @click="showFilters = !showFilters">
            mdi-filter
          </v-icon>
        </template>
      </v-tooltip>
    </v-row>

    <!-- Selected Filters as Chips (Shown when filters are hidden) -->

    <!-- Filters (Toggles Visibility) -->
    <v-expand-transition class="pt-2">
      <div v-if="showFilters && selectedSearchSettings?.configurableFilters.length">
        <v-row v-for="(options, key) in selectedSearchSettings.configurableFilters" :key="key">
          {{ options }}
        </v-row>
      </div>
    </v-expand-transition>

    <!-- Filtered Layers -->
    <div v-if="searchResults">
      <v-card v-for="result in searchResults" :key="result.id">
        {{ result.title }}
        <v-list-item-subtitle>
          <div v-for="item in result.subtitles" :key="item">
            {{ item }}
          </div>
        </v-list-item-subtitle>
      </v-card>
    </div>
  </v-container>
</template>

<style scoped>
</style>
