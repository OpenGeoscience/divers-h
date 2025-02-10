<!-- eslint-disable vue/max-len -->
<script lang="ts">
import {
  PropType, Ref, computed, defineComponent, ref, watch,
} from 'vue';
import { difference } from 'lodash';
import { NetCDFData } from '../../types';
import { toggleLayerSelection } from '../../map/mapLayers';
import MapStore from '../../MapStore';
import UVdatApi, { NetCDFGenerateParams, NetCDFPreviewParams } from '../../api/UVDATApi';
import ColorSchemes from '../Utilities/ColorSchemes.vue';
import { convert360Longitude, convertTimestampNSToDatetimeString } from '../../utils';
import NetCDFMapSelection from './NetCDFMapSelection.vue';

interface MultiDimensionValue {
  key: string;
  title: string;
  min: number;
  max: number;
  attributes: Record<string, string>
  dimensions: string[];
}

export default defineComponent({
  components: {
    ColorSchemes,
    NetCDFMapSelection,
  },
  props: {
    data: {
      type: Object as PropType<NetCDFData>,
      required: true,
    },
    processing: {
      type: Boolean,
      required: true,
    },
  },
  emits: ['deleted', 'generate-layer'],
  setup(props, { emit }) {
    const netCDFEditor = ref(false);
    const imagePreview = ref<string | null>(null);
    const loadingPreview = ref(false);

    const multidimensionValues = computed(() => {
      const output: MultiDimensionValue[] = [];
      Object.entries(props.data.metadata.variables).forEach(([key, data]) => {
        if (data.dimensions.length >= 3) {
          output.push({
            key,
            title: data.attributes.long_name || data.attributes.standard_name || key,
            min: data.min,
            max: data.max,
            attributes: data.attributes,
            dimensions: data.dimensions,
          });
        }
      });
      return output;
    });
    const selectedMultiDimensionValueKey = ref('');
    const selectedMultiDimensionValue = computed(() => {
      if (selectedMultiDimensionValueKey.value) {
        const found = multidimensionValues.value.find((item) => item.key === selectedMultiDimensionValueKey.value);
        return found;
      }
      return null;
    });

    const newLayerName = ref('New Layer');
    const newLayerX = ref('');
    const newLayerY = ref('');
    const xLayerRange: Ref<[number, number]> = ref([0, 0]);
    const xLayerRangeStep = ref(1);
    const yLayerRange: Ref<[number, number]> = ref([0, 0]);
    const yLayerRangeStep = ref(1);
    const sliceLayerRange: Ref<[number, number]> = ref([0, 0]);
    const sliceLayerRangeStep = ref(1);
    const newLayerSlice = ref('');
    const newLayerDescription = ref('');
    const newLayerColor = ref('viridis');
    const XYRangeTool: Ref<'map' | 'sliders'> = ref('sliders');
    const maxPanBounds = ref([0, 0, 0, 0]);
    const editBounds = ref([0, 0, 0, 0]);
    const previewIndex = ref(0);
    const additionalVariables: Ref<{ variable: string; index: number }[]> = ref([]);
    const getVariableInformation = (variable: string) => props.data.metadata.variables[variable];
    const getVariableName = (variable: string) => props.data.metadata.variables[variable]?.attributes.long_name || props.data.metadata.variables[variable]?.attributes.standard_name || variable;
    const getDimensionSize = (variable: string) => props.data.metadata.dimensions[variable];
    const getVariableMinMax = (variable: string) => {
      const data = getVariableInformation(variable);
      if (data) {
        if (data.geospatial === 'longitude360') {
          return [convert360Longitude(data.min), convert360Longitude(data.max)];
        }
        return [data.min, data.max];
      }
      return [0, 1];
    };

    const isValidLongitude = (value: number) => value >= -180 && value <= 180;
    const isValidLatitude = (value: number) => value >= -90 && value <= 90;
    const validMapDimensions = computed(() => {
      if (newLayerX.value && newLayerY.value && selectedMultiDimensionValue.value) {
        // Ensure both elements in the range are valid numbers
        const dataX = getVariableInformation(newLayerX.value);
        let xRange = [dataX.min, dataX.max];
        if (dataX.geospatial === 'longitude360') {
          xRange = [convert360Longitude(dataX.min), convert360Longitude(dataX.max)];
        }
        const dataY = getVariableInformation(newLayerY.value);
        const yRange = [dataY.min, dataY.max];
        const xValid = xRange.every(isValidLongitude);

        const yValid = yRange.every(isValidLatitude);

        return xValid && yValid;
      }
      return false;
    });
    watch(selectedMultiDimensionValue, () => {
      if (selectedMultiDimensionValue.value) {
        const possibleXValues = ['X', 'longitude', 'lon'];
        const matchingX = selectedMultiDimensionValue.value.dimensions.find((val) => possibleXValues.some((term) => val.toLocaleLowerCase().includes(term.toLowerCase())));
        const possibleYValues = ['Y', 'latitude', 'lat'];
        const matchingY = selectedMultiDimensionValue.value.dimensions.find((val) => possibleYValues.some((term) => val.toLocaleLowerCase().includes(term.toLowerCase())));
        const possibleSliceValues = ['time', 'step', 'valid_time'];
        const matchingSlice = selectedMultiDimensionValue.value.dimensions.find((val) => possibleSliceValues.some((term) => val.toLocaleLowerCase().includes(term.toLowerCase())));
        if (matchingX) {
          newLayerX.value = matchingX;
        }
        if (matchingY) {
          newLayerY.value = matchingY;
        }
        if (matchingSlice) {
          newLayerSlice.value = matchingSlice;
        }
      }
    });
    watch(validMapDimensions, () => {
      if (validMapDimensions.value && newLayerX.value && newLayerY.value && selectedMultiDimensionValue.value) {
        const dataX = getVariableInformation(newLayerX.value);
        let xRange = [dataX.min, dataX.max];
        if (dataX.geospatial === 'longitude360') {
          xRange = [convert360Longitude(dataX.min), convert360Longitude(dataX.max)];
        }
        const dataY = getVariableInformation(newLayerY.value);

        const yRange = [dataY.min, dataY.max];

        maxPanBounds.value = [xRange[0], yRange[0], xRange[1], yRange[1]];
        if (xRange[0] < -175 && xRange[0] > 175) {
          xRange[0] = -100;
          xRange[1] = 100;
        }
        if (yRange[0] < -89 && yRange[1] > 89) {
          yRange[0] = -40;
          yRange[1] = 40;
        }
        editBounds.value = [xRange[0], yRange[0], xRange[1], yRange[1]];
      }
    });
    watch(newLayerX, () => {
      if (!newLayerX.value) {
        return;
      }
      const data = getVariableInformation(newLayerX.value);
      xLayerRange.value = [data.min, data.max];
      xLayerRangeStep.value = (data.max - data.min) / (data.steps || 1);
      if (data.geospatial === 'longitude360') {
        xLayerRange.value = [convert360Longitude(data.min), convert360Longitude(data.max)];
        xLayerRangeStep.value = (xLayerRange.value[1] - xLayerRange.value[0]) / (data.steps || 1);
      }
    });
    watch(newLayerY, () => {
      if (!newLayerY.value) {
        return;
      }
      const data = getVariableInformation(newLayerY.value);
      yLayerRange.value = [data.min, data.max];
      yLayerRangeStep.value = (data.max - data.min) / (data.steps || 1);
      if (yLayerRange.value.every(isValidLatitude)) {
        if (yLayerRange.value[0] < -60) {
          yLayerRange.value[0] = -60;
        }
        if (yLayerRange.value[1] > 60) {
          yLayerRange.value[1] = 60;
        }
      }
    });
    watch(newLayerSlice, () => {
      if (!newLayerSlice.value) {
        return;
      }
      const data = getVariableInformation(newLayerSlice.value);
      if (data.startDate) {
        sliceLayerRangeStep.value = (data.max / 1e6 - data.min / 1e6) / (data.steps || 1);
        const startDate = new Date(data.min / 1e6);
        const endDate = new Date(data.max / 1e6);
        const diffMilli = endDate.getTime() - startDate.getTime();
        const differenceInHours = diffMilli / (1000 * 60 * 60);
        sliceLayerRange.value = [data.min / 1e6, data.max / 1e6];
        sliceLayerRangeStep.value = Math.round(differenceInHours / (data.steps || 1)) * (1000 * 60 * 60);
      } else {
        sliceLayerRange.value = [data.min, data.max];
        sliceLayerRangeStep.value = data.steps ? (data.max - data.min) / (data.steps) : 1;
      }
    });
    const additionalDimensions = computed(() => {
      if (selectedMultiDimensionValue.value) {
        const dimensionCopy = [...selectedMultiDimensionValue.value.dimensions];
        const setValues = [newLayerX.value, newLayerY.value, newLayerSlice.value].filter((item) => item);
        const remaining = difference(dimensionCopy, setValues);
        return remaining;
      }
      return [];
    });
    watch(additionalDimensions, () => {
      additionalVariables.value = [];
      if (additionalDimensions.value.length) {
        additionalDimensions.value.forEach((dimension) => {
          additionalVariables.value.push({ variable: dimension, index: 0 });
        });
      }
    });

    const getPreview = async () => {
      loadingPreview.value = true;
      let additionalVars: undefined | string;
      if (additionalVariables.value.length) {
        additionalVars = additionalVariables.value.map((item) => `${item.variable},${item.index}`).join('&');
      }
      const data: NetCDFPreviewParams = {
        netcdf_data_id: props.data.id,
        i: previewIndex.value,
        variable: selectedMultiDimensionValueKey.value,
        sliding_variable: newLayerSlice.value,
        color_map: newLayerColor.value,
        x_variable: newLayerX.value,
        y_variable: newLayerY.value,
        additional_vars: additionalVars,
        xRange: xLayerRange.value,
        yRange: yLayerRange.value,
      };
      const response = await UVdatApi.getNetCDFPreview(data);
      imagePreview.value = `data:image/png;base64,${response.image}`;
      loadingPreview.value = false;
    };

    const generateLayer = async () => {
      let additionalVars: undefined | string;
      if (additionalVariables.value.length) {
        additionalVars = additionalVariables.value.map((item) => `${item.variable},${item.index}`).join('&');
      }
      const data: NetCDFGenerateParams = {
        netcdf_data_id: props.data.id,
        name: newLayerName.value,
        description: newLayerDescription.value,
        variable: selectedMultiDimensionValueKey.value,
        sliding_variable: newLayerSlice.value,
        x_variable: newLayerX.value,
        y_variable: newLayerY.value,
        additional_vars: additionalVars,
        color_map: newLayerColor.value,
        xRange: xLayerRange.value,
        yRange: yLayerRange.value,
        slicerRange: sliceLayerRange.value,
      };
      await UVdatApi.generateNetCDFLayer(data);
      emit('generate-layer');
      netCDFEditor.value = false;
    };

    const confirmDeletionDialog = ref(false);
    const deletionId: Ref<null | number> = ref(null);
    const initDeletion = (layerId: number) => {
      confirmDeletionDialog.value = true;
      deletionId.value = layerId;
    };

    const deleteLayer = async () => {
      if (deletionId.value !== null) {
        await UVdatApi.deleteNetCDFLayer(deletionId.value);
      }
      deletionId.value = null;
      confirmDeletionDialog.value = false;
      emit('deleted', deletionId.value);
    };

    const setColorScheme = (scheme: string) => {
      newLayerColor.value = scheme.replace('d3.', '');
    };

    const getIndexRange = () => {
      const steps = Math.floor((sliceLayerRange.value[1] - sliceLayerRange.value[0]) / sliceLayerRangeStep.value);
      return steps;
    };

    const mapEditBounds = (bounds: [number, number, number, number]) => {
      xLayerRange.value = [bounds[0], bounds[2]];
      yLayerRange.value = [bounds[1], bounds[3]];
    };

    const cancelNetCDFEditor = () => {
      netCDFEditor.value = false;
      selectedMultiDimensionValueKey.value = '';
      newLayerName.value = 'New Layer';
      newLayerX.value = '';
      newLayerY.value = '';
      xLayerRange.value = [0, 0];
      xLayerRangeStep.value = 1;
      yLayerRange.value = [0, 0];
      yLayerRangeStep.value = 1;
      sliceLayerRange.value = [0, 0];
      sliceLayerRangeStep.value = 1;
      newLayerSlice.value = '';
      newLayerDescription.value = '';
      newLayerColor.value = 'viridis';
      XYRangeTool.value = 'sliders';
      maxPanBounds.value = [0, 0, 0, 0];
      editBounds.value = [0, 0, 0, 0];
      previewIndex.value = 0;
      additionalVariables.value = [];
    };

    watch(netCDFEditor, () => {
      if (!netCDFEditor.value) {
        cancelNetCDFEditor();
      }
    });

    return {
      toggleLayerSelection,
      selectedLayers: MapStore.selectedMapLayers,
      netCDFEditor,
      multidimensionValues,
      selectedMultiDimensionValue,
      selectedMultiDimensionValueKey,
      newLayerName,
      newLayerDescription,
      newLayerX,
      newLayerY,
      newLayerSlice,
      getVariableInformation,
      getVariableMinMax,
      getVariableName,
      additionalVariables,
      getDimensionSize,
      getPreview,
      imagePreview,
      loadingPreview,
      previewIndex,
      generateLayer,
      initDeletion,
      deleteLayer,
      confirmDeletionDialog,
      proMode: MapStore.proMode,
      setColorScheme,
      xLayerRange,
      xLayerRangeStep,
      yLayerRange,
      yLayerRangeStep,
      sliceLayerRange,
      sliceLayerRangeStep,
      convertTimestampNSToDatetimeString,
      validMapDimensions,
      editBounds,
      maxPanBounds,
      XYRangeTool,
      getIndexRange,
      mapEditBounds,
      cancelNetCDFEditor,
    };
  },
});
</script>

