<script lang="ts">
import {
  computed, defineComponent, inject, onMounted, ref,
  watch,
} from 'vue';
import OAuthClient from '@girder/oauth-client';
import MapVue from '../components/Map.vue';
import SourceSelection from './SourceSelection.vue';
import MapStore from '../MapStore';
import MapLegend from '../components/MapLegend.vue';
import IndicatorFilterableList from '../components/Indicators/IndicatorFilterableList.vue';
import MapTypePicker from '../components/MapTypePicker.vue';
import SelectedFeatureList from '../components/FeatureSelection/SelectedFeatureList.vue';
import Charts from '../components/Charts/Charts.vue';
import MapLayerTableGraph from '../components/TabularData/MapLayerTableGraph.vue';
import VectorFeatureTableGraph from '../components/TabularData/VectorFeatureTableGraph.vue';
import UVdatApi from '../api/UVDATApi';
import VectorFeatureSearch from '../components/VectorFeatureSearch/VectorFeatureSearch.vue';
// eslint-disable-next-line import/no-cycle
import { toggleLayerSelection } from '../map/mapLayers';

export default defineComponent({
  components: {
    MapVue,
    MapTypePicker,
    SourceSelection,
    MapLegend,
    IndicatorFilterableList,
    SelectedFeatureList,
    Charts,
    MapLayerTableGraph,
    VectorFeatureTableGraph,
    VectorFeatureSearch,
  },
  setup() {
    const oauthClient = inject<OAuthClient>('oauthClient');
    const loading = ref(false);
    const drawerOpen = ref(true);
    if (oauthClient === undefined) {
      throw new Error('Must provide "oauthClient" into component.');
    }
    const loginText = computed(() => (UVdatApi.user ? 'Logout' : 'Login'));
    const logInOrOut = async () => {
      if (MapStore.userIsStaff.value) {
        await oauthClient.logout();
        MapStore.proModeButtonEnabled.value = false;
        // Also log out the server-side session to avoid confusion
        window.location.href = `${UVdatApi.origin}/accounts/logout/`;
      } else {
        oauthClient.redirectToLogin();
      }
    };

    onMounted(async () => {
      loading.value = true;
      const layers = await MapStore.getDisplayConfiguration(true);
      loading.value = false;
      layers.forEach((layer) => toggleLayerSelection(layer));
    });

    watch(MapStore.userIsStaff, () => {
      if (!MapStore.userIsStaff.value) {
        MapStore.proModeButtonEnabled.value = false;
      }
    }, { immediate: true });
    const toolTipOpen = computed(() => MapStore.toolTipsEnabled.value);

    const toggleProModeButton = (val: boolean) => {
      MapStore.proModeButtonEnabled.value = val;
    };
    const toggleToolTips = (val: boolean) => {
      MapStore.toolTipsEnabled.value = val;
    };

    const selectedFeatures = computed(() => MapStore.selectedFeatures.value);

    const selectedIds = computed(() => MapStore.selectedIds.value);

    const hasMapLayerVectorGraphs = computed(() => !!MapStore.mapLayerFeatureGraphs.value.length);

    const hasVectorFeatureSearch = computed(() => !!MapStore.mapLayerVectorSearchable.value.length);

    const toggleMapLayerVectorGraphs = () => {
      if (MapStore.mapLayerFeatureGraphs.value.length) {
        MapStore.mapLayerFeatureGraphsVisible.value = !MapStore.mapLayerFeatureGraphsVisible.value;
        if (MapStore.mapLayerFeatureGraphsVisible.value) {
          MapStore.vectorFeatureTableGraphVisible.value = false;
        }
      }
    };

    const toggleVectorFeatureSearch = () => {
      if (MapStore.mapLayerVectorSearchable.value.length) {
        MapStore.toggleContext('searchableVectors');
      }
    };

    const chartView = computed(() => MapStore.activeSideBarCard.value === 'charts');
    const toggleChartView = () => {
      MapStore.toggleContext('charts');
    };

    const osmBaseMapType = computed(() => {
      const type = MapStore.osmBaseMap.value;
      if (type === 'none') return 'None';
      if (type === 'osm-raster') return 'Raster';
      if (type === 'osm-vector') return 'Vector';
      throw new Error('Invalid base map type');
    });

    const rightSideBarPadding = computed(() => {
      if (MapStore.sideBarOpen.value && MapStore.activeSideBarCard.value) {
        return `${MapStore.sideBarCardSettings.value[MapStore.activeSideBarCard.value].width + 20}px`;
      }
      return '20px';
    });

    const SideBarHasData = computed(() => {
      if (MapStore.activeSideBarCard.value === 'searchableVectors') {
        return !!MapStore.mapLayerVectorSearchable.value.length;
      }
      if (MapStore.activeSideBarCard.value === 'charts') {
        return true;
      }
      return false;
    });

    return {
      oauthClient,
      loginText,
      logInOrOut,
      userIsStaff: MapStore.userIsStaff,
      drawerOpen,
      toolTipOpen,
      toggleToolTips,
      selectedFeatures,
      selectedIds,
      osmBaseMapState: MapStore.osmBaseMap,
      osmBaseMapType,
      vectorBaseMapAvailable: MapStore.vectorBaseMapAvailable,
      proModeButtonEnabled: MapStore.proModeButtonEnabled,
      toggleProModeButton,
      tvaOutlineLayer: MapStore.tvaOutlineLayer,
      naipSatelliteLayer: MapStore.naipSatelliteLayer,
      tdotSatelliteLayer: MapStore.tdotSatelliteLayer,
      chartView,
      toggleChartView,
      hasMapLayerVectorGraphs,
      toggleMapLayerVectorGraphs,
      mapLayerVectorGraphsVisible: MapStore.mapLayerFeatureGraphsVisible,
      vectorFeatureTableGraphVisible: MapStore.vectorFeatureTableGraphVisible,
      vectorFeatureTableData: MapStore.vectorFeatureTableData,
      mapLayerFeatureGraphs: MapStore.mapLayerFeatureGraphs,
      mapLayerVectorSearch: MapStore.mapLayerVectorSearchable,
      hasVectorFeatureSearch,
      toggleVectorFeatureSearch,
      sideBarWidth: MapStore.currentSideBarWidth,
      sideBarOpen: MapStore.sideBarOpen,
      activeSideBar: MapStore.activeSideBarCard,
      rightSideBarPadding,
      SideBarHasData,
      loading,
    };
  },
});
</script>

