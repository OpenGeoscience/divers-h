<script lang="ts">
import {
  PropType, Ref, defineComponent, onMounted, ref,
} from 'vue';
import maplibre, { Map } from 'maplibre-gl';

export default defineComponent({
  name: 'MapSelection',
  props: {
    defaultMapSettings: {
      type: Object as PropType<{ location: {
        center: [number, number];
        zoom: number;
      } }>,
      required: true,
    },
  },
  emits: ['update:settings'],
  setup(props, { emit }) {
    const mapContainer = ref<HTMLDivElement | null>(null);
    const mapInstance: Ref<Map | null> = ref(null);

    const mapMove = () => {
      if (mapInstance.value) {
        const center = mapInstance.value.getCenter();
        const zoom = mapInstance.value.getZoom();
        emit('update:settings', {
          location: {
            center: [center.lng, center.lat],
            zoom,
          },
        });
      }
    };
    // Initialize Map
    onMounted(() => {
      if (!mapContainer.value) return;
      mapInstance.value = new maplibre.Map({
        container: mapContainer.value,
        style: {
          version: 8,
          sources: {
            osm: {
              type: 'raster',
              tiles: [
                'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
                'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
                'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
              ],
              tileSize: 256,
              attribution: '© OpenStreetMap contributors',
            },
          },
          layers: [
            {
              id: 'osm-tiles',
              type: 'raster',
              source: 'osm',
              maxzoom: 19,
            },
          ],
        },
        center: props.defaultMapSettings.location.center,
        zoom: props.defaultMapSettings.location.zoom,
      });
      mapInstance.value.on('load', () => {
        if (mapInstance.value) {
          mapInstance.value.on('move', mapMove);
        }
      });
    });

    return {
      mapContainer,
    };
  },
});
</script>

<template>
  <div ref="mapContainer" class="map-container" />
</template>

<style scoped>
  .map-container {
    width: 100%;
    height: 400px;
  }
</style>
