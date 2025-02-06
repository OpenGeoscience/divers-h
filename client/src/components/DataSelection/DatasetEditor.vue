<script lang="ts">
import {
  PropType,
  Ref, defineComponent, onMounted, onUnmounted, ref,
} from 'vue';
import UploadFile from './UploadFile.vue';
import UVdatApi from '../../api/UVDATApi';
import {
  AbstractMapLayer,
  FileItem, RasterMapLayer, VectorMapLayer,
} from '../../types';

export default defineComponent({
  name: 'DatasetModification',
  components: {
    UploadFile,
  },
  props: {
    editingDatasetId: {
      type: Number as PropType<number | null>,
      default: null,
    },
  },
  emits: ['update-dataset', 'update-map-layers', 'cancel'],
  setup(props, { emit }) {
    const datasetName = ref('New Dataset Name');
    const datasetDescription = ref('Dataset Description');
    const datasetCategory = ref('Category');
    const mapLayerList: Ref<(VectorMapLayer | RasterMapLayer)[]> = ref([]);
    const mapLayerHeaders = ref([
      { title: 'Name', key: 'name', width: 200 },
      { title: 'Type', key: 'type' },
      { title: 'Created', key: 'created' },
      { title: 'Actions', value: 'actions' },
    ]);

    const fileItemList: Ref<(FileItem & { edited?: boolean })[]> = ref([]);
    const fileItemHeaders = ref([
      { title: 'Name', key: 'name', width: 200 },
      { title: 'Type', key: 'file_type' },
      { title: 'Created', key: 'created' },
      { title: 'Status', value: 'status' },
      { title: 'Actions', value: 'actions' },
    ]);
    const deleteDialog = ref(false);
    const deleteData: Ref<{ type: 'file' | 'layer', itemId:number } | null> = ref(null);
    const updateDatasetEnabled = ref(false);
    let timeOutId: NodeJS.Timeout | null = null;
    const editingName: Ref<null | { name: string, id: number; type: (AbstractMapLayer['type'] | 'file') }> = ref(null);
    const checkRunningTasks = async () => {
      if (props.editingDatasetId) {
        fileItemList.value = (await UVdatApi.getDatasetFiles(props.editingDatasetId)).map(
          (subItem) => ({ ...subItem, edited: false }),
        );
      }
      const runningFileProcessingTask = fileItemList.value.some(
        (item) => item.processing_tasks?.length && item.processing_tasks?.some(
          (task) => ['Running', 'Queued'].includes(task.status) && task.metadata.type === 'file processing',
        ),
      );
      if (runningFileProcessingTask) {
        timeOutId = setTimeout(checkRunningTasks, 5000);
      } else if (props.editingDatasetId !== null) {
        timeOutId = null;
        mapLayerList.value = await UVdatApi.getDatasetLayers(props.editingDatasetId);
        emit('update-map-layers');
      }
    };
    const getDatasetInfo = async () => {
      if (props.editingDatasetId !== null) {
        const data = await UVdatApi.getDataset(props.editingDatasetId);
        datasetName.value = data.name;
        datasetDescription.value = data.description;
        datasetCategory.value = data.category;
        mapLayerList.value = await UVdatApi.getDatasetLayers(props.editingDatasetId);
        checkRunningTasks();
      }
    };

    onMounted(() => {
      getDatasetInfo();
    });
    onUnmounted(() => {
      if (timeOutId) {
        clearTimeout(timeOutId);
      }
    });

    const addNewDataset = async () => {
      const data = {
        name: datasetName.value,
        category: datasetCategory.value,
        description: datasetDescription.value,
        metadata: {},
      };
      const result = await UVdatApi.addDataset(data);
      emit('update-dataset', result.id);
    };

    const deleteLayer = async (item: VectorMapLayer | RasterMapLayer) => {
      await UVdatApi.deleteLayer(item.id, item.type);
      if (props.editingDatasetId !== null) {
        fileItemList.value = (await UVdatApi.getDatasetFiles(props.editingDatasetId)).map(
          (subItem) => ({ ...subItem, edited: false }),
        );
        mapLayerList.value = await UVdatApi.getDatasetLayers(props.editingDatasetId);
        emit('update-map-layers', mapLayerList.value);
      }
    };

    const deleteFile = async (item: FileItem) => {
      await UVdatApi.deleteFileItem(item.id);
      if (props.editingDatasetId !== null) {
        fileItemList.value = (await UVdatApi.getDatasetFiles(props.editingDatasetId)).map(
          (subItem) => ({ ...subItem, edited: false }),
        );
        mapLayerList.value = await UVdatApi.getDatasetLayers(props.editingDatasetId);
      }
    };

    const downloadItem = (item: FileItem) => {
      const link = document.createElement('a');
      link.href = item.file;
      link.download = `${item.name}.${item.file_type}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    };

    const finalizeUpload = async (
      { result, name } : { result: string, name: string },
    ) => {
      if (props.editingDatasetId !== null) {
        await UVdatApi.postFileItem(
          name,
          {},
          0,
          props.editingDatasetId,
          result,
        );
        checkRunningTasks();
      }
    };

    const showDeleteDialog = (item: { type: 'file' | 'layer', itemId:number }) => {
      deleteData.value = item;
      deleteDialog.value = true;
    };

    const confirmDelete = () => {
      if (deleteData.value !== null) {
        if (deleteData.value.type === 'file') {
          const deleteItem = fileItemList.value.find((item) => item.id === deleteData.value?.itemId);
          if (deleteItem) {
            deleteFile(deleteItem);
          }
        } else {
          const deleteItem = mapLayerList.value.find((item) => item.id === deleteData.value?.itemId);
          if (deleteItem) {
            deleteLayer(deleteItem);
          }
        }
        deleteDialog.value = false;
        deleteData.value = null;
      }
    };

    const changedDatasetData = () => {
      if (props.editingDatasetId !== null) {
        updateDatasetEnabled.value = true;
      }
    };

    const updateDataset = async () => {
      if (props.editingDatasetId !== null) {
        updateDatasetEnabled.value = false;
        await UVdatApi.updateDataset(props.editingDatasetId, datasetName.value, datasetCategory.value, datasetDescription.value);
        emit('update-dataset', props.editingDatasetId);
      }
    };

    const updateFileItem = async (fileItemId: number, name: string) => {
      if (props.editingDatasetId !== null) {
        await UVdatApi.updateFileItem(fileItemId, name);
        await getDatasetInfo();
      }
    };

    const updateMapLayerName = async (layerId: number, type: AbstractMapLayer['type'], name: string) => {
      if (props.editingDatasetId !== null) {
        await UVdatApi.updateMapLayerName(layerId, type, name);
      }
      emit('update-map-layers');
    };

    const editName = (id: number, name: string, type: (AbstractMapLayer['type'] | 'file')) => {
      editingName.value = {
        id,
        name,
        type,
      };
    };
    const updateEditingName = () => {
      if (editingName.value !== null) {
        if (editingName.value.type === 'file') {
          updateFileItem(editingName.value.id, editingName.value.name);
        } else {
          updateMapLayerName(editingName.value.id, editingName.value.type, editingName.value.name);
        }
      }
    };

    return {
      datasetName,
      datasetDescription,
      datasetCategory,
      mapLayerList,
      mapLayerHeaders,
      fileItemList,
      fileItemHeaders,
      addNewDataset,
      downloadItem,
      finalizeUpload,
      showDeleteDialog,
      confirmDelete,
      deleteDialog,
      updateDatasetEnabled,
      changedDatasetData,
      updateDataset,
      editName,
      editingName,
      updateEditingName,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      <v-row v-if="editingDatasetId !== null">
        <v-spacer />
        <div>
          Editing {{ datasetName }}
        </div>
        <v-spacer />
      </v-row>
      <v-row v-else>
        <v-spacer />
        <div>
          Add New Dataset
        </div>
        <v-spacer />
      </v-row>
    </v-card-title>
    <v-card-text>
      <v-expansion-panels :model-value="editingDatasetId !== null ? [] : [0]">
        <v-expansion-panel title="Dataset Information">
          <v-expansion-panel-text>
            <v-row>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="datasetName"
                  label="Dataset Name"
                  @update:model-value="changedDatasetData"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="datasetCategory"
                  label="Category"
                  @update:model-value="changedDatasetData"
                />
              </v-col>
              <v-col cols="12">
                <v-textarea
                  v-model="datasetDescription"
                  label="Description"
                  @update:model-value="changedDatasetData"
                />
              </v-col>
            </v-row>
            <v-row v-if="editingDatasetId === null">
              <v-spacer />
              <v-btn
                color="success"
                @click="addNewDataset"
              >
                Create
              </v-btn>
            </v-row>
            <v-row v-else>
              <v-spacer />
              <v-btn
                :disabled="!updateDatasetEnabled"
                color="primary"
                @click="updateDataset"
              >
                Update
              </v-btn>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
      <div v-if="editingDatasetId !== null" class="pt-5">
        <v-row>
          <v-col cols="12">
            <v-data-table
              :headers="fileItemHeaders"
              :items="fileItemList"
              item-key="id"
              class="elevation-1"
            >
              <template #top>
                <v-toolbar flat>
                  <v-toolbar-title>Files</v-toolbar-title>
                  <v-divider class="mx-4" inset vertical />
                  <v-spacer />
                  <upload-file @upload="finalizeUpload($event)" />
                </v-toolbar>
              </template>
              <template #[`item.name`]="{ item }">
                <v-text-field
                  v-if="editingName !== null && editingName.id === item.id && editingName.type === 'file'"
                  v-model="editingName.name"
                  density="compact"
                  @update:focused="updateEditingName"
                />
                <span
                  v-else
                >
                  <span>{{ item.name }} </span>
                  <v-icon color="warning" class="ml-2" @click="editName(item.id, item.name, 'file')">mdi-pencil</v-icon>
                </span>
              </template>

              <template #[`item.actions`]="{ item }">
                <v-icon @click="downloadItem(item)">
                  mdi-download
                </v-icon>
                <v-icon color="error" @click="showDeleteDialog({ type: 'file', itemId: item.id })">
                  mdi-delete
                </v-icon>
              </template>
              <template #[`item.status`]="{ item }">
                <v-chip
                  v-if="item.processing_tasks && item.processing_tasks.length && item.processing_tasks[0].status === 'Running'"
                  color="warning"
                >
                  Processing <v-icon>mdi-sync mdi-spin</v-icon>
                </v-chip>
                <v-chip
                  v-else-if="item.processing_tasks
                    && item.processing_tasks.length && item.processing_tasks[0].status === 'Queued'"
                  color="gray"
                >
                  Queued
                </v-chip>
                <v-tooltip
                  v-else-if="item.processing_tasks && item.processing_tasks.length && item.processing_tasks[0].status === 'Error'"
                >
                  <template #activator="{ props }">
                    <v-chip
                      v-bind="props"
                      color="error"
                    >
                      Error <v-icon>mdi-alert-circle</v-icon>
                    </v-chip>
                  </template>
                  <v-alert
                    color="error"
                    title="File Item Processing Error"
                    icon="$error"
                    :text="item.processing_tasks[0].error"
                    dense
                  />
                </v-tooltip>
                <v-chip
                  v-else
                  color="success"
                >
                  Complete
                </v-chip>
              </template>
            </v-data-table>
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="12">
            <v-data-table
              :headers="mapLayerHeaders"
              :items="mapLayerList"
              item-key="id"
              class="elevation-1"
            >
              <template #top>
                <v-toolbar flat>
                  <v-toolbar-title>Map Layers</v-toolbar-title>
                </v-toolbar>
              </template>
              <template #[`item.name`]="{ item }">
                <v-text-field
                  v-if="editingName !== null && editingName.id === item.id && editingName.type === item.type"
                  v-model="editingName.name"
                  density="compact"
                  @update:focused="updateEditingName"
                />
                <span
                  v-else
                >
                  <span>{{ item.name }} </span>
                  <v-icon color="warning" class="ml-2" @click="editName(item.id, item.name, item.type)">mdi-pencil</v-icon>
                </span>
              </template>
              <template #[`item.actions`]="{ item }">
                <v-icon color="error" @click="showDeleteDialog({ type: 'layer', itemId: item.id })">
                  mdi-delete
                </v-icon>
              </template>
            </v-data-table>
          </v-col>
        </v-row>
      </div>
    </v-card-text>
    <v-card-actions>
      <v-row dense>
        <v-spacer />
        <v-btn color="" variant="outlined" class="mx-4" @click="$emit('cancel')">
          Cancel
        </v-btn>
      </v-row>
    </v-card-actions>
    <v-dialog v-model="deleteDialog" max-width="500">
      <v-card>
        <v-card-title class="headline">
          Confirm Deletion
        </v-card-title>
        <v-card-text>Are you sure you want to delete this dataset?</v-card-text>
        <v-card-actions>
          <v-row>
            <v-spacer />
            <v-btn
              class="mx-2"
              @click="deleteDialog = false"
            >
              Cancel
            </v-btn>
            <v-btn
              color="error"
              class="mx-2"
              @click="confirmDelete()"
            >
              Delete
            </v-btn>
          </v-row>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>
