<!-- eslint-disable @typescript-eslint/naming-convention -->
<script lang="ts">
import {
  Ref, computed, defineComponent, onMounted, ref,
  watch,
} from 'vue';
import MapStore from '../../MapStore';
import {
  LayerRepresentation,
} from '../../types';

import UVdatApi from '../../api/UVDATApi';
import { updateLayer } from '../../map/mapLayers';

export default defineComponent({
  name: 'LayerRepresentation',
  components: {
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
  },
  emits: ['selectedLayer'],
  setup(props, { emit }) {
    const possibleLayerReps: Ref<LayerRepresentation[]> = ref([]);
    const addOrEdit = ref(false);
    const editingLayerRep: Ref<null | (LayerRepresentation & { id: number | null })> = ref(null);
    const selectedMapLayer = computed(() => MapStore.selectedMapLayers.value.find((item) => item.id === props.layerId));
    const selectedLayerRepId: Ref<null | number> = ref(null);
    const selectedLayerRep = computed(() => possibleLayerReps.value.find((item) => item.id === selectedLayerRepId.value));

    const getLayerReps = async (resetLayerRepId = false) => {
      if (selectedMapLayer.value === undefined) {
        throw Error(`No SelectedMapLayer found for MapId: ${props.layerId}`);
      }
      const reps = await UVdatApi.getLayerRepresentations(props.layerId, selectedMapLayer.value.type);
      selectedLayerRepId.value = selectedMapLayer.value.layerRepresentationId ?? null;
      possibleLayerReps.value = reps.filter((item) => (!MapStore.proMode.value ? item.enabled : true));
      if (selectedLayerRepId.value === null || resetLayerRepId) {
        selectedLayerRepId.value = possibleLayerReps.value[0].id;
      }
    };
    onMounted(() => getLayerReps());
    const saveEditingRep = async () => {
      if (editingLayerRep.value !== null) {
        if (editingLayerRep.value.id !== -1 && selectedMapLayer.value) {
          await UVdatApi.patchLayerRepresentation(
            editingLayerRep.value.id,
            {
              ...editingLayerRep.value,
              type: selectedMapLayer.value.type,
              layer_id: props.layerId,
            },
          );
        } else {
          await UVdatApi.addLayerRepresentation(editingLayerRep.value);
        }
      }
      await getLayerReps();
      if (editingLayerRep.value && editingLayerRep.value.id === -1) {
        // If creating new layer set it as the current layer
        selectedLayerRepId.value = possibleLayerReps.value[possibleLayerReps.value.length - 1].id;
      }
      editingLayerRep.value = null;
      addOrEdit.value = false;
    };

    watch(selectedLayerRep, () => {
      const found = MapStore.selectedMapLayers.value.find((item) => item.id === props.layerId);
      if (found && selectedLayerRep.value !== null) {
        found.default_style = selectedLayerRep.value?.default_style;
        emit('selectedLayer', selectedLayerRep.value);
        updateLayer(found);
      }
    });

    watch(MapStore.proMode, () => {
      getLayerReps(true);
    });

    const addNewRep = () => {
      if (selectedMapLayer.value) {
        editingLayerRep.value = {
          id: -1, // New LayerRep
          layer_id: props.layerId,
          name: 'New Representation Name',
          description: '',
          enabled: true,
          type: selectedMapLayer.value?.type,
          default_style: selectedMapLayer.value?.default_style,
        };
        addOrEdit.value = true;
      }
    };
    const editRep = () => {
      if (selectedLayerRep.value) {
        editingLayerRep.value = selectedLayerRep.value;
        addOrEdit.value = true;
      }
    };

    const deleteRep = async () => {
      if (selectedLayerRepId.value !== null) {
        await UVdatApi.deleteLayerRepresentation(selectedLayerRepId.value);
        await getLayerReps(true);
      }
    };

    return {
      proMode: MapStore.proMode,
      possibleLayerReps,
      addOrEdit,
      selectedLayerRep,
      selectedLayerRepId,
      editingLayerRep,
      saveEditingRep,
      addNewRep,
      editRep,
      deleteRep,
    };
  },
});
</script>

<template>
  <v-row align="center" justify="center" class="mt-2">
    <v-select
      v-model="selectedLayerRepId"
      :items="possibleLayerReps"
      item-value="id"
      item-title="name"
      density="compact"
      style="max-width: 300px;"
      class="ma-auto"
    >
      <template v-if="proMode" #prepend>
        <v-tooltip text="Delete Current Representation" location="top">
          <template #activator="{ props, isActive }">
            <v-btn
              v-bind="props"
              icon="mdi-delete"
              variant="plain"
              density="compact"
              :color="isActive ? 'error' : '' "
              :disabled="selectedLayerRepId === -1"
              @click="deleteRep()"
            />
          </template>
        </v-tooltip>
      </template>
      <template #item="{ props, item }">
        <v-list-item v-bind="props">
          <v-list-item-subtitle>
            <v-icon v-if="!item.raw.enabled" size="x-small" color="error">
              mdi-alert
            </v-icon>
            {{ item.raw.description }}
          </v-list-item-subtitle>
        </v-list-item>
      </template>
      <template v-if="proMode" #append>
        <v-tooltip text="Edit Representation" location="top">
          <template #activator="{ props, isActive }">
            <v-btn
              v-bind="props"
              icon="mdi-pencil"
              variant="plain"
              density="compact"
              :color="isActive ? 'warning' : '' "
              :disabled="selectedLayerRepId === -1"
              @click="editRep()"
            />
          </template>
        </v-tooltip>
        <v-tooltip text="Add Representation" location="top">
          <template #activator="{ props, isActive }">
            <v-btn
              v-bind="props"
              icon="mdi-plus-thick"
              variant="plain"
              density="compact"
              :color="isActive ? 'success' : '' "
              @click="addNewRep()"
            />
          </template>
        </v-tooltip>
      </template>
    </v-select>
  </v-row>
  <v-dialog v-model="addOrEdit" width="500">
    <v-card v-if="editingLayerRep">
      <v-card-title>
        {{ editingLayerRep.id ? `Edit ${editingLayerRep.name} Layer` : 'Add New Layer' }}
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-text-field v-model="editingLayerRep.name" label="Name" />
        </v-row>
        <v-row>
          <v-text-field v-model="editingLayerRep.description" label="Description" />
        </v-row>
        <v-row>
          <v-checkbox v-model="editingLayerRep.enabled" label="Enabled" />
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-row>
          <v-spacer />
          <v-btn color="error" class="mx-2" @click="addOrEdit = false; editingLayerRep = null">
            Cancel
          </v-btn>
          <v-btn color="success" class="mx-2" @click="saveEditingRep()">
            {{ editingLayerRep.id !== null ? 'Save' : 'Add' }}
          </v-btn>
        </v-row>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
</style>
