<script lang="ts">
import {
  PropType,
  Ref,
  defineComponent,
  nextTick,
  onMounted,
  ref,
  watch,
} from 'vue';
import { StyleBandEdit, StyleBands } from '../../types';
import { colorSchemes, drawGradients } from '../../utils';
// Import the function to update the layer
export default defineComponent({
  name: 'RasterStyleEditor',
  props: {
    band: {
      type: Object as PropType<StyleBandEdit>,
      required: true,
    },
    min: {
      type: Number,
      required: true,
    },
    max: {
      type: Number,
      required: true,
    },
    compact: {
      type: String as PropType<'none' | 'minmax' | 'palette'>,
      default: 'none',
    },
  },
  emits: ['cancel', 'save', 'updateMinmax', 'updatePalette'],
  setup(props, { emit }) {
    const minTypes = ref(['min', 'auto', 'value', 'threshold']);
    const maxTypes = ref(['max', 'auto', 'value', 'threshold']);
    const minValueType: Ref<'min' | 'auto' | 'value' | 'threshold'> = ref('min');
    const maxValueType: Ref<'max' | 'auto' | 'value' | 'threshold'> = ref('max');
    const minValue: Ref<StyleBands['min']> = ref(props.band.min || 'min');
    const maxValue: Ref<StyleBands['max']> = ref(props.band.max || 'max');
    const palette: Ref<string[]> = ref([]);
    const scheme: Ref<'discrete' | 'linear'> = ref(
      props.band.scheme || 'linear',
    );
    const clampValues = ref([
      { name: 'Unset', value: undefined, description: 'Unset default value' },
      {
        name: 'Clamp',
        value: true,
        description: 'Clamps Min/Max to the end values',
      },
      {
        name: 'Transparent',
        value: false,
        description: 'Values outside Min/Max are transparent',
      },
    ]);
    const clampValue: Ref<undefined | boolean | 'Unset'> = ref(undefined);

    const schemeValues = ref([
      {
        name: 'linear',
        value: 'linear',
        description: 'Linear interpoaltion of colors',
      },
      {
        name: 'discrete',
        value: 'discrete',
        description: 'discrete color calculations between number of colors',
      },
    ]);
    onMounted(() => {
      if (typeof props.band.min === 'number') {
        minValueType.value = 'value';
        minValue.value = props.band.min;
      } else if (typeof props.band.min === 'string') {
        if (props.band.min.includes('min:')) {
          minValueType.value = 'threshold';
          minValue.value = parseFloat(props.band.min.replace('min:', ''));
        } else {
          minValueType.value = props.band.min as 'min' | 'auto';
        }
      }
      if (typeof props.band.max === 'number') {
        maxValueType.value = 'value';
        maxValue.value = props.band.max;
      } else if (typeof props.band.max === 'string') {
        if (props.band.max.includes('max:')) {
          maxValueType.value = 'threshold';
          maxValue.value = parseFloat(props.band.max.replace('max:', ''));
        } else {
          maxValueType.value = props.band.max as 'max' | 'auto';
        }
      }
      if (props.band.palette && Array.isArray(props.band.palette)) {
        palette.value = props.band.palette;
      } else if (props.band.palette) {
        palette.value = [props.band.palette as string];
      }
      clampValue.value = props.band.clamp;
      nextTick(() => drawGradients(palette.value, props.band.band?.toString() || ''));
    });
    const saveBand = () => {
      const numericalMinValue = minValueType.value === 'threshold'
        ? `min:${minValue.value}`
        : minValue.value;
      const outputMinValue = ['min', 'auto'].includes(minValueType.value)
        ? minValueType.value
        : numericalMinValue;
      const numericalMaxValue = maxValueType.value === 'threshold'
        ? `max:${maxValue.value}`
        : maxValue.value;
      const outputMaxValue = ['min', 'auto'].includes(maxValueType.value)
        ? maxValueType.value
        : numericalMaxValue;
      const outputClampValue = clampValue.value === 'Unset' ? undefined : clampValue.value;
      const outputPaletteValue = palette.value && palette.value.length > 1
        ? palette.value
        : palette.value[0];

      if (props.compact === 'minmax') {
        emit('updateMinmax', {
          min: outputMinValue,
          max: outputMaxValue,
          clamp: outputClampValue,
        });
        return;
      }
      if (props.compact === 'palette') {
        emit('updatePalette', {
          palette: outputPaletteValue,
        });
        return;
      }
      const data = {
        ...props.band,
        min: outputMinValue,
        max: outputMaxValue,
        clamp: outputClampValue,
        scheme: scheme.value,
        palette: !palette.value.length ? undefined : outputPaletteValue,
      };
      emit('save', data);
    };

    watch([minValueType, maxValueType], () => {
      if (
        minValue.value !== undefined
        && ['value', 'threshold'].includes(minValueType.value)
        && ['min', 'auto'].includes(minValue.value.toString())
      ) {
        minValue.value = props.min;
      }
      if (
        maxValue.value !== undefined
        && ['value', 'threshold'].includes(maxValueType.value)
        && ['max', 'auto'].includes(maxValue.value.toString())
      ) {
        maxValue.value = props.max;
      }
      if (props.compact === 'minmax') {
        saveBand();
      }
    });
    watch([minValue, maxValue], () => {
      if (props.compact === 'minmax') {
        saveBand();
      }
    });
    const getDisplayClampValue = (val: undefined | boolean) => {
      const found = clampValues.value.find((item) => item.value === val);
      return found?.name;
    };
    watch(clampValue, () => {
      if (props.compact === 'minmax') {
        saveBand();
      }
    });

    const colorMapper: Record<string, string> = {
      blue: '#0000FF',
      red: '#FF0000',
      green: '#00FF00',
    };
    const addColor = () => {
      if (props.band.interpretation && colorMapper[props.band.interpretation]) {
        palette.value.push(colorMapper[props.band.interpretation]);
      } else {
        palette.value.push('#888888');
      }
      nextTick(() => drawGradients(palette.value, props.band.band?.toString() || ''));
      if (props.compact === 'palette') {
        saveBand();
      }
    };
    const d3ColorSchemes = ref(colorSchemes);

    const applyScheme = (colorScheme: { name:string, colors: string[] }) => {
      palette.value = colorScheme.colors;
      drawGradients(palette.value, props.band.band?.toString() || '');
      if (props.compact === 'palette') {
        saveBand();
      }
    };

    const clearColors = () => {
      palette.value = [];
      drawGradients(palette.value, props.band.band?.toString() || '');
      if (props.compact === 'palette') {
        saveBand();
      }
    };
    const deleteColor = (index: number) => {
      palette.value.splice(index, 1);
      drawGradients(palette.value, props.band.band?.toString() || '');
      if (props.compact === 'palette') {
        saveBand();
      }
    };

    const updateColor = (color: string, index: number) => {
      if (palette.value[index]) {
        palette.value[index] = color;
        drawGradients(palette.value, props.band.band?.toString() || '');
        if (props.compact === 'palette') {
          saveBand();
        }
      }
    };
    return {
      minTypes,
      maxTypes,
      minValueType,
      maxValueType,
      minValue,
      maxValue,
      saveBand,
      clampValues,
      clampValue,
      scheme,
      schemeValues,
      palette,
      addColor,
      deleteColor,
      updateColor,
      getDisplayClampValue,
      d3ColorSchemes,
      applyScheme,
      clearColors,

    };
  },
});
</script>

