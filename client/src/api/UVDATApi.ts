import axios, { AxiosInstance, AxiosRequestHeaders } from 'axios';
import { ref } from 'vue';
import OauthClient from '@girder/oauth-client/dist/oauth-client';
import {
  AbstractMapLayer,
  Chart,
  Context,
  ContextWithIds,
  Dataset,
  DerivedRegion,
  FeatureGraphData,
  FileItem,
  LayerCollection,
  LayerCollectionLayer,
  LayerRepresentation,
  NetCDFData,
  NetCDFImages,
  NetCDFLayer,
  NetworkNode,
  ProcessingTask,
  PropertySummary,
  RasterData,
  RasterMapLayer,
  SimulationType,
  TableSummary,
  VectorMapLayer,
} from '../types';

export const currentError = ref<string>();

export interface MetadataResponse {
  levels: number;
  sizeX: number;
  sizeY: number;
  tileWidth: number;
  tileHeight: number;
  magnification: number | null;
  mm_x: number;
  mm_y: number;
  dtype: string; // Data type, e.g., "float32"
  bandCount: number;
  geospatial: boolean;
  sourceLevels: number;
  sourceSizeX: number;
  sourceSizeY: number;
  bounds?: Bounds;
  projection: string | null;
  sourceBounds?: Bounds;
  bands: Record<string, BandInfo>;
  frames: FrameInfo[] | false;
}

interface Bounds {
  ll: Coordinate; // Lower-left coordinate
  ul: Coordinate; // Upper-left coordinate
  lr: Coordinate; // Lower-right coordinate
  ur: Coordinate; // Upper-right coordinate
  srs: string; // Spatial reference system
  xmin: number;
  xmax: number;
  ymin: number;
  ymax: number;
}

interface Coordinate {
  x: number;
  y: number;
}

export interface BandInfo {
  min: number;
  max: number;
  mean: number;
  stdev: number;
  interpretation: string; // e.g., "gray"
  nodata?: number | null;
}

interface FrameInfo {
  frame: string;
  bands: BandInfo[];
}

export interface NetCDFGenerateParams {
  netcdf_data_id: number;
  variable: string;
  name: string;
  description?: string;
  sliding_variable?: string;
  x_variable?: string;
  y_variable?: string;
  color_map?: string;
  additional_vars?: string;
  xRange?: [number, number];
  yRange?: [number, number];
  slicerRange?: [number, number];
}
export interface NetCDFPreviewParams {
  netcdf_data_id: number;
  variable: string;
  i: number;
  sliding_variable?: string;
  x_variable?: string;
  y_variable?: string;
  color_map?: string;
  additional_vars?: string;
  xRange?: [number, number];
  yRange?: [number, number];
  slicerRange?: [number, number];
}
interface User {
  id: number;
  username: string;
  is_staff: boolean;
}

interface AddDatasetParams {
  name: string;
  description?: string;
  category?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  metadata: Record<string, any>;
}

const baseURL = new URL((import.meta.env.VUE_APP_API_ROOT as string || 'http://localhost:8000/api/v1/'), window.location.origin);

const UVDATApiRoot = ''; // If we have another location this would be modified
export default class UVdatApi {
  public static apiClient: AxiosInstance;

  public static baseURL = `${baseURL}${UVDATApiRoot}/`;

  public static user: User | null = null;

  public static get origin(): string {
    return baseURL.origin;
  }

  public static initialize(oauthClient: OauthClient) {
    UVdatApi.apiClient = axios.create({
      baseURL: `${baseURL}`,
      headers: oauthClient?.authHeaders,
    });

    UVdatApi.apiClient.interceptors.request.use((config) => ({
      ...config,
      headers: {
        ...oauthClient?.authHeaders,
        ...config.headers,
      } as AxiosRequestHeaders,
    }));
  }

  public static async fetchCurrentUser() : Promise<User | null> {
    const { data, status } = await UVdatApi.apiClient.get('/users/me/');
    if (status === 204) {
      UVdatApi.user = null;
    } else if (status === 200) {
      UVdatApi.user = {
        id: data.id,
        username: data.username,
        is_staff: data.is_staff,
      };
    } else {
      throw new Error('Failed to fetch current user');
    }
    return UVdatApi.user;
  }

  public static async getContexts(): Promise<Context[]> {
    return (await UVdatApi.apiClient.get('contexts')).data.results;
  }

  public static async getContext(id: number): Promise<ContextWithIds> {
    return (await UVdatApi.apiClient.get(`contexts/${id}/`)).data;
  }

