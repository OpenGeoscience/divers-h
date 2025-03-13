<script lang="ts">
import {
  PropType, Ref, computed, defineComponent, ref,
} from 'vue';
import MapStore from '../MapStore';
import {
  LayerRepresentation, NetCDFLayer, RasterMapLayer, VectorMapLayer,
} from '../types';
import RasterLayerConfig from './RasterLayerConfig.vue';
import VectorLayerConfig from './VectorLayerConfig.vue';
import LayerRepresentationVue from './LayerRepresentation/LayerRepresentation.vue';
import UVdatApi from '../api/UVDATApi';
import { zoomToBounds } from '../map/mapLayers';
import NetCDFLayerConfig from './NetCDFLayerConfig.vue';

export default defineComponent({
  components: {
    RasterLayerConfig, VectorLayerConfig, LayerRepresentationVue, NetCDFLayerConfig,
  },
  props: {
    layer: {
      type: Object as PropType<(VectorMapLayer | RasterMapLayer | NetCDFLayer)>,
      required: true,
    },
  },
  emits: ['toggleLayer', 'deselectLayer'],
  setup(props) {
    const expanded = ref(false);
    const visibility = computed(() => MapStore.visibleMapLayers.value.has(`${props.layer.type}_${props.layer.id}`));
    const selectedLayerRep: Ref<LayerRepresentation> = ref({
      id: -1,
      layer_id: props.layer.id,
      type: props.layer.type,
      default_style: props.layer.default_style,
      name: 'Default',
      description: 'Basic Default Style for this Layer',
      enabled: true,
    });
    const save = () => {
      if (selectedLayerRep.value.id === -1) {
        if (props.layer.type === 'vector') {
          UVdatApi.patchVectorLayer(props.layer.id, props.layer.default_style);
        }
        if (props.layer.type === 'raster') {
          UVdatApi.patchRasterLayer(props.layer.id, props.layer.default_style);
        }
      } else {
        // We update the LayerRepresentation Style:
        UVdatApi.patchLayerRepresentation(
          selectedLayerRep.value.id,
          {
            ...selectedLayerRep.value,
            default_style: props.layer.default_style,
            type: props.layer.type,
            layer_id: props.layer.id,
          },
        );
      }
    };

    const setSelectedLayer = (layer: LayerRepresentation) => {
      selectedLayerRep.value = layer;
      const currentLayer = MapStore.selectedMapLayers.value.find(
        (item) => item.id === props.layer.id && item.type === props.layer.type,
      );
      if (currentLayer) {
        currentLayer.layerRepresentationId = layer.id;
      }
    };

    const zoomMapLayer = async () => {
      if (props.layer.type === 'raster') {
        const bounds = await UVdatApi.getRasterBbox(props.layer.id);
        zoomToBounds(bounds);
      } else if (props.layer.type === 'vector') {
        const bounds = await UVdatApi.getVectorBbox(props.layer.id);
        zoomToBounds(bounds);
      } else if (props.layer.type === 'netcdf') {
        const { bounds } = (props.layer as NetCDFLayer);
        zoomToBounds(bounds);
      }
    };
    return {
      expanded,
      visibility,
      save,
      setSelectedLayer,
      selectedLayerRep,
      proMode: MapStore.proMode,
      zoomMapLayer,
    };
  },
});
</script>

<template>
  <v-card variant="outlined">
    <v-row
      dense
      align="center"
      justify="center"
    >
      <v-col
        title="Drag"
        cols="1"
        class="handle"
      >
        <v-icon
          size="large"
        >
          mdi-format-align-justify
        </v-icon>
      </v-col>

      <v-col
        title="Deselect"
        cols="1"
      >
        <v-icon
          size="large"
          color="error"
          @click="$emit('deselectLayer')"
        >
          mdi-close
        </v-icon>
      </v-col>
      <v-col
        title="Toggle Visibility"
        cols="1"
      >
        <v-icon
          size="large"
          @click="$emit('toggleLayer', !visibility)"
        >
          {{
            visibility ? "mdi-checkbox-marked" : "mdi-checkbox-blank-outline"
          }}
        </v-icon>
      </v-col>
      <v-col
        :title="layer.name"
        style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis"
      >
        {{ layer.name }}
      </v-col>
      <v-col
        title="Reset Camera to Map Layer"
        cols="1"
      >
        <v-icon
          size="large"
          @click="zoomMapLayer()"
        >
          mdi-image-filter-center-focus
        </v-icon>
      </v-col>

      <v-col cols="2">
        <v-icon
          class="5"
          :disabled="!visibility"
          size="large"
          @click="expanded = !expanded"
        >
          {{ expanded ? "mdi-chevron-up" : "mdi-chevron-down" }}
        </v-icon>
      </v-col>
    </v-row>
    <v-card v-if="visibility && expanded">
      <layer-representation-vue
        v-if="['raster', 'vector'].includes(layer.type)"
        :layer-id="layer.id"
        @selected-layer="setSelectedLayer($event)"
      />
      <raster-layer-config v-if="proMode && layer.type === 'raster'" :layer="layer" />
      <vector-layer-config v-if="proMode && layer.type === 'vector'" :layer="layer" />
      <NetCDFLayerConfig
        v-if="layer.type === 'netcdf'"
        :layer="layer"
      />
      <v-card-actions v-if="proMode">
        <v-row dense>
          <v-spacer />
          <v-tooltip :text="`Save: ${selectedLayerRep.name}`" location="top">
            <template #activator="{ props }">
              <v-btn
                v-bind="props"
                color="success"
                @click="save()"
              >
                <v-icon>mdi-content-save</v-icon>
              </v-btn>
            </template>
          </v-tooltip>
        </v-row>
      </v-card-actions>
    </v-card>
  </v-card>
</template>

<style scoped>
.tab {
  border: 1px solid lightgray;
}

.tab:hover {
  cursor: pointer;
}

.selected-tab {
  background-color: lightgray;
}

.icon-center {
  width: 35px;
  height: 35px;
  border: 1px solid lightgray;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
