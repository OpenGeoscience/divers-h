<!-- eslint-disable vuejs-accessibility/mouse-events-have-key-events -->
<!-- eslint-disable vuejs-accessibility/mouse-events-have-key-events -->
<script lang="ts">
import {
  Ref,
  computed, defineComponent, onMounted, onUnmounted, ref, watch,
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
    const availableProperties = computed(() => {
      if (selectedLayer.value !== null) {
        const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === selectedLayer.value);
        if (found) {
          if (found.default_style.properties?.availableProperties) {
            return found.default_style.properties.availableProperties;
          }
        }
      }
      return {};
    });

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

    const displayKeys = computed(() => {
      if (selectedSearchSettings.value) {
        const subTitleKeys = selectedSearchSettings.value.display.subtitleKeys.filter((key) => key.showDisplayName).map((key) => key.key);
        const detailKeys = selectedSearchSettings.value.display.detailStrings.filter((key) => key.showDisplayName).map((key) => key.key);
        return { subTitleKeys, detailKeys };
      }
      return { subTitleKeys: [], detailKeys: [] };
    });

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

    onMounted(() => {
      if (availableLayers.value.length) {
        selectedLayer.value = availableLayers.value[0].value;
      }
      updateSearch();
    });

    onUnmounted(() => {
      if (internalMap.value) {
        internalMap.value.off('moveend', onMapMoveEnd);
        internalMap.value.off('move', onMapMove);
      }
    });

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

    const getPropertyDisplayName = (key: string) => {
      if (availableProperties.value[key]) {
        return availableProperties.value[key].displayName;
      }
      return key;
    };

    const zoomToFeature = (id: number) => {
      const found = searchResults.value.find((item) => item.id === id);
      if (found && internalMap.value && selectedSearchSettings.value?.display.zoomBufferOrLevel) {
        internalMap.value.setCenter([found.center.lon, found.center.lat]);
        internalMap.value.setZoom(selectedSearchSettings.value.display.zoomBufferOrLevel);
      }
    };

    const onCardHover = (vectorFeatureId: number) => {
      if (!MapStore.hoveredFeatures.value.includes(vectorFeatureId)) {
        MapStore.hoveredFeatures.value.push(vectorFeatureId);
      }
    };
    const onCardExit = (vectorFeatureId: number) => {
      const foundIndex = MapStore.hoveredFeatures.value.findIndex((item) => item === vectorFeatureId);
      if (foundIndex !== -1) {
        MapStore.hoveredFeatures.value.splice(foundIndex, 1);
      }
    };

    return {
      search,
      filterBBox,
      showFilters,
      selectedLayer,
      availableLayers,
      selectedSearchSettings,
      searchResults,
      getPropertyDisplayName,
      displayKeys,
      zoomToFeature,
      onCardHover,
      onCardExit,
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
      <!-- Eventual Filters added to the system -->
      <v-tooltip v-if="false" text="View metadata filters">
        <template #activator="{ props }">
          <v-icon :color="showFilters ? 'primary' : ''" v-bind="props" @click="showFilters = !showFilters">
            mdi-filter
          </v-icon>
        </template>
      </v-tooltip>
    </v-row>

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
      <v-card
        v-for="result in searchResults"
        :key="result.id"
        class="my-1 search-card"
        @mouseenter="onCardHover(result.id)"
        @focusin="onCardHover(result.id)"
        @focusout="onCardExit(result.id)"
        @mouseleave="onCardExit(result.id)"
      >
        <v-container>
          <v-row dense>
            <h4>{{ result.title }}</h4>
            <v-spacer />
            <v-tooltip v-if="selectedSearchSettings?.display.zoomButton" text="Zoom to Feature">
              <template #activator="{ props }">
                <v-icon v-bind="props" @click="zoomToFeature(result.id)">
                  mdi-magnify
                </v-icon>
              </template>
            </v-tooltip>
          </v-row>
          <div v-for="item in result.subtitles" :key="item.key">
            <b v-if="displayKeys.subTitleKeys.includes(item.key)" class="mx-2">{{ getPropertyDisplayName(item.key) }}:</b>
            <span>{{ item.value }}</span>
          </div>
          <ul v-if="result.details.length" class="ml-8">
            <li v-for="item in result.details" :key="item.key">
              <b v-if="displayKeys.detailKeys.includes(item.key)" class="mx-2">{{ getPropertyDisplayName(item.key) }}:</b>
              <span>{{ item.value }}</span>
            </li>
          </ul>
        </v-container>
      </v-card>
    </div>
  </v-container>
</template>

<style scoped>
.search-card:hover {
  background-color: #adf4ff78;
}
</style>
