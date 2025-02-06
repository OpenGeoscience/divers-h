<script lang="ts">
import {
  PropType, Ref, computed, defineComponent, onMounted, ref,
} from 'vue';
import MapStore from '../MapStore';
import { AnnotationTypes, RasterMapLayer } from '../types';
import { getRasterLayerDisplayConfig } from '../utils';
import { updateLayer } from '../map/mapLayers';
import LargeImageStyle from './Raster/LargeImageStyle.vue';
import { autoMinMax } from '../map/mapRasterLayers';

export default defineComponent({
  components: { LargeImageStyle },
  props: {
    layer: {
      type: Object as PropType<RasterMapLayer>,
      required: true,
    },
  },
  emits: ['toggleLayer', 'deselectLayer'],
  setup(props) {
    const tab: Ref<AnnotationTypes | 'properties' | 'filters'> = ref('line');
    onMounted(() => {
      const found = MapStore.selectedRasterMapLayers.value.find(
        (item: RasterMapLayer) => item.id === props.layer.id,
      );
      if (found && !found?.default_style) {
        found.default_style = {
          selectable: false,
          hoverable: false,
        };
      }
    });

    const currentDisplayConfig = computed(
      () => getRasterLayerDisplayConfig(props.layer.id).displayConfig,
    );

    const updateLayerTypeField = (
      field: 'selectable' | 'hoverable' | 'opacity' | 'zoom',
      val: boolean,
    ) => {
      const { layer, displayConfig } = getRasterLayerDisplayConfig(
        props.layer.id,
      );
      if (displayConfig) {
        if (field === 'selectable') {
          displayConfig.selectable = val;
        }
        if (field === 'hoverable') {
          displayConfig.hoverable = val;
        }
        if (field === 'opacity') {
          if (val) {
            displayConfig.opacity = 0.75;
          } else {
            delete displayConfig.opacity;
          }
        }
        if (field === 'zoom') {
          if (val) {
            displayConfig.zoom = { min: 0, max: 24 };
          } else {
            delete displayConfig.zoom;
          }
        }

        if (layer) {
          updateLayer(layer);
        }
      }
    };

    const valueDisplayCheckbox = (
      field: 'selectable' | 'hoverable' | 'opacity' | 'zoom',
    ) => {
      const { layer, displayConfig } = getRasterLayerDisplayConfig(
        props.layer.id,
      );
      if (!layer) {
        return false;
      }
      if (displayConfig) {
        if (field === 'opacity') {
          if (displayConfig[field] !== undefined) {
            return true;
          }
        }
        return !!displayConfig[field];
      }
      if (displayConfig === undefined) {
        return false;
      }
      return false;
    };
    const updateOpacity = (val: number) => {
      const { layer, displayConfig } = getRasterLayerDisplayConfig(
        props.layer.id,
      );
      if (displayConfig) {
        displayConfig.opacity = val;
        if (layer) {
          updateLayer(layer);
        }
      }
    };

    const updateZoom = (val: [number, number]) => {
      const { layer, displayConfig } = getRasterLayerDisplayConfig(
        props.layer.id,
      );
      if (displayConfig) {
        displayConfig.zoom = { min: val[0], max: val[1] };
        if (layer) {
          updateLayer(layer);
        }
      }
    };

    const bandEditor = ref(false);

    const styleParmas = computed(() => {
      const { displayConfig } = getRasterLayerDisplayConfig(props.layer.id);
      if (displayConfig) {
        if (displayConfig.largeImageStyle) {
          return displayConfig.largeImageStyle;
        }
      }
      return {};
    });

    const autoCalcMinMax = () => {
      autoMinMax(props.layer);
    };
    return {
      tab,
      currentDisplayConfig,
      autoCalcMinMax,
      valueDisplayCheckbox,
      updateLayerTypeField,
      updateZoom,
      updateOpacity,
      bandEditor,
      styleParmas,
    };
  },
});
</script>

