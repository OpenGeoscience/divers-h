<script lang="ts">
import {
  PropType,
  Ref, computed, defineComponent, onMounted, ref, watch,
} from 'vue';
import UVdatApi from '../../api/UVDATApi';
import { ContextWithIds, Dataset } from '../../types';
import { getCenterAndZoom } from '../../map/mapLayers';
import ContextMap from './ContextMap.vue';
import MapStore from '../../MapStore';

export default defineComponent({
  // eslint-disable-next-line vue/multi-word-component-names
  name: 'ContextEditor',
  components: { ContextMap },
  props: {
    selectedContextId: {
      type: Number as PropType<number | null>,
      default: null,
    },
    disableMap: { // We use a calculated area for the centering
      type: Boolean,
      default: true,
    },
  },
  emits: ['update-context', 'cancel'],
  setup(props, { emit }) {
    const datasetList: Ref<(Dataset & { connected: boolean })[]> = ref([]);
    const loading = ref(true);
    const search = ref('');

    const selectedContext: Ref<null | ContextWithIds> = ref(null);
    const baseName = ref('');
    const getDatasets = async () => {
      datasetList.value = (await MapStore.loadGlobalDatasets(
        { unconnected: false },
      )).map((item) => ({ ...item, connected: selectedContext.value?.datasets.includes(item.id) || false }));
    };

    const existingContextNames = computed(() => MapStore.availableContexts.value.map((item) => item.name));
    const validForm = ref(false);
    const customSearch = (
      value: string,
      query: string,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      item?: { raw?: Dataset & { connected: boolean } },
    ) => item?.raw?.name.toLowerCase().includes(query.toLowerCase()) || false;

    const datasetHeader = ref([
      { title: 'Selected', key: 'connected' },
      { title: 'Name', key: 'name' },
      { title: 'Category', key: 'category' },
      { title: 'Modified', key: 'modified' },
    ]);

    const formatDateTime = (input: string): string => {
    // Parse the input date string
      const date = new Date(input);

      // Extract the date components
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');

      // Combine them into the desired format
      return `${year}-${month}-${day} ${hours}:${minutes}`;
    };

    const modifyContext = (item: Dataset & { connected: boolean }) => {
      if (selectedContext.value) {
        if (item.connected) {
          // Remove Connection;
          const index = selectedContext.value.datasets.findIndex((datasetId) => (datasetId === item.id));
          if (index !== -1) {
            selectedContext.value.datasets.splice(index, 1);
          }
        } else if (!item.connected) {
          selectedContext.value.datasets.push(item.id);
        }
        // Update the dataset list
        datasetList.value = datasetList.value.map(
          (datasetListItem) => {
            if (selectedContext.value) {
              return {
                ...datasetListItem,
                connected: selectedContext.value.datasets.some((datasetId) => datasetId === datasetListItem.id),
              };
            }
            return { ...datasetListItem, connected: false };
          },
        );
      }
    };

    const updateMap = (data: { center: number[], zoom: number }) => {
      if (selectedContext.value) {
        selectedContext.value.default_map_center = data.center;
        selectedContext.value.default_map_zoom = data.zoom;
      }
    };

    const saveChanges = async () => {
      if (selectedContext.value && props.selectedContextId !== null) {
        await UVdatApi.patchContext(selectedContext.value.id, {
          name: selectedContext.value.name,
          datasets: selectedContext.value.datasets || [],
          default_map_center: selectedContext.value.default_map_center,
          default_map_zoom: selectedContext.value.default_map_zoom,
        });
        emit('update-context', props.selectedContextId);
      } else if (selectedContext.value && props.selectedContextId === null) {
        const newContext = await UVdatApi.addContext({
          name: selectedContext.value.name,
          datasets: selectedContext.value.datasets || [],
          default_map_center: selectedContext.value.default_map_center,
          default_map_zoom: selectedContext.value.default_map_zoom,
        });
        emit('update-context', newContext.id);
      }
    };

    onMounted(async () => {
      if (props.selectedContextId !== null) {
        selectedContext.value = await UVdatApi.getContext(props.selectedContextId);
        baseName.value = selectedContext.value.name;
      } else {
        const { center, zoom } = getCenterAndZoom();
        let newName = 'New Context Name';
        let index = 1;
        while (existingContextNames.value.includes(newName)) {
          newName = `New Context Name ${index}`;
          index += 1;
        }
        selectedContext.value = {
          id: -1,
          name: newName,
          default_map_center: center,
          default_map_zoom: zoom,
          datasets: [],
          created: '', // empty default val
          modified: '', // empty default val
          indicators: [], // emtpy default val
        };
      }
      await getDatasets();
      loading.value = false;
    });
    watch(() => props.selectedContextId, async () => {
      if (props.selectedContextId !== null) {
        selectedContext.value = await UVdatApi.getContext(props.selectedContextId);
      }
    });
    return {
      datasetHeader,
      datasetList,
      selectedContext,
      modifyContext,
      saveChanges,
      updateMap,
      loading,
      search,
      customSearch,
      formatDateTime,
      existingContextNames,
      validForm,
      baseName,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      <v-row>
        <v-spacer />
        Context Editor
        <v-spacer />
      </v-row>
    </v-card-title>
    <v-card-text>
      <div v-if="selectedContext" class="pt-5">
        <v-row>
          <v-col>
            <v-form v-model="validForm">
              <v-text-field
                v-model="selectedContext.name"
                :rules="[v => (!existingContextNames.includes(v) && v !== baseName) || 'Name must be Unique']"
                label="Name"
              />
            </v-form>
          </v-col>
          <v-col v-if="!disableMap">
            <context-map
              :zoom="selectedContext.default_map_zoom"
              :center="selectedContext.default_map_center"
              @update="updateMap($event)"
            />
          </v-col>
        </v-row>
      </div>
      <v-row
        v-if="!loading"
        dense
        class="mb-2"
      >
        <v-text-field
          v-model="search"
          label="Search"
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          hide-details
          single-line
        />
      </v-row>

      <v-row>
        <v-col>
          <v-row v-if="!loading">
            <v-data-table
              density="compact"
              :headers="datasetHeader"
              :items="datasetList"
              fixed-header
              :search="search"
              :custom-filter="customSearch"
              hide-default-footer
              :items-per-page="-1"
              height="350"
            >
              <template #[`item.connected`]="{ item }">
                <v-icon
                  :disabled="selectedContext === null"
                  @click="modifyContext(item)"
                >
                  {{
                    item.connected
                      ? "mdi-checkbox-marked"
                      : "mdi-checkbox-blank-outline"
                  }}
                </v-icon>
              </template>
              <template #[`item.modified`]="{ item }">
                <span> {{ formatDateTime(item.modified) }}</span>
              </template>
            </v-data-table>
          </v-row>
          <v-row v-else>
            <v-spacer />
            <v-progress-circular indeterminate :size="80" />
            <v-spacer />
          </v-row>
        </v-col>
      </v-row>
    </v-card-text>
    <v-card-actions>
      <v-row v-if="selectedContext !== null">
        <v-spacer />
        <v-btn color="" variant="outlined" class="mx-2" @click="$emit('cancel')">
          Cancel
        </v-btn>
        <v-btn color="success" :disabled="!validForm" variant="outlined" class="mx-2" @click="saveChanges()">
          {{ selectedContextId === null ? 'Add' : 'Save' }}
        </v-btn>
      </v-row>
    </v-card-actions>
  </v-card>
</template>

<style scoped>
.main-area {
  position: absolute;
  top: 65px;
  height: calc(100% - 70px);
  width: 100%;
}
.static-map-legend {
  position: absolute;
  top: 90px;
  right: 20px;
  max-height: calc(100% - 125px);
  z-index: 2;
  overflow-y: auto;
}
</style>
