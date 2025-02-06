<script lang="ts">
import {
  PropType, Ref, computed, defineComponent, ref,
  watch,
} from 'vue';
import { VNumberInput } from 'vuetify/labs/VNumberInput';
import { cloneDeep } from 'lodash';
import MapStore from '../../MapStore';
import {
  AnnotationTypes,
  ColorCategoricalNumber,
  ColorLinearNumber,
  ColorObjectDisplay,
  VectorLayerDisplayConfig,
  VectorMapLayer,
} from '../../types';

import { updateLayer } from '../../map/mapLayers';
import ColorSaver from './ColorSaver.vue';
import {
  colorSchemes, formatNumPrecision, getLayerAvailableProperties, getVectorLayerDisplayConfig, isWithinPercent,
} from '../../utils';

const oneHundredScale = [{
  color: '#FFFFFF',
  value: 50,
},
{
  color: '#FFF7BC',
  value: 80,
},
{
  color: '#FED976',
  value: 90,
},
{
  color: '#FD8D3C',
  value: 95,
},
{
  color: '#BD2600',
  value: 100,
}];
export default defineComponent({
  components: {
    VNumberInput,
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
      type: String as PropType<'ColorLinearNumber' | 'ColorCategoricalNumber'>,
      required: true,
    },
    defaultScheme: {
      type: String,
      default: 'd3.YlOrRd',
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
    const colorType = ref(props.colorType);
    const currentScheme = ref(props.defaultScheme);

    const getLayerConfigColor = () => {
      const found = MapStore.selectedVectorMapLayers.value.find(
        (item) => item.id === layerId,
      );
      if (found?.default_style?.layers) {
        const layerTypeVal = found?.default_style?.layers[layerType];
        if (layerTypeVal !== false && layerTypeVal !== true) {
          if (
            layerTypeVal.color
            && (typeof layerTypeVal.color !== 'string')
            && colorType.value === (layerTypeVal.color as ColorObjectDisplay).type
          ) {
            return layerTypeVal.color as
              | ColorCategoricalNumber
              | ColorLinearNumber;
          }
          const subProps = getLayerAvailableProperties(layerId);
          const attribute = Object.keys(subProps)[0];
          const attributeObj = subProps[attribute];

          let numberColorPairs = [
            { value: attributeObj.min !== undefined ? attributeObj.min : 50, color: '#FF0000' },
            { value: attributeObj.max !== undefined ? attributeObj.max : 100, color: '#00FF00' },
          ];
          const scheme = colorSchemes.find((item) => item.name === currentScheme.value);
          if (scheme && attributeObj.min !== undefined && attributeObj.max !== undefined) {
            const { colors } = scheme;
            const range = attributeObj.max - attributeObj.min;
            const incrementVal = range / colors.length;
            const colorPairs: { value: number, color: string }[] = [];
            for (let i = 0; i < colors.length; i += 1) {
              colorPairs.push({ value: formatNumPrecision(attributeObj.min + (i * incrementVal), range), color: colors[i] });
            }
            numberColorPairs = colorPairs;
          }

          if (attributeObj.min !== undefined && attributeObj.max !== undefined) {
            if (isWithinPercent(0, attributeObj.min, 1) && isWithinPercent(1000, attributeObj.max, 1)) {
              numberColorPairs = oneHundredScale.map((item) => ({ ...item, value: item.value / 100.0 }));
            } else if (isWithinPercent(0, attributeObj.min, 1)
            && isWithinPercent(100, attributeObj.min, 1)) {
              numberColorPairs = oneHundredScale;
            }
          }
          return {
            type: colorType.value,
            defaultColor: '#FFFFFF',
            attribute,
            numberColorPairs,
          };
        }
      }
      const baseProps = getLayerAvailableProperties(layerId);
      const attribute = Object.keys(baseProps)[0];
      return {
        type: colorType.value,
        defaultColor: '#FFFFFF',
        attribute,
        numberColorPairs: [
          // eslint-disable-next-line @typescript-eslint/no-use-before-define
          { value: minMax.value?.min || 0, color: '#FF0000' },
          // eslint-disable-next-line @typescript-eslint/no-use-before-define
          { value: minMax.value?.max, color: '#00FF00' },
        ],
      };
    };
    const localColorConfig: Ref<ColorCategoricalNumber | ColorLinearNumber> = ref(getLayerConfigColor());

    const baseColorConfig = computed(() => getLayerConfigColor());

    const sortedValues = computed(() => {
      const pairs = cloneDeep(localColorConfig.value.numberColorPairs);
      return pairs.sort((a, b) => a.value - b.value);
    });
    const addNumber = ref(false);
    const newNumber = ref(0);
    const newColor = ref('#FF0000');

    const addNumberPair = () => {
      localColorConfig.value.numberColorPairs.push({
        value: newNumber.value,
        color: newColor.value,
      });

      addNumber.value = false;
    };

    const removeNumberPair = (value: number, color: string) => {
      const index = localColorConfig.value.numberColorPairs.findIndex(
        (item) => item.color === color && item.value === value,
      );
      if (index !== -1) {
        localColorConfig.value.numberColorPairs.splice(index, 1);
      }
    };

    watch(() => props.colorType, () => {
      localColorConfig.value.type = props.colorType;
      colorType.value = props.colorType;
    });
    const updateAttribute = (attribute: string) => {
      localColorConfig.value.attribute = attribute;
      const subProps = getLayerAvailableProperties(layerId);
      const attributeObj = subProps[attribute];
      let numberColorPairs = [
        { value: attributeObj.min !== undefined ? attributeObj.min : 50, color: '#FF0000' },
        { value: attributeObj.max !== undefined ? attributeObj.max : 100, color: '#00FF00' },
      ];
      const scheme = colorSchemes.find((item) => item.name === currentScheme.value);
      if (scheme && attributeObj.min !== undefined && attributeObj.max !== undefined) {
        const { colors } = scheme;
        const range = attributeObj.max - attributeObj.min;
        const incrementVal = range / colors.length;
        const colorPairs: { value: number, color: string }[] = [];
        for (let i = 0; i < colors.length; i += 1) {
          colorPairs.push({ value: formatNumPrecision(attributeObj.min + (i * incrementVal), range), color: colors[i] });
        }
        numberColorPairs = colorPairs;
      }

      if (attributeObj.min !== undefined) {
        if ((attributeObj.min === 0 || attributeObj.min === 0.01)
            && (attributeObj.max === 0.99 || attributeObj.max === 1)) {
          numberColorPairs = oneHundredScale.map((item) => ({ ...item, value: item.value / 100.0 }));
        } else if ((attributeObj.min === 0 || attributeObj.min === 1)
            && (attributeObj.max === 99 || attributeObj.max === 100)) {
          numberColorPairs = oneHundredScale;
        }
      }
      localColorConfig.value.numberColorPairs = numberColorPairs;
    };
    const updateNumberPair = (
      strValue: string,
      color: string,
      oldValue: number,
      oldColor: string,
    ) => {
      const value = parseFloat(strValue);
      const index = localColorConfig.value.numberColorPairs.findIndex(
        (item) => item.color === oldColor && item.value === oldValue,
      );
      if (index !== -1) {
        localColorConfig.value.numberColorPairs[index] = {
          value,
          color,
        };
      }
    };

    const attributeObjectValue = computed(() => {
      const found = propertyListing.value.find(
        (item) => item.key === localColorConfig.value.attribute,
      );
      return found;
    });
    const minMax = computed(() => ({
      // eslint-disable-next-line @typescript-eslint/no-use-before-define
      min: attributeObjectValue.value?.min,
      // eslint-disable-next-line @typescript-eslint/no-use-before-define
      max: attributeObjectValue.value?.max,
    }));

    const chooseColorScheme = (schemeName: string) => {
      const scheme = colorSchemes.find((item) => item.name === schemeName);
      if (scheme && minMax.value.min !== undefined && minMax.value.max !== undefined) {
        const { colors } = scheme;
        const range = minMax.value.max - minMax.value.min;
        const incrementVal = range / colors.length;
        const colorPairs: { value: number, color: string }[] = [];
        for (let i = 0; i < colors.length; i += 1) {
          colorPairs.push({ value: formatNumPrecision(minMax.value.min + (i * incrementVal), range), color: colors[i] });
        }
        localColorConfig.value.numberColorPairs = colorPairs;
        currentScheme.value = schemeName;
      }
    };

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

    const saveAsDialog = ref(false);
    const saveAsName = ref('');
    const saveAsDescription = ref('');

    const pushSaveAs = () => {
      const found = MapStore.selectedVectorMapLayers.value.find(
        (item: VectorMapLayer) => item.id === props.layerId,
      );
      if (found) {
        if (found.default_style && !found.default_style?.savedColors) {
          found.default_style.savedColors = [];
        }
        if (found.default_style && found.default_style?.savedColors) {
          // find if there is an existing option
          const foundSaveColorIndex = found.default_style.savedColors.findIndex((item) => item.name === saveAsName.value);
          if (foundSaveColorIndex !== -1) {
            found.default_style.savedColors.splice(foundSaveColorIndex, 1, {
              name: saveAsName.value,
              description: saveAsDescription.value,
              color: localColorConfig.value,
            });
          } else {
            found.default_style.savedColors.push({
              name: saveAsName.value,
              description: saveAsDescription.value,
              color: localColorConfig.value,
            });
          }
        }
        saveAsDialog.value = false;
      }
    };
    // eslint-disable-next-line vue/max-len
    const cannotAddNumber = computed(() => !!(sortedValues.value && sortedValues.value.find((item) => item.value === newNumber.value)));
    function hasDuplicateValues(arr: { value: number, color: string }[]): boolean {
      return arr.some((item, index) => arr.slice(index + 1).some((otherItem) => otherItem.value === item.value));
    }

    const disablePush = computed(() => {
      if (sortedValues.value.length < 2) {
        return 'The number of colors is less than 2';
      }
      if (hasDuplicateValues(sortedValues.value)) {
        return 'There are duplicate values';
      }
      return false;
    });
    return {
      baseColorConfig,
      d3ColorSchemes: colorSchemes,
      propertyListing,
      sortedValues,
      addNumber,
      newNumber,
      newColor,
      addNumberPair,
      removeNumberPair,
      formatNumPrecision,
      updateNumberPair,
      updateAttribute,
      attributeObjectValue,
      localColorConfig,
      pushColor,
      saveAsDialog,
      saveAsName,
      saveAsDescription,
      pushSaveAs,
      chooseColorScheme,
      cannotAddNumber,
      minMax,
      disablePush,
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
  </v-row>
  <v-row dense>
    <v-col>
      <v-menu
        offset-y
        offset-x
        nudge-left="180"
        max-width="180"
        open-on-hover
      >
        <template #activator="{ props }">
          <v-btn
            size="x-small"
            color="primary"
            v-bind="props"
          >
            Color Schemes
          </v-btn>
        </template>
        <v-card outlined>
          <v-list>
            <v-list-item
              v-for="(scheme, index) in d3ColorSchemes"
              :key="index"
              @click="chooseColorScheme(scheme.name)"
            >
              <v-list-item-title>
                {{ scheme.name }}
              </v-list-item-title>
              <v-list-item-subtitle>
                <!-- Display color swatches as squares -->
                <v-avatar v-for="color in scheme.colors" :key="color" size="10" :style="{ backgroundColor: color }" />
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card>
      </v-menu>
    </v-col>
    <v-col>
      <v-btn @click="addNumber = true">
        Add <v-icon>mdi-plus</v-icon>
      </v-btn>
    </v-col>
  </v-row>
  <v-row v-if="minMax.min !== undefined || minMax.max !== undefined">
    <v-spacer />
    <v-col><b>Min:</b>{{ formatNumPrecision(minMax.min || 0) }}</v-col>
    <v-col><b>Max:</b>{{ formatNumPrecision(minMax.max || 0) }}</v-col>
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
        v-model="newNumber"
        density="compact"
        label="number"
        :error-messages="cannotAddNumber ? 'Number must be unique' : ''"
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
    <v-spacer />
    <v-col cols="6" class="d-flex justify-center">
      Number
    </v-col>
    <v-col class="d-flex justify-center">
      Color
    </v-col>
    <v-col class="d-flex justify-center">
      Delete
    </v-col>
    <v-spacer />
  </v-row>
  <v-row
    v-for="item in sortedValues"
    :key="`number_color_pair_${item.value}`"
    dense
    align="center"
    justify="center"
  >
    <v-spacer />
    <v-col cols="6">
      <v-text-field
        :model-value="item.value"
        type="number"
        hide-spin-buttons
        density="compact"
        hide-details
        @change="
          updateNumberPair(
            $event.target._value,
            item.color,
            item.value,
            item.color,
          )
        "
      />
    </v-col>
    <v-col class="d-flex justify-center">
      <v-menu
        :close-on-content-click="false"
        offset-y
      >
        <template #activator="{ props }">
          <div
            class="color-square"
            :style="{ backgroundColor: item.color }"
            v-bind="props"
          />
        </template>
        <v-color-picker
          mode="hex"
          @update:model-value="
            updateNumberPair(item.value, $event, item.value, item.color)
          "
        />
      </v-menu>
    </v-col>
    <v-col class="d-flex justify-center">
      <v-icon color="error" @click="removeNumberPair(item.value, item.color)">
        mdi-delete
      </v-icon>
    </v-col>
    <v-spacer />
  </v-row>
  <v-row v-if="disablePush" class="pb-5">
    <v-alert type="error">
      {{ disablePush }}
    </v-alert>
  </v-row>
  <v-row dense>
    <color-saver
      :layer-id="layerId"
      :disabled="!!disablePush"
      :data="localColorConfig"
    />
    <v-spacer />
    <v-btn
      color="success"
      :disabled="!!disablePush"
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