<template>
  <v-card-title />
  <v-card-text>
    <v-row
      dense
      align="center"
      justify="center"
    >
      <v-col cols="2">
        <v-tooltip text="Selectable">
          <template #activator="{ props }">
            <v-icon
              class="pl-3"
              v-bind="props"
            >
              mdi-mouse-left-click
            </v-icon>
          </template>
        </v-tooltip>
      </v-col>
      <v-col>
        <v-icon
          @click="
            updateLayerTypeField(
              'selectable',
              !valueDisplayCheckbox('selectable'),
            )
          "
        >
          {{
            valueDisplayCheckbox("selectable")
              ? "mdi-checkbox-marked"
              : "mdi-checkbox-blank-outline"
          }}
        </v-icon>
        <span class="pl-2">Selectable</span>
      </v-col>
    </v-row>
    <v-row
      dense
      align="center"
      justify="center"
    >
      <v-col cols="2">
        <v-tooltip text="Hoverable (Tooltip)">
          <template #activator="{ props }">
            <v-icon
              class="pl-3"
              v-bind="props"
            >
              mdi-tooltip-text-outline
            </v-icon>
          </template>
        </v-tooltip>
      </v-col>
      <v-col>
        <v-icon
          @click="
            updateLayerTypeField(
              'hoverable',
              !valueDisplayCheckbox('hoverable'),
            )
          "
        >
          {{
            valueDisplayCheckbox("hoverable")
              ? "mdi-checkbox-marked"
              : "mdi-checkbox-blank-outline"
          }}
        </v-icon>
        <span class="pl-2">Hoverable</span>
      </v-col>
    </v-row>
    <v-row
      dense
      align="center"
      justify="center"
    >
      <v-col cols="2">
        <v-tooltip text="Opacity">
          <template #activator="{ props }">
            <v-icon
              class="pl-3"
              v-bind="props"
            >
              mdi-square-opacity
            </v-icon>
          </template>
        </v-tooltip>
      </v-col>
      <v-col>
        <v-icon
          @click="
            updateLayerTypeField(
              'opacity',
              !valueDisplayCheckbox('opacity'),
            )
          "
        >
          {{
            valueDisplayCheckbox("opacity")
              ? "mdi-checkbox-marked"
              : "mdi-checkbox-blank-outline"
          }}
        </v-icon>
        <span class="pl-2">Opacity
          {{
            currentDisplayConfig && currentDisplayConfig.opacity
              ? currentDisplayConfig.opacity.toFixed(2)
              : ""
          }}</span>
      </v-col>
      <v-col
        v-if="
          valueDisplayCheckbox('opacity')
            && currentDisplayConfig
            && currentDisplayConfig.opacity !== undefined
        "
      >
        <v-slider
          density="compact"
          min="0"
          max="1.0"
          :model-value="currentDisplayConfig.opacity"
          @update:model-value="updateOpacity($event)"
        />
      </v-col>
    </v-row>
    <v-row
      dense
      align="center"
      justify="center"
    >
      <v-col cols="2">
        <v-tooltip text="Layer Style Editor">
          <template #activator="{ props }">
            <v-icon
              class="pl-3"
              v-bind="props"
            >
              mdi-layers
            </v-icon>
          </template>
        </v-tooltip>
      </v-col>
      <v-col>
        <span class="pl-2">Layer Styles</span>
      </v-col>
      <v-col cols="2">
        <v-tooltip text="Calculate Min/Max">
          <template #activator="{ props }">
            <v-icon
              class="pl-3"
              v-bind="props"
              @click="autoCalcMinMax()"
            >
              mdi-calculator
            </v-icon>
          </template>
        </v-tooltip>
      </v-col>
      <v-col cols="2">
        <v-icon @click="bandEditor = true">
          mdi-cog
        </v-icon>
      </v-col>
    </v-row>
  </v-card-text>
  <v-dialog
    v-model="bandEditor"
    width="1200"
  >
    <large-image-style
      :layer-id="layer.id"
      :style-params="styleParmas"
    />
  </v-dialog>
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
