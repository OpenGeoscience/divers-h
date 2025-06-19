<script lang="ts">
import maplibregl, { Map, VectorTileSource } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Protocol as PMTilesProtocol } from 'pmtiles';
import {
  Ref, defineComponent, onMounted, ref, shallowRef, watch,
} from 'vue';
import MapStore from '../MapStore';
import {
  updateSelected,
} from '../map/mapVectorLayers';
import { popupLogic } from '../map/mouseEvents';
import { setInternalMap } from '../map/mapLayers';
import TVA_GEOJSON_RAW from '../assets/tva.geojson?raw';
import vectorMapStyles from '../assets/basic-map-styles.json';
import oauthClient from '../plugins/Oauth';
import { updateFMVFlightPathSelected } from '../map/mapFMVLayer';

const TVA_GEOJSON = JSON.parse(TVA_GEOJSON_RAW) as GeoJSON.GeoJSON;
const OSM_VECTOR_ID = 'osm-vector';

function reloadPmTileProtocol() {
  maplibregl.addProtocol('pmtiles', new PMTilesProtocol().tile);
}

function reloadPmTileSource(source: VectorTileSource) {
  // Workaround: clear internal PMTile promise cache
  reloadPmTileProtocol();
  // Triggers a source refresh. Better than calling source.load(), because setSourceProperty()
  // aborts any in-progress load requests.
  source.setSourceProperty(() => {});
}

reloadPmTileProtocol();

const VECTOR_LAYERS = vectorMapStyles.layers.map((layer) => {
  if ('source' in layer) {
    return {
      ...layer,
      source: OSM_VECTOR_ID,
    };
  }
  return layer;
}) as maplibregl.LayerSpecification[];
const VECTOR_LAYER_IDS = VECTOR_LAYERS.map((layer) => layer.id);