  public static async getContextDatasets(
    contextId: number,
  ): Promise<Dataset[]> {
    return (await UVdatApi.apiClient.get(`datasets?context=${contextId}`)).data.results;
  }

  public static async getContextCharts(contextId: number): Promise<Chart[]> {
    return (await UVdatApi.apiClient.get(`charts?context=${contextId}`)).data.results;
  }

  public static async getContextDerivedRegions(
    contextId: number,
  ): Promise<DerivedRegion[]> {
    return (await UVdatApi.apiClient.get(`derived-regions?context=${contextId}`)).data
      .results;
  }

  public static async getContextSimulationTypes(
    contextId: number,
  ): Promise<SimulationType[]> {
    return (await UVdatApi.apiClient.get(`simulations/available/context/${contextId}`))
      .data;
  }

  public static async getDataset(datasetId: number): Promise<Dataset> {
    return (await UVdatApi.apiClient.get(`datasets/${datasetId}`)).data;
  }

  public static async deleteLayer(layerId: number, type: 'vector' | 'raster'): Promise<{ detail: string }> {
    return (await UVdatApi.apiClient.delete(`/${type}s/${layerId}/`)).data;
  }

  public static async deleteFileItem(fileItemId: number): Promise<{ detail: string }> {
    return (await UVdatApi.apiClient.delete(`/files/${fileItemId}/`)).data;
  }

  public static async getGlobalDatasets(filter: { unconnected: boolean }): Promise<(Dataset & { contextCount: number })[]> {
    return (await UVdatApi.apiClient.get('datasets', { params: { ...filter } })).data.results;
  }

  public static async getDatasetNetwork(
    datasetId: number,
  ): Promise<NetworkNode[]> {
    return (await UVdatApi.apiClient.get(`datasets/${datasetId}/network`)).data;
  }

  public static async getNetworkGCC(
    datasetId: number,
    contextId: number,
    exclude_nodes: number[],
  ): Promise<NetworkNode[]> {
    return (
      await UVdatApi.apiClient.get(
        `datasets/${datasetId}/gcc?context=${contextId}&exclude_nodes=${exclude_nodes.toString()}`,
      )
    ).data;
  }

  public static async getMapLayer(
    mapLayerId: number,
    mapLayerType: string,
  ): Promise<VectorMapLayer | RasterMapLayer> {
    return (await UVdatApi.apiClient.get(`${mapLayerType}s/${mapLayerId}`)).data;
  }

  public static async getRasterData(layerId: number): Promise<RasterData> {
    const resolution = 0.1;
    const { data } = await UVdatApi.apiClient.get(`rasters/${layerId}/raster-data/${resolution}`);
    const { sourceBounds } = (
      await UVdatApi.apiClient.get(`rasters/${layerId}/info/metadata`)
    ).data;
    return {
      data,
      sourceBounds,
    };
  }

  public static async clearChart(chartId: number) {
    await UVdatApi.apiClient.post(`charts/${chartId}/clear/`);
  }

  public static async runSimulation(
    simulationId: number,
    contextId: number,
    args: object,
  ) {
    return (
      await UVdatApi.apiClient.post(
        `simulations/run/${simulationId}/context/${contextId}/`,
        args,
      )
    ).data;
  }

  public static async getSimulationResults(
    simulationId: number,
    contextId: number,
  ) {
    return (
      await UVdatApi.apiClient.get(
        `simulations/${simulationId}/context/${contextId}/results/`,
      )
    ).data;
  }

  public static async getDerivedRegion(regionId: number) {
    const res = await UVdatApi.apiClient.get(`derived-regions/${regionId}/`);
    return res.data;
  }

  public static async postDerivedRegion(
    name: string,
    context: number,
    regions: number[],
    op: 'union' | 'intersection' | undefined,
  ) {
    if (!op) return;
    const operation = op.toUpperCase();
    const res = await UVdatApi.apiClient.post('derived-regions/', {
      name,
      context,
      operation,
      regions,
    });

    // eslint-disable-next-line consistent-return
    return res.data;
  }

  public static async patchVectorLayer(layerId: number, default_style: VectorMapLayer['default_style']) {
    const res = await UVdatApi.apiClient.patch(`vectors/${layerId}/`, { default_style });
    return res.data;
  }

  public static async patchRasterLayer(layerId: number, default_style: RasterMapLayer['default_style']) {
    const res = await UVdatApi.apiClient.patch(`rasters/${layerId}/`, { default_style });
    return res.data;
  }

