import {
  Ref, computed, reactive, ref,
} from 'vue';
import {
  AnnotationTypes,
  ClickedProps,
  ColorFilters,
  Context,
  Dataset,
  DisplayConfiguration,
  LayerCollection,
  NetCDFData,
  NetCDFImageWorking,
  NetCDFLayer,
  RasterMapLayer,
  SearchableVectorData,
  VectorFeatureTableGraph,
  VectorMapLayer,
} from './types';
import UVdatApi from './api/UVDATApi';

export const VECTOR_PMTILES_URL = '/public/vectortiles/us.pmtiles';

async function isVectorBaseMapAvailable(vectorMapUrl: string) {
  const resp = await fetch(vectorMapUrl, { method: 'HEAD' });
  return Number(resp.headers.get('content-length') ?? 0) > 0 && resp.status === 200;
}

type SideBarCard = 'indicators' | 'charts' | 'searchableVectors';

export default class MapStore {
  public static osmBaseMap = ref<'none' | 'osm-raster' | 'osm-vector'>('osm-raster');

  public static userIsStaff = computed(() => !!UVdatApi.user?.is_staff);

  public static proModeButtonEnabled = ref(true);

  public static globalTime = ref(Math.floor(new Date().getTime() / 1000));

  public static displayConfiguration: Ref<DisplayConfiguration> = ref(
    { default_displayed_layers: [], enabled_ui: ['Collections', 'Datasets', 'Metadata'], default_tab: 'Scenarios' },
  );

  // Ability to toggle proMode so Staff users can see what other users see.
  public static proMode = computed(() => MapStore.userIsStaff.value && MapStore.proModeButtonEnabled.value);

  public static vectorBaseMapAvailable = ref(true);

  public static tvaOutlineLayer = ref(true);

  public static naipSatelliteLayer = ref(false);

  public static tdotSatelliteLayer = ref(false);

  // Collection
  public static availableCollections = ref<LayerCollection[]>([]);

  public static selectedCollection = ref<LayerCollection | null>(null);

  // Context
  public static availableContexts = ref<Context[]>([]);

  public static selectedContextId = ref<number | null>(null);

  // Datasets
  public static datasetsByContext = reactive<Record<number, Dataset[]>>({});

  // Layers
  public static mapLayersByDataset = reactive<Record<number, (VectorMapLayer | RasterMapLayer | NetCDFData)[]>>({});

  public static selectedMapLayers = ref<(VectorMapLayer | RasterMapLayer | NetCDFLayer)[]>([]);

  public static visibleMapLayers: Ref<Set<string>> = ref(new Set());

  // Net CDF Layers

  public static visibleNetCDFLayers: Ref<NetCDFImageWorking[]> = ref([]);

  public static selectedVectorMapLayers: Ref<VectorMapLayer[]> = computed(
    () => MapStore.selectedMapLayers.value.filter((layer) => layer.type === 'vector'),
  );

  public static selectedRasterMapLayers: Ref<RasterMapLayer[]> = computed(
    () => MapStore.selectedMapLayers.value.filter((layer) => layer.type === 'raster'),
  );

  public static selectedNetCDFMapLayers: Ref<NetCDFLayer[]> = computed(
    () => this.selectedMapLayers.value.filter((layer) => layer.type === 'netcdf'),
  );

  public static async loadCollections() {
    MapStore.availableCollections.value = await UVdatApi.getLayerCollections();
  }

  public static async loadContexts() {
    MapStore.availableContexts.value = await UVdatApi.getContexts();
  }

  public static async loadGlobalDatasets(filters:{ unconnected: boolean }) {
    const data = await UVdatApi.getGlobalDatasets(filters);
    return data;
  }

  public static async loadDatasets(contextId: number) {
    // Doesn't guard against multiple calls to loadDatasets with the same contextId,
    // but that scenario isn't a concern. Also, no cancellation behavior.
    if (contextId in MapStore.datasetsByContext) return;
    MapStore.datasetsByContext[contextId] = await UVdatApi.getContextDatasets(contextId);
  }