export default defineComponent({
  name: 'MapComponent',
  props: {
    bottomPanel: {
      type: Boolean,
      default: false,
    },
  },
  setup() {
    const mapContainer: Ref<HTMLDivElement | null> = ref(null);
    const map: Ref<null | Map> = shallowRef(null);
    const mapAlert = ref(false);
    const mapAlertMessage = ref('');

    function handleFailedVectorSource() {
      mapAlert.value = true;
      mapAlertMessage.value = 'Could not load vector maps. Falling back to raster maps.';
      MapStore.osmBaseMap.value = 'osm-raster';
      MapStore.vectorBaseMapAvailable.value = false;
    }

    const initializeMap = () => {
      if (mapContainer.value) {
        const center = MapStore.displayConfiguration.value.default_map_settings?.location.center || [-86.1794, 34.8019];
        const zoom = MapStore.displayConfiguration.value.default_map_settings?.location.zoom || 6;
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
              'tva-region': {
                type: 'geojson',
                data: TVA_GEOJSON,
              },
              'naip-imagery': {
                type: 'raster',
                tiles: [
                  // eslint-disable-next-line vue/max-len
                  'https://gis.apfo.usda.gov/arcgis/rest/services/NAIP/USDA_CONUS_PRIME/ImageServer/tile/{z}/{y}/{x}?blankTile=false',
                ],
                tileSize: 256,
              },
              'tdot-imagery': {
                type: 'raster',
                tiles: [
                  `https://tnmap.tn.gov/arcgis/services/BASEMAPS/IMAGERY_WEB_MERCATOR/MapServer/WMSServer?${[
                    'version=1.3.0',
                    'service=WMS',
                    'request=GetMap',
                    'layers=0', // corresponds to "Tennessee Ortho Index"
                    'styles=',
                    'crs=EPSG:3857',
                    'format=image/png',
                    'width=256',
                    'height=256',
                    'transparent=true',
                    'bbox={bbox-epsg-3857}',
                  ].join('&')}`,
                ],
                tileSize: 256,
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
              {
                id: 'naip-imagery-tiles',
                type: 'raster',
                source: 'naip-imagery',
                paint: {},
                layout: {
                  visibility: MapStore.naipSatelliteLayer.value ? 'visible' : 'none',
                },
              },
              {
                id: 'tdot-imagery-tiles',
                type: 'raster',
                source: 'tdot-imagery',
                paint: {},
                layout: {
                  visibility: MapStore.tdotSatelliteLayer.value ? 'visible' : 'none',
                },
              },
              {
                id: 'tva-region',
                type: 'line',
                source: 'tva-region',
                layout: {
                  visibility: MapStore.tvaOutlineLayer.value ? 'visible' : 'none',
                },
                paint: {
                  'line-color': '#d39700',
                  'line-width': 3,
                },
              },
            ],
            // gets style from opensource style editor: https://github.com/maplibre/maputnik
            sprite: 'https://maputnik.github.io/osm-liberty/sprites/osm-liberty',
            glyphs: 'https://orangemug.github.io/font-glyphs/glyphs/{fontstack}/{range}.pbf',
          },
          center,
          zoom,
        });
        if (map.value) {
          setInternalMap(map as Ref<Map>);
        }
        map.value.on('error', (err: ErrorEvent & { sourceId?: string, isSourceLoaded?: boolean }) => {
          if (err.type === 'error' && err?.sourceId === OSM_VECTOR_ID && !err?.isSourceLoaded) {
            handleFailedVectorSource();
            popupLogic(map);
          } else {
            // eslint-disable-next-line no-console
            console.error(err);
          }
        });

        map.value.on('load', () => {
          popupLogic(map);
        });
      }
    };

    onMounted(() => {
      initializeMap();
      if (map.value) {
        map.value.setTransformRequest((url) => {
          // Auth headers are only needed for our own Tile endpoints
          if (url.startsWith(window.location.origin) || url.startsWith('http://localhost:8000/api/v1')) {
            return {
              url,
              headers: oauthClient.authHeaders,
            };
          }
          return { url };
        });
      }
    });

    watch(MapStore.osmBaseMap, (mapType) => {
      if (!map.value) return;

      if (MapStore.osmBaseMap.value === 'osm-vector') {
        const source = map.value.getSource('osm-vector') as VectorTileSource;
        if (!source.loaded()) {
          reloadPmTileSource(source);
        }
      }

      map.value.setLayoutProperty('osm-tiles', 'visibility', mapType === 'osm-raster' ? 'visible' : 'none');
      VECTOR_LAYER_IDS
        .filter((layerId) => !!map.value?.getLayer(layerId))
        .forEach((layerId) => {
          map.value?.setLayoutProperty(layerId, 'visibility', mapType === 'osm-vector' ? 'visible' : 'none');
        });
    }, { immediate: true });

    watch(MapStore.tvaOutlineLayer, (visible) => {
      map.value?.setLayoutProperty('tva-region', 'visibility', visible ? 'visible' : 'none');
    });

    watch(MapStore.naipSatelliteLayer, (visible) => {
      map.value?.setLayoutProperty('naip-imagery-tiles', 'visibility', visible ? 'visible' : 'none');
    });

    watch(MapStore.tdotSatelliteLayer, (visible) => {
      map.value?.setLayoutProperty('tdot-imagery-tiles', 'visibility', visible ? 'visible' : 'none');
    });

    watch(
      [MapStore.selectedFeatures, MapStore.enabledMapLayerFeatureColorMapping],
      () => {
        if (map.value) {
          updateSelected(map.value);
          updateFMVFlightPathSelected(map.value);
        }
      },
      { deep: true },
    );

    watch(
      MapStore.hoveredFeatures,
      () => {
        if (map.value
        && (MapStore.mapLayerFeatureGraphsVisible.value || MapStore.activeSideBarCard.value === 'searchableVectors')) {
          updateSelected(map.value);
        }
      },
      { deep: true },
    );

    return {
      mapContainer,
      mapAlert,
      mapAlertMessage,
    };
  },
});
</script>

<template>
  <div class="map-container">
    <div
      id="map"
      ref="mapContainer"
      class="map-content"
    />
  </div>
  <v-snackbar v-model="mapAlert" content-class="map-alert">
    <v-alert type="warning" variant="tonal">
      {{ mapAlertMessage }}
    </v-alert>
  </v-snackbar>
</template>

<style>
@import "maplibre-gl/dist/maplibre-gl.css";

.map-container {
  display: flex;
  flex-grow: 1;
  width: 100%;
}

.map-content {
  flex-grow: 1;
  width: 100%;
  min-height: 300px; /* Ensure map has a minimum height */
}

.map-alert > .v-snackbar__content {
  padding: 0;
}
</style>
