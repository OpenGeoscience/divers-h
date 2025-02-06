<script lang="ts">
import {
  PropType, Ref, computed, defineComponent, ref,
} from 'vue';
import { cloneDeep } from 'lodash';
import MapStore from '../../MapStore';
import {
  AnnotationTypes,
  ColorCategoricalString,
  VectorLayerDisplayConfig,
} from '../../types';

import { updateLayer } from '../../map/mapLayers';
import { colorGenerator } from '../../map/mapColors';
import ColorSaver from './ColorSaver.vue';
import { getLayerAvailableProperties, getVectorLayerDisplayConfig } from '../../utils';

export default defineComponent({
  components: {
    ColorSaver,
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
    colorType: {
      type: String as PropType<'ColorCategoricalString'>,
      required: true,
    },
  },
  setup(props) {
    const propertyListing = computed(() => {
      const baseProps = getLayerAvailableProperties(props.layerId);
      return Object.values(baseProps).filter(
        (item) => item.type === 'string' && !item.searchable,
      );
    });
    const { layerId } = props;
    const { layerType } = props;
    const { colorType } = props;
    const getLayerConfigColor = () => {
      const found = MapStore.selectedVectorMapLayers.value.find(
        (item) => item.id === layerId,
      );
      if (found?.default_style?.layers) {
        const layerTypeVal = found?.default_style?.layers[layerType];
        if (layerTypeVal !== false && layerTypeVal !== true) {
          if (
            layerTypeVal.color
            && typeof (layerTypeVal.color !== 'string')
            && colorType === (layerTypeVal.color as ColorCategoricalString).type
          ) {
            return layerTypeVal.color as ColorCategoricalString;
          }
          const baseProps = getLayerAvailableProperties(layerId);
          const attribute = Object.keys(baseProps)[0];

          return {
            type: colorType,
            defaultColor: '#FFFFFF',
            attribute,
            colorPairs: { default: '#FF0000' },
          };
        }
      }
      const baseProps = getLayerAvailableProperties(props.layerId);
      const attribute = Object.keys(baseProps)[0];
      return {
        type: colorType,
        defaultColor: '#FFFFFF',
        attribute,
        colorPairs: { default: '#FF0000' },
      };
    };

    const baseColorConfig = computed(() => getLayerConfigColor());

    const addColor = ref(false);
    const newValue = ref('newVal');
    const newColor = ref('#FF0000');

    const localColorConfig: Ref<ColorCategoricalString> = ref(getLayerConfigColor());
    const createColors = () => {
      if (localColorConfig.value) {
        localColorConfig.value.colorPairs = {};
        const availableProps = getLayerAvailableProperties(props.layerId);
        if (availableProps && availableProps[localColorConfig.value.attribute]) {
          const { values } = availableProps[localColorConfig.value.attribute];
          if (values && values.length) {
            values.forEach((item) => {
              localColorConfig.value.colorPairs[item] = colorGenerator(item);
            });
          }
        }
      }
    };

    const addColorPair = () => {
      localColorConfig.value.colorPairs[newValue.value] = newColor.value;
      addColor.value = false;
    };

    const removeColorPair = (value: string) => {
      if (localColorConfig.value.colorPairs[value]) {
        delete localColorConfig.value.colorPairs[value];
      }
    };
    const colorValues = computed(() => {
      const pairs = cloneDeep(localColorConfig.value.colorPairs);
      return pairs;
    });

    const updateAttribute = (attribute: string) => {
      localColorConfig.value.attribute = attribute;
    };
    const updateColorPair = (
      value: string,
      color: string,
    ) => {
      if (localColorConfig.value.colorPairs[value]) {
        localColorConfig.value.colorPairs[value] = color;
      }
    };

    const attributeObjectValue = computed(() => {
      const found = propertyListing.value.find(
        (item) => item.key === localColorConfig.value.attribute,
      );
      return found;
    });

    const pushColor = () => {
      const { layer } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      if (
        layer?.default_style?.layers
        && layer.default_style.layers[layerType] !== false
        && layer.default_style.layers[layerType] !== true
      ) {
        (layer.default_style.layers[layerType] as VectorLayerDisplayConfig).color = localColorConfig.value;
        updateLayer(layer);
      }
    };

    return {
      baseColorConfig,
      propertyListing,
      addColor,
      newValue,
      newColor,
      addColorPair,
      removeColorPair,
      updateColorPair,
      createColors,
      updateAttribute,
      attributeObjectValue,
      localColorConfig,
      colorValues,
      pushColor,
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
      :model-value="attributeObjectValue"
      :items="propertyListing"
      item-value="key"
      item-title="displayName"
      label="Color Type"
      @update:model-value="updateAttribute($event)"
    >
      <template #item="{ props, item }">
        <v-list-item
          v-bind="props"
          :subtitle="item.raw.description"
        />
      </template>
    </v-select>
  </v-row>
  <v-row
    dense
    align="center"
    justify="center"
  >
    <v-col cols="10">
      <p>
        This Color format uses attribute values and maps them to colors
      </p>
    </v-col>
    <v-col>
      <v-btn @click="addColor = true">
        Add <v-icon>mdi-plus</v-icon>
      </v-btn>
    </v-col>
  </v-row>
  <v-row
    v-if="addColor"
    dense
    align="center"
    justify="center"
  >
    <v-col>
      <v-text-field
        v-model="newValue"
        density="compact"
        label="value"
      />
    </v-col>
    <v-col>
      <v-menu
        :close-on-content-click="false"
        offset-y
      >
        <template #activator="{ props }">
          <div
            class="color-square"
            :style="{ backgroundColor: newColor }"
            v-bind="props"
          />
        </template>
        <v-color-picker
          v-model="newColor"
          mode="hex"
        />
      </v-menu>
    </v-col>
    <v-col>
      <v-btn @click="addColorPair()">
        Add
      </v-btn>
    </v-col>
  </v-row>
  <v-row
    dense
    align="center"
    justify="center"
  >
    <v-col>Value</v-col>
    <v-col>Color</v-col>
    <v-col>Delete</v-col>
  </v-row>
  <v-row
    v-for="(color, value) in colorValues"
    :key="`value_color_pair_${value}`"
    dense
    align="center"
    justify="center"
  >
    <v-col>
      <v-text-field
        control-variant="split"
        :model-value="value"
        density="compact"
        @change="
          updateColorPair(
            $event.target._value,
            color,
          )
        "
      />
    </v-col>
    <v-col>
      <v-menu
        :close-on-content-click="false"
        offset-y
      >
        <template #activator="{ props }">
          <div
            class="color-square"
            :style="{ backgroundColor: color }"
            v-bind="props"
          />
        </template>
        <v-color-picker
          @update:model-value="
            updateColorPair(value, $event)
          "
        />
      </v-menu>
    </v-col>
    <v-col>
      <v-icon @click="removeColorPair(value)">
        mdi-delete
      </v-icon>
    </v-col>
  </v-row>
  <v-row dense>
    <v-btn
      color="primary"
      @click="createColors()"
    >
      Generate Colors
    </v-btn>
    <v-spacer />
    <color-saver
      :layer-id="layerId"
      :data="localColorConfig"
    />
    <v-spacer />
    <v-btn
      color="success"
      @click="pushColor()"
    >
      Push Color
    </v-btn>
  </v-row>
</template>

<style scoped>
.color-square {
  width: 25px;
  height: 25px;
  border: 1px solid #000;
  cursor: pointer;
}
</style>