<template>
  <div v-if="compact === 'none'">
    <v-row dense>
      Editing Band: {{ band.band }}
      <v-spacer />
      <v-btn
        color="error"
        class="mx-2"
        @click="$emit('cancel')"
      >
        Cancel
      </v-btn>
      <v-btn
        color="success"
        class="mx-2"
        @click="saveBand()"
      >
        Save
      </v-btn>
    </v-row>
    <v-row>
      <v-col class="mx-6">
        <v-row>
          <b>Min:</b><span>{{ min.toFixed(4) }}</span>
        </v-row>
        <v-row>
          <v-select
            v-model="minValueType"
            :items="minTypes"
            label="Min"
          />
        </v-row>
        <v-row v-if="['value', 'threshold'].includes(minValueType)">
          <v-slider
            v-model="minValue"
            thumb-label="always"
            :min="minValueType === 'threshold' ? 0 : min"
            :max="minValueType === 'threshold' ? 100 : max"
          />
        </v-row>
      </v-col>
      <v-col class="mx-6">
        <v-row>
          <b>Max:</b><span>{{ max.toFixed(4) }}</span>
        </v-row>
        <v-row>
          <v-select
            v-model="maxValueType"
            :items="maxTypes"
            label="Max"
          />
        </v-row>
        <v-row v-if="['value', 'threshold'].includes(maxValueType)">
          <v-slider
            v-model="maxValue"
            thumb-label="always"
            :min="minValueType === 'threshold' ? 0 : min"
            :max="minValueType === 'threshold' ? 100 : max"
          />
        </v-row>
      </v-col>
    </v-row>
    <v-row>
      <v-col class="mx-4">
        <v-select
          v-model="clampValue"
          :items="clampValues"
          item-title="name"
          item-value="value"
          label="Clamp"
          style="max-width: 200px"
        >
          <template #item="{ props, item }">
            <v-list-item
              v-bind="props"
              :subtitle="item.raw.description"
            />
          </template>
        </v-select>
      </v-col>
      <v-col class="mx-4">
        <v-select
          v-model="scheme"
          :items="schemeValues"
          item-title="name"
          item-value="value"
          label="Scheme"
          style="max-width: 200px"
        >
          <template #item="{ props, item }">
            <v-list-item
              v-bind="props"
              :subtitle="item.raw.description"
            />
          </template>
        </v-select>
      </v-col>
    </v-row>
    <v-row>
      <v-expansion-panels>
        <v-expansion-panel>
          <v-expansion-panel-title>
            <div v-if="palette">
              <svg
                :id="`gradientImage-${band.band}`"
                width="125"
                height="20"
              />
            </div>
            <div v-else>
              <span>Default</span>
            </div>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-row dense>
              <v-menu
                offset-y
                offset-x
                nudge-left="180"
                max-width="180"
                open-on-hover
              >
                <template #activator="{ props }">
                  <v-btn
                    color="primary"
                    @click="addColor()"
                  >
                    Add Color
                    <v-icon v-bind="props">
                      mdi-chevron-down
                    </v-icon>
                  </v-btn>
                </template>
                <v-card outlined>
                  <v-list>
                    <v-list-item
                      v-for="(scheme, index) in d3ColorSchemes"
                      :key="index"
                      @click="applyScheme(scheme)"
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
              <v-spacer />
              <v-btn
                v-if="palette.length"
                v-tooltip="'Clear all Colors'"
                size="x-large"
                variant="plain"
                icon="mdi-delete"
                color="error"
                @click="clearColors()"
              />
            </v-row>
            <v-row dense>
              <v-col
                v-for="(color, index) in palette"
                :key="`color_${band.band}_${index}`"
              >
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
                    <v-icon
                      color="error"
                      @click="deleteColor(index)"
                    >
                      mdi-delete
                    </v-icon>
                  </template>
                  <v-color-picker
                    mode="hex"
                    :model-value="color"
                    @update:model-value="updateColor($event, index)"
                  />
                </v-menu>
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-row>
  </div>
  <div
    v-else-if="compact === 'minmax'"
    style="max-width: 250px"
  >
    <v-expansion-panels>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-row
            dense
            style="font-size: 0.85em"
            align="center"
            justify="center"
          >
            <v-col cols="6">
              <span>{{
                typeof minValue === "number" ? minValue.toFixed(2) : minValue
              }}<span>/</span>{{
                typeof maxValue === "number" ? maxValue.toFixed(2) : maxValue
              }}</span>
            </v-col>
            <v-col>{{ getDisplayClampValue(clampValue) }}</v-col>
          </v-row>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-row
            dense
            class="pa-0 ma-0"
            style="font-size: 0.85em"
          >
            <v-col>
              <b>Min:</b><span>{{
                typeof minValue === "number" ? minValue.toFixed(2) : minValue
              }}</span>
            </v-col>
            <v-col>
              <b>Range:</b><span>{{ min.toFixed(2) }}</span>
            </v-col>
          </v-row>
          <v-row
            v-if="['value', 'threshold'].includes(minValueType)"
            dense
          >
            <v-slider
              v-model="minValue"
              density="compact"
              :min="minValueType === 'threshold' ? 0 : min"
              :max="minValueType === 'threshold' ? 100 : max"
            />
          </v-row>
          <v-row
            dense
            class="pa-0 ma-0"
            style="font-size: 0.85em"
          >
            <v-col>
              <b>Max:</b><span>{{
                typeof maxValue === "number" ? maxValue.toFixed(2) : maxValue
              }}</span>
            </v-col>
            <v-col>
              <b>Range:</b><span>{{ max.toFixed(2) }}</span>
            </v-col>
          </v-row>
          <v-row
            v-if="['value', 'threshold'].includes(maxValueType)"
            dense
          >
            <v-slider
              v-model="maxValue"
              density="compact"
              :min="minValueType === 'threshold' ? 0 : min"
              :max="minValueType === 'threshold' ? 100 : max"
            />
          </v-row>
          <v-row dense>
            <v-select
              v-model="clampValue"
              :items="clampValues"
              item-title="name"
              item-value="value"
              label="Clamp"
              density="compact"
              style="max-width: 200px"
            />
          </v-row>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
  <div
    v-else-if="compact === 'palette'"
    style="max-width: 300px"
  >
    <v-expansion-panels>
      <v-expansion-panel>
        <v-expansion-panel-title>
          <div v-if="palette && palette.length">
            <svg
              :id="`gradientImage-${band.band}`"
              width="250"
              height="20"
            />
          </div>
          <div v-else>
            <span>Default</span>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-row dense>
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
                  @click="addColor()"
                >
                  Add Color
                  <v-icon v-bind="props">
                    mdi-chevron-down
                  </v-icon>
                </v-btn>
              </template>
              <v-card outlined>
                <v-list>
                  <v-list-item
                    v-for="(scheme, index) in d3ColorSchemes"
                    :key="index"
                    @click="applyScheme(scheme)"
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
            <v-spacer />
            <v-btn
              v-if="palette.length"
              v-tooltip="'Clear all Colors'"
              size="x-small"
              variant="plain"
              icon="mdi-delete"
              color="error"
              @click="clearColors()"
            />
          </v-row>
          <v-row dense>
            <v-col
              v-for="(color, index) in palette"
              :key="`color_${band.band}_${index}`"
            >
              <v-menu
                :close-on-content-click="false"
                offset-y
              >
                <template #activator="{ props }">
                  <div
                    class="compact-color-square"
                    :style="{ backgroundColor: color }"
                    v-bind="props"
                  />
                  <v-icon
                    size="x-small"
                    color="error"
                    @click="deleteColor(index)"
                  >
                    mdi-delete
                  </v-icon>
                </template>
                <v-color-picker
                  mode="hex"
                  :model-value="color"
                  @update:model-value="updateColor($event, index)"
                />
              </v-menu>
            </v-col>
          </v-row>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<style scoped>
.color-square {
  width: 50px;
  height: 50px;
  border: 1px solid #000;
  cursor: pointer;
}
.compact-color-square {
  width: 15px;
  height: 15px;
  border: 1px solid #000;
  cursor: pointer;
}
</style>