  public static async loadLayers(datasetId: number, force = false) {
    // Doesn't guard against multiple calls to loadDatasets with the same contextId,
    // but that scenario isn't a concern. Also, no cancellation behavior.
    if (datasetId in MapStore.mapLayersByDataset && !force) return;
    MapStore.mapLayersByDataset[datasetId] = await UVdatApi.getDatasetLayers(datasetId);
  }

  public static async getDisplayConfiguration(initial = false) {
    MapStore.displayConfiguration.value = await UVdatApi.getDisplayConfiguration();
    // Loading first time process default map layers
    if (initial && MapStore.displayConfiguration.value.default_displayed_layers.length) {
      const datasetIds = MapStore.displayConfiguration.value.default_displayed_layers.map((item) => item.dataset_id);
      const datasetIdLayers = await UVdatApi.getDatasetsLayers(datasetIds);
      const layerByDataset: Record<number, (VectorMapLayer | RasterMapLayer | NetCDFData)[]> = {};
      const toggleLayers: (VectorMapLayer | RasterMapLayer | NetCDFLayer)[] = [];
      const enabledLayers = MapStore.displayConfiguration.value.default_displayed_layers;
      datasetIdLayers.forEach((item) => {
        if (item.dataset_id !== undefined) {
          if (layerByDataset[item.dataset_id] === undefined) {
            layerByDataset[item.dataset_id] = [];
          }
          layerByDataset[item.dataset_id].push(item);
        }
        enabledLayers.forEach((enabledLayer) => {
          if (item.type === 'netcdf') {
            if (enabledLayer.dataset_id === item.dataset_id) {
              const netCDFLayers = ((item as NetCDFData).layers);
              for (let i = 0; i < netCDFLayers.length; i += 1) {
                const layer = netCDFLayers[i];
                if (layer.id === enabledLayer.id) {
                  toggleLayers.push(layer);
                }
              }
            }
          } else if (
            enabledLayer.type === item.type
            && enabledLayer.id === item.id
            && enabledLayer.dataset_id === item.dataset_id) {
            toggleLayers.push(item);
          }
        });
      });
      Object.keys(layerByDataset).forEach((datasetIdKey) => {
        const datasetId = parseInt(datasetIdKey, 10);
        if (!Number.isNaN(datasetId)) {
          MapStore.mapLayersByDataset[datasetId] = layerByDataset[datasetId];
        }
      });
      // Now we enable these default layers
      return toggleLayers;
    }
    return [];
  }

  public static mapLayerFeatureGraphs = computed(() => {
    const foundMapLayerFeatureGraphs: { name: string, id: number; graphs: VectorFeatureTableGraph[] }[] = [];
    MapStore.selectedVectorMapLayers.value.forEach((item) => {
      if (item.default_style?.mapLayerFeatureTableGraphs && item.default_style.mapLayerFeatureTableGraphs.length) {
        foundMapLayerFeatureGraphs.push({
          name: item.name,
          id: item.id,
          graphs: item.default_style.mapLayerFeatureTableGraphs,
        });
      }
    });
    return foundMapLayerFeatureGraphs;
  });

  public static mapLayerFeatureGraphsVisible = ref(false);

  public static vectorFeatureTableGraphVisible = ref(false);

  public static vectorFeatureTableData: Ref<{ layerId: number, vectorFeatureId: number, defaultGraphs?: string[] } | null> = ref(null);

  public static setVectorFeatureTableData = (layerId: number, vectorFeatureId: number, defaultGraphs?: string[]) => {
    if (MapStore.mapLayerFeatureGraphsVisible.value) {
      MapStore.mapLayerFeatureGraphsVisible.value = false;
    }
    MapStore.vectorFeatureTableData.value = {
      layerId,
      vectorFeatureId,
      defaultGraphs,
    };
    MapStore.vectorFeatureTableGraphVisible.value = true;
  };

