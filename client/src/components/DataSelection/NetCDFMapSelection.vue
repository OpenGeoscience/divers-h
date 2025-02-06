<script lang="ts">
import MapboxDraw from '@mapbox/mapbox-gl-draw';
import {
  PropType, Ref, computed, defineComponent, onMounted, ref,
} from 'vue';
import maplibre, { Map } from 'maplibre-gl';
import { TxRectMode, drawStyle } from './mapbox-draw-rectangle';

export default defineComponent({
  name: 'MapComponent',
  props: {
    maxPanBounds: {
      type: Array as PropType<number[]>,
      required: true,
      validator(value: [number, number, number, number]) {
        return value.length === 4 && value.every(Number.isFinite);
      },
    },
    editBounds: {
      type: Array as PropType<number[]>,
      required: true,
      validator(value: [number, number, number, number]) {
        return value.length === 4 && value.every(Number.isFinite);
      },
    },
    padding: {
      type: Number,
      default: 30,
    },
  },
  emits: ['update:editBounds'],
  setup(props, { emit }) {
    const mapContainer = ref<HTMLDivElement | null>(null);
    const mapInstance = ref<Map | null>(null);
    const drawInstance = ref<MapboxDraw | null>(null);
    const boxId: Ref<string[]> = ref([]);
    const mouseDown = ref(false);
    const changeCoordinates = ref(false);
    const updatedBounds: Ref<number[]> = ref([]);
    // Compute bounds for editing polygon
    const xmin = computed(() => props.editBounds[0]);
    const ymin = computed(() => props.editBounds[1]);
    const xmax = computed(() => props.editBounds[2]);
    const ymax = computed(() => props.editBounds[3]);

    const createBoundingBoxFeature = (minX: number, minY: number, maxX: number, maxY: number) => ({
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [minX, minY],
            [minX, maxY],
            [maxX, maxY],
            [maxX, minY],
            [minX, minY],
          ],
        ],
      },
      properties: {},
    });

    const AdjustCappedBounds = () => {
      if (updatedBounds.value.length === 4) {
        const [xminMax, yminMax, xmaxMax, ymaxMax] = props.maxPanBounds;
        const [xmin1, ymin1, xmax1, ymax1] = updatedBounds.value;
        const cappedBounds = [
          Math.max(xmin1, xminMax), // Ensure xmin1 is at least xminMax
          Math.max(ymin1, yminMax), // Ensure ymin1 is at least yminMax
          Math.min(xmax1, xmaxMax), // Ensure xmax1 is at most xmaxMax
          Math.min(ymax1, ymaxMax), // Ensure ymax1 is at most ymaxMax
        ];
        if (drawInstance.value) {
          drawInstance.value?.delete(boxId.value);
          const newbboxFeature = createBoundingBoxFeature(
            cappedBounds[0],
            cappedBounds[1],
            cappedBounds[2],
            cappedBounds[3],
          ) as GeoJSON.Feature & { id?: string };
          newbboxFeature.id = 'rectangleId';
          boxId.value = drawInstance.value.add(newbboxFeature);
          drawInstance.value.changeMode('tx_poly', {
            featureId: newbboxFeature.id, // required
            canRotate: false,
            canTrash: false,
            canSelectFeature: false,
          });
        }

        emit('update:editBounds', cappedBounds);
      }
    };
    const initializeDraw = () => {
      if (!mapInstance.value) return;

      drawInstance.value = new MapboxDraw({
        displayControlsDefault: false,
        controls: {
        },

        modes: { tx_poly: TxRectMode, ...MapboxDraw.modes },

        styles: drawStyle,
      });
      mapInstance.value.addControl(drawInstance.value as unknown as IControl, 'top-right');

      // Add initial editable polygon
      const bboxFeature = createBoundingBoxFeature(
        xmin.value,
        ymin.value,
        xmax.value,
        ymax.value,
      ) as GeoJSON.Feature & { id?: string };
      bboxFeature.id = 'rectangleId';
      boxId.value = drawInstance.value.add(bboxFeature);
      drawInstance.value.changeMode('tx_poly', {
        featureId: bboxFeature.id, // required
        canRotate: false,
        canTrash: false,
      });

      mapInstance.value.on('mousedown', () => {
        mouseDown.value = true;
      });
      mapInstance.value.on('mouseup', () => {
        if (mouseDown.value && changeCoordinates.value) {
          AdjustCappedBounds();
        }
        mouseDown.value = false;
        changeCoordinates.value = false;
      });

      // Listen to updates to the editable polygon
      mapInstance.value.on('draw.update', (e: MapboxDraw.DrawUpdateEvent) => {
        const coordinates = (e.features[0].geometry as GeoJSON.Polygon).coordinates[0];
        if (e.action !== 'change_coordinates') {
          return;
        }
        changeCoordinates.value = true;
        let xmin1 = Infinity;
        let ymin1 = Infinity;
        let xmax1 = -Infinity;
        let ymax1 = -Infinity;

        // Iterate through all coordinates to calculate bounds
        coordinates.forEach(([x, y]) => {
          if (x < xmin1) xmin1 = x;
          if (y < ymin1) ymin1 = y;
          if (x > xmax1) xmax1 = x;
          if (y > ymax1) ymax1 = y;
        });
        updatedBounds.value = [xmin1, ymin1, xmax1, ymax1];
        // If any of the bounds are outside the max
      });
    };

    // Initialize Map
    onMounted(() => {
      if (!mapContainer.value) return;
      const adjustedX = ((props.maxPanBounds[2] - props.maxPanBounds[0]) / 2.0) * (props.padding * 0.01);
      const adjustedY = ((props.maxPanBounds[3] - props.maxPanBounds[1]) / 2.0) * (props.padding * 0.01);
      // Adjust the bounds
      const adjustedBounds = [
        [
          Math.max(-179.9, props.maxPanBounds[0] - adjustedX), // Clamp longitude to [-180, 180]
          Math.max(-89.9, props.maxPanBounds[1] - adjustedY), // Clamp latitude to [-90, 90]
        ],
        [
          Math.min(179.9, props.maxPanBounds[2] + adjustedX), // Clamp longitude to [-180, 180]
          Math.min(89.9, props.maxPanBounds[3] + adjustedY), // Clamp latitude to [-90, 90]
        ],
      ];
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
        center: [(xmin.value + xmax.value) / 2, (ymin.value + ymax.value) / 2],
        zoom: 12,
        maxBounds: adjustedBounds as [[number, number], [number, number]],
      });
      mapInstance.value.on('load', initializeDraw);
      mapInstance.value.fitBounds(adjustedBounds as [[number, number], [number, number]]);
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
