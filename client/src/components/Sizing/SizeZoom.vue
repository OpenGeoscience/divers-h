<script lang="ts">
import {
  PropType, Ref, computed, defineComponent, ref,
} from 'vue';
import { VNumberInput } from 'vuetify/labs/VNumberInput';
import { cloneDeep } from 'lodash';
import MapStore from '../../MapStore';
import {
  AnnotationTypes,
  SizeTypeConfig,
  SizeZoom,
  VectorLayerDisplayConfig,
  VectorMapLayer,
} from '../../types';

import { updateLayer } from '../../map/mapLayers';
import { getVectorLayerDisplayConfig } from '../../utils';

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
      type: String as PropType<'SizeZoom'>,
      required: true,
    },
  },
  setup(props) {
    const { layerId } = props;
    const { layerType } = props;
    const { sizeType } = props;
    const getLayerConfigSize = () => {
      const found = MapStore.selectedVectorMapLayers.value.find(
        (item: VectorMapLayer) => item.id === layerId,
      );
      if (found?.default_style?.layers) {
        const layerTypeVal = found?.default_style?.layers[layerType];
        if (layerTypeVal !== false && layerTypeVal !== true) {
          if (
            layerTypeVal.size
            && (typeof layerTypeVal.size !== 'number')
            && sizeType === (layerTypeVal.size as SizeTypeConfig).type
          ) {
            return layerTypeVal.size as SizeZoom;
          }

          return {
            type: 'SizeZoom',
            zoomLevels: [[16, 5], [12, 3], [10, 2]],
          } as SizeZoom;
        }
      }
      return {
        type: 'SizeZoom',
        zoomLevels: [[16, 5], [12, 3], [10, 2]],
      } as SizeZoom;
    };
    const localSizeConfig: Ref<SizeZoom> = ref(getLayerConfigSize());

    const baseSizeConfig = computed(() => getLayerConfigSize());

    const sortedValues = computed(() => {
      const pairs = cloneDeep(localSizeConfig.value.zoomLevels);
      return pairs.sort((a: [number, number], b: [number, number]) => a[0] - b[0]);
    });
    const addNumber = ref(false);
    const newZoom = ref(0);
    const newNumber = ref(10);

    const addNumberPair = () => {
      localSizeConfig.value.zoomLevels.push([newZoom.value, newNumber.value]);
      addNumber.value = false;
    };

    const removeNumberPair = (zoom: number, value: number) => {
      const index = localSizeConfig.value.zoomLevels.findIndex(
        (item) => item[0] === zoom && item[1] === value,
      );
      if (index !== -1) {
        localSizeConfig.value.zoomLevels.splice(index, 1);
      }
    };

    const updateNumberPair = (
      zoom: number,
      value: number,
      oldZoom: number,
      oldValue: number,
    ) => {
      const index = localSizeConfig.value.zoomLevels.findIndex(
        (item) => item[0] === oldZoom && item[1] === oldValue,
      );
      if (index !== -1) {
        localSizeConfig.value.zoomLevels[index] = [
          zoom,
          value,
        ];
      }
    };

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

    return {
      baseSizeConfig,
      sortedValues,
      addNumber,
      newZoom,
      newNumber,
      addNumberPair,
      removeNumberPair,
      updateNumberPair,
      localSizeConfig,
      pushSize,
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
    <v-col cols="10">
      <p>
        This Size Format uses Zoom levels (0-24) and sizes the element based on the current zoom level
      </p>
    </v-col>
  </v-row>
  <v-row>
    <v-spacer />
    <v-col>
      <v-btn
        :disabled="addNumber"
        @click="addNumber = true"
      >
        Add <v-icon>mdi-plus</v-icon>
      </v-btn>
    </v-col>
  </v-row>
  <v-row
    v-if="addNumber"
    dense
    align="center"
    justify="center"
  >
    <v-col>
      <v-number-input
        v-model="newZoom"
        density="compact"
        label="zoom"
        control-variant="split"
      />
    </v-col>
    <v-col>
      <v-number-input
        v-model="newNumber"
        density="compact"
        label="value"
        control-variant="split"
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
    <v-col>Zoom Level</v-col>
    <v-col>Value</v-col>
    <v-col>Delete</v-col>
  </v-row>
  <v-row
    v-for="item in sortedValues"
    :key="`zoom_value_pair_${item[0]}`"
    dense
    align="center"
    justify="center"
  >
    <v-col>
      <v-number-input
        control-variant="split"
        :model-value="item[0]"
        density="compact"
        @update:model-value="
          updateNumberPair(
            $event,
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
        @update:model-value="
          updateNumberPair(
            item[0],
            $event,
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
