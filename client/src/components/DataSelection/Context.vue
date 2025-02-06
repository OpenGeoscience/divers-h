<script lang="ts">
import {
  Ref, computed, defineComponent, onMounted, ref,
} from 'vue';
import MapStore from '../../MapStore';
import {
  Context, Dataset,
} from '../../types';
import { centerAndZoom } from '../../map/mapVectorLayers';
import DatasetItem from './DatasetItem.vue';
import { toggleLayerSelection } from '../../map/mapLayers';
import ContextEditor from './ContextEditor.vue';
import UVdatApi from '../../api/UVDATApi';

export default defineComponent({
  components: {
    ContextEditor,
    DatasetItem,

  },
  setup() {
    const currentLevel: Ref<'Context' | 'Dataset' | 'Layer'> = ref('Context');
    const searchQuery = ref('');
    const loading = ref(false);
    const editingContext = ref(false);
    const selectedContextId: Ref<null | number> = ref(null);
    const deletionContext: Ref<Context | null> = ref(null);
    const deletionDialog = ref(false);
    const deletionError = ref('');
    const filteredContexts = computed(() => {
      const query = searchQuery.value.toLowerCase();
      return MapStore.availableContexts.value.filter((context) => context.name.toLowerCase().includes(query));
    });
    onMounted(async () => {
      loading.value = true;
      await MapStore.loadContexts();
      loading.value = false;
    });
    const focusMapToContext = async (context: Context) => {
      if (context.default_map_center) {
        centerAndZoom(context.default_map_center, context.default_map_zoom);
      }
    };
    const loadContext = async (context: Context) => {
      await MapStore.loadDatasets(context.id);
    };
    const loadDataset = async (dataset: Dataset) => {
      await MapStore.loadLayers(dataset.id);
    };
    const updateNetCDFLayer = async (datasetId: number) => {
      await MapStore.loadLayers(datasetId, true);
    };

    const jumpToLevel = (level: 'Context' | 'Dataset') => {
      currentLevel.value = level;
    };

    const selectedContext = computed(
      () => MapStore.availableContexts.value.find(
        (context) => context.id === MapStore.selectedContextId.value,
      ),
    );

    const onContextOpenOrClose = (context: Context, isOpen: boolean) => {
      if (isOpen) {
        if (selectedContext.value?.indicators.length && MapStore.activeSideBarCard.value === 'indicators') {
          MapStore.closeSideBar();
        }
        if (context.id === MapStore.selectedContextId.value) {
          MapStore.selectedContextId.value = null;
        }
      } else {
        MapStore.selectedContextId.value = context.id;
        loadContext(context);
      }
    };

    const editContext = (context: Context) => {
      selectedContextId.value = context.id;
      editingContext.value = true;
    };
    const deleteContext = async (context: Context) => {
      try {
        loading.value = true;
        await UVdatApi.deleteContext(context.id);
        await MapStore.loadContexts();
        loading.value = false;
        deletionContext.value = null;
        deletionDialog.value = false;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (error: any) {
        if (error.response && error.response.status === 403) {
          deletionError.value = error.response.data?.detail || 'Forbidden: You do not have permission to delete this dataset.';
        } else {
          deletionError.value = 'An unexpected error occurred while deleting the dataset.';
        }
      }
    };

    const setDeletionContext = (context: Context) => {
      deletionContext.value = context;
      deletionDialog.value = true;
    };

    const cancelDeletion = () => {
      deletionContext.value = null;
      deletionDialog.value = false;
    };

    const updateContext = async (contextId: number) => {
      loading.value = true;
      await MapStore.loadContexts();
      loading.value = false;
      selectedContextId.value = contextId;
      editingContext.value = false;
    };

    const addNewContext = () => {
      selectedContextId.value = null;
      editingContext.value = true;
    };

    const contextEditorExit = () => {
      editingContext.value = false;
    };

    return {
      currentLevel,
      filteredContexts,
      datasetsByContext: MapStore.datasetsByContext,
      layersByDataset: MapStore.mapLayersByDataset,
      selectedLayers: MapStore.selectedMapLayers,
      selectedContextId,
      proMode: MapStore.proMode,
      loadContext,
      focusMapToContext,
      loadDataset,
      jumpToLevel,
      toggleLayerSelection,
      onContextOpenOrClose,
      updateNetCDFLayer,
      searchQuery,
      addNewContext,
      editContext,
      editingContext,
      deletionDialog,
      deletionContext,
      setDeletionContext,
      cancelDeletion,
      deletionError,
      deleteContext,
      updateContext,
      contextEditorExit,
      loading,
    };
  },
});
</script>

<template>
  <div
    class="layer-browser"
  >
    <v-progress-linear
      v-if="loading"
      indeterminate
      color="primary"
      :height="5"
    />
    <div v-else style="height: 5px" />
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
      <v-tooltip
        v-if="proMode"
        text="Add New Context"
        location="top"
      >
        <template #activator="{ props }">
          <v-icon v-bind="props" color="success" @click="addNewContext">
            mdi-plus-thick
          </v-icon>
        </template>
      </v-tooltip>
    </div>
    <v-list>
      <v-list-group
        v-for="context in filteredContexts"
        :key="context.id"
        :value="`context:${context.id}`"
        class="list-group"
      >
        <template #activator="{ props, isOpen }">
          <v-list-item
            v-bind="props"
            :class="selectedContextId === context.id ? 'bg-light-blue-lighten-5' : null"
            @click="onContextOpenOrClose(context, isOpen)"
          >
            <div class="d-flex flex-row align-center">
              <span class="scenario-title">{{ context.name }}</span>
              <v-spacer />
              <v-btn icon variant="text" color="grey-darken-2" @click.stop="focusMapToContext(context)">
                <v-icon>mdi-image-filter-center-focus</v-icon>
                <v-tooltip activator="parent" text="Focus region" location="bottom" />
              </v-btn>
            </div>
            <v-tooltip
              :text="context.name"
              activator="parent"
              location="bottom"
              open-delay="1000"
            />
            <template #prepend="{ isOpen }">
              <div class="mr-3">
                <v-progress-circular
                  v-if="isOpen && !(context.id in datasetsByContext)"
                  indeterminate
                  size="24"
                  width="3"
                />
                <v-icon v-else size="24">
                  mdi-archive-outline
                </v-icon>
              </div>
            </template>
            <template #append="{ isOpen }">
              <div v-if="proMode">
                <v-icon color="error" @click.stop="setDeletionContext(context)">
                  mdi-delete
                </v-icon>
              </div>
              <div v-if="proMode">
                <v-icon color="warning" @click.stop="editContext(context)">
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
        <v-list-group
          v-for="dataset in datasetsByContext[context.id]"
          :key="dataset.id"
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
            </v-list-item>
          </template>
          <v-list-item
            v-for="layer in layersByDataset[dataset.id]"
            :key="layer.id"
          >
            <DatasetItem :layer="layer" @netcdf-deleted="updateNetCDFLayer(dataset.id)" />
          </v-list-item>
        </v-list-group>
      </v-list-group>
    </v-list>
    <v-dialog v-model="editingContext" width="600">
      <ContextEditor
        :selected-context-id="selectedContextId"
        @update-context="updateContext($event)"
        @cancel="contextEditorExit()"
      />
    </v-dialog>
    <v-dialog v-if="deletionContext" v-model="deletionDialog" width="400">
      <v-card>
        <v-card-title>Delete Context</v-card-title>
        <v-card-text>
          <div v-if="deletionError">
            {{ deletionError }}
          </div>
          <div v-else>
            <div>
              Would you like to delete the {{ deletionContext.name }}?
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-row dense>
            <v-spacer />
            <v-btn class="mx-2" @click="cancelDeletion()">
              Cancel
            </v-btn>
            <v-btn v-if="!deletionError" color="error" class="mx-2" @click="deleteContext(deletionContext)">
              Delete
            </v-btn>
          </v-row>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
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

.layer-checkbox-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.scenario-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.search-bar-container {
  display: flex;
  align-items: center;
}

</style>
