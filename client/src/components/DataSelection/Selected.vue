<script lang="ts">
import {
  defineComponent, ref,
} from 'vue';
import draggable from 'vuedraggable';
import MapStore from '../../MapStore';
import {
  getCenterAndZoom, reorderMapLayers, toggleLayerSelection, toggleLayerVisibility, zoomToBounds,
} from '../../map/mapLayers';
import LayerConfig from '../LayerConfig.vue';
import EditCollection from './EditCollection.vue';
import UVdatApi from '../../api/UVDATApi';

export default defineComponent({
  components: {
    LayerConfig,
    draggable,
    EditCollection,
  },
  setup() {
    const reorder = () => {
      reorderMapLayers();
    };

    const addEditCollection = ref(false);

    const getLayerCollectionLayers = () => MapStore.selectedMapLayers.value.map((item) => ({
      layerId: item.id,
      type: item.type,
      visible: MapStore.visibleMapLayers.value.has(`${item.type}_${item.id}`),
      defaultLayerRepresentationId: item.layerRepresentationId,
    }));

    const saveEditingCollection = async () => {
      if (MapStore.selectedCollection.value) {
        const layers = getLayerCollectionLayers();
        MapStore.selectedCollection.value.configuration.layers = layers;
        MapStore.selectedCollection.value.configuration.mapInfo = getCenterAndZoom();
        await UVdatApi.patchLayerCollection(MapStore.selectedCollection.value.id, MapStore.selectedCollection.value);
      }
      MapStore.loadCollections();
    };

    const resetMapLayerBounds = async () => {
      const rasterIds: number[] = [];
      const vectorIds: number[] = [];
      const netCDFIds: number[] = [];
      MapStore.selectedMapLayers.value.forEach((layer) => {
        if (MapStore.visibleMapLayers.value.has(`${layer.type}_${layer.id}`)) {
          if (layer.type === 'raster') {
            rasterIds.push(layer.id);
          } else if (layer.type === 'vector') {
            vectorIds.push(layer.id);
          } else if (layer.type === 'netcdf') {
            netCDFIds.push(layer.id);
          }
        }
      });
      const bounds = await UVdatApi.getMapLayersBoundingBox(rasterIds, vectorIds, netCDFIds);
      zoomToBounds(bounds);
    };

    return {
      proMode: MapStore.proMode,
      addEditCollection,
      selectedLayers: MapStore.selectedMapLayers,
      selectedCollection: MapStore.selectedCollection,
      toggleLayerSelection,
      toggleLayerVisibility,
      reorder,
      saveEditingCollection,
      resetMapLayerBounds,
    };
  },
});
</script>

<template>
  <div
    v-if="selectedLayers.length"
    class="selected-layers"
  >
    <v-container class="pa-0 ma-0">
      <v-row dense class="pt-2" style="max-width:350px">
        <h4 class="pl-2">
          Selected Layers
        </h4>
        <v-tooltip text="Reset Camera to Visible Map Layer Bounds">
          <template #activator="{ props }">
            <v-icon v-bind="props" class="pl-4" @click="resetMapLayerBounds()">
              mdi-image-filter-center-focus
            </v-icon>
          </template>
        </v-tooltip>

        <v-spacer />
        <v-tooltip v-if="proMode && selectedCollection" :text="`Save Collection: ${selectedCollection.name}`">
          <template #activator="{ props }">
            <v-icon v-bind="props" color="success" @click="saveEditingCollection()">
              mdi-content-save
            </v-icon>
          </template>
        </v-tooltip>
        <v-tooltip v-if="proMode" text="Add New Collection based on current styling">
          <template #activator="{ props }">
            <v-icon v-bind="props" color="success" @click="addEditCollection = true; selectedCollection = null">
              mdi-plus-thick
            </v-icon>
          </template>
        </v-tooltip>
      </v-row>
      <draggable
        :list="selectedLayers"
        item-key="name"
        handle=".handle"
        class="list-group"
        ghost-class="ghost"
        @end="reorder"
      >
        <template #item="{ element }">
          <v-list-item>
            <layer-config
              :layer="element"
              @toggle-layer="toggleLayerVisibility(element, $event)"
              @deselect-layer="toggleLayerSelection(element)"
            />
          </v-list-item>
        </template>
      </draggable>
    </v-container>
  </div>
  <v-dialog v-model="addEditCollection" width="500">
    <edit-collection :collection="selectedCollection || null" @close="addEditCollection = false" />
  </v-dialog>
</template>

<style scoped>
.ghost {
  opacity: 0.5;
  background: #c8ebfb;
}
.selected-layers {
  max-height: 50%;
  min-height: 50%;
  overflow-y: auto;
}

</style>
