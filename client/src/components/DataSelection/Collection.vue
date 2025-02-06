<script lang="ts">
import {
  Ref, defineComponent, onMounted, ref,
} from 'vue';
import MapStore from '../../MapStore';
import { LayerCollection } from '../../types';
import UVdatApi from '../../api/UVDATApi';
import { toggleMapLayers } from '../../map/mapLayers';
import { centerAndZoom } from '../../map/mapVectorLayers';
import EditCollection from './EditCollection.vue';

export default defineComponent({
  components: {
    EditCollection,
  },
  setup() {
    // Collection should be reloaded when mounted incase new items have been modified
    onMounted(() => MapStore.loadCollections());

    const selectCollection = async (item: LayerCollection) => {
      MapStore.selectedMapLayers.value = [];
      // filter only for enabled if not in 'pro' mode
      const enabled = MapStore.proMode.value ? undefined : true;
      const selectedLayers = await UVdatApi.getMapLayerCollectionList(item.configuration.layers, enabled);
      MapStore.selectedMapLayers.value = selectedLayers;
      item.configuration.layers.forEach((subItem) => {
        if (subItem.visible) {
          MapStore.visibleMapLayers.value.add(`${subItem.type}_${subItem.layerId}`);
        }
      });
      centerAndZoom(item.configuration.mapInfo.center, item.configuration.mapInfo.zoom);
      MapStore.selectedCollection.value = item;
      toggleMapLayers();
    };

    const editCollectionDialog = ref(false);
    const editingCollection: Ref<LayerCollection | null> = ref(null);
    const editCollection = (item: LayerCollection) => {
      editingCollection.value = item;
      editCollectionDialog.value = true;
    };

    const deleteCollection = async (item: LayerCollection) => {
      await UVdatApi.deleteLayerCollection(item.id);
      MapStore.loadCollections();
    };

    return {
      proMode: MapStore.proMode,
      collectionList: MapStore.availableCollections,
      selectedCollection: MapStore.selectedCollection,
      selectCollection,
      editCollection,
      deleteCollection,
      editingCollection,
      editCollectionDialog,
    };
  },
});
</script>

<template>
  <v-list>
    <v-list-item
      v-for="item in collectionList"
      :key="`collection_${item.id}`"
      @click="selectCollection(item)"
    >
      <v-list-item-title>{{ item.name }}</v-list-item-title>
      <v-list-item-subtitle>{{ item.description }}</v-list-item-subtitle>
      <v-list-item-action v-if="proMode">
        <v-spacer />
        <v-tooltip text="Edit Collection" location="top">
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              icon="mdi-pencil"
              variant="plain"
              density="compact"
              color="warning"
              @click.stop="editCollection(item)"
            />
          </template>
        </v-tooltip>
        <v-tooltip text="Delete Collection" location="top">
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              icon="mdi-delete"
              variant="plain"
              density="compact"
              color="error"
              @click.stop="deleteCollection(item)"
            />
          </template>
        </v-tooltip>
      </v-list-item-action>
    </v-list-item>
  </v-list>
  <v-dialog v-model="editCollectionDialog" width="500">
    <edit-collection :collection="editingCollection" @close="editCollectionDialog = false" />
  </v-dialog>
</template>

<style scoped>
</style>