  public static clearVectorFeatureTableData = () => {
    MapStore.vectorFeatureTableData.value = null;
    MapStore.vectorFeatureTableGraphVisible.value = false;
  };

  // Graph color mapping implementation
  public static enabledMapLayerFeatureColorMapping = ref(false);

  public static mapLayerFeatureColorMapping: Ref<Record<number, string>> = ref({});

  public static clearMapLayerFeatureColorMapping = () => {
    MapStore.mapLayerFeatureColorMapping.value = {};
  };

  // Searchable Vector Features

  public static mapLayerVectorSearchable = computed(() => {
    const foundMapLayerSearchable: { name: string, id: number; searchSettings: SearchableVectorData }[] = [];
    MapStore.selectedVectorMapLayers.value.forEach((item) => {
      if (item.default_style?.searchableVectorFeatureData) {
        foundMapLayerSearchable.push({
          name: item.name,
          id: item.id,
          searchSettings: item.default_style.searchableVectorFeatureData,
        });
      }
    });
    return foundMapLayerSearchable;
  });

  // ToolTips
  public static toolTipMenuOpen = ref(false);

  public static toolTipsEnabled = ref(false);

  public static toolTipDisplay: Ref<Record<string, boolean>> = ref({});

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  public static selectedFeatures: Ref<ClickedProps[]> = ref([]);

  public static addSelectedFeature = (clicked: ClickedProps) => {
    const found = MapStore.selectedFeatures.value.find((item) => item.id === clicked.id);
    if (!found) {
      MapStore.selectedFeatures.value.push(clicked);
    }
  };

  public static clearSelectedFeatures = () => {
    MapStore.selectedFeatures.value = [];
  };

  public static removeSelectedFeature = (id: number) => {
    const foundIndex = MapStore.selectedFeatures.value.findIndex((item) => item.id === id);
    if (foundIndex !== -1) {
      MapStore.selectedFeatures.value.splice(foundIndex, 1);
    }
  };

  public static selectedFeatureExpanded = ref(true);

  public static selectedIds = computed(() => MapStore.selectedFeatures.value.map((item) => item.properties.vectorfeatureid));

  public static hoveredFeatures: Ref<number[]> = ref([]);

  public static setHoveredFeature = (feature: number) => {
    MapStore.hoveredFeatures.value = [feature];
  };

  public static removeHoveredFeature = (feature: number) => {
    const foundIndex = MapStore.hoveredFeatures.value.findIndex((item) => item === feature);
    if (foundIndex !== -1) {
      MapStore.hoveredFeatures.value.splice(foundIndex, 1);
    }
  };

  public static removeHoveredFeatures = (features: number[]) => {
    MapStore.hoveredFeatures.value = MapStore.hoveredFeatures.value.filter((item) => !features.includes(item));
  };

  public static clearHoveredFeatures = () => {
    MapStore.hoveredFeatures.value = [];
  };

  public static pollForVectorBasemap = (pollInterval: number = 5000) => {
    let cancelled = false;

    async function check() {
      if (cancelled) return;

      if (await isVectorBaseMapAvailable(VECTOR_PMTILES_URL)) {
        MapStore.vectorBaseMapAvailable.value = true;
      } else {
        setTimeout(() => {
          check();
        }, pollInterval);
      }
    }
    check();

    return {
      cancel: () => {
        cancelled = true;
      },
    };
  };

  // SideBar Cards
  public static activeSideBarCard: Ref<undefined | SideBarCard> = ref(undefined);

  public static sideBarCardSettings: Ref<
  Record<SideBarCard, { name: string; width: number; icon: string, enabled: boolean; key: SideBarCard }>> = ref(
      {
        indicators: {
          name: 'Indicators', width: 450, icon: 'mdi-thermometer', enabled: false, key: 'indicators',
        },
        charts: {
          name: 'Chart', width: 650, icon: 'mdi-chart-bar', enabled: false, key: 'charts',
        },
        searchableVectors: {
          name: 'Search Vector Features', width: 300, icon: 'mdi-map-search-outline', enabled: false, key: 'searchableVectors',
        },

      },
    );

