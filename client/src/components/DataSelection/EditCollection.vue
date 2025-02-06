<script lang="ts">
import {
  PropType, Ref, defineComponent, onMounted, ref,
  watch,
} from 'vue';
import MapStore from '../../MapStore';
import { LayerCollection } from '../../types';
import { getCenterAndZoom } from '../../map/mapLayers';
import UVdatApi from '../../api/UVDATApi';

export default defineComponent({
  components: {
  },
  props: {
    collection: {
      type: Object as PropType<LayerCollection | null>,
      required: false,
      default: null,
    },
  },
  emits: ['close'],
  setup(props, { emit }) {
    const getLayerCollectionLayers = () => MapStore.selectedMapLayers.value.map((item) => ({
      layerId: item.id,
      type: item.type,
      visible: MapStore.visibleMapLayers.value.has(`${item.type}_${item.id}`),
      defaultLayerRepresentationId: item.layerRepresentationId,
    }));

    const editCollection: Ref<null | LayerCollection> = ref(props.collection);
    const addCollection = () => {
      const layers = getLayerCollectionLayers();
      editCollection.value = {
        id: -1,
        name: 'New Collection Name',
        description: '',
        configuration: {
          mapInfo: getCenterAndZoom(),
          layers,
        },
      };
    };
    const computeCollection = () => {
      if (props.collection) {
        editCollection.value = props.collection;
      } else {
        addCollection();
      }
    };
    onMounted(() => computeCollection());
    watch(() => props.collection, () => {
      computeCollection();
    });
    const saveEditingCollection = async () => {
      if (editCollection.value) {
        if (props.collection === null) {
          const layers = getLayerCollectionLayers();
          editCollection.value.configuration.layers = layers;
          editCollection.value.configuration.mapInfo = getCenterAndZoom();
          await UVdatApi.addLayerCollection(editCollection.value);
        } else {
          await UVdatApi.patchLayerCollection(editCollection.value.id, editCollection.value);
        }
        MapStore.loadCollections();
      }
      emit('close');
    };

    return {
      editCollection,
      addCollection,
      saveEditingCollection,
    };
  },
});
</script>

<template>
  <v-card v-if="editCollection">
    <v-card-title>
      {{ editCollection.id === -1 ? 'Add New Collection' : `Edit Collection: ${editCollection.name}` }}
    </v-card-title>
    <v-card-text>
      <v-row>
        <v-text-field v-model="editCollection.name" label="Name" />
      </v-row>
      <v-row>
        <v-text-field v-model="editCollection.description" label="Description" />
      </v-row>
    </v-card-text>
    <v-card-actions>
      <v-row>
        <v-spacer />
        <v-btn color="error" class="mx-2" @click="$emit('close')">
          Cancel
        </v-btn>
        <v-btn color="success" class="mx-2" @click="saveEditingCollection()">
          {{ editCollection.id !== -1 ? 'Save' : 'Add' }}
        </v-btn>
      </v-row>
    </v-card-actions>
  </v-card>
</template>

<style scoped>
.ghost {
  opacity: 0.5;
  background: #c8ebfb;
}

</style>
