<script lang="ts">
import maplibregl, { Map } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import {
  PropType, Ref, defineComponent, onMounted, ref, shallowRef, watch,
} from 'vue';

export default defineComponent({
  name: 'MapComponent',
  props: {
    center: {
      type: Array as PropType<number[]>,
      required: true,
    },
    zoom: {
      type: Number,
      required: true,
    },
  },
  emits: ['update'],
  setup(props, { emit }) {
    const mapContainer: Ref<HTMLDivElement | null> = ref(null);
    const map: Ref<null | Map> = shallowRef(null);
    const mapLoaded = ref(false);
    const emitData = () => {
      if (map.value) {
        const centerCoords = map.value.getCenter();
        const center = [centerCoords.lng, centerCoords.lat];
        const zoom = map.value.getZoom();
        emit('update', { center, zoom });
      }
    };

    const initializeMap = () => {
      if (mapContainer.value) {
        map.value = new maplibregl.Map({
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
                minzoom: 0,
                maxzoom: 19,
              },
            ],
            // gets style from opensource style editor: https://github.com/maplibre/maputnik
            sprite: 'https://maputnik.github.io/osm-liberty/sprites/osm-liberty',
            glyphs: 'https://orangemug.github.io/font-glyphs/glyphs/{fontstack}/{range}.pbf',
          },
          center: props.center as [number, number],
          zoom: props.zoom, // Initial zoom level
        });
        map.value.on('load', () => {
          // Insert the layer beneath any symbol layer.
          mapLoaded.value = true;
          // One time call to setup Popup logic
          if (map.value) {
            map.value.on('zoomend', () => {
              emitData();
            });
            map.value.on('moveend', () => {
              emitData();
            });
          }
        });
      }
    };

    watch([() => props.center, () => props.zoom], () => {
      if (map.value) {
        const currentCenter = map.value.getCenter();
        if (currentCenter.lat !== props.center[1] || currentCenter.lng !== props.center[0]) {
          map.value.setCenter(props.center as [number, number]);
        }
        if (map.value.getZoom() !== props.zoom) {
          map.value.setZoom(props.zoom);
        }
      }
    });

    onMounted(() => {
      initializeMap();
    });

    return {
      mapContainer,
    };
  },
});
</script>

<template>
  <div
    id="contextMap"
    ref="mapContainer"
    class="map-context-container"
  />
</template>

<style>
@import "maplibre-gl/dist/maplibre-gl.css";

.map-context-container {
  width: 300px;
  height: 200px;
}
</style>
