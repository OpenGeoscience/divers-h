<script lang="ts">
import {
  PropType, Ref, computed, defineComponent, ref,
} from 'vue';
import { VNumberInput } from 'vuetify/labs/VNumberInput';
import { cloneDeep } from 'lodash';
import MapStore from '../../MapStore';
import {
  AnnotationTypes,
  SizeLinear,
  SizeTypeConfig,
  VectorLayerDisplayConfig,
} from '../../types';

import { updateLayer } from '../../map/mapLayers';
import { getLayerAvailableProperties, getVectorLayerDisplayConfig } from '../../utils';

export default defineComponent({
  components: {
    VNumberInput,
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
    sizeType: {
      type: String as PropType<'SizeLinear'>,
      required: true,
    },
  },
  setup(props) {
    const propertyListing = computed(() => {
      const baseProps = getLayerAvailableProperties(props.layerId);
      return Object.values(baseProps).filter(
        (item) => item.type === 'number' && !item.static,
      );
    });
    const { layerId } = props;
    const { layerType } = props;
    const { sizeType } = props;
    const getLayerConfigSize = (): SizeLinear => {
      const found = MapStore.selectedVectorMapLayers.value.find(
        (item) => item.id === layerId,
      );
      if (found?.default_style?.layers) {
        const layerTypeVal = found?.default_style?.layers[layerType];
        if (layerTypeVal !== false && layerTypeVal !== true) {
          if (
            layerTypeVal.size
            && (typeof layerTypeVal.size !== 'number')
            && sizeType === (layerTypeVal.size as SizeTypeConfig).type
          ) {
            return layerTypeVal.size as SizeLinear;
          }
          const attributes = getLayerAvailableProperties(props.layerId);
          const attribute = propertyListing.value[0].key;
          const min = attributes[attribute].min || 0;
          const max = attributes[attribute].max || 1;
          return {
            type: 'SizeLinear',
            attribute,
            linearLevels: [[min, 5], [max, 15]],
          } as SizeLinear;
        }
      }
      const attributes = getLayerAvailableProperties(props.layerId);
      const attribute = propertyListing.value[0].key;
      const min = attributes[attribute].min || 0;
      const max = attributes[attribute].max || 1;
      return {
        type: 'SizeLinear',
        attribute,
        linearLevels: [[min, 5], [max, 15]],
      } as SizeLinear;
    };
    const localSizeConfig: Ref<SizeLinear> = ref(getLayerConfigSize());

    const baseSizeConfig = computed(() => getLayerConfigSize());

    const sortedValues = computed(() => {
      const pairs = cloneDeep(localSizeConfig.value.linearLevels);
      return pairs.sort((a: [number, number], b: [number, number]) => a[0] - b[0]);
    });
    const addNumber = ref(false);
    const newBase = ref(0);
    const newValue = ref(10);

    const addNumberPair = () => {
      localSizeConfig.value.linearLevels.push([newBase.value, newValue.value]);
      addNumber.value = false;
    };

    const removeNumberPair = (base: number, value: number) => {
      const index = localSizeConfig.value.linearLevels.findIndex(
        (item) => item[0] === base && item[1] === value,
      );
      if (index !== -1) {
        localSizeConfig.value.linearLevels.splice(index, 1);
      }
    };

    const updateAttribute = (attribute: string) => {
      localSizeConfig.value.attribute = attribute;
    };
    const updateNumberPair = (
      base: number,
      value: number,
      oldBase: number,
      oldValue: number,
    ) => {
      const index = localSizeConfig.value.linearLevels.findIndex(
        (item) => item[0] === oldBase && item[1] === oldValue,
      );
      if (index !== -1) {
        baseSizeConfig.value.linearLevels[index] = [
          base,
          value,
        ];
      }
    };

    const attributeObjectValue = computed(() => {
      const found = propertyListing.value.find(
        (item) => item.key === baseSizeConfig.value.attribute,
      );
      return found;
    });

    const pushSize = () => {
      const { layer } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      if (
        layer?.default_style?.layers
        && layer.default_style.layers[layerType] !== false
        && layer.default_style.layers[layerType] !== true
      ) {
        (layer.default_style.layers[layerType] as VectorLayerDisplayConfig).size = localSizeConfig.value;
        updateLayer(layer);
      }
    };

    const minMax = computed(() => ({
      min: attributeObjectValue.value?.min,
      max: attributeObjectValue.value?.max,
    }));

    return {
      baseSizeConfig,
      propertyListing,
      sortedValues,
      addNumber,
      newBase,
      newValue,
      addNumberPair,
      removeNumberPair,
      updateNumberPair,
      updateAttribute,
      attributeObjectValue,
      localSizeConfig,
      pushSize,
      minMax,
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
      label="Attribute"
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
        This Color format takes an attribute numberical value and divides it
        into categories based on the values below.
      </p>
    </v-col>
    <v-col>
      <v-btn @click="addNumber = true">
        Add <v-icon>mdi-plus</v-icon>
      </v-btn>
    </v-col>
  </v-row>
  <v-row v-if="minMax.min !== undefined || minMax.max !== undefined">
    <v-spacer />
    <v-col><b>Min:</b>{{ minMax.min?.toFixed(2) }}</v-col>
    <v-col><b>Max:</b>{{ minMax.max?.toFixed(2) }}</v-col>
    <v-spacer />
  </v-row>
  <v-row
    v-if="addNumber"
    dense
    align="center"
    justify="center"
  >
    <v-col>
      <v-number-input
        v-model="newBase"
        density="compact"
        label="base"
        :min="0"
        :max="24"
        control-variant="split"
      />
    </v-col>
    <v-col>
      <v-number-input
        v-model="newBase"
        density="compact"
        control-variant="split"
        label="Value"
      />
    </v-col>
    <v-col>
      <v-btn @click="addNumberPair()">
        Add
      </v-btn>
    </v-col>
  </v-row>
  <v-row
    dense
    align="center"
    justify="center"
  >
    <v-col>Attribute Value</v-col>
    <v-col>Value</v-col>
    <v-col>Delete</v-col>
  </v-row>
  <v-row
    v-for="item in sortedValues"
    :key="`base_value_pair_${item[0]}`"
    dense
    align="center"
    justify="center"
  >
    <v-col>
      <v-number-input
        control-variant="split"
        :model-value="item[0]"
        density="compact"
        @change="
          updateNumberPair(
            $event.target._value,
            item[1],
            item[0],
            item[1],
          )
        "
      />
    </v-col>
    <v-col>
      <v-number-input
        control-variant="split"
        :model-value="item[1]"
        density="compact"
        @change="
          updateNumberPair(
            item[0],
            $event.target._value,
            item[0],
            item[1],
          )
        "
      />
    </v-col>
    <v-col>
      <v-icon @click="removeNumberPair(item[0], item[1])">
        mdi-delete
      </v-icon>
    </v-col>
  </v-row>
  <v-row dense>
    <v-spacer />
    <v-btn
      color="success"
      @click="pushSize()"
    >
      Push Size
    </v-btn>
  </v-row>
</template>

<style scoped></style>