  public static async getLayerPropertySummary(layerId: number): Promise<PropertySummary> {
    return (await UVdatApi.apiClient.get(`vectors/${layerId}/property-summary`)).data;
  }

  public static async getRasterMetadata(layerId: number): Promise<MetadataResponse> {
    return (await UVdatApi.apiClient.get(`/rasters/${layerId}/info/metadata/`)).data;
  }

  public static async getLayerRepresentations(mapLayerId: number, type: 'vector' | 'raster'): Promise<LayerRepresentation[]> {
    return (await UVdatApi.apiClient.get(`/layer-representations/map-layer/${mapLayerId}/`, { params: { type } })).data;
  }

  public static async addLayerRepresentation(layerRepresentation: LayerRepresentation) {
    return (await UVdatApi.apiClient.post('/layer-representations/', { ...layerRepresentation })).data;
  }

  public static async patchLayerRepresentation(layerRepresentationId: number, layerRepresentation: LayerRepresentation) {
    return (await UVdatApi.apiClient.patch(`/layer-representations/${layerRepresentationId}/`, { ...layerRepresentation })).data;
  }

  public static async deleteLayerRepresentation(layerRepresentationId: number) {
    return (await UVdatApi.apiClient.delete(`/layer-representations/${layerRepresentationId}/`)).data;
  }

  public static async getLayerCollections(): Promise<LayerCollection[]> {
    return (await UVdatApi.apiClient.get('/layer-collections/')).data.results;
  }

  public static async addLayerCollection(layerCollection: LayerCollection) {
    return (await UVdatApi.apiClient.post('/layer-collections/', { ...layerCollection })).data;
  }

  public static async patchLayerCollection(layerCollectionId: number, layerCollection: LayerCollection) {
    return (await UVdatApi.apiClient.patch(`/layer-collections/${layerCollectionId}/`, { ...layerCollection })).data;
  }

  public static async deleteLayerCollection(layerCollectionId: number) {
    return (await UVdatApi.apiClient.delete(`/layer-collections/${layerCollectionId}/`)).data;
  }

  public static async getMapLayerCollectionList(
    layers: LayerCollectionLayer[],
    enabled? : boolean,
  ): Promise<(VectorMapLayer | RasterMapLayer | NetCDFLayer)[]> {
    return (await UVdatApi.apiClient.post('/map-layers/', { layers }, { params: { enabled } })).data;
  }

  public static async getRasterBbox(mapLayerId: number): Promise<Bounds> {
    return (await UVdatApi.apiClient.get(`/rasters/${mapLayerId}/bbox`)).data;
  }

  public static async getVectorBbox(mapLayerId: number): Promise<Bounds> {
    return (await UVdatApi.apiClient.get(`/vectors/${mapLayerId}/bbox`)).data;
  }

  public static async getMapLayersBoundingBox(
    rasterMapLayerIds: number[] = [],
    vectorMapLayerIds: number[] = [],
    netCDFMapLayerIds: number[] = [],
  ): Promise<Bounds> {
    // Create query parameters for the request
    const params = new URLSearchParams();

    rasterMapLayerIds.forEach((id) => params.append('rasterMapLayerIds', id.toString()));
    vectorMapLayerIds.forEach((id) => params.append('vectorMapLayerIds', id.toString()));
    netCDFMapLayerIds.forEach((id) => params.append('netCDFMapLayerIds', id.toString()));

    // Make the request using axios
    const response = await UVdatApi.apiClient.get('/map-layers/bbox', { params });

    // Return the bounding box data from the response
    return response.data;
  }

  public static async getPropertyStatistics(mapLayerId: number, property_keys: string, bbox?: string, bins?: number) {
    return (await UVdatApi.apiClient.get(
      `/vectors/${mapLayerId}/property-statistics/`,
      { params: { property_keys, bbox, bins } },
    )).data;
  }

  public static async deleteDataset(datasetId: number): Promise<{ detail: string }> {
    return (await UVdatApi.apiClient.delete(`/datasets/${datasetId}/`)).data;
  }

  public static async getNetCDFPreview(data: NetCDFPreviewParams): Promise<{ image: string }> {
    return (await UVdatApi.apiClient.post('/netcdf/preview/', { ...data })).data;
  }

  public static async getNetCDFLayerImages(layerId: number): Promise<NetCDFImages> {
    return (await UVdatApi.apiClient.get(`/netcdf/layer/${layerId}/images/`)).data;
  }