<template>
  <v-app-bar app>
    <v-tooltip>
      <div>
        <p>Map Layers</p>
        <p>Current: <strong>{{ osmBaseMapType }}</strong></p>
      </div>
      <template #activator="{ props: tooltipProps }">
        <v-menu :close-on-content-click="false">
          <template #activator="{ props: menuProps }">
            <v-icon
              v-bind="{ ...tooltipProps, ...menuProps }"
              class="mx-2"
              size="30"
              :color="osmBaseMapState !== 'none' ? 'primary' : ''"
            >
              mdi-map
            </v-icon>
          </template>
          <v-card>
            <v-card-text>
              <div class="text-subtitle-2">
                Base Map
              </div>
              <map-type-picker v-model="osmBaseMapState" />
              <div class="text-subtitle-2">
                Map Layers
                <v-checkbox v-model="tvaOutlineLayer" density="compact" label="TVA Outline" hide-details />
                <v-checkbox v-model="naipSatelliteLayer" density="compact" hide-details>
                  <template #label>
                    USA Satellite Imagery
                    <v-tooltip location="bottom">
                      From the National Agriculture Imagery Program (NAIP)
                      <template #activator="{ props }">
                        <v-icon size="x-small" class="ml-2" v-bind="props">
                          mdi-information
                        </v-icon>
                      </template>
                    </v-tooltip>
                  </template>
                </v-checkbox>
                <v-checkbox v-model="tdotSatelliteLayer" density="compact" hide-details>
                  <template #label>
                    TDOT Satellite Imagery
                    <v-tooltip location="bottom">
                      From the Tennessee Dept. Of Transportation
                      <template #activator="{ props }">
                        <v-icon size="x-small" class="ml-2" v-bind="props">
                          mdi-information
                        </v-icon>
                      </template>
                    </v-tooltip>
                  </template>
                </v-checkbox>
              </div>
            </v-card-text>
          </v-card>
        </v-menu>
      </template>
    </v-tooltip>

    <v-tooltip text="Feature Tooltips">
      <template #activator="{ props }">
        <v-icon
          v-bind="props"
          class="mx-2"
          size="30"
          :color="toolTipOpen ? 'primary' : ''"
          @click="toggleToolTips(!toolTipOpen)"
        >
          mdi-tooltip-text-outline
        </v-icon>
      </template>
    </v-tooltip>
    <v-tooltip v-if="hasMapLayerVectorGraphs" text="Tabular Data Graphs">
      <template #activator="{ props }">
        <v-icon
          v-bind="props"
          class="mx-2"
          size="30"
          :color="mapLayerVectorGraphsVisible ? 'primary' : ''"
          @click="toggleMapLayerVectorGraphs()"
        >
          mdi-chart-line
        </v-icon>
      </template>
    </v-tooltip>
    <v-tooltip v-if="hasVectorFeatureSearch" text="Vector Feature Search">
      <template #activator="{ props }">
        <v-icon
          v-bind="props"
          class="mx-2"
          size="30"
          :color="activeSideBar === 'searchableVectors' ? 'primary' : ''"
          @click="toggleVectorFeatureSearch()"
        >
          mdi-map-search-outline
        </v-icon>
      </template>
    </v-tooltip>

    <v-tooltip text="Chart View">
      <template #activator="{ props }">
        <v-icon
          v-bind="props"
          class="mx-2"
          size="30"
          :color="chartView ? 'primary' : ''"
          @click="toggleChartView()"
        >
          mdi-chart-bar
        </v-icon>
      </template>
    </v-tooltip>
    <v-tooltip
      v-if="userIsStaff"
      text="Pro Mode (Editing Layer Views)"
    >
      <template #activator="{ props }">
        <v-icon
          v-bind="props"
          class="mx-2"
          size="30"
          :color="proModeButtonEnabled ? 'primary' : ''"
          @click="toggleProModeButton(!proModeButtonEnabled)"
        >
          mdi-professional-hexagon
        </v-icon>
      </template>
    </v-tooltip>
    <v-spacer />
    <v-btn v-if="userIsStaff" to="/admin">
      Admin
    </v-btn>
    <v-btn @click="logInOrOut">
      {{ loginText }}
    </v-btn>
    <v-tooltip text="Documentation" location="bottom">
      <template #activator="{ props }">
        <v-btn
          v-bind="props"
          class="mx-2"
          variant="text"
          href="/docs"
          target="_blank"
          icon="mdi-book-open-variant-outline"
        />
      </template>
    </v-tooltip>
  </v-app-bar>
  <v-container>
    <v-navigation-drawer
      :model-value="drawerOpen"
      permanent
      width="375"
      class="main-area drawer"
    >
      <source-selection />
    </v-navigation-drawer>
    <v-row v-if="!loading" dense class="fill-height">
      <v-col class="d-flex flex-column fill-height" style="min-height: 90vh">
        <MapVue />
        <MapLayerTableGraph
          v-if="mapLayerVectorGraphsVisible && mapLayerFeatureGraphs.length" />
        <VectorFeatureTableGraph
          v-else-if="vectorFeatureTableGraphVisible && vectorFeatureTableData"
          :map-layer-id="vectorFeatureTableData.layerId"
          :vector-feature-id="vectorFeatureTableData.vectorFeatureId" />
      </v-col>
    </v-row>
    <selected-feature-list />
    <v-navigation-drawer v-if="SideBarHasData" :model-value="sideBarOpen" location="right" :width="sideBarWidth" permanent>
      <indicator-filterable-list v-if="activeSideBar === 'indicators'" :indicators="indicators" />
      <charts v-if="activeSideBar === 'charts'" />
      <VectorFeatureSearch v-if="mapLayerVectorSearch.length && activeSideBar === 'searchableVectors'" />
    </v-navigation-drawer>
    <MapLegend class="static-map-legend" :style="`right: ${rightSideBarPadding};transition: all 0.2s ease`" />
  </v-container>
</template>

<style scoped>
.main-area {
  position: absolute;
  top: 65px;
  height: calc(100% - 70px);
  width: 100%;
}
.static-map-legend {
  position: absolute;
  top: 90px;
  right: 20px;
  max-height: calc(100% - 125px);
  z-index: 2;
  overflow-y: auto;
}

</style>
