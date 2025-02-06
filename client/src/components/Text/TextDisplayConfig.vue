<script lang="ts">
import {
  PropType, Ref, computed, defineComponent, ref,
} from 'vue';
import MapStore from '../../MapStore';
import {
  AnnotationTypes,
  TextConfig,
  VectorLayerDisplayConfig,
  VectorMapLayer,
} from '../../types';

import { updateLayer } from '../../map/mapLayers';
import { getLayerAvailableProperties, getVectorLayerDisplayConfig } from '../../utils';

export default defineComponent({
  components: {
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
    const propertyListing = computed(() => {
      const baseProps = getLayerAvailableProperties(props.layerId);
      return Object.values(baseProps);
    });
    const { layerId } = props;
    const { layerType } = props;
    const getLayerConfigText = () => {
      const found = MapStore.selectedVectorMapLayers.value.find(
        (item: VectorMapLayer) => item.id === layerId,
      );
      if (found?.default_style?.layers) {
        const layerTypeVal = found?.default_style?.layers[layerType];
        if (layerTypeVal !== false && layerTypeVal !== true) {
          if (
            layerTypeVal.text
          ) {
            return layerTypeVal.text as TextConfig;
          }
          const baseProps = getLayerAvailableProperties(props.layerId);
          const attribute = Object.keys(baseProps)[0];

          return {
            key: attribute,
          };
        }
      }
      const baseProps = getLayerAvailableProperties(props.layerId);
      const attribute = Object.keys(baseProps)[0];
      return {
        key: attribute,
      };
    };
    const localTextConfig: Ref<TextConfig> = ref(getLayerConfigText());

    const pushText = () => {
      const { layer } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      if (
        layer?.default_style?.layers
        && layer.default_style.layers[layerType] !== false
        && layer.default_style.layers[layerType] !== true
      ) {
        (layer.default_style.layers[layerType] as VectorLayerDisplayConfig).text = localTextConfig.value;
        updateLayer(layer);
      }
    };

    const updateAttribute = (attribute: string) => {
      localTextConfig.value.key = attribute;
      pushText();
    };

    const attributeObjectValue = computed(() => {
      const found = propertyListing.value.find(
        (item) => item.key === localTextConfig.value.key,
      );
      return found;
    });

    return {
      propertyListing,
      updateAttribute,
      attributeObjectValue,
      localTextConfig,
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
      label="Text Attribute"
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
        This Displays the Selected Attributes Text value
      </p>
    </v-col>
  </v-row>
</template>

<style scoped>
</style>
