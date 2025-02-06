<script lang="ts">
import {
  computed, defineComponent, inject, ref,
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
import UVdatApi from '../api/UVDATApi';

export default defineComponent({
  components: {
    MapVue,
    MapTypePicker,
    SourceSelection,
    MapLegend,
    IndicatorFilterableList,
    SelectedFeatureList,
    Charts,
  },
  setup() {
    const oauthClient = inject<OAuthClient>('oauthClient');
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

    const selectedContext = computed(
      () => MapStore.availableContexts.value.find(
        (context) => context.id === MapStore.selectedContextId.value,
      ),
    );

    const indicators = computed(() => selectedContext.value?.indicators ?? []);
    const hasIndicators = computed(() => indicators.value.length > 0);
    const showIndicatorsUserToggle = ref(true);
    const showIndicators = computed(() => hasIndicators.value && MapStore.sideBarCardSettings.value.indicators.enabled);
    const chartView = computed(() => MapStore.activeSideBarCard.value === 'charts');
    watch(hasIndicators, () => {
      if (hasIndicators.value && showIndicatorsUserToggle.value) {
        MapStore.toggleContext('indicators');
      }
    });
    const toggleIndicators = () => {
      showIndicatorsUserToggle.value = !showIndicatorsUserToggle.value;
      MapStore.toggleContext('indicators');
    };
    const toggleChartView = () => {
      MapStore.toggleContext('charts');
      MapStore.chartsOpen.value = MapStore.sideBarCardSettings.value.charts.enabled;
    };

    const osmBaseMapType = computed(() => {
      const type = MapStore.osmBaseMap.value;
      if (type === 'none') return 'None';
      if (type === 'osm-raster') return 'Raster';
      if (type === 'osm-vector') return 'Vector';
      throw new Error('Invalid base map type');
    });

    return {
      indicators,
      hasIndicators,
      showIndicators,
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
      toggleIndicators,
      sideBarWidth: MapStore.currentSideBarWidth,
      sideBarOpen: MapStore.sideBarOpen,
      activeSideBar: MapStore.activeSideBarCard,
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
    <v-tooltip text="Indicator List">
      <template #activator="{ props }">
        <v-icon
          v-bind="props"
          class="mx-2"
          size="30"
          :color="showIndicators ? 'primary' : ''"
          :disabled="!hasIndicators"
          @click="toggleIndicators()"
        >
          mdi-thermometer
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
    <MapVue />
    <selected-feature-list />
    <v-navigation-drawer :model-value="sideBarOpen" location="right" :width="sideBarWidth" permanent>
      <indicator-filterable-list v-if="activeSideBar === 'indicators'" :indicators="indicators" />
      <charts v-if="activeSideBar === 'charts'" />
    </v-navigation-drawer>
    <MapLegend class="static-map-legend" />
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
