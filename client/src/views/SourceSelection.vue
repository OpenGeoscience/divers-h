<script lang="ts">
import {
  Ref, computed, defineComponent, onMounted, ref,
} from 'vue';
import Collection from '../components/DataSelection/Collection.vue';
import Datasets from '../components/DataSelection/Datasets.vue';
import Context from '../components/DataSelection/Context.vue';
import Selected from '../components/DataSelection/Selected.vue';
import MapStore from '../MapStore';
import MetadataLayerFilter from '../components/MetadataLayerFilter/MetadataLayerFilter.vue';

export default defineComponent({
  components: {
    Context,
    Selected,
    Collection,
    Datasets,
    MetadataLayerFilter,
  },
  setup() {
    onMounted(() => MapStore.loadCollections()); // Load for tab display if collections exists
    const tab: Ref<'Scenarios' | 'Datasets' | 'Collections' | 'Metadata Filters'> = ref('Scenarios');
    const selectedLayersCount = computed(() => MapStore.selectedMapLayers.value.length);
    return {
      tab,
      selectedLayersCount,
      collectionList: MapStore.availableCollections,
    };
  },
});
</script>

<template>
  <div
    :class="{ 'selected-open-height': selectedLayersCount, 'full-height': selectedLayersCount === 0 }"
  >
    <v-tabs v-model="tab" density="compact" class="tabs">
      <v-tab value="Scenarios" class="tab">
        Scenarios
      </v-tab>
      <v-tab value="Datasets" class="tab">
        Datasets
      </v-tab>
      <v-tab v-if="collectionList.length" value="Collections" class="tab">
        Collections
      </v-tab>
      <v-tab value="Metadata Filters" class="tab">
        Metadata <v-icon>mdi-filter</v-icon>
      </v-tab>
    </v-tabs>
    <context v-if="tab === 'Scenarios'" />
    <datasets
      v-else-if="tab === 'Datasets'"
    />
    <collection
      v-else-if="tab === 'Collections'"
    />
    <MetadataLayerFilter v-else-if="tab === 'Metadata Filters'" />
  </div>
  <v-divider v-if="selectedLayersCount" />
  <selected />
</template>

<style scoped>
.full-height {
  min-height: 100%;
  max-height: 100%;
  overflow-y: auto;
}
.selected-open-height {
  /* 1px is the divider */
  max-height: calc(50% - 1px);
  min-height: calc(50% - 1px);
  overflow-y: auto;
}
.tab {
  font-size: 10px;
}
</style>