  public static sideBarOpen = computed(() => (
    !!(MapStore.activeSideBarCard && Object.values(MapStore.sideBarCardSettings.value).find((item) => item.enabled))));

  public static currentSideBarWidth = computed(() => {
    if (!MapStore.activeSideBarCard.value) {
      return 0;
    }
    return MapStore.sideBarCardSettings.value[MapStore.activeSideBarCard.value].width;
  });

  public static toggleContext = (card: SideBarCard) => {
    MapStore.sideBarCardSettings.value[card].enabled = !MapStore.sideBarCardSettings.value[card].enabled;
    if (MapStore.sideBarCardSettings.value[card].enabled) {
      MapStore.activeSideBarCard.value = card;
      Object.keys(MapStore.sideBarCardSettings.value).forEach((key) => {
        if (key !== card) {
          MapStore.sideBarCardSettings.value[key as SideBarCard].enabled = false;
        }
      });
    } else {
      const found = Object.values(MapStore.sideBarCardSettings.value).find((item) => item.enabled);
      if (found) {
        MapStore.activeSideBarCard.value = found.key;
      } else {
        MapStore.activeSideBarCard.value = undefined;
      }
    }
  };

  public static closeSideBar = () => {
    MapStore.activeSideBarCard.value = undefined;
    Object.keys(MapStore.sideBarCardSettings.value).forEach((key) => {
      MapStore.sideBarCardSettings.value[key as SideBarCard].enabled = false;
    });
  };

  public static vectorColorFilters: Ref<ColorFilters[]> = ref([]);

  public static toggleColorFilter = (layerId: number, layerType: (AnnotationTypes | 'all'), key: string, value: string) => {
    const foundIndex = MapStore.vectorColorFilters.value.findIndex(
      (item) => item.layerId === layerId && layerType === item.layerType && key === item.key,
    );
    if (foundIndex === -1) {
      MapStore.vectorColorFilters.value.push({
        layerId,
        layerType,
        type: 'not in',
        key,
        values: new Set<string>([value]),
      });
    } else {
      const found = MapStore.vectorColorFilters.value[foundIndex];
      if (found.values.has(value)) {
        found.values.delete(value);
        if (found.values.size === 0) {
          MapStore.vectorColorFilters.value.splice(foundIndex, 1);
        }
      } else {
        found.values.add(value);
      }
    }
  };

  // Graph Charts current Min/Max Values in unix_time
  public static graphChartsMinMax = ref({
    min: 0,
    max: 0,
    stepSize: 0,
  });

  public static timeLinked = ref(true);

  public static updateChartsMinMax = (min: number, max: number, stepSize: number) => {
    MapStore.graphChartsMinMax.value = { min, max, stepSize };
  };

  // Computes in Unix Time
  public static globalTimeRange: Ref<{ min: number; max: number, stepSize: number }> = computed(() => {
    let globalMin = Infinity;
    let globalMax = -Infinity;
    let stepSize = Infinity;
    MapStore.visibleNetCDFLayers.value.forEach((layer) => {
      if (layer.sliding) {
        const { min, max } = layer.sliding;
        const stepsize = layer.images.length;
        stepSize = Math.min(stepSize, (max - min) / stepsize);
        globalMin = Math.min(globalMin, min);
        globalMax = Math.max(globalMax, max);
      }
    });
    if ((MapStore.mapLayerFeatureGraphsVisible.value && MapStore.mapLayerFeatureGraphs.value.length) || MapStore.vectorFeatureTableGraphVisible.value) {
      globalMin = Math.min(globalMin, MapStore.graphChartsMinMax.value.min);
      globalMax = Math.max(globalMax, MapStore.graphChartsMinMax.value.max);
      stepSize = Math.min(stepSize, MapStore.graphChartsMinMax.value.stepSize);
    }
    return { min: globalMin, max: globalMax, stepSize };
  });
}
