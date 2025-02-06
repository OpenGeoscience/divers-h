<!-- eslint-disable no-param-reassign -->
<script lang="ts">
import {
  Ref, computed, defineComponent, onMounted, ref,
} from 'vue';
import { getRasterLayerDisplayConfig } from '../../utils';
import uvdatAPI from '../../api/UVDATApi';
import BandEditor from './BandEditor.vue';
import { updateLayer } from '../../map/mapLayers';
import { MapRasterParams, StyleBandEdit, StyleBands } from '../../types';

export default defineComponent({
  name: 'RasterStyleEditor',
  components: {
    BandEditor,
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
    styleParams: {
      type: Object as () => MapRasterParams['style'],
      required: true,
    },
  },
  setup(props) {
    const loaded = ref(false);
    const bands: Ref<StyleBandEdit[]> = ref(props.styleParams?.bands || []);
    const minMaxMap: Ref<Record<string, { min: number; max: number }>> = ref(
      {},
    );
    const tableBands: Ref<StyleBands[]> = computed(() => bands.value);
    const bandHeader = ref([
      { title: 'Enabled', key: 'enabled', width: '5px' },
      { title: 'Band', key: 'band', width: '20px' },
      { title: 'Interpretation', key: 'interpretation', width: '20px' },

      { title: 'Min/Max Clamp', value: 'minmax' },
      { title: 'Palette', value: 'palette' },
      { title: 'Actions', value: 'actions' },
    ]);
    const getBands = async () => {
      minMaxMap.value = {};
      const metadata = await uvdatAPI.getRasterMetadata(props.layerId);
      Object.entries(metadata.bands).forEach(([key, item]) => {
        minMaxMap.value[key] = { min: item.min, max: item.max };
        // We do a n == to convert string to int conversions, based on how large image
        // indexes using string numbers and we store differently because it can be
        // a string or a key
        // NOTE:  these are indexed by 1 so they avoid falsy issues
        // eslint-disable-next-line eqeqeq
        const found = bands.value.find((subItem) => subItem.band == key);
        if (!found) {
          bands.value.push({
            band: key as StyleBands['band'],
            interpretation: item.interpretation,
            enabled: false,
            min: 'min',
            max: 'max',
          });
        } else if (found) {
          // if found we still want interpretation information
          found.interpretation = item.interpretation;
        }
      });
    };
    onMounted(async () => {
      await getBands();
      loaded.value = true;
    });
    const editingBand: Ref<null | StyleBands> = ref(null);
    const editingMinMax: Ref<{ min: number; max: number }> = ref({
      min: 0,
      max: 100,
    });
    const editBand = (item: StyleBands) => {
      editingBand.value = item;
      if (
        item.band !== undefined
        && item.band !== null
        && minMaxMap.value[item.band]
      ) {
        editingMinMax.value = minMaxMap.value[item.band];
      }
    };

    const saveBand = (newBand: StyleBandEdit) => {
      const index = bands.value.findIndex(
        (item) => item.band === newBand.band,
      );
      if (index !== -1) {
        bands.value.splice(index, 1, newBand);
      }
      editingBand.value = null;
    };

    const pushChanges = () => {
      const { layer, displayConfig } = getRasterLayerDisplayConfig(
        props.layerId,
      );
      if (layer && displayConfig) {
        if (!displayConfig.largeImageStyle) {
          displayConfig.largeImageStyle = {};
        }
        displayConfig.largeImageStyle.bands = bands.value;
        updateLayer(layer);
      }
    };

    const updateMinMax = (
      updateBand: StyleBandEdit,
      data: {
        min: StyleBandEdit['min'],
        max: StyleBandEdit['max'],
        clamp: StyleBandEdit['clamp'],
      },
    ) => {
      const index = bands.value.findIndex(
        (item) => item.band === updateBand.band,
      );
      updateBand.min = data.min;
      updateBand.max = data.max;
      updateBand.clamp = data.clamp;
      if (index !== -1) {
        bands.value.splice(index, 1, updateBand);
      }
    };
    const updatePalette = (updateBand: StyleBandEdit, data: { palette: StyleBandEdit['palette'] }) => {
      const index = bands.value.findIndex(
        (item) => item.band === updateBand.band,
      );
      updateBand.palette = data.palette;
      if (index !== -1) {
        bands.value.splice(index, 1, updateBand);
      }
    };

    const updateEnabled = (item: StyleBandEdit) => {
      item.enabled = !item.enabled;
    };

    return {
      loaded,
      tableBands,
      bandHeader,
      editBand,
      minMaxMap,
      editingBand,
      editingMinMax,
      saveBand,
      pushChanges,
      updateEnabled,
      updateMinMax,
      updatePalette,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title> Raster Style Editor </v-card-title>
    <v-card-text>
      <v-data-table
        v-if="!editingBand && loaded"
        :headers="bandHeader"
        :items="tableBands"
      >
        <template #[`item.enabled`]="{ item }">
          <v-icon
            size="large"
            @click="updateEnabled(item)"
          >
            {{
              item.enabled ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline' }}
          </v-icon>
        </template>
        <template #[`item.minmax`]="{ item }">
          <band-editor
            compact="minmax"
            :band="item"
            :min="minMaxMap[item.band].min"
            :max="minMaxMap[item.band].max"
            @update-minmax="updateMinMax(item, $event)"
          />
        </template>
        <template #[`item.palette`]="{ item }">
          <band-editor
            compact="palette"
            :band="item"
            :min="minMaxMap[item.band].min"
            :max="minMaxMap[item.band].max"
            @update-palette="updatePalette(item, $event)"
          />
        </template>

        <template #[`item.range`]="{ item }">
          <v-row>
            <b>{{ minMaxMap[item.band].min.toFixed(2) }}</b><span class="mx-2">to</span>
            <b>{{ minMaxMap[item.band].max.toFixed(2) }}</b>
          </v-row>
        </template>

        <template #[`item.actions`]="{ item }">
          <v-icon @click="editBand(item)">
            mdi-pencil
          </v-icon>
        </template>
      </v-data-table>
      <BandEditor
        v-else-if="editingBand"
        :band="editingBand"
        :min="editingMinMax.min"
        :max="editingMinMax.max"
        @cancel="editingBand = null"
        @save="saveBand($event)"
      />
    </v-card-text>
    <v-card-actions>
      <v-row dense>
        <v-spacer />
        <v-btn
          color="success"
          @click="pushChanges()"
        >
          Push Changes
        </v-btn>
      </v-row>
    </v-card-actions>
  </v-card>
</template>

<style scoped>
/* Add any additional styling as needed */
</style>
