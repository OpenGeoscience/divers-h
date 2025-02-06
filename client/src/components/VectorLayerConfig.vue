<script lang="ts">
import {
  PropType,
  Ref,
  computed,
  defineComponent,
  onMounted,
  ref,
} from 'vue';
import MapStore from '../MapStore';
import { AnnotationTypes, VectorLayerDisplayConfig, VectorMapLayer } from '../types';
import LayerTypeConfig from './LayerTypeConfig.vue';
import PropertiesConfig from './PropertiesConfig.vue';
import FilteringConfig from './FilteringConfig.vue';

export default defineComponent({
  components: {
    LayerTypeConfig,
    PropertiesConfig,
    FilteringConfig,
  },
  props: {
    layer: {
      type: Object as PropType<VectorMapLayer>,
      required: true,
    },
  },
  emits: ['toggleLayer', 'deselectLayer'],
  setup(props) {
    const tab: Ref<AnnotationTypes | 'properties' | 'filters'> = ref('line');

    onMounted(() => {
      const found = MapStore.selectedMapLayers.value.find(
        (item) => item.id === props.layer.id,
      ) as VectorMapLayer;
      if (found && !found?.default_style) {
        found.default_style = {
          properties: { availableProperties: {} },
          layers: {
            fill: { enabled: true, color: '#888888' },
            line: { enabled: true, color: '#888888' },
            circle: { enabled: true, color: '#888888' },
            text: { enabled: true, color: '#888888' },
            'fill-extrusion': { enabled: true, color: '#888888' },
            heatmap: { enabled: false },
          },
        };
      } else if (found && found.default_style) {
        if (!found.default_style.layers) {
          found.default_style.layers = {
            fill: { enabled: true, color: '#888888' },
            line: { enabled: true, color: '#888888' },
            circle: { enabled: true, color: '#888888' },
            text: { enabled: true, color: '#888888' },
            'fill-extrusion': { enabled: true, color: '#888888' },
            heatmap: { enabled: false },
          };
        }
        if (!found.default_style.properties) {
          found.default_style.properties = {
            availableProperties: {},
          };
        }
      }
      if (found && found?.default_style?.layers) {
        // Go through and any true values properly initialize
        let foundFirstEnabledLayer = false;
        Object.entries(found.default_style.layers).forEach(([key, value]) => {
          if (found.default_style?.layers) {
            const layerKey = key as AnnotationTypes;
            if (value === true) {
              found.default_style.layers[layerKey] = { enabled: true, color: '#888888' };
            } else if (value !== false) {
              if (value.enabled && !foundFirstEnabledLayer) {
                foundFirstEnabledLayer = true;
                tab.value = key as AnnotationTypes;
              }
              if (!value.color) {
                found.default_style.layers[layerKey] = {
                  ...found.default_style.layers[layerKey] as VectorLayerDisplayConfig,
                  color: '#888888',
                };
              }
            }
          }
        });
      }
    });

    const layerStates = computed(() => {
      const annotationTypes: (AnnotationTypes)[] = [
        'line',
        'fill',
        'circle',
        'fill-extrusion',
        'text',
        'heatmap',
      ];
      const layers = props.layer.default_style?.layers;
      const results: (AnnotationTypes)[] = [];
      annotationTypes.forEach((type) => {
        if (layers && layers[type]) {
          if (layers[type] === true) {
            results.push(type);
          } else if (
            (layers[type] as VectorLayerDisplayConfig)?.enabled !== false
          ) {
            results.push(type);
          }
        }
      });
      return results;
    });

    return {
      tab,
      layerStates,
    };
  },
});
</script>

<template>
  <v-card-title>
    <v-row dense>
      <v-spacer />
      <v-tooltip text="Properties">
        <template #activator="{ props }">
          <v-icon
            class="icon-center"
            :class="{ 'selected-tab': tab === 'properties' }"
            v-bind="props"
            color="primary"
            size="x-small"
            @click="tab = 'properties'"
          >
            mdi-format-list-bulleted
          </v-icon>
        </template>
      </v-tooltip>
      <v-tooltip text="Filters">
        <template #activator="{ props }">
          <v-icon
            class="icon-center"
            :class="{ 'selected-tab': tab === 'filters' }"
            v-bind="props"
            color="primary"
            size="x-small"
            @click="tab = 'filters'"
          >
            mdi-filter
          </v-icon>
        </template>
      </v-tooltip>

      <v-tooltip text="Line Display">
        <template #activator="{ props }">
          <v-icon
            class="icon-center"
            :class="{ 'selected-tab': tab === 'line' }"
            v-bind="props"
            :color="layerStates.includes('line') ? 'primary' : ''"
            size="x-small"
            @click="tab = 'line'"
          >
            mdi-vector-line
          </v-icon>
        </template>
      </v-tooltip>
      <v-tooltip text="Polygon Display">
        <template #activator="{ props }">
          <v-icon
            class="icon-center"
            :class="{ 'selected-tab': tab === 'fill' }"
            v-bind="props"
            :color="layerStates.includes('fill') ? 'primary' : ''"
            size="x-small"
            @click="tab = 'fill'"
          >
            mdi-pentagon
          </v-icon>
        </template>
      </v-tooltip>
      <v-tooltip text="Point Display">
        <template #activator="{ props }">
          <v-icon
            class="icon-center"
            :class="{ 'selected-tab': tab === 'circle' }"
            v-bind="props"
            :color="layerStates.includes('circle') ? 'primary' : ''"
            size="x-small"
            @click="tab = 'circle'"
          >
            mdi-circle-outline
          </v-icon>
        </template>
      </v-tooltip>
      <v-tooltip text="Building Display">
        <template #activator="{ props }">
          <v-icon
            class="icon-center"
            :class="{ 'selected-tab': tab === 'fill-extrusion' }"
            v-bind="props"
            :color="
              layerStates.includes('fill-extrusion') ? 'primary' : ''
            "
            size="x-small"
            @click="tab = 'fill-extrusion'"
          >
            mdi-domain
          </v-icon>
        </template>
      </v-tooltip>
      <v-tooltip text="Text Display">
        <template #activator="{ props }">
          <v-icon
            class="icon-center"
            :class="{ 'selected-tab': tab === 'text' }"
            v-bind="props"
            :color="layerStates.includes('text') ? 'primary' : ''"
            size="x-small"
            @click="tab = 'text'"
          >
            mdi-format-text
          </v-icon>
        </template>
      </v-tooltip>
      <v-tooltip text="HeatMap Display">
        <template #activator="{ props }">
          <v-icon
            class="icon-center"
            :class="{ 'selected-tab': tab === 'heatmap' }"
            v-bind="props"
            :color="layerStates.includes('heatmap') ? 'primary' : ''"
            size="x-small"
            @click="tab = 'heatmap'"
          >
            mdi-heat-wave
          </v-icon>
        </template>
      </v-tooltip>

      <v-spacer />
    </v-row>
  </v-card-title>
  <v-card-text>
    <properties-config
      v-if="tab === 'properties'"
      :layer-id="layer.id"
    />
    <filtering-config
      v-else-if="tab === 'filters'"
      :layer-id="layer.id"
    />
    <layer-type-config
      v-else
      :layer-id="layer.id"
      :layer-type="tab"
    />
  </v-card-text>
</template>

<style scoped>
.tab {
  border: 1px solid lightgray;
}

.tab:hover {
  cursor: pointer;
}

.selected-tab {
  background-color: lightgray;
}

.icon-center {
  width:35px;
  height:35px;
  border: 1px solid lightgray;
  display: flex;
  align-items: center;
  justify-content: center;
}

</style>
