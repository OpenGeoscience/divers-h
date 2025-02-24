<script lang="ts">
import {
  Ref, computed, defineComponent, ref,
} from 'vue';
import MapStore from '../MapStore';
import ColorKey from './MapLegends/ColorKey.vue';
import FilterKey from './MapLegends/FilterKey.vue';
import OpacityFilter from './MapLegends/ControlsKey.vue';

export default defineComponent({
  components: {
    ColorKey,
    FilterKey,
    OpacityFilter,
  },
  props: {
  },
  setup() {
    const selectedNetCDFMapLayers = computed(
      () => MapStore.selectedNetCDFMapLayers.value.filter(
        (layer) => MapStore.visibleMapLayers.value.has(`${layer.type}_${layer.id}`),
      ),
    );

    const selectedRasterMapLayers = computed(
      () => MapStore.selectedRasterMapLayers.value.filter(
        (layer) => MapStore.visibleMapLayers.value.has(`${layer.type}_${layer.id}`),
      ),
    );

    const selectedVectorMapLayers = computed(
      () => MapStore.selectedVectorMapLayers.value.filter(
        (layer) => MapStore.visibleMapLayers.value.has(`${layer.type}_${layer.id}`),
      ),
    );
    const hasFilters = computed(() => {
      let exists = false;
      selectedVectorMapLayers.value.forEach((layer) => {
        if (layer?.default_style?.filters?.length) {
          exists = true;
        }
      });
      return exists;
    });
    const tab: Ref<'colors' | 'opacity' | 'filters'> = ref('opacity');
    return {
      selectedVectorMapLayers,
      selectedNetCDFMapLayers,
      selectedRasterMapLayers,
      tab,
      hasFilters,
    };
  },
});
</script>

<template>
  <v-card
    v-if="selectedVectorMapLayers.length || selectedNetCDFMapLayers.length || selectedRasterMapLayers.length"
    width="375"
  >
    <v-card-title>
      <v-row class="pb-2">
        <v-spacer />
        <v-tabs
          v-model="tab"
          density="compact"
        >
          <v-tab value="opacity">
            Controls
          </v-tab>
          <v-tab value="colors">
            Colors
          </v-tab>
          <v-tab v-if="hasFilters" value="filters">
            Filters
          </v-tab>
        </v-tabs>
        <v-spacer />
      </v-row>
    </v-card-title>
    <v-card-text>
      <ColorKey
        v-if="tab === 'colors'"
        :vector-layers="selectedVectorMapLayers"
        :netcdf-layers="selectedNetCDFMapLayers"
        :raster-layers="selectedRasterMapLayers"
      />
      <OpacityFilter
        v-if="tab === 'opacity'"
        :vector-layers="selectedVectorMapLayers"
        :netcdf-layers="selectedNetCDFMapLayers"
        :raster-layers="selectedRasterMapLayers"
      />
      <filter-key
        v-if="tab === 'filters'"
        :layers="selectedVectorMapLayers"
      />
    </v-card-text>
  </v-card>
</template>

<style scoped>
.tab {
    border: 1px solid lightgray;

}

.tab:hover {
    cursor: pointer;
}

.selected-tab {
    background-color: lightgray;
}

.color-square {
    width: 15px;
    height: 15px;
    border: 1px solid #000;
    cursor: pointer;
}
</style>
