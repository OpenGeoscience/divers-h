<!-- eslint-disable vue/max-len -->
<script lang="ts">
import {
  PropType, computed, defineComponent, ref,
} from 'vue';
import MapStore from '../MapStore';
import {
  AnnotationTypes, ColorObjectDisplay, SizeTypeConfig, VectorLayerDisplayConfig, VectorMapLayer,
} from '../types';

import { updateLayer } from '../map/mapLayers';
import ColorSelector from './Coloring/ColorSelector.vue';
import SizingSelector from './Sizing/SizingSelector.vue';
import TextDisplayConfig from './Text/TextDisplayConfig.vue';
import { getLayerAvailableProperties, getVectorLayerDisplayConfig } from '../utils';
import HeatmapLayerControls from './Heatmap/HeatmapLayerControls.vue';

export default defineComponent({
  components: {
    ColorSelector,
    SizingSelector,
    TextDisplayConfig,
    HeatmapLayerControls,
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
    layerType: {
      type: String as PropType<AnnotationTypes>,
      required: true,
    },
  },
  setup(props) {
    const initializeConfig = () => {
      const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.layerId);
      if (found?.default_style?.layers) {
        const layerTypeVal = found?.default_style?.layers[props.layerType];
        if (layerTypeVal === undefined || layerTypeVal === false || layerTypeVal === true) {
          found.default_style.layers[props.layerType] = { enabled: !!layerTypeVal, color: '#888888' };
        }
      }
    };
    const currentLayerType = computed(() => {
      const { displayConfig } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      if (displayConfig !== false && displayConfig !== true) {
        return displayConfig;
      }
      return false;
    });
    const enabledComputed = computed(() => {
      const { enabled } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      return enabled;
    });

    type LayerActionItems = 'enabled' | 'selectable' | 'hoverable' | 'opacity' | 'zoomMinMax' | 'selectColor' | 'defaultSize' | 'color' | 'text' | 'heatmapControls';
    const layerActionItemsMap: Record<LayerActionItems, AnnotationTypes[]> = {
      enabled: ['line', 'fill', 'circle', 'fill-extrusion', 'text', 'heatmap'],
      selectable: ['line', 'fill', 'circle', 'fill-extrusion'],
      hoverable: ['line', 'fill', 'circle', 'fill-extrusion'],
      opacity: ['line', 'fill', 'circle', 'fill-extrusion', 'text', 'heatmap'],
      zoomMinMax: ['line', 'fill', 'circle', 'fill-extrusion', 'text', 'heatmap'],
      selectColor: ['line', 'fill', 'circle', 'fill-extrusion'],
      defaultSize: ['line', 'circle', 'text'],
      color: ['line', 'fill', 'circle', 'fill-extrusion', 'text'],
      text: ['text'],
      heatmapControls: ['heatmap'],
    };

    const actionItemVisible = computed(() => {
      const enabledItems = new Set<LayerActionItems>();
      const itemList: LayerActionItems[] = ['enabled', 'selectable', 'hoverable', 'opacity', 'zoomMinMax', 'selectColor', 'defaultSize', 'color', 'text', 'heatmapControls'];
      itemList.forEach((key) => {
        if (layerActionItemsMap[key].includes(props.layerType)) {
          enabledItems.add(key);
        }
      });
      return enabledItems;
    });

    const updateLayerTypeField = (field: keyof VectorLayerDisplayConfig | 'singleSelect', val: boolean) => {
      initializeConfig();
      const { layer, displayConfig } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      if (displayConfig !== false && displayConfig !== true) {
        if (field === 'enabled') {
          displayConfig.enabled = val;
        }
        if (field === 'selectable') {
          displayConfig.selectable = val;
        }
        if (field === 'singleSelect' && val) {
          displayConfig.selectable = 'singleSelect';
        }
        if (field === 'singleSelect' && !val) {
          displayConfig.selectable = true;
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

        if (field === 'selectColor') {
          if (!val) {
            delete displayConfig.selectColor;
          } else {
            displayConfig.selectColor = '#00FFFF';
          }
        }
        if (layer) {
          updateLayer(layer);
        }
      }
    };
    const updateOpacity = (val: number) => {
      const { layer, displayConfig } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      if (displayConfig !== false && displayConfig !== true) {
        displayConfig.opacity = val;
        if (layer) {
          updateLayer(layer);
        }
      }
    };
    const updateZoom = (val: [number, number]) => {
      const { layer, displayConfig } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      if (displayConfig !== false && displayConfig !== true) {
        displayConfig.zoom = { min: val[0], max: val[1] };
        if (layer) {
          updateLayer(layer);
        }
      }
    };
    const updateSelectColor = (field: keyof VectorLayerDisplayConfig, val: string) => {
      const { layer, displayConfig } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      if (displayConfig !== false && displayConfig !== true) {
        if (field === 'selectColor') {
          displayConfig.selectColor = val;
        }
        if (layer) {
          updateLayer(layer);
        }
      }
    };
    const colorPickerVisible = ref(false);
    const valueDisplayCheckbox = (field: keyof VectorLayerDisplayConfig | 'singleSelect') => {
      const { layer, displayConfig } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      if (!layer) {
        return false;
      }
      if (displayConfig === undefined) {
        return false;
      }
      if (displayConfig !== false && displayConfig !== true) {
        if (field === 'singleSelect') {
          return displayConfig.selectable === 'singleSelect';
        }
        if (field === 'enabled') {
          return (displayConfig[field] !== false);
        }
        return displayConfig[field] !== undefined && displayConfig[field] !== false;
      }
      if (field === 'enabled') {
        return displayConfig;
      }
      return false;
    };

    const getColorType = () => {
      if (currentLayerType.value) {
        if (typeof currentLayerType.value.color === 'string') {
          return 'Static Color';
        }
        return (currentLayerType.value.color as ColorObjectDisplay).type;
      }
      return 'noColor';
    };

    const getTextValue = () => {
      if (currentLayerType.value) {
        if (currentLayerType.value.text && currentLayerType.value.text.key) {
          const { key } = currentLayerType.value.text;
          const properties = getLayerAvailableProperties(props.layerId);
          if (properties[key]) {
            return properties[key].displayName;
          }
        } else {
          return 'noText';
        }
      }
      return 'noText';
    };
    const getSizeType = () => {
      if (currentLayerType.value && currentLayerType.value.size !== undefined) {
        if (typeof currentLayerType.value.size === 'number') {
          return 'Static Size';
        }
        return (currentLayerType.value.size as SizeTypeConfig).type;
      }
      return 'defaultSize';
    };
    const colorDisplayDialog = ref(false);
    const sizeDisplayDialog = ref(false);
    const textDisplayDialog = ref(false);

    const savedColors = computed(() => {
      const found = MapStore.selectedVectorMapLayers.value.find((item: VectorMapLayer) => item.id === props.layerId);
      if (found && found.default_style && found.default_style.savedColors?.length) {
        return found.default_style.savedColors;
      }
      return [];
    });

    const colorSaveChooser = ref(false);
    const savedColorChoice = ref('');
    const chooseSavedColor = (name: string) => {
      if (currentLayerType.value) {
        const found = MapStore.selectedVectorMapLayers.value.find((item: VectorMapLayer) => item.id === props.layerId);
        if (found && found.default_style && found.default_style.savedColors?.length) {
          const foundColorIndex = found.default_style.savedColors.findIndex((item) => item.name === name);
          if (foundColorIndex !== -1) {
            currentLayerType.value.color = found.default_style.savedColors[foundColorIndex].color;
            updateLayer(found);
          }
          colorSaveChooser.value = false;
          colorDisplayDialog.value = true;
        }
      }
    };
    return {
      currentLayerType,
      colorPickerVisible,
      enabledComputed,
      colorDisplayDialog,
      sizeDisplayDialog,
      textDisplayDialog,
      savedColors,
      updateSelectColor,
      valueDisplayCheckbox,
      updateLayerTypeField,
      getColorType,
      getSizeType,
      getTextValue,
      colorSaveChooser,
      savedColorChoice,
      chooseSavedColor,
      updateOpacity,
      updateZoom,
      actionItemVisible,
    };
  },
});
</script>

