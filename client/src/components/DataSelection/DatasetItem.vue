<script lang="ts">
import {
  PropType, defineComponent,
  onMounted,
  onUnmounted,
  ref,
} from 'vue';
import {
  FMVLayer, NetCDFData, RasterMapLayer, VectorMapLayer,
} from '../../types';
import { toggleLayerSelection } from '../../map/mapLayers';
import MapStore from '../../MapStore';
import NetCDFDataConfigurator from './NetCDFDataConfigurator.vue';

export default defineComponent({
  components: {
    NetCDFDataConfigurator,
  },
  props: {
    layer: {
      type: Object as PropType<RasterMapLayer | VectorMapLayer | NetCDFData | FMVLayer>,
      required: true,
    },
  },
  emits: ['netcdf-deleted'],
  setup(props) {
    let timeOutId: NodeJS.Timeout | null = null;
    const processing = ref(false);
    const checkProcessingTasks = async () => {
      const id = props.layer.dataset_id;
      if (id !== undefined) {
        processing.value = true;
        await MapStore.loadLayers(id, true);
        const layersByDataset = MapStore.mapLayersByDataset;
        const layers = layersByDataset[id];
        if (layers) {
          const currentLayer = layers.find((item) => item.id === props.layer.id && item.type === props.layer.type);
          if (currentLayer && currentLayer.processing_tasks) {
            timeOutId = setTimeout(checkProcessingTasks, 5000);
            return;
          }
        }
      }
      processing.value = false;
      if (timeOutId !== null) {
        clearTimeout(timeOutId);
        timeOutId = null;
      }
    };
    onMounted(async () => {
      if (props.layer.processing_tasks?.length) {
        // Processing is occuring so we need to refresh every few seconds
        processing.value = true;
        timeOutId = setTimeout(checkProcessingTasks, 5000);
      }
    });
    onUnmounted(() => {
      if (timeOutId !== null) {
        clearTimeout(timeOutId);
        timeOutId = null;
        processing.value = false;
      }
    });
    return {
      toggleLayerSelection,
      selectedLayers: MapStore.selectedMapLayers,
      processing,
      checkProcessingTasks,
    };
  },
});
</script>

<template>
  <v-checkbox
    v-if="layer.type === 'raster' || layer.type === 'vector' || layer.type === 'fmv'"
    :model-value="!!selectedLayers.find((item) => (item.id === layer.id))"
    class="layer-checkbox"
    density="compact"
    hide-details
    @change="toggleLayerSelection(layer)"
  >
    <template #label>
      <v-icon v-tooltip="layer.type === 'raster' ? 'Raster Layer' : 'Vector Layer'">
        {{ layer.type === 'raster' ? 'mdi-image-outline' : 'mdi-map-marker-outline' }}
      </v-icon>

      <span class="layer-checkbox-label">
        {{ layer.name }}
        <v-tooltip
          :text="layer.name"
          activator="parent"
          location="bottom"
          open-delay="1000"
        />
      </span>
    </template>
  </v-checkbox>
  <div v-else-if="layer.type === 'netcdf'">
    <NetCDFDataConfigurator
      :data="layer"
      :processing="processing"
      @deleted="$emit('netcdf-deleted', $event)"
      @generate-layer="checkProcessingTasks"
    />
  </div>
</template>

<style scoped>
.layer-checkbox-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

</style>
