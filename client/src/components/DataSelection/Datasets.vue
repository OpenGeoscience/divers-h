<script lang="ts">
import {
  Ref, computed, defineComponent, onMounted, ref,
  watch,
} from 'vue';
import MapStore from '../../MapStore';
import { Dataset } from '../../types';
import { toggleLayerSelection } from '../../map/mapLayers';
import UVdatApi from '../../api/UVDATApi';
import DatasetEditor from './DatasetEditor.vue';
import DatasetItem from './DatasetItem.vue';

export default defineComponent({
  components: {
    DatasetEditor,
    DatasetItem,
  },
  setup() {
    const datasets: Ref<(Dataset & { contextCount: number })[]> = ref([]);
    const datasetModDialog = ref(false);
    const selectedDatasetId: Ref<number | null> = ref(null);
    const unconnected = ref(false);
    const searchQuery = ref('');
    const filtersVisible = ref(false);
    const loadDatasets = async () => {
      datasets.value = await MapStore.loadGlobalDatasets({ unconnected: unconnected.value });
    };

    onMounted(async () => loadDatasets());
    const loadDataset = async (dataset: Dataset, force = false) => {
      await MapStore.loadLayers(dataset.id, force);
    };

    const filteredDatasets = computed(() => {
      const query = searchQuery.value.toLowerCase();
      return datasets.value.filter((dataset) => dataset.name.toLowerCase().includes(query));
    });

    watch(unconnected, () => {
      loadDatasets();
    });

    const updateNetCDFLayer = async (datasetId: number) => {
      await MapStore.loadLayers(datasetId, true);
    };

    const deleteConfirmDialog = ref(false);
    const deletionDataset: Ref<(Dataset & { contextCount: number }) | null> = ref(null);
    const deletionError = ref(''); // New ref to store error message
    const deletionMessage = ref('');

    const deleteDataset = (dataset: Dataset & { contextCount: number }) => {
      deleteConfirmDialog.value = true;
      deletionDataset.value = dataset;
      deletionError.value = '';
      if (dataset.contextCount > 0) {
        deletionMessage.value = `This Dataset is connected to ${dataset.contextCount} Scenarios`;
      }
    };

    const cancelDeletion = () => {
      deleteConfirmDialog.value = false;
      deletionDataset.value = null;
      deletionError.value = '';
      deletionMessage.value = '';
    };
    const confirmDeletion = async () => {
      if (deletionDataset.value) {
        try {
          await UVdatApi.deleteDataset(deletionDataset.value?.id);
          deleteConfirmDialog.value = false;
          deletionDataset.value = null;
          deletionMessage.value = '';
          loadDatasets();
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } catch (error: any) {
          if (error.response && error.response.status === 403) {
            deletionError.value = error.response.data?.detail || 'Forbidden: You do not have permission to delete this dataset.';
          } else {
            deletionError.value = 'An unexpected error occurred while deleting the dataset.';
          }
        }
      }
    };

    const addNewDataset = () => {
      datasetModDialog.value = true;
      selectedDatasetId.value = null;
    };

    const selectDatasetForEditing = (datasetId: number) => {
      datasetModDialog.value = true;
      selectedDatasetId.value = datasetId;
    };

    const updateDataset = (datasetId: number) => {
      datasetModDialog.value = true;
      selectedDatasetId.value = datasetId;
      loadDatasets();
    };

    const loadSelectedDatasetId = async (datasetId: number | null) => {
      if (datasetId !== null) {
        await loadDataset(datasets.value.find((dataset) => dataset.id === datasetId) as Dataset, true);
      }
    };
    return {
      datasets: filteredDatasets,
      layersByDataset: MapStore.mapLayersByDataset,
      selectedLayers: MapStore.selectedMapLayers,
      toggleLayerSelection,
      loadDataset,
      updateNetCDFLayer,
      searchQuery,
      filtersVisible,
      unconnected,
      deleteConfirmDialog,
      deletionDataset,
      deletionError,
      deletionMessage,
      deleteDataset,
      cancelDeletion,
      confirmDeletion,
      proMode: MapStore.proMode,
      datasetModDialog,
      selectedDatasetId,
      addNewDataset,
      selectDatasetForEditing,
      updateDataset,
      loadSelectedDatasetId,
    };
  },
});
</script>

