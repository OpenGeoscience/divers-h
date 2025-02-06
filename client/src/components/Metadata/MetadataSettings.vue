<script lang="ts">
import {
  Ref, defineComponent, onMounted, ref,
} from 'vue';
import MapStore from '../../MapStore';
import { PropertyDisplay } from '../../types';
import { updateLayer } from '../../map/mapLayers';

export default defineComponent({
  components: {
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const propertyDisplay: Ref<PropertyDisplay | null> = ref(null);
    const getPropertyDisplay = () => {
      const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.layerId);
      if (found && found.default_style.properties) {
        propertyDisplay.value = found.default_style.properties;
      } else {
        propertyDisplay.value = {
          tooltipDisplay: false, selectedDisplay: {}, availableProperties: {}, selectionDisplay: false,
        };
      }
    };
    onMounted(() => getPropertyDisplay());
    const updateValue = (
      type: 'selectionDisplay'
      | 'tooltipDisplay'
      | 'displayFeatureId',
      val: boolean,
    ) => {
      if (propertyDisplay.value) {
        if (type === 'selectionDisplay' || type === 'tooltipDisplay' || type === 'displayFeatureId') {
          propertyDisplay.value[type] = val;
        }
        const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.layerId);
        if (found && found.default_style) {
          found.default_style.properties = propertyDisplay.value;
          updateLayer(found);
        }
      }
    };
    return {
      propertyDisplay,
      updateValue,
    };
  },
});
</script>

<template>
  <v-row
    v-if="propertyDisplay"
    dense
    align="center"
    justify="center"
  >
    <v-col cols="2">
      <v-icon @click="updateValue('selectionDisplay', !propertyDisplay.selectionDisplay)">
        {{
          propertyDisplay.selectionDisplay ? 'mdi-checkbox-marked'
          : 'mdi-checkbox-blank-outline' }}
      </v-icon>
    </v-col>

    <v-col>
      <v-tooltip text="Only display the comfigured selected values when selecting a feature">
        <template #activator="{ props }">
          <div v-bind="props">
            Selection Display
          </div>
        </template>
      </v-tooltip>
    </v-col>
  </v-row>
  <v-row
    v-if="propertyDisplay"
    dense
    align="center"
    justify="center"
  >
    <v-col cols="2">
      <v-icon @click="updateValue('tooltipDisplay', !propertyDisplay.tooltipDisplay)">
        {{
          propertyDisplay.tooltipDisplay ? 'mdi-checkbox-marked'
          : 'mdi-checkbox-blank-outline' }}
      </v-icon>
    </v-col>
    <v-col>
      <v-tooltip text="Only display the configured tooltip values when hovering a feature">
        <template #activator="{ props }">
          <div v-bind="props">
            Tooltip Display
          </div>
        </template>
      </v-tooltip>
    </v-col>
  </v-row>
  <v-row
    v-if="propertyDisplay"
    dense
    align="center"
    justify="center"
  >
    <v-col cols="2">
      <v-icon @click="updateValue('displayFeatureId', !propertyDisplay.displayFeatureId)">
        {{
          propertyDisplay.displayFeatureId ? 'mdi-checkbox-marked'
          : 'mdi-checkbox-blank-outline' }}
      </v-icon>
    </v-col>
    <v-col>
      <v-tooltip text="Display the FeatureId when selected">
        <template #activator="{ props }">
          <div v-bind="props">
            Display Feature Id
          </div>
        </template>
      </v-tooltip>
    </v-col>
  </v-row>
</template>

<style scoped></style>