<template>
  <v-list dense>
    <v-row dense align="center" justify="center" class="mx-1">
      <v-icon v-tooltip="'NetCDF Layer'">
        mdi-grid
      </v-icon>
      <div class="layer-checkbox-label">
        {{ data.name }}
        <v-tooltip
          :text="data.name"
          activator="parent"
          location="bottom"
          open-delay="1000"
        />
      </div>
      <div>
        <v-icon color="success" class="ml-2" @click="netCDFEditor = true">
          mdi-plus-thick
        </v-icon>
      </div>
      <div v-if="processing">
        <v-icon color="warning" class="ml-2">
          mdi-sync mdi-spin
        </v-icon>
      </div>
      <v-spacer />
    </v-row>
    <v-list-item
      v-for="layer in data.layers"
      :key="`layer_${layer.id}`"
      dense
    >
      <v-row dense align="center">
        <v-checkbox
          :model-value="!!selectedLayers.find((item) => (item.id === layer.id))"
          class="layer-checkbox"
          density="compact"
          hide-details
          @change="toggleLayerSelection(layer)"
        >
          <template #label>
            <v-icon v-tooltip="'NetCDF Data'">
              mdi-grid
            </v-icon>
            <span class="layer-checkbox-label">
              {{ layer.name }}
              <v-tooltip
                :text="layer.name"
                activator="parent"
                location="bottom"
                open-delay="1000"
              />
            </span>
          </template>
        </v-checkbox>
        <v-spacer />
        <v-icon v-if="proMode" v-tooltip="'Delete Layer'" color="error" @click="initDeletion(layer.id)">
          mdi-delete
        </v-icon>
      </v-row>
    </v-list-item>
    <v-dialog v-model="netCDFEditor" width="700">
      <v-card>
        <v-card-title>NetCDF Editor</v-card-title>
        <v-card-text>
          <v-row>
            <v-text-field v-model="newLayerName" label="name" />
          </v-row>
          <v-row>
            <v-text-field v-model="newLayerDescription" label="Description" />
          </v-row>
          <v-row>
            <ColorSchemes display-selected @choose-color-scheme="setColorScheme($event)" />
          </v-row>
          <v-row>
            <v-select
              v-model="selectedMultiDimensionValueKey"
              item-value="key"
              item-title="title"
              :items="multidimensionValues"
              label="Variable"
            >
              <template #item="{ props, item }">
                <v-list-item v-bind="props" class="select-variable">
                  <template #title>
                    <b>Variable:</b> <span class="mx-2">{{ item.raw.title }}</span>
                    <v-tooltip>
                      <template #activator="{ props: tooltipProps }">
                        <v-icon class="ml-2" v-bind="tooltipProps">
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <div v-for="(attribute, attributeKey) in item.raw.attributes" :key="`${item.raw.key}_${attributeKey}`">
                        <span class="mx-2">{{ attributeKey }}:</span>
                        <span class="mx-2">{{ attribute }}</span>
                      </div>
                    </v-tooltip>
                  </template>
                  <b>Dimensions:</b>
                  <span
                    v-for="dimension in item.raw.dimensions"
                    :key="`${item.raw.key}_${dimension}`"
                    class="mx-2"
                  >
                    <span>{{ getVariableName(dimension) }} </span>
                    <v-tooltip>
                      <template #activator="{ props: tooltipProps }">
                        <v-icon class="ml-2" v-bind="tooltipProps">
                          mdi-information-outline
                        </v-icon>
                      </template>
                      <div>
                        <span class="mx-2">Min:</span>
                        <span class="mx-2">{{ getVariableInformation(dimension)?.min }}</span>
                      </div>
                      <div>
                        <span class="mx-2">Max:</span>
                        <span class="mx-2">{{ getVariableInformation(dimension)?.max }}</span>
                      </div>
                      <div
                        v-for="(attribute, attributeKey) in getVariableInformation(dimension)?.attributes"
                        :key="`${item.raw.key}_${attributeKey}`"
                      >
                        <span class="mx-2">{{ attributeKey }}:</span>
                        <span class="mx-2">{{ attribute }}</span>
                      </div>
                    </v-tooltip>
                  </span>
                </v-list-item>
              </template>
            </v-select>
          </v-row>
          <div v-if="selectedMultiDimensionValue">
            <v-row>
              <v-tooltip width="300">
                <template #activator="{ props: tooltipProps }">
                  <div>
                    <span>Configure XY And Sliding Coordinates
                    </span>
                    <v-icon v-bind="tooltipProps" class="ml-1">
                      mdi-information
                    </v-icon>
                  </div>
                </template>
                <p>
                  Configure the variables for the rendering of this netCDF slice.
                  Typically the X/Y values will correspond to latitude/longitude and the slicing parameter will
                  be connected to time or a dimension to scrub through.
                  Additional coordinates if there are more than 3 dimensions will need a default index configured.
                  The system will automatically try to populate the base values
                </p>
              </v-tooltip>
              <v-spacer />
              <v-tooltip width="300">
                <template #activator="{ props: tooltipProps }">
                  <v-icon
                    v-bind="tooltipProps"
                    :color="XYRangeTool === 'sliders' ? 'primary' : ''"
                    @click="XYRangeTool = 'sliders'"
                  >
                    mdi-tune-variant
                  </v-icon>
                </template>
                <span>Configure the X and Y range using sliders for the min/max values</span>
              </v-tooltip>
              <v-tooltip v-if="validMapDimensions" width="300">
                <template #activator="{ props: tooltipProps }">
                  <v-icon v-bind="tooltipProps" :color="XYRangeTool === 'map' ? 'primary' : ''" @click="XYRangeTool = 'map'">
                    mdi-map
                  </v-icon>
                </template>
                <span>The Variables appear to be latitude/longitude, configure the X/Y Range using a Map</span>
              </v-tooltip>
            </v-row>
            <v-row v-if="XYRangeTool === 'sliders'">
              <v-col>
                <v-select v-model="newLayerX" :items="selectedMultiDimensionValue.dimensions" label="X" />
                <div v-if="newLayerX">
                  <v-range-slider
                    v-model="xLayerRange"
                    :step="xLayerRangeStep"
                    :min="getVariableMinMax(newLayerX)[0]"
                    :max="getVariableMinMax(newLayerX)[1]"
                    thumb-label="always"
                    class="pt-2"
                  >
                    <template #thumb-label="{ modelValue }">
                      <span> {{ modelValue.toFixed(2) }}</span>
                    </template>
                    <template #prepend>
                      <span>{{ getVariableMinMax(newLayerX)[0].toFixed(2) }}</span>
                    </template>
                    <template #append>
                      <span>{{ getVariableMinMax(newLayerX)[1].toFixed(2) }}</span>
                    </template>
                  </v-range-slider>
                </div>
              </v-col>
              <v-col>
                <v-select v-model="newLayerY" :items="selectedMultiDimensionValue.dimensions" label="Y" />
                <div v-if="newLayerY">
                  <v-range-slider
                    v-model="yLayerRange"
                    :step="yLayerRangeStep"
                    :min="getVariableInformation(newLayerY).min"
                    :max="getVariableInformation(newLayerY).max"
                    thumb-label="always"
                    class="pt-2"
                    hide-details
                  >
                    <template #thumb-label="{ modelValue }">
                      <span> {{ modelValue.toFixed(2) }}</span>
                    </template>
                    <template #prepend>
                      <span>{{ getVariableInformation(newLayerY)?.min.toFixed(2) }}</span>
                    </template>
                    <template #append>
                      <span>{{ getVariableInformation(newLayerY)?.max.toFixed(2) }}</span>
                    </template>
                  </v-range-slider>
                  <v-tooltip v-if="getVariableInformation(newLayerY)?.geospatial === 'latitude'">
                    <template #activator="{ props: tooltipProps }">
                      <v-icon color="warning" v-bind="tooltipProps">
                        mdi-alert
                      </v-icon>
                    </template>
                    <v-alert
                      color="warning"
                      text="Extreme Latitude Values (<-70 or >70) may cause extreme distortion in the map"
                      density="compact"
                    />
                  </v-tooltip>
                </div>
              </v-col>
            </v-row>
            <v-row v-if="validMapDimensions && XYRangeTool === 'map'">
              <NetCDFMapSelection
                :max-pan-bounds="maxPanBounds"
                :edit-bounds="editBounds"
                @update:edit-bounds="mapEditBounds($event)"
              />
            </v-row>
            <v-row v-if="newLayerSlice">
              <v-col>
                <v-select v-model="newLayerSlice" :items="selectedMultiDimensionValue.dimensions" label="Slice" />
                <div v-if="newLayerSlice && getVariableInformation(newLayerSlice).startDate === undefined">
                  <v-range-slider
                    v-model="sliceLayerRange"
                    :step="sliceLayerRangeStep"
                    :min="getVariableInformation(newLayerSlice).min"
                    :max="getVariableInformation(newLayerSlice).max"
                    hide-details
                    class="pt-2"
                  >
                    <template #thumb-label="{ modelValue }">
                      <span> {{ modelValue.toFixed(2) }}</span>
                    </template>

                    <template #prepend>
                      <span>{{ getVariableInformation(newLayerSlice)?.min }}</span>
                    </template>
                    <template #append>
                      <span>{{ getVariableInformation(newLayerSlice)?.max }}</span>
                    </template>
                  </v-range-slider>
                  <v-row align="center" justify="center">
                    <v-spacer />
                    <v-col>
                      <span>{{ (sliceLayerRange[0].toFixed(2)) }}</span>
                      <span class="mx-2">to</span>
                      <span>{{ (sliceLayerRange[1].toFixed(2)) }}</span>
                    </v-col>
                    <v-spacer />
                  </v-row>
                </div>
                <div v-else-if="newLayerSlice && getVariableInformation(newLayerSlice).startDate">
                  <v-range-slider
                    v-model="sliceLayerRange"
                    :step="sliceLayerRangeStep"
                    :min="getVariableInformation(newLayerSlice).min / 1e6"
                    :max="getVariableInformation(newLayerSlice).max / 1e6"
                    class="pt-2"
                    hide-details
                  >
                    <template #thumb-label="{ modelValue }">
                      <span> {{ convertTimestampNSToDatetimeString(modelValue) }}</span>
                    </template>

                    <template #prepend>
                      <span>{{ convertTimestampNSToDatetimeString(getVariableInformation(newLayerSlice)?.min / 1e6) }}</span>
                    </template>
                    <template #append>
                      <span>{{ convertTimestampNSToDatetimeString(getVariableInformation(newLayerSlice)?.max / 1e6) }}</span>
                    </template>
                  </v-range-slider>
                  <v-row align="center" justify="center" class="py-2">
                    <v-spacer />
                    <span>{{ convertTimestampNSToDatetimeString(sliceLayerRange[0]) }}</span>
                    <span class="mx-2">to</span>
                    <span>{{ convertTimestampNSToDatetimeString(sliceLayerRange[1]) }}</span>
                    <v-spacer />
                  </v-row>
                </div>
              </v-col>
            </v-row>
          </div>
          <div v-if="newLayerX && newLayerY && newLayerSlice">
            <v-tooltip v-if="additionalVariables.length" width="300">
              <template #activator="{ props: tooltipProps }">
                <div>
                  <span>Additional Coordinates
                  </span>
                  <v-icon v-bind="tooltipProps" class="ml-2">
                    mdi-information
                  </v-icon>
                </div>
              </template>
              <p>Additional coordinates in the variable that need an index to be chosen</p>
            </v-tooltip>
            <v-row>
              <v-col v-for="item in additionalVariables" :key="`${item.variable}`">
                <v-slider
                  v-model="item.index"
                  step="1"
                  min="0"
                  :max="getDimensionSize(item.variable) - 1"
                  :label="`${item.variable} (${item.index})`"
                />
              </v-col>
            </v-row>
            <v-row v-if="imagePreview || loadingPreview">
              <v-spacer />
              <v-progress-circular v-if="loadingPreview" indeterminate />
              <img v-else-if="imagePreview" :src="imagePreview" alt="NetCDF Preview" class="img" />
              <v-spacer />
            </v-row>
            <v-row>
              <v-slider
                v-model="previewIndex"
                step="1"
                :max="getIndexRange()"
                :label="`Index (${previewIndex})`"
              />
              <v-spacer />
              <v-btn class="mx-2" @click="getPreview()">
                Preview
              </v-btn>
              <v-btn class="mx-2" @click="generateLayer()">
                Generate
              </v-btn>
            </v-row>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-row dense>
            <v-spacer />
            <v-btn color="" @click="cancelNetCDFEditor()">
              Cancel
            </v-btn>
          </v-row>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-list>
  <v-dialog v-model="confirmDeletionDialog" width="300">
    <v-card>
      <v-card-title>Delete Layer</v-card-title>
      <v-card-text>Do you want to delete the NetCDF layer?</v-card-text>
      <v-card-actions>
        <v-row>
          <v-spacer />
          <v-btn class="mx-2" color="warning" @click="confirmDeletionDialog = false">
            Cancel
          </v-btn>
          <v-btn color="error" class="mx-2" @click="deleteLayer()">
            Delete
          </v-btn>
        </v-row>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>

.layer-checkbox-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  }
.select-variable {
    border: 1px solid gray;
  }
.img {
  width: 100%;
  height: 100%;
  object-fit: cover; /* The image will fill the container and may be cropped */
}

</style>
