<!-- eslint-disable vue/max-len -->
<script lang="ts">
import {
  PropType, computed, defineComponent, ref, watch,
} from 'vue';
import MapStore from '../../MapStore';
import {
  AnnotationTypes,
  ColorObjectDisplay,
  VectorLayerDisplayConfig,
  VectorMapLayer,
} from '../../types';
import ColorCategoricalLinearNumber from './ColorCategoricalLinearNumber.vue';
import ColorCategoricalString from './ColorCategoricalString.vue';
import ColorBoolean from './ColorBoolean.vue';
import ColorAttributeValue from './ColorAttributeValue.vue';
import { updateLayer } from '../../map/mapLayers';
import { getLayerAvailableProperties, getVectorLayerDisplayConfig } from '../../utils';

export default defineComponent({
  components: {
    ColorCategoricalLinearNumber,
    ColorCategoricalString,
    ColorBoolean,
    ColorAttributeValue,
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
    const colorTypes = ref([
      {
        type: 'none',
        name: 'No Color',
        typeRequirements: [],
        description: 'Removes the color from being set',
      },

      {
        type: 'static',
        name: 'Solid Color',
        typeRequirements: [],
        description: 'Applies solid color to all items',
      },
      {
        type: 'ColorCategoricalString',
        name: 'Color Attribute Mapping',
        typeRequirements: ['string'],
        description:
          'Maps each attribute value to a color.  Requires a limited number of values so that the color mapping can be generated',
      },
      {
        type: 'ColorAttributeValue',
        name: 'Color Attribute Name Value',
        typeRequirements: ['string'],
        description:
          'Attempts to get a color from cascasing specified attributes.  Expects the attribute to have a string name color or hex code',
      },
      {
        type: 'ColorLinearNumber',
        name: 'Color Linear Scale',
        typeRequirements: ['number'],
        description:
          'Uses numerical values to generate a color scale that interpolates between the unmbers',
      },
      {
        type: 'ColorCategoricalNumber',
        name: 'Color Categorical Number',
        typeRequirements: ['number'],
        description:
          'Uses numerical values to generate distintive ranges of numbers that apply to a single color',
      },
      {
        type: 'ColorBoolean',
        name: 'Color Boolean',
        typeRequirements: ['bool'],
        description: 'Expectrs a true/false value and assigns colors to each of these values.',
      },
    ]);

    const initializeColor = () => {
      const found = MapStore.selectedVectorMapLayers.value.find((item: VectorMapLayer) => item.id === props.layerId);
      if (found?.default_style?.layers) {
        const layerTypeVal = found?.default_style?.layers[props.layerType];
        if (layerTypeVal !== false && layerTypeVal !== true) {
          if (layerTypeVal.color === undefined) {
            layerTypeVal.color = '#00FF00';
          }
        }
      }
    };
    initializeColor();
    const getLayerConfigColor = () => {
      const found = MapStore.selectedVectorMapLayers.value.find((item: VectorMapLayer) => item.id === props.layerId);
      if (found?.default_style?.layers) {
        const layerTypeVal = found?.default_style?.layers[props.layerType];
        if (layerTypeVal !== false && layerTypeVal !== true) {
          if (layerTypeVal.color === undefined) {
            layerTypeVal.color = '#00FF00';
          }
          return layerTypeVal.color;
        }
      }
      return '#00FF00';
    };
    const baseColorConfig = computed(() => getLayerConfigColor());
    const selectedColorType = ref(
      typeof baseColorConfig.value === 'string'
        ? 'static'
        : (baseColorConfig.value as ColorObjectDisplay).type,
    );

    watch(selectedColorType, () => {
      if (selectedColorType.value === 'static') {
        const { layer } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
        if (layer?.default_style?.layers && layer.default_style.layers[props.layerType]) {
          if (
            layer.default_style.layers[props.layerType] !== false
            && layer.default_style.layers[props.layerType] !== true
          ) {
            (layer.default_style.layers[props.layerType] as VectorLayerDisplayConfig).color = '#888888';
            (layer.default_style.layers[props.layerType] as VectorLayerDisplayConfig).legend = false;
          }
        }
      } else {
        const { layer } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
        if (layer?.default_style?.layers && layer.default_style.layers[props.layerType]) {
          if (
            layer.default_style.layers[props.layerType] !== false
            && layer.default_style.layers[props.layerType] !== true
          ) {
            (layer.default_style.layers[props.layerType] as VectorLayerDisplayConfig).legend = true;
          }
        }
      }
    });

    const updateStaticColor = (color: string) => {
      const { layer } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      if (layer?.default_style?.layers && layer.default_style.layers[props.layerType]) {
        if (
          layer.default_style.layers[props.layerType] !== false
          && layer.default_style.layers[props.layerType] !== true
        ) {
          (layer.default_style.layers[props.layerType] as VectorLayerDisplayConfig).color = color;
          updateLayer(layer);
        }
      }
    };
    const propTypes = computed(() => {
      const properties = getLayerAvailableProperties(props.layerId);
      const types = new Set<string>();
      Object.values(properties).forEach((property) => {
        types.add(property.type);
      });
      return types;
    });

    const computedColorTypes = computed(() => colorTypes.value.filter((colorType) => {
      const { typeRequirements } = colorType;
      if (!typeRequirements.length) {
        return true;
      }
      for (let i = 0; i < typeRequirements.length; i += 1) {
        if (propTypes.value.has(typeRequirements[i])) {
          return true;
        }
      }
      return false;
    }));

    return {
      selectedColorType,
      baseColorConfig,
      colorTypes,
      updateStaticColor,
      computedColorTypes,
    };
  },
});
</script>

<template>
  <v-row
    dense
    align="center"
    justify="center"
  >
    <v-select
      v-model="selectedColorType"
      :items="computedColorTypes"
      item-value="type"
      item-title="name"
      label="Color Type"
    >
      <template #item="{ props, item }">
        <v-list-item
          v-bind="props"
          :subtitle="item.raw.description"
        />
      </template>
    </v-select>
  </v-row>
  <v-row v-if="selectedColorType === 'static'">
    <v-col>
      <h3>Select Static Color:</h3>
    </v-col>
    <v-col>
      <v-menu
        :close-on-content-click="false"
        offset-y
      >
        <template #activator="{ props }">
          <div
            class="color-square"
            :style="{ backgroundColor: baseColorConfig }"
            v-bind="props"
          />
        </template>
        <v-color-picker
          mode="hex"
          :model-value="baseColorConfig"
          @update:model-value="updateStaticColor($event)"
        />
      </v-menu>
    </v-col>
  </v-row>
  <div v-if="['ColorCategoricalNumber', 'ColorLinearNumber'].includes(selectedColorType)">
    <ColorCategoricalLinearNumber
      :layer-id="layerId"
      :layer-type="layerType"
      :color-type="selectedColorType"
    />
  </div>
  <div v-if="'ColorCategoricalString' === selectedColorType">
    <ColorCategoricalString
      :layer-id="layerId"
      :layer-type="layerType"
      :color-type="selectedColorType"
    />
  </div>
  <div v-if="'ColorBoolean' === selectedColorType">
    <ColorBoolean
      :layer-id="layerId"
      :layer-type="layerType"
      :color-type="selectedColorType"
    />
  </div>
  <div v-if="'ColorAttributeValue' === selectedColorType">
    <ColorAttributeValue
      :layer-id="layerId"
      :layer-type="layerType"
      :color-type="selectedColorType"
    />
  </div>
</template>

<style scoped>
.color-square {
  width: 25px;
  height: 25px;
  border: 1px solid #000;
  cursor: pointer;
}
</style>