<template>
  <div class="layer-browser">
    <div class="search-bar-container">
      <v-text-field
        v-model="searchQuery"
        label="Search datasets"
        prepend-icon="mdi-magnify"
        hide-details
        density="compact"
        class="pl-2 pt-2"
        style="max-width: 325px;"
      />
      <v-icon :color="filtersVisible ? 'primary' : ''" @click="filtersVisible = !filtersVisible">
        mdi-filter
      </v-icon>
      <v-tooltip
        v-if="proMode"
        text="Add New Dataset"
        location="top"
      >
        <template #activator="{ props }">
          <v-icon v-bind="props" color="success" @click="addNewDataset">
            mdi-plus-thick
          </v-icon>
        </template>
      </v-tooltip>
    </div>
    <div v-if="filtersVisible" class="filter-options">
      <v-tooltip
        text="Filter for Datasets not connected to Scenario"
        location="top"
      >
        <template #activator="{ props }">
          <v-checkbox
            v-model="unconnected"
            label="Unconnected"
            v-bind="props"
            hide-details
          />
        </template>
      </v-tooltip>
    </div>
    <v-list>
      <v-list-group
        v-for="dataset in datasets"
        :key="`${dataset.id}_${dataset.modified}`"
        :value="`dataset:${dataset.id}`"
        class="list-group"
      >
        <template #activator="{ props, isOpen }">
          <v-list-item
            v-bind="props"
            :title="dataset.name"
            @click="!isOpen && loadDataset(dataset)"
          >
            <v-tooltip
              :text="dataset.name"
              activator="parent"
              location="bottom"
              open-delay="1000"
            />
            <template #prepend="{ isOpen }">
              <div class="mr-3">
                <v-progress-circular
                  v-if="isOpen && !(dataset.id in layersByDataset)"
                  indeterminate
                  size="24"
                  width="3"
                />
                <v-icon v-else size="24">
                  mdi-database-outline
                </v-icon>
              </div>
            </template>
            <template #append="{ isOpen }">
              <div v-if="dataset.contextCount === 0 && proMode">
                <v-icon color="error" @click.stop="deleteDataset(dataset)">
                  mdi-delete
                </v-icon>
              </div>
              <div v-else-if="dataset.contextCount > 0 && proMode">
                <v-tooltip>
                  <template #activator="{ props }">
                    <v-icon color="error" v-bind="props" @click.stop="deleteDataset(dataset)">
                      mdi-delete-alert
                    </v-icon>
                  </template>
                  <span>Dataset is bound to {{ dataset.contextCount }} scenarios</span>
                </v-tooltip>
              </div>
              <div v-if="proMode">
                <v-icon color="warning" @click.stop="selectDatasetForEditing(dataset.id)">
                  mdi-pencil
                </v-icon>
              </div>
              <div class="ml-3">
                <v-icon v-if="isOpen">
                  mdi-chevron-up
                </v-icon>
                <v-icon v-else-if="!isOpen">
                  mdi-chevron-down
                </v-icon>
              </div>
            </template>
          </v-list-item>
        </template>
        <v-list-item
          v-for="layer in layersByDataset[dataset.id]"
          :key="layer.id"
        >
          <DatasetItem :layer="layer" @netcdf-deleted="updateNetCDFLayer(dataset.id)" />
        </v-list-item>
      </v-list-group>
    </v-list>
    <v-dialog v-if="deletionDataset" v-model="deleteConfirmDialog" width="400">
      <v-card>
        <v-card-title>Delete Dataset</v-card-title>
        <v-card-text>
          <div v-if="deletionError">
            {{ deletionError }}
          </div>
          <div v-else>
            <div>
              Would you like to delete the {{ deletionDataset.name }}?
            </div>
            <v-alert v-if="deletionMessage" type="warning">
              {{ deletionMessage }}
            </v-alert>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-row dense>
            <v-spacer />
            <v-btn class="mx-2" @click="cancelDeletion()">
              Cancel
            </v-btn>
            <v-btn v-if="!deletionError" color="error" class="mx-2" @click="confirmDeletion()">
              Delete
            </v-btn>
          </v-row>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
  <v-dialog v-model="datasetModDialog" width="800">
    <dataset-editor
      :editing-dataset-id="selectedDatasetId"
      @update-dataset="updateDataset($event)"
      @cancel="datasetModDialog = false"
      @update-map-layers="loadSelectedDatasetId(selectedDatasetId)"
    />
  </v-dialog>
</template>

<style scoped>
.list-group {
  /* reduce padding of nested groups */
  --list-indent-size: 0px;
  --prepend-width: 24px;
}

.layer-selection {
  height: 100%;
}

.layer-checkbox :deep(.v-checkbox-btn) {
  overflow: hidden;
}

.search-bar-container {
  display: flex;
  align-items: center;
}

.filter-options {
  margin: 10px;
  display: flex;
  flex-direction: column;
  border: 1px solid gray;
}
</style>