<template>
  <v-row
    v-if="actionItemVisible.has('enabled')"
    dense
    align="center"
    justify="center"
  >
    <v-col cols="2">
      <v-tooltip text="Enabled Feature Type">
        <template #activator="{ props }">
          <v-icon
            class="pl-3"
            v-bind="props"
          >
            mdi-shape
          </v-icon>
        </template>
      </v-tooltip>
    </v-col>
    <v-col>
      <v-icon
        @click="updateLayerTypeField('enabled', !valueDisplayCheckbox('enabled'))"
      >
        {{
          valueDisplayCheckbox('enabled') ? 'mdi-checkbox-marked'
          : 'mdi-checkbox-blank-outline' }}
      </v-icon>
      <span class="pl-2">Enabled</span>
    </v-col>
  </v-row>
  <v-row
    v-if="actionItemVisible.has('selectable')"
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
      <v-icon @click="updateLayerTypeField('selectable', !valueDisplayCheckbox('selectable'))">
        {{
          valueDisplayCheckbox('selectable') ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline' }}
      </v-icon>
      <span class="pl-2">Selectable</span>
      <span v-if="valueDisplayCheckbox('selectable')">
        <v-icon class="pl-4" @click="updateLayerTypeField('singleSelect', !valueDisplayCheckbox('singleSelect'))">
          {{
            valueDisplayCheckbox('singleSelect') ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline' }}
        </v-icon>
        <span class="pl-2">Single</span>
      </span>
    </v-col>
  </v-row>
  <v-row
    v-if="actionItemVisible.has('hoverable')"
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
      <v-icon @click="updateLayerTypeField('hoverable', !valueDisplayCheckbox('hoverable'))">
        {{
          valueDisplayCheckbox('hoverable') ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline' }}
      </v-icon>
      <span class="pl-2">Hoverable</span>
    </v-col>
  </v-row>
  <v-row
    v-if="actionItemVisible.has('opacity')"
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
    <v-col :cols="!valueDisplayCheckbox('opacity') ? '' : 3">
      <v-icon @click="updateLayerTypeField('opacity', !valueDisplayCheckbox('opacity'))">
        {{
          valueDisplayCheckbox('opacity') ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline' }}
      </v-icon>
      <span v-if="!valueDisplayCheckbox('opacity')" class="pl-2">Opacity</span>
      <span v-else class="pl-2" style="font-size:0.85em">{{ currentLayerType.opacity.toFixed(2) }}</span>
    </v-col>
    <v-col v-if="valueDisplayCheckbox('opacity') && currentLayerType && currentLayerType.opacity !== undefined">
      <v-slider
        density="compact"
        class="opacity-slider"
        min="0"
        max="1.0"
        :model-value="currentLayerType.opacity"
        @update:model-value="updateOpacity($event)"
      />
    </v-col>
  </v-row>
  <v-row
    v-if="actionItemVisible.has('zoomMinMax')"
    dense
    align="center"
    justify="center"
  >
    <v-col cols="2">
      <v-tooltip text="Zoom Min and Zoom max for displaying Feature Type">
        <template #activator="{ props }">
          <v-icon
            class="pl-3"
            v-bind="props"
          >
            mdi-magnify
          </v-icon>
        </template>
      </v-tooltip>
    </v-col>
    <v-col>
      <v-icon @click="updateLayerTypeField('zoom', !valueDisplayCheckbox('zoom'))">
        {{
          valueDisplayCheckbox('zoom') ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline' }}
      </v-icon>
      <span class="pl-2">Zoom Min/Max</span>
    </v-col>
    <v-col v-if="valueDisplayCheckbox('zoom') && currentLayerType && currentLayerType.zoom !== undefined">
      <v-range-slider
        density="compact"
        step="1"
        height="1"
        thumb-size="5"
        thumb-label="always"
        min="0"
        max="24"
        :model-value="[currentLayerType.zoom.min || 0, currentLayerType.zoom.max || 24]"
        @update:model-value="updateZoom($event)"
      />
    </v-col>
  </v-row>

  <v-row
    v-if="actionItemVisible.has('selectColor')"
    dense
    align="center"
    justify="center"
  >
    <v-col cols="2">
      <v-tooltip text="Selected Color">
        <template #activator="{ props }">
          <v-icon
            class="pl-3"
            v-bind="props"
          >
            mdi-format-color-highlight
          </v-icon>
        </template>
      </v-tooltip>
    </v-col>
    <v-col cols="8">
      <v-icon @click="updateLayerTypeField('selectColor', !valueDisplayCheckbox('selectColor'))">
        {{
          valueDisplayCheckbox('selectColor') ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline' }}
      </v-icon>
      <span class="pl-2">Select Color</span>
    </v-col>
    <v-col>
      <v-menu
        :close-on-content-click="false"
        offset-y
      >
        <template #activator="{ props }">
          <div
            v-if="currentLayerType && currentLayerType.selectColor"
            class="color-square"
            :style="{ backgroundColor: currentLayerType.selectColor }"
            v-bind="props"
          />
        </template>
        <v-color-picker
          v-if="currentLayerType"
          mode="hex"
          :model-value="currentLayerType.selectColor"
          @update:model-value="updateSelectColor('selectColor', $event)"
        />
      </v-menu>
    </v-col>
  </v-row>
  <v-row
    v-if="actionItemVisible.has('color')"
    dense
    align="center"
    justify="center"
  >
    <v-col cols="2">
      <v-tooltip text="Display Color">
        <template #activator="{ props }">
          <v-icon
            class="pl-3"
            v-bind="props"
          >
            mdi-brush
          </v-icon>
        </template>
      </v-tooltip>
    </v-col>
    <v-col v-if="savedColors.length">
      <v-tooltip text="Choose Saved Color">
        <template #activator="{ props }">
          <v-icon
            class="pl-3"
            v-bind="props"
            @click="colorSaveChooser = true"
          >
            mdi-palette
          </v-icon>
        </template>
      </v-tooltip>
    </v-col>
    <v-col cols="6">
      <span style="font-size: 0.75em"> {{ getColorType() }}</span>
    </v-col>
    <v-col>
      <v-tooltip text="Edit Color Display">
        <template #activator="{ props }">
          <v-icon
            class="pl-3"
            v-bind="props"
            @click="colorDisplayDialog = true"
          >
            mdi-pencil
          </v-icon>
        </template>
      </v-tooltip>
    </v-col>
  </v-row>
  <v-row
    v-if="actionItemVisible.has('defaultSize')"

    dense
    align="center"
    justify="center"
  >
    <v-col cols="2">
      <v-tooltip text="Size">
        <template #activator="{ props }">
          <v-icon
            class="pl-3"
            v-bind="props"
          >
            mdi-resize
          </v-icon>
        </template>
      </v-tooltip>
    </v-col>
    <v-col cols="6">
      <span style="font-size: 0.75em"> {{ getSizeType() }}</span>
    </v-col>
    <v-col>
      <v-tooltip text="Edit Size">
        <template #activator="{ props }">
          <v-icon
            class="pl-3"
            v-bind="props"
            @click="sizeDisplayDialog = true"
          >
            mdi-pencil
          </v-icon>
        </template>
      </v-tooltip>
    </v-col>
  </v-row>
  <v-row
    v-if="actionItemVisible.has('text')"
    dense
    align="center"
    justify="center"
  >
    <v-col cols="2">
      <v-tooltip text="Size">
        <template #activator="{ props }">
          <v-icon
            class="pl-3"
            v-bind="props"
          >
            mdi-format-title
          </v-icon>
        </template>
      </v-tooltip>
    </v-col>
    <v-col cols="6">
      <span style="font-size: 0.75em"> {{ getTextValue() }}</span>
    </v-col>
    <v-col>
      <v-tooltip text="Edit Size">
        <template #activator="{ props }">
          <v-icon
            class="pl-3"
            v-bind="props"
            @click="textDisplayDialog = true"
          >
            mdi-pencil
          </v-icon>
        </template>
      </v-tooltip>
    </v-col>
  </v-row>
  <div v-if="actionItemVisible.has('heatmapControls')">
    <heatmap-layer-controls :layer-id="layerId" :layer-type="layerType" />
  </div>
  <v-dialog
    v-model="colorSaveChooser"
    width="500"
  >
    <v-card>
      <v-card-title>Saved Color Profiles</v-card-title>
      <v-card-text>
        <p>Choose a presaved color profile</p>
        <v-select
          :model-value="savedColorChoice"
          :items="savedColors"
          item-value="name"
          item-title="name"
          label="Saved Color Profile"
          @update:model-value="chooseSavedColor($event)"
        >
          <template #item="{ props, item }">
            <v-list-item
              v-bind="props"
              :subtitle="item.raw.description"
            />
          </template>
        </v-select>
      </v-card-text>
    </v-card>
  </v-dialog>
  <v-dialog
    v-model="sizeDisplayDialog"
    width="500"
  >
    <v-card>
      <v-card-title>Size Display</v-card-title>
      <v-card-text>
        <sizing-selector
          :layer-id="layerId"
          :layer-type="layerType"
        />
      </v-card-text>
    </v-card>
  </v-dialog>
  <v-dialog
    v-model="colorDisplayDialog"
    width="500"
  >
    <v-card>
      <v-card-title>Color Display</v-card-title>
      <v-card-text>
        <color-selector
          :layer-id="layerId"
          :layer-type="layerType"
        />
      </v-card-text>
    </v-card>
  </v-dialog>
  <v-dialog
    v-model="textDisplayDialog"
    width="500"
  >
    <v-card>
      <v-card-title>Text Display</v-card-title>
      <v-card-text>
        <text-display-config
          :layer-id="layerId"
          :layer-type="layerType"
        />
      </v-card-text>
    </v-card>
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

.color-square {
    width: 15px;
    height: 15px;
    border: 1px solid #000;
    cursor: pointer;
}

.opacity-slider {
    height: 20px;
    margin-bottom: 15px;
}

</style>
