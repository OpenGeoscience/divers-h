<script lang="ts">
import {
  PropType, Ref, computed, defineComponent, onMounted, ref, watch,
} from 'vue';
import { VNumberInput } from 'vuetify/labs/VNumberInput';
import { cloneDeep } from 'lodash';
import {
  AnnotationTypes,
} from '../../types';

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
    dataType: {
      type: String as PropType<'weight' | 'intensity'>,
      required: true,
    },
  },
  emits: ['update'],
  setup(props, { emit }) {
    const propertyListing = computed(() => {
      const baseProps = getLayerAvailableProperties(props.layerId);
      return Object.values(baseProps).filter(
        (item) => item.type === 'number' && !item.static,
      );
    });
    const localNumberPairs: Ref<[number, number][]> = ref([]);
    const selectedAttribute = ref('');
    const configType: Ref<'static' | 'linear' | 'zoom'> = ref('static');
    const configOptions = computed(() => {
      if (props.dataType === 'weight') {
        return ['static', 'linear'];
      }
      return ['static', 'zoom'];
    });
    const numberValue: Ref<number> = ref(1);
    const initialize = () => {
      const { displayConfig } = getVectorLayerDisplayConfig(props.layerId, props.layerType);
      if (displayConfig !== false && displayConfig !== true && displayConfig !== undefined) {
        if (displayConfig.heatmap) {
          if (props.dataType === 'weight') {
            if (displayConfig.heatmap.weight !== undefined) {
              if (typeof displayConfig.heatmap.weight === 'number') {
                configType.value = 'static';
                numberValue.value = displayConfig.heatmap.weight;
              } else {
                configType.value = 'linear';
                localNumberPairs.value = displayConfig.heatmap.weight.linearLevels;
                selectedAttribute.value = displayConfig.heatmap.weight.attribute;
              }
            }
          } else if (props.dataType === 'intensity') {
            if (displayConfig.heatmap.intensity !== undefined) {
              if (typeof displayConfig.heatmap.intensity === 'number') {
                configType.value = 'static';
                numberValue.value = displayConfig.heatmap.intensity;
              } else {
                configType.value = 'zoom';
                localNumberPairs.value = displayConfig.heatmap.intensity.zoomLevels;
              }
            }
          }
        }
      }
    };
    onMounted(() => initialize());
    const sortedValues = computed(() => {
      const pairs = cloneDeep(localNumberPairs.value);
      return pairs.sort((a: [number, number], b: [number, number]) => a[0] - b[0]);
    });
    const addNumber = ref(false);
    const newBase = ref(0);
    const newValue = ref(10);

    const addNumberPair = () => {
      localNumberPairs.value.push([newBase.value, newValue.value]);
      addNumber.value = false;
    };

    const removeNumberPair = (base: number, value: number) => {
      const index = localNumberPairs.value.findIndex(
        (item) => item[0] === base && item[1] === value,
      );
      if (index !== -1) {
        localNumberPairs.value.splice(index, 1);
      }
    };

    const updateAttribute = (attribute: string) => {
      selectedAttribute.value = attribute;
    };
    const updateNumberPair = (
      base: number,
      value: number,
      oldBase: number,
      oldValue: number,
    ) => {
      const index = localNumberPairs.value.findIndex(
        (item) => item[0] === oldBase && item[1] === oldValue,
      );
      if (index !== -1) {
        localNumberPairs.value[index] = [
          base,
          value,
        ];
      }
    };

    const attributeObjectValue = computed(() => {
      const found = propertyListing.value.find(
        (item) => item.key === selectedAttribute.value,
      );
      return found;
    });

    const pushData = () => {
      if (configType.value === 'static') {
        emit('update', {
          type: 'static',
          value: numberValue.value,
        });
      } else if (configType.value === 'linear') {
        emit('update', {
          type: 'linear',
          attribute: selectedAttribute.value,
          numberPairs: localNumberPairs.value,
        });
      } else if (configType.value === 'zoom') {
        emit('update', {
          type: 'zoom',
          numberPairs: localNumberPairs.value,
        });
      }
    };

    const minMax = computed(() => ({
      min: attributeObjectValue.value?.min,
      max: attributeObjectValue.value?.max,
    }));

    watch(configType, () => {
      if (configType.value === 'linear') {
        if (selectedAttribute.value === '' && propertyListing.value.length) {
          selectedAttribute.value = propertyListing.value[0].key;
        }
        if (localNumberPairs.value.length === 0) {
          localNumberPairs.value = [
            [minMax.value.min || 0, 0],
            [minMax.value.max || 10, minMax.value.max || 10],
          ];
        }
      }
    });

    return {
      configType,
      configOptions,
      numberValue,
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
      pushData,
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
      v-model="configType"
      :items="configOptions"
      label="Type"
    />
  </v-row>
  <v-row v-if="configType === 'static'">
    <v-slider
      v-model="numberValue"
      label="Value"
      min="0"
      max="200"
    />
    <span class="mx-2" style="min-width:25px">{{ numberValue.toFixed(0) }}</span>
  </v-row>
  <v-row
    v-if="configType === 'linear'"
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
    v-if="configType !== 'static'"
    dense
    align="center"
    justify="center"
  >
    <v-col v-if="!addNumber">
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
        label="val"
        :min="0"
        :max="configType === 'zoom' ? 24 : undefined"
        control-variant="split"
      />
    </v-col>
    <v-col>
      <v-number-input
        v-model="newValue"
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
    v-if="configType !== 'static'"
    dense
    align="center"
    justify="center"
  >
    <v-col>{{ configType === 'linear' ? 'Attribute Value' : 'Value' }}</v-col>
    <v-col>{{ configType === 'linear' ? 'Value' : 'Zoom' }}</v-col>
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
        :max="configType === 'zoom' ? 24 : undefined"
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
      @click="pushData()"
    >
      Push Values
    </v-btn>
  </v-row>
</template>

<style scoped></style>
