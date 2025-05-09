<script lang="ts">
import {
  Ref, computed, defineComponent, onMounted, ref, watch,
} from 'vue';
import {
  AbstractMapLayerListItem, DisplayConfiguration,
} from '../../types';
import UVdatApi from '../../api/UVDATApi';
import MapSelection from '../../components/Admin/MapSelection.vue';

export default defineComponent({
  name: 'DisplayConfigurationEditor',
  components: {
    MapSelection,
  },
  setup() {
    const config: Ref<DisplayConfiguration | null> = ref(null);
    const enabledUiOptions = ['Scenarios', 'Collections', 'Datasets', 'Metadata'];
    const layerTypes = ['netcdf', 'vector', 'raster'];
    const snackbar = ref({ show: false, text: '', color: '' });
    const layers: Ref<AbstractMapLayerListItem[]> = ref([]);
    const selectedLayers: Ref<string[]> = ref([]);
    onMounted(async () => {
      config.value = await UVdatApi.getDisplayConfiguration();
      layers.value = await UVdatApi.getMapLayerAll();
      selectedLayers.value = config.value.default_displayed_layers.map((item) => (`${item.type}_${item.id}_${item.dataset_id}`));
    });

    watch(() => config.value?.enabled_ui, (newVal) => {
      if (config.value && newVal && !newVal?.includes(config.value.default_tab)) {
        config.value.default_tab = newVal[0] || '';
      }
    });

    const availableLayers = computed(() => {
      if (layers.value) {
        return layers.value.map((item) => ({
          id: item.id,
          name: item.name,
          dataset_id: item.dataset_id,
          type: item.type,
          index: `${item.type}_${item.id}_${item.dataset_id}`,
        }));
      }
      return [];
    });

    const saveConfig = async () => {
      try {
        if (config.value) {
          config.value.default_displayed_layers = [];
          selectedLayers.value.forEach((item) => {
            const data = availableLayers.value.find((layer) => layer.index === item);
            if (data) {
              config.value?.default_displayed_layers.push({
                id: data.id, name: data.name, dataset_id: data.dataset_id, type: data.type,
              });
            }
          });
          await UVdatApi.updateDisplayConfiguration(config.value);
        }
        snackbar.value = { show: true, text: 'Configuration updated successfully!', color: 'success' };
      } catch (error) {
        snackbar.value = { show: true, text: 'Failed to update configuration', color: 'error' };
      }
    };

    const updateDefaultMapSettings = (settings: { location: { center: [number, number]; zoom: number; }; }) => {
      if (config.value) {
        config.value.default_map_settings = settings;
      }
    };

    return {
      config,
      enabledUiOptions,
      layerTypes,
      saveConfig,
      snackbar,
      availableLayers,
      selectedLayers,
      updateDefaultMapSettings,
    };
  },
});
</script>
<template>
  <v-app-bar app>
    <v-btn to="/">
      <v-icon size="x-large" to="/">
        mdi-arrow-left
      </v-icon>
    </v-btn>
  </v-app-bar>
  <v-container v-if="config">
    <v-card>
      <v-card-title>Display Configuration</v-card-title>
      <v-card-text>
        <v-select
          v-model="config.enabled_ui"
          :items="enabledUiOptions"
          label="Enabled UI Features"
          multiple
          chips
        />
        <v-select
          v-model="config.default_tab"
          :items="config.enabled_ui"
          label="Default Tab"
        />
        <v-select
          v-model="selectedLayers"
          :items="availableLayers"
          item-title="name"
          item-value="index"
          label="Default Visible Layers"
          multiple
          clearable
          closable-chips
        >
          <template #chip="{ props, item }">
            <v-chip v-bind="props">
              {{ item.raw.name }}:{{ item.raw.type }}
            </v-chip>
          </template>
          <template #item="{ item, props }">
            <v-list-item v-bind="props">
              {{ item.raw.type }}
            </v-list-item>
          </template>
        </v-select>
        <map-selection
          :default-map-settings="config?.default_map_settings || { location: { center: [-86.1794, 34.8019], zoom: 6 } }"
          @update:settings="updateDefaultMapSettings($event)"
        />
      </v-card-text>
      <v-card-actions>
        <v-btn color="primary" @click="saveConfig">
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>
  </v-container>
</template>

<style scoped>
</style>
