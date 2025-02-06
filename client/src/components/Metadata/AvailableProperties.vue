<script lang="ts">
import {
  Ref, defineComponent, ref, watch,
} from 'vue';
import MapStore from '../../MapStore';
import { AvailablePropertyDisplay, VectorMapLayer } from '../../types';
import MetadataConfig from './MetadataConfig.vue';
import { getLayerAvailableProperties } from '../../utils';

export default defineComponent({
  components: {
    MetadataConfig,
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const availableProperties: Ref<Record<string, AvailablePropertyDisplay>> = ref(getLayerAvailableProperties(props.layerId));
    watch(MapStore.selectedVectorMapLayers, () => {
      const found = MapStore.selectedVectorMapLayers.value.find((item: VectorMapLayer) => item.id === props.layerId);
      if (found?.default_style?.properties) {
        availableProperties.value = found?.default_style?.properties?.availableProperties || {};
      } else {
        availableProperties.value = {};
      }
    }, { deep: true });

    const editMetadata = ref(false);
    return {
      availableProperties,
      editMetadata,
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
    <h3>Available Properties</h3>
    <v-spacer />
    <v-icon @click="editMetadata = true">
      mdi-cog
    </v-icon>
  </v-row>
  <v-row
    dense
    align="center"
    justify="center"
  >
    <v-col cols="6">
      <span>Display Name</span>
    </v-col>
    <v-col cols="3">
      <span>Type</span>
    </v-col>
    <v-col cols="3">
      <span>Details</span>
    </v-col>
  </v-row>
  <v-row
    v-for="property in availableProperties"
    :key="property.key"
    dense
    align="center"
    justify="center"
  >
    <v-col cols="6">
      <span>{{ property.displayName }}</span>
    </v-col>
    <v-col cols="3">
      <span>{{ property.type }}</span>
    </v-col>
    <v-col cols="3">
      <v-tooltip :text="property.description">
        <template #activator="{ props }">
          <v-icon
            v-if="property.description"
            class="pl-3"
            v-bind="props"
          >
            mdi-text-long
          </v-icon>
        </template>
      </v-tooltip>
    </v-col>
  </v-row>
  <v-dialog
    v-model="editMetadata"
    width="1200"
  >
    <v-card>
      <v-card-title>Available Metadata</v-card-title>
      <v-card-text>
        <MetadataConfig :layer-id="layerId" />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped></style>
