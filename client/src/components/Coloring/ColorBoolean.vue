<script lang="ts">
import {
  PropType, Ref, computed, defineComponent, ref,
} from 'vue';
import MapStore from '../../MapStore';
import {
  AnnotationTypes,
  ColorBoolean,
  VectorLayerDisplayConfig,
  VectorMapLayer,
} from '../../types';

import ColorSaver from './ColorSaver.vue';
import { getLayerAvailableProperties, getVectorLayerDisplayConfig } from '../../utils';

import { updateLayer } from '../../map/mapLayers';

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
      type: String as PropType<'ColorBoolean'>,
      required: true,
    },
  },
  setup(props) {
    const propertyListing = computed(() => {
      const baseProps = getLayerAvailableProperties(props.layerId);
      return Object.values(baseProps).filter(
        (item) => item.type === 'bool',
      );
    });
    const { layerId } = props;
    const { layerType } = props;
    const { colorType } = props;
    const getLayerConfigColor = () => {
      const found = MapStore.selectedVectorMapLayers.value.find(
        (item: VectorMapLayer) => item.id === layerId,
      );
      if (found?.default_style?.layers) {
        const layerTypeVal = found?.default_style?.layers[layerType];
        if (layerTypeVal !== false && layerTypeVal !== true) {
          if (
            layerTypeVal.color
            && typeof (layerTypeVal.color !== 'string')
            && colorType === (layerTypeVal.color as ColorBoolean).type
          ) {
            return layerTypeVal.color as ColorBoolean;
          }
          const baseProps = getLayerAvailableProperties(props.layerId);
          const attribute = Object.keys(baseProps)[0];

          return {
            type: colorType,
            defaultColor: '#FFFFFF',
            attribute,
            falseColor: '#FF0000',
            trueColor: '#00FF00',
          };
        }
      }
      const baseProps = getLayerAvailableProperties(props.layerId);
      const attribute = Object.keys(baseProps)[0];
      return {
        type: colorType,
        defaultColor: '#FFFFFF',
        attribute,
        falseColor: '#FF0000',
        trueColor: '#00FF00',
      };
    };
    const localColorConfig: Ref<ColorBoolean> = ref(getLayerConfigColor());

    const baseColorConfig = computed(() => getLayerConfigColor());

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

    const updateAttribute = (attribute: string) => {
      localColorConfig.value.attribute = attribute;
    };
    const updateColor = (
      value: 'true' | 'false',
      color: string,
    ) => {
      if (value === 'true') {
        localColorConfig.value.trueColor = color;
      }
      if (value === 'false') {
        localColorConfig.value.falseColor = color;
      }
    };

    const attributeObjectValue = computed(() => {
      const found = propertyListing.value.find(
        (item) => item.key === localColorConfig.value.attribute,
      );
      return found;
    });

    return {
      baseColorConfig,
      propertyListing,
      updateColor,
      updateAttribute,
      pushColor,
      attributeObjectValue,
      localColorConfig,
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
        This Color format has a True and False Color Pair
      </p>
    </v-col>
  </v-row>
  <v-row
    dense
    align="center"
    justify="center"
  >
    <v-col>
      <b>True</b>
    </v-col>
    <v-col>
      <v-menu
        :close-on-content-click="false"
        offset-y
      >
        <template #activator="{ props }">
          <div
            class="color-square"
            :style="{ backgroundColor: baseColorConfig.trueColor }"
            v-bind="props"
          />
        </template>
        <v-color-picker
          @update:model-value="
            updateColor('true', $event)
          "
        />
      </v-menu>
    </v-col>
  </v-row>
  <v-row
    dense
    align="center"
    justify="center"
  >
    <v-col>
      <b>False</b>
    </v-col>
    <v-col>
      <v-menu
        :close-on-content-click="false"
        offset-y
      >
        <template #activator="{ props }">
          <div
            class="color-square"
            :style="{ backgroundColor: baseColorConfig.falseColor }"
            v-bind="props"
          />
        </template>
        <v-color-picker
          @update:model-value="
            updateColor('false', $event)
          "
        />
      </v-menu>
    </v-col>
  </v-row>
  <v-row dense>
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
