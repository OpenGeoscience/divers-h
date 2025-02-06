<script lang="ts">
import {
  PropType, computed, defineComponent, ref, watch,
} from 'vue';
import { VNumberInput } from 'vuetify/labs/VNumberInput';
import MapStore from '../../MapStore';
import {
  AnnotationTypes,
  SizeTypeConfig,
  VectorLayerDisplayConfig,
  VectorMapLayer,
} from '../../types';
import { updateLayer } from '../../map/mapLayers';
import SizeLinear from './SizeLinear.vue';
import SizeZoom from './SizeZoom.vue';
import { getLayerAvailableProperties, getVectorLayerDisplayConfig } from '../../utils';

export default defineComponent({
  components: {
    VNumberInput,
    SizeLinear,
    SizeZoom,
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
    const sizeTypes = ref([
      {
        type: 'none',
        name: 'No Sizing',
        typeRequirements: [],
        description: 'No Sizing (Defaults) - Circle, LineWidth: 5 - TextSize: 16',
      },

      {
        type: 'static',
        name: 'Static',
        typeRequirements: [],
        description: 'Applies a Static Size Value',
      },
      {
        type: 'SizeZoom',
        name: 'Size Zooming',
        typeRequirements: [],
        description:
          'Varies the size based on the 0-24 zoom levels',
      },
      {
        type: 'SizeLinear',
        name: 'Attribute Linear Scaling',
        typeRequirements: ['number'],
        description:
          'Given an attribute numerical value set a scale to use',
      },

    ]);

    const getLayerConfigSize = () => {
      const found = MapStore.selectedVectorMapLayers.value.find(
        (item: VectorMapLayer) => item.id === props.layerId,
      );
      if (found?.default_style?.layers) {
        const layerTypeVal = found?.default_style?.layers[props.layerType];
        if (layerTypeVal !== false && layerTypeVal !== true) {
          if (layerTypeVal.size === undefined) {
            layerTypeVal.size = 5;
          }
          return layerTypeVal.size;
        }
      }
      return 5;
    };

    const baseSizeConfig = computed(() => getLayerConfigSize());
    const selectedSizeType = ref(
      typeof baseSizeConfig.value === 'number'
        ? 'static'
        : (baseSizeConfig.value as SizeTypeConfig).type,
    );

    watch(selectedSizeType, () => {
      if (selectedSizeType.value === 'static') {
        const { layer } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
        if (layer?.default_style?.layers && layer.default_style.layers[props.layerType]) {
          if (
            layer.default_style.layers[props.layerType] !== false
            && layer.default_style.layers[props.layerType] !== true
          ) {
            (layer.default_style.layers[props.layerType] as VectorLayerDisplayConfig).size = 15;
          }
        }
      }
    });

    const updateStaticSize = (size: number) => {
      const { layer } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      if (layer?.default_style?.layers && layer.default_style.layers[props.layerType]) {
        if (
          layer.default_style.layers[props.layerType] !== false
          && layer.default_style.layers[props.layerType] !== true
        ) {
          (layer.default_style.layers[props.layerType] as VectorLayerDisplayConfig).size = size;
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

    const computedSizeTypes = computed(() => sizeTypes.value.filter((sizeType) => {
      const { typeRequirements } = sizeType;
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
      selectedSizeType,
      baseSizeConfig,
      computedSizeTypes,
      updateStaticSize,
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
      v-model="selectedSizeType"
      :items="computedSizeTypes"
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
  <v-row v-if="selectedSizeType === 'static'">
    <v-col>
      <h3>Set Static Size:</h3>
    </v-col>
    <v-col v-if="typeof baseSizeConfig === 'number'">
      <v-number-input
        :model-value="baseSizeConfig"
        :min="1"
        @update:model-value="updateStaticSize($event)"
      />
    </v-col>
  </v-row>
  <div v-if="'SizeZoom' === selectedSizeType">
    <SizeZoom
      :layer-id="layerId"
      :layer-type="layerType"
      :size-type="selectedSizeType"
    />
  </div>
  <div v-if="'SizeLinear' === selectedSizeType">
    <SizeLinear
      :layer-id="layerId"
      :layer-type="layerType"
      :size-type="selectedSizeType"
    />
  </div>
</template>

<style scoped>
</style>
