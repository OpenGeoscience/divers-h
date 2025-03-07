<script lang="ts">
import {
  defineComponent, onMounted, ref, watch,
} from 'vue';
import * as d3 from 'd3';
import UVdatApi from '../../api/UVDATApi';
import MapStore from '../../MapStore';
import { AbstractMapLayer } from '../../types';
import { getStringBBox, toggleLayerSelection } from '../../map/mapLayers';

export default defineComponent({
  name: 'MetadataLayerFilter',
  setup() {
    const metadataFilters = ref<Record<string, string[]>>({});
    const selectedFilters = ref<Record<string, string[]>>({});
    const filteredLayers = ref<{ id: number; type: string; matches: string[]; name: string }[]>([]);
    const colorScale = d3.scaleOrdinal(d3.schemeCategory10);
    const search = ref('');
    const showFilters = ref(false); // Toggle filter visibility
    const filterBBox = ref(false);

    onMounted(async () => {
      metadataFilters.value = await UVdatApi.getMetadataFilters();
      Object.keys(metadataFilters.value).forEach((key) => {
        selectedFilters.value[key] = [];
      });
    });

    watch(
      [selectedFilters, search],
      async () => {
        let bbox: string;
        if (filterBBox.value) {
          bbox = getStringBBox();
        }
        const result = await UVdatApi.filterOnMetadata(selectedFilters.value, search.value, bbox);
        filteredLayers.value = result;
      },
      { deep: true },
    );

    function getIcon(type: string) {
      switch (type) {
        case 'netcdf':
          return 'mdi-grid';
        case 'raster':
          return 'mdi-image';
        case 'vector':
          return 'mdi-map-marker-outline';
        default:
          return 'mdi-map-marker-outline';
      }
    }

    const toggleFilterLayerSelection = async (layerId: number, layerType: AbstractMapLayer['type'], val: boolean) => {
      if (!val) {
        const found = MapStore.selectedMapLayers.value.find((item) => item.id === layerId && layerType === item.type);
        if (found) {
          toggleLayerSelection(found);
        }
      } else {
        const data = await UVdatApi.getMapLayerList([layerId], [layerType]);
        if (data.length) {
          toggleLayerSelection(data[0]);
        }
      }
    };

    return {
      selectedLayers: MapStore.selectedMapLayers,
      getIcon,
      selectedFilters,
      colorScale,
      filteredLayers,
      metadataFilters,
      toggleFilterLayerSelection,
      search,
      showFilters,
      filterBBox,
    };
  },
});
</script>

<template>
  <v-container>
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
    <v-row v-if="!showFilters && Object.values(selectedFilters).some(arr => arr.length)">
      <span v-for="(options, key) in metadataFilters" :key="key">

        <v-chip
          v-for="item in selectedFilters[key]"
          :key="item"
          :color="colorScale(item)"
          size="x-small"
          class="mr-1 mb-1"
        >
          {{ item }}
        </v-chip>
      </span>
    </v-row>

    <!-- Filters (Toggles Visibility) -->
    <v-expand-transition class="pt-2">
      <div v-if="showFilters">
        <v-row v-for="(options, key) in metadataFilters" :key="key">
          <v-combobox
            v-model="selectedFilters[key]"
            :items="options"
            :label="key"
            dense
            hide-details
            multiple
            chips
            clearable
          >
            <template #chip="{ item }">
              <v-chip size="x-small" :color="colorScale(item.value)">
                {{ item.title }}
              </v-chip>
            </template>
          </v-combobox>
        </v-row>
      </div>
    </v-expand-transition>

    <!-- Filtered Layers -->
    <v-list>
      <v-list-item v-for="layer in filteredLayers" :key="layer.id">
        <v-checkbox
          :model-value="!!selectedLayers.find((item) => (item.id === layer.id))"
          class="layer-checkbox"
          density="compact"
          hide-details
          @change="toggleFilterLayerSelection(layer.id, layer.type, $event)"
        >
          <template #label>
            <v-icon v-tooltip="layer.type === 'raster' ? 'Raster Layer' : 'Vector Layer'">
              {{ getIcon(layer.type) }}
            </v-icon>
            <span class="layer-checkbox-label">
              {{ layer.name }}
              <v-tooltip
                :text="layer.name"
                activator="parent"
                location="bottom"
                open-delay="1000"
              />
            </span>
          </template>
        </v-checkbox>
        <v-list-item-subtitle>
          <v-chip
            v-for="match in layer.matches"
            :key="match"
            :style="{ backgroundColor: colorScale(match) }"
            size="x-small"
          >
            {{ match }}
          </v-chip>
        </v-list-item-subtitle>
      </v-list-item>
    </v-list>
  </v-container>
</template>

<style scoped>
.v-chip {
  color: white;
}
.layer-checkbox-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
