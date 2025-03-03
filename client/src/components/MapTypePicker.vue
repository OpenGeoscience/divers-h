<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import MapStore from '../MapStore';

const mapType = defineModel<string>({ required: true });

const { vectorBaseMapAvailable } = MapStore;
let cancel: (() => void) | undefined;
const disableOSMVector = ref(true);
onMounted(() => {
  ({ cancel } = MapStore.pollForVectorBasemap());
});

onUnmounted(() => {
  cancel?.();
});
</script>

<template>
  <v-radio-group v-model="mapType" hide-details>
    <v-list>
      <v-list-item>
        <v-radio label="No Map" value="none" />
      </v-list-item>
      <v-list-item>
        <v-radio label="OSM Raster Map" value="osm-raster" />
      </v-list-item>
      <v-list-item v-if="!disableOSMVector">
        <div class="d-flex flex-row align-center">
          <v-radio label="OSM Vector Map" value="osm-vector" :disabled="!vectorBaseMapAvailable" />
          <v-tooltip v-if="!vectorBaseMapAvailable" location="bottom">
            <template #activator="{ props }">
              <v-progress-circular indeterminate size="x-small" class="ml-2" width="3" />
              <v-icon size="x-small" class="ml-2" v-bind="props">
                mdi-help-circle
              </v-icon>
            </template>
            <div style="width: 240px">
              <p>
                The vector tiles are currently being generated.
                The process may take a long time (involves a several-GB download).
              </p>
              <br>
              <p>If this option does not enable itself after a long time, the generation may have failed.</p>
            </div>
          </v-tooltip>
        </div>
      </v-list-item>
    </v-list>
  </v-radio-group>
</template>