  public static async deleteNetCDFLayer(layerId: number): Promise<{ message?: string, error?: string }> {
    return (await UVdatApi.apiClient.delete(`/netcdf/layer/${layerId}/delete-layer/`)).data;
  }

  public static async generateNetCDFLayer(data: NetCDFGenerateParams): Promise<{ image: string }> {
    return (await UVdatApi.apiClient.post('/netcdf/generate-layer/', { ...data })).data;
  }

  public static async addDataset(data: AddDatasetParams): Promise<AddDatasetParams & { id: number }> {
    return (await UVdatApi.apiClient.post('/datasets/', { ...data })).data;
  }

  public static async convertDataset(datasetId: number): Promise<Dataset> {
    return (await UVdatApi.apiClient.get(`datasets/${datasetId}/convert`)).data;
  }

  public static async patchFileItem(itemId: number, data:{ name?: string }) {
    return (UVdatApi.apiClient.patch(`files/${itemId}/`, data));
  }

  public static async postFileItem(
    name: string,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    metadata: Record<string, any>,
    index: number,
    dataset: number,
    fileKey: string,
  ): Promise<{ detail: string }> {
    return (await UVdatApi.apiClient.post('/files/', {
      name, metadata, index, dataset, fileKey,
    })).data;
  }

  public static async getDatasetFiles(datasetId: number): Promise<FileItem[]> {
    return (await UVdatApi.apiClient.get(`/datasets/${datasetId}/file_items`)).data;
  }

  public static async getDatasetLayers(datasetId: number): Promise<(VectorMapLayer | RasterMapLayer | NetCDFData)[]> {
    return (await UVdatApi.apiClient.get(`/datasets/${datasetId}/map_layers`)).data;
  }

  public static async getProcessingTasks(): Promise<ProcessingTask[]> {
    return (await UVdatApi.apiClient.get('/processing-tasks')).data;
  }

  public static async getFilteredProcessingTasks(
    status: ProcessingTask['status'],
  ): Promise<ProcessingTask[]> {
    return (await UVdatApi.apiClient.get('/processing-tasks/filtered/', { params: { status } })).data;
  }

  public static async cancelProcessingTask(taskId: number): Promise<{ detail: string }> {
    return (await UVdatApi.apiClient.post(`/processing-tasks/${taskId}/cancel/`)).data;
  }

  public static async updateMapLayerName(id: number, type: AbstractMapLayer['type'], name: string) {
    return (await UVdatApi.apiClient.patch('/map-layers/update-name/', { name, type, id })).data;
  }

  public static async updateFileItem(id: number, name: string) {
    return (await UVdatApi.apiClient.patch(`files/${id}/`, { name })).data;
  }

  public static async updateDataset(id: number, name: string, category: string, description: string) {
    return (await UVdatApi.apiClient.patch(`/datasets/${id}/`, { name, category, description })).data;
  }

  public static async addContext(
    data:{ name?: string, datasets: number[], default_map_zoom: number, default_map_center: number[] },
  ) {
    return (await (UVdatApi.apiClient.post<Context>('contexts/', data))).data;
  }

  public static async patchContext(
    itemId: number,
    data:{ name?: string, datasets: number[], default_map_zoom?: number, default_map_center?: number[] },
  ) {
    return (UVdatApi.apiClient.patch(
      `contexts/${itemId}/all/`,
      {
        ...data,
        default_map_zoom: data.default_map_zoom ? Math.round(data.default_map_zoom) : undefined,
      },
    ));
  }

  public static async deleteContext(contextId: number): Promise<{ detail: string }> {
    return (await UVdatApi.apiClient.delete(`/contexts/${contextId}/`)).data;
  }

  public static async getVectorTableSummary(layerId: number): Promise<TableSummary> {
    return (await UVdatApi.apiClient.get('/vectorfeature/tabledata/table-summary/', { params: { layerId } })).data;
  }

  public static async getFeatureGraphData(
    tableType: string,
    vectorFeatureId: number,
    xAxis: string = 'index',
    yAxis: string = 'mean_va',
    filter?: string,
    filterVal?: string,
  ): Promise<FeatureGraphData> {
    const response = await UVdatApi.apiClient.get('/vectorfeature/tabledata/feature-graph/', {
      params: {
        tableType,
        vectorFeatureId,
        xAxis,
        yAxis,
        filter,
        filterVal,
      },
    });
    return response.data;
  }
}
