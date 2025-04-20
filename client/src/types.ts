export interface Dataset {
  id: number;
  name: string;
  description: string;
  category: string;
  created: string;
  modified: string;
  processing: boolean;
  metadata: object;
  map_layers?: (VectorMapLayer | RasterMapLayer)[];
  current_layer_index?: number;
  network: {
    nodes: NetworkNode[];
    edges: NetworkEdge[];
  };
}

export interface ProcessingTask {
  id: number;
  created: string;
  modified: string;
  name: string;
  file_items: number[];
  error? : string;
  status: 'Complete' | 'Running' | 'Error' | 'Queued';
  metadata: Record<string, unknown> & { type?: 'file processing' | 'task' };
  output_metadata: Record<string, unknown> & { output_layers?: { raster_map_layers: number[], vector_map_layers: number[] } };
}

export interface FileItem {
  id: number,
  created: string;
  modified: string;
  name: string;
  file: string;
  file_size: number;
  file_type: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  metadata: Record<string, any>;
  dataset: number;
  index: number;
  processing_tasks?: ProcessingTask[];
}

export interface SourceRegion {
  id: number;
  name?: string;
  dataset_id?: number;
  metadata?: object;
  boundary?: object;
}

export interface DerivedRegion {
  id: number;
  name: string;
  context: number;
  metadata: object;
  boundary: object;
  source_regions: number[];
  operation: 'UNION' | 'INTERSECTION';
  map_layers: {
    id: number;
    index: number;
    type: string;
  }[];
  current_layer_index: null;
}

export interface Indicator {
  short_name: string;
  long_name: string;
  hierarchy: string[];
  value: string | number;
  units: string;
}

export interface Context {
  id: number;
  name: string;
  default_map_center: [number, number];
  default_map_zoom: number;
  datasets: Dataset[];
  created: string;
  modified: string;
  indicators: Indicator[];
}

export interface ContextWithIds {
  id: number;
  name: string;
  default_map_center: [number, number];
  default_map_zoom: number;
  datasets: number[];
  created: string;
  modified: string;
  indicators: Indicator[];

}

export type PropertySummary = Record<string, PropertySummaryItem>;

export interface PropertySummaryItem {
  type: 'number' | 'string' | 'bool';
  value_count: number;
  values?: string[];
  searchable?: boolean;
  unique?: number;
  static?: boolean;
  min?: number;
  max?: number;
}

export interface Feature {
  type: string;
  geometry: {
    [key: string]: string | object;
  };
  properties: {
    [key: string]: string | object;
  };
}

export interface NetworkNode {
  id: number;
  name: string;
  dataset: number;
  metadata: object;
  capacity: number | null;
  location: number[];
}

export interface NetworkEdge {
  id: number;
  name: string;
  dataset: number;
  metadata: object;
  capacity: number | null;
  line_geopmetry: object;
  directed: boolean;
  from_node: number;
  to_node: number;
}
export interface MetadataLayers {}

export type AnnotationTypes = 'line' | 'circle' | 'fill-extrusion' | 'text' | 'fill' | 'heatmap';

type ColorSolid = string; // Hex or text color code

export interface ColorCategoricalString {
  type: 'ColorCategoricalString';
  defaultColor: ColorSolid;
  attribute: string;
  colorPairs: Record<string, string>;
}

export interface ColorAttributeValue {
  type: 'ColorAttributeValue';
  defaultColor: ColorSolid;
  attributeValues:string[]; // cascading list of attributes
}

export interface ColorLinearNumber {
  type: 'ColorLinearNumber';
  defaultColor: ColorSolid;
  attribute: string;
  numberColorPairs: { value: number, color: string }[];
}
export interface ColorCategoricalNumber {
  type: 'ColorCategoricalNumber';
  defaultColor: ColorSolid;
  attribute: string;
  numberColorPairs: { value: number, color: string }[];
}

export interface ColorBoolean {
  type: 'ColorBoolean';
  defaultColor: ColorSolid;
  attribute: string;
  trueColor: ColorSolid;
  falseColor: ColorSolid;
}
export type ColorDisplay = ColorSolid | ColorObjectDisplay;
export type ColorObjectDisplay =
ColorAttributeValue |
ColorCategoricalString |
ColorCategoricalNumber |
ColorLinearNumber |
ColorBoolean;
export type VectorLayerDisplay = boolean | VectorLayerDisplayConfig;

export interface SizeZoom {
  type: 'SizeZoom';
  zoomLevels: [number, number][]; // [ZoomLevel, Size]
}

export interface SizeLinear {
  type: 'SizeLinear',
  attribute: string;
  linearLevels: [number, number][]; // [Linear Value, Size]
}
export type SizeStatic = number;
export type SizeTypes = SizeStatic | SizeLinear | SizeZoom;
export type SizeTypeConfig = SizeLinear | SizeZoom;

export interface TextConfig {
  // Starting simple with just key, may have more features in future
  key: string;
}

// Define a base interface for filters
export interface BaseFilter {
  key: string; // Attribute key to filter on
  name: string;
  description?: string;
  type: 'number' | 'string' | 'bool';
  interactable: boolean;
  enabled: boolean;
  userEnabled: boolean;
  layers: AnnotationTypes[];
}

// Number filters
export interface NumberComparisonFilter extends BaseFilter {
  type: 'number';
  operator: '>' | '<' | '>=' | '<=' | '==';
  value: number;
}

export interface NumberBetweenFilter extends BaseFilter {
  type: 'number';
  operator: 'between';
  minValue: number;
  maxValue: number;
}

export type NumberFilters = NumberComparisonFilter | NumberBetweenFilter;

// String filters
export interface StringInArrayFilter extends BaseFilter {
  type: 'string';
  operator: 'in';
  values: string[];
}

export interface StringMatchFilter extends BaseFilter {
  type: 'string';
  operator: '==';
  value: string;
}

export interface StringContainsFilter extends BaseFilter {
  type: 'string';
  operator: 'contains';
  value: string;
}

export type StringFilters = StringInArrayFilter | StringMatchFilter | StringContainsFilter;

// Boolean filters
export interface BooleanEqualsFilter extends BaseFilter {
  type: 'bool';
  operator: '==';
  value: boolean;
}

// Logical filters
export interface LogicalFilter {
  type: 'any' | 'all' | 'and' | 'or';
  filters: Filter[];
}

// Unified filter type
export type Filter =
  | NumberComparisonFilter
  | NumberBetweenFilter
  | StringInArrayFilter
  | StringMatchFilter
  | StringContainsFilter
  | BooleanEqualsFilter;
export interface VectorLayerDisplayConfig {
  color?: ColorDisplay;
  enabled?: boolean;
  selectable?: boolean | 'singleSelect';
  selectColor?: ColorSolid;
  hoverable?: boolean;
  legend?: boolean;
  opacity?: number;
  size?: SizeTypes;
  text?: TextConfig;
  zoom?: {
    min?: number;
    max?: number;
  },
  heatmap?: HeatMapConfig;
  drawPoints?: boolean;
}

export interface HeatMapConfig {
  radius?: number;
  weight?: number | SizeLinear;
  intensity?: number | SizeZoom | SizeLinear;
  color?: { value: number, color: string }[];
}

export interface AvailablePropertyDisplay {
  key: string;
  display?: boolean;
  tooltip?: boolean;
  displayName: string;
  description?: string;
  type: 'number' | 'string' | 'bool';
  static? : boolean;
  searchable?: boolean;
  unique?: number;
  values?: string[];
  min?: number;
  max?: number;
}

export interface SelectedPropertyDisplay {
  key: string;
  displayName: string;
}

export interface PropertyDisplay {
  availableProperties?: Record<string, AvailablePropertyDisplay>;
  selectedDisplay?: Record<string, SelectedPropertyDisplay>;
  selectionDisplay?: boolean; // Will only diplay values found in availableProperties.display
  tooltipDisplay?: boolean; // Will only display tooltip values found in availableProperties.display
  displayFeatureId?: boolean; // display featureId in selected
}

export interface AbstractMapLayer {
  id: number;
  name: string;
  type: 'vector' | 'raster' | 'netcdf';
  file_item?: {
    id: number;
    name: string;
  };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  metadata?: Record<string, any> & {
    network?: boolean;
  };
  default_style?: Record<string, unknown>;
  index: number;
  dataset_id?: number;
  derived_region_id?: number;
  // Custom values used for Collections
  layerRepresentationId?: number;
  processing_tasks?: ProcessingTask[];
}

export function isNonNullObject(obj: unknown): obj is object {
  return typeof obj === 'object' && obj !== null;
}

export interface RasterMapLayer extends AbstractMapLayer {
  cloud_optimized_geotiff: string;
  type: 'raster';
  default_style?: {
    charts?: CustomChart[];
    largeImageStyle?: MapRasterParams['style'];
    selectable?: boolean | 'singleSelect';
    hoverable?: boolean;
    opacity?: number;
    zoom?: {
      min?: number;
      max?: number;
    },
  }
}

export function isRasterMapLayer(obj: unknown): obj is RasterMapLayer {
  return isNonNullObject(obj) && 'type' in obj && obj.type === 'raster';
}

export interface Bounds {
  xmax: number;
  xmin: number;
  ymax: number;
  ymin: number;

}
export interface RasterData {
  sourceBounds: Bounds;
  data: number[][];
}

export interface VectorMapLayer extends AbstractMapLayer {
  type: 'vector';
  default_style: {
    layers?: Record<AnnotationTypes, VectorLayerDisplay>
    savedColors?: { color: ColorDisplay, name: string, description: string }[];
    properties?: PropertyDisplay;
    filters?: Filter[];
    charts?: CustomChart[];
    selectedFeatureCharts?: FeatureChart[];
    vectorFeatureTableGraphs?: VectorFeatureTableGraph[];
    mapLayerFeatureTableGraphs?: VectorFeatureTableGraph[];
    searchableVectorFeatureData?: SearchableVectorData;

  }
}

export interface NetCDFData extends AbstractMapLayer {
  type: 'netcdf';
  metadata: {
    variables: Record<string, NetCDFVariable>;
    attributes: Record<string, string>;
    dimensions: Record<string, number>;

  }
  layers: NetCDFLayer[];
}

export interface NetCDFLayer {
  id: number;
  type: 'netcdf';
  name: string;
  parameters: Record<string, string> & NetCDFLayerParameters
  color_scheme: string;
  bounds: Bounds;
  description: string;
  netcdf_data: number;
}

export interface NetCDFLayerParameters {
  stepCount: number;
  x: NetCDFLayerParameter;
  y: NetCDFLayerParameter;
  main_variable: NetCDFLayerParameter & { longName?: string;
    standardName?: string;
  };
  colorScheme: string;
}

export interface NetCDFLayerParameter {
  variable: string;
  min: number;
  max: number;
}

export type MapLibreCoordinates = [[number, number], [number, number], [number, number], [number, number]];
export interface NetCDFImages {
  netCDFLayer: number;
  parent_bounds: [[[number, number], [number, number], [number, number], [number, number], [number, number]]];
  images: string[];
  sliding: { min: number, max: number; step: number, variable: string };
}

// Working type for setting index/opacity
export type NetCDFImageWorking = NetCDFImages
& { currentIndex: number; opacity: number; resampling: 'linear' | 'nearest'; name: string };
export interface NetCDFVariable {
  max: number;
  min: number;
  attributes: Record<string, string> & { long_name?: string; standard_name?: string };
  dimensions: string[];
  startDate?: string;
  endDate?: string;
  steps?: number;
  geospatial?: 'longitude' | 'latitude' | 'longitude360';
}

export function isVectorMapLayer(obj: unknown): obj is VectorMapLayer {
  return isNonNullObject(obj) && 'type' in obj && obj.type === 'vector';
}

export interface VectorTile {
  id: number;
  map_layer: number;
  geojson_data: object;
  x: number;
  y: number;
  z: number;
}

export interface Chart {
  id: number;
  name: string;
  description: string;
  context: number;
  metadata: object;
  chart_data: {
    labels: string[];
    datasets: {
      data: number[];
    }[];
  };
  chart_options: {
    chart_title: string;
    x_title: string;
    y_title: string;
    x_range: number[];
    y_range: number[];
  };
  editable: boolean;
}

export interface ChartOptions {
  plugins: {
    title?: object;
  };
  scales: {
    x?: {
      min?: number;
      max?: number;
      title?: {
        display?: boolean;
        text: string;
      };
    };
    y?: {
      min?: number;
      max?: number;
      title?: {
        display?: boolean;
        text: string;
      };
    };
  };
}

export interface SimulationType {
  id: number;
  name: string;
  description: string;
  output_type: string;
  args: {
    name: string;
    options: {
      id: number;
      name: string;
    }[];
  }[];
}

export interface SimulationResult {
  id: number;
  name: string;
  simulation_type: string;
  context: number;
  input_args: object;
  output_data: {
    node_failures: [];
    node_recoveries: [];
  };
  error_message: string;
  created: string;
  modified: string;
}

// Type for processed layer information

export interface KeyProcessedLayer {
  id: number;
  name: string;
  type: AbstractMapLayer['type'];
  keyTypes: KeyProcessedType[];
}

export interface KeyProcessedType {
  type: string;
  colors: KeyColorConfig[];
}

// Type for color configuration
export type KeyColorConfig =
  | { type: 'solid'; color: string }
  | { attribute: string, type: 'categorical'; pairs: { value: number | string; color: string, disabled?: boolean }[] }
  | { attribute: string, type: 'linear'; colors: ColorLinearNumber['numberColorPairs'], name: string }
  | { name: string, type: 'categorical-raster'; pairs: { value: number | string; color: string }[], value:string }
  | {
    type: 'linear-raster';
    colors: ColorLinearNumber['numberColorPairs'];
    name: string; min: number, max: number, value: string }
  | { type: 'linearNetCDF'; colors: ColorLinearNumber['numberColorPairs'], name: string, min: number, max: number, value: string }
  | { type: 'heatmap'; colors: ColorLinearNumber['numberColorPairs'], name: string };

// Utility types for color processing
export interface KeySolidColorConfig {
  type: 'solid';
  color: string;
}

export interface KeyCategoricalColorConfig {
  type: 'categorical';
  pairs: { value: number | string; color: string }[];
}

export interface KeyLinearColorConfig {
  type: 'linear';
  colors: {
    startColor: string;
    endColor: string;
    startValue: number;
    endValue: number;
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type FeatureProps = Record<string, any>;

export interface ClickedProps {
  id: string | number | undefined;
  layerId: number;
  properties: FeatureProps;
}

type FunctionDefinition = {
  name: string; // Python module and function name
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  parameters?: Record<string, any>; // Dictionary of parameters
  stage?: string | string[]; // One or more stages
  context?: boolean | string; // Pass the style context to the function
};

export type StyleBandEdit = StyleBands & { enabled?: boolean, interpretation?: string };

export interface StyleBands {
  band?: number | 'red' | 'green' | 'blue' | 'gray' | 'alpha' | null;
  frame?: number;
  framedelta?: number;
  min?: number | 'auto' | 'min' | 'max' | `min:${number}` | `max:${number}` | `auto:${number}` | 'full';
  max?: number | 'auto' | 'min' | 'max' | `min:${number}` | `max:${number}` | `auto:${number}` | 'full';
  palette?: string | string[]; // Single color or array of colors
  scheme?: 'linear' | 'discrete';
  nodata?: number | null;
  composite?: 'lighten' | 'multiply';
  clamp?: boolean; // takes items outside the range and true clamps to end, false makes transparent, undefined does nothing
  dtype?: 'uint16' | 'float' | 'source';
  axis?: number;
  icc?: boolean | string; // boolean or a string representing ICC intent
  function?: FunctionDefinition | FunctionDefinition[]; // Function object(s)
}
export interface MapRasterParams {
  projection: 'EPSG:3857'; // Should always be EPSG:3857 for clients
  style?: { // JSON-encoded string or object
    bands?: Array<StyleBandEdit>;
    dtype?: 'uint16' | 'float' | 'source';
    minMaxMapper: Record<string, { min: number; max: number }>;
    axis?: number;
    icc?: boolean | string;
    function?: FunctionDefinition | FunctionDefinition[];
  };
}

export interface LayerRepresentation {
  name: string;
  id: number;
  layer_id: number;
  description?: string;
  enabled: boolean;
  type: 'vector' | 'raster';
  default_style: RasterMapLayer['default_style'] | VectorMapLayer['default_style']
}

export interface LayerCollectionLayer {
  layerId: number;
  visible: boolean;
  type: 'vector' | 'raster' | 'netcdf'
  defaultLayerRepresentationId?: number; // If not it will use the default_style
}
export interface LayerCollection {
  id: number;
  name: string;
  description?: string;
  configuration: {
    mapInfo: {
      center: [number, number];
      zoom: number;
    };
    layers: LayerCollectionLayer[];
  }
}

export interface CustomChart {
  title: string;
  description: string;
  chartType: 'histogram' | 'pie';
  chartData: HistogramChart | PieChart // allows future chart types
  mapLayer: number;
  sourceArea: 'global' | 'bbox';
  enableBbox: boolean;
  expanded?: boolean;
  // If using a custom location it defaults to bbox
  // Also provides a button for going to the default bbox
  customLocation?: {
    bounds: {
      xmin: number;
      xmax: number;
      ymin: number;
      ymax: number;
    }
    zoomLevel: number;
  }
}

export interface HistogramChart {
  keys: string[]; // for future of visualizing multiple histogram values
  type: 'histogram';
  bins?: number;
  xAxisLabel?: string;
  yAxisLabel?: string;
}

export interface PieChart {
  keys: string[]; // for future of using multiple categorical keys
  type: 'pie';
  staticLabels: boolean;
  highlightLabels: boolean;
}

export interface FeatureChart {
  name: string;
  description?: string;
  type: 'bar';
  keys: { key: string, color?: string }[];
  sort: 'value' | 'name' | 'static';
  display: {
    xAxis?: string;
    yAxis?: string;
    expanded: boolean;
    keyStaticLabels: boolean;
    keyHighlightLabels: boolean;
  }
}

export interface VectorTimeSeriesNumericalSteps {
  min: number;
  max: number;
  division: {
    type: 'calc' | 'static'
    value: number;
  }
}

export interface VectorTimeSeriesDateSteps {
  min: Date;
  max: Date;
  division: 'minute' | 'hour' | 'day' | 'week' | 'month' | 'year'
}

export interface VectorTimeSeries {
  property: string;
  type: 'numerical'; // Prep for 'date' based times | 'date'
  steps: VectorTimeSeriesNumericalSteps; // Add VectorStireSeriesDateSteps in future
}

export type FeatureChartWithData = FeatureChart & { data: { key: string, value: number; color: string }[] };

export interface TableSummary {
  vectorFeatureCount: number;
  tables: Record<string, TableInfo>;
}

interface TableInfo {
  tableCount: number;
  columns: string[];
  summary: Record<string, ColumnSummary>;
}

type ColumnSummary =
  | NumberColumnSummary
  | StringColumnSummary;

interface NumberColumnSummary {
  type: 'number';
  min: number;
  max: number;
  value_count: number;
  description?: string;
}

interface StringColumnSummary {
  type: 'string';
  values: string[];
  value_count: number;
  description?: string;
}

export interface VectorFeatureTableGraph {
  name: string;
  type: string;
  xAxis: string;
  xAxisLabel?: string;
  yAxis: string;
  yAxisLabel?: string;
  indexer?: string;
}

export type VectorFeatureTableGraphSelected = VectorFeatureTableGraph & { expanded: boolean };

export interface FeatureGraphs {
  tableType: string;
  xAxis: string;
  yAxis: string;
  indexer: string;
  graph: FeatureGraphData; // You can replace `any` with your actual graph structure interface
}

export interface FeatureGraphsRequest {
  tableTypes: string[];
  vectorFeatureId: number;
  xAxes?: string[];
  yAxes?: string[];
  indexers?: string[];
  display?: ('data' | 'trendLine' | 'confidenceInterval' | 'movingAverage')[];
  confidenceLevel?: number;
  aggregate?: boolean;
  movingAverage?: number;
}

export interface FeatureGraphData {
  table_name: string;
  graphs:
  Record<number | string | 'all', {
    data:[number, number][];
    vectorFeatureId: number;
    indexer: string | number;
    trendLine?:[number, number][];
    confidenceIntervals?:[number, number, number][];
    movingAverage?:[number, number][];
  }>
  xAxisRange:[number, number];
  yAxisRange:[number, number];
}

export interface ColorFilterCategorical {
  layerId: number;
  layerType: AnnotationTypes | 'all';
  type: 'not in';
  key: string;
  values: Set<string>;
}

export interface ColorFilterLinear {
  type: 'between';
  min: number;
  max: number;
}

export type ColorFilters = ColorFilterCategorical;

export interface SearchableVectorFilter {
  key: string;
  defaultDisplay?: boolean;
  type: 'number' | 'string' | 'bool';
  min?: number;
  max?: number;
  searchable?: boolean;
  value: string | string[] | [number, number]
}

export interface SearchableVectorDisplayItem {
  key: string; // key of propery to display
  showDisplayName: boolean;
}

export interface SearchableVectorDisplayActionItem {
  type: 'select' | 'zoom' | 'navigate';
}
export interface SearchableVectorDisplayActionZoom {
  type: 'zoom'
  zoomType: 'buffer' | 'level';
  value: number;
  delay?: number; // ms to delay until next action
}

export interface SearchableVectorDisplayActionSelect {
  type: 'select';
  delay?: number;
}

export interface SearchableVectorDisplayActionNavigate {
  type: 'navigate';
  to: 'metadata' | 'datasets' | 'context';
  special: Record<string, string>; // special actions like geospatial filtering
}

export interface SearchableVectorData {
  // mainTextSearch Field keys, The main search will use these keys to filter items
  mainTextSearchFields?: { title: string, value: string }[];
  configurableFilters: string[]; // Keys for searchable vector features
  display: {
    autoOpenSideBar: boolean;
    geospatialFilterEnabled: boolean; // Filter results based on map display as well
    sortable: boolean; // Ability to sort items by something other than the name of the titleKey field.
    titleKey: string; // key of property to display
    subtitleKeys: SearchableVectorDisplayItem[]; // Allows zero or multiple subtitles that will be in a single line
    detailStrings: SearchableVectorDisplayItem[];
    selectionButton: boolean;
    hoverHighlight: boolean;
    zoomButton: boolean;
    zoomType?: 'buffer' | 'level';
    zoomBufferOrLevel?: number;
  };
  action?: {
    icon?: string; // new button to the item for selection, if none clicking on the title will select it
    toolTip: string; // describes what happens
    actions: (SearchableVectorDisplayActionNavigate | SearchableVectorDisplayActionSelect | SearchableVectorDisplayActionZoom)[]
  }
}

export interface SearchableVectorDataRequest {
  mapLayerId: number;
  // mainTextSearch Field keys, The main search will use these keys to filter items
  mainTextSearchFields?: { title: string, value: string }[];
  search?: string;
  filters?: Record<string, { type: 'bool' | 'number' | 'string', value: string | number | boolean | [number, number] }>;
  bbox?: string;
  sortKey?: string;
  titleKey: SearchableVectorDisplayItem;
  subtitleKeys: SearchableVectorDisplayItem[]; // Allows zero or multiple subtitles that will be in a single line
  detailStrings: SearchableVectorDisplayItem[];
}

export interface SearchableVectorFeatureResponse {
  id: number;
  title: string;
  subtitles: { key: string; value: string }[];
  details: { key: string; value: string }[];
  center: { lat: number, lon: number };
}

export interface DisplayConfiguration {
  enabled_ui: ('Scenarios' | 'Collections' | 'Datasets' | 'Metadata')[];
  default_tab: 'Scenarios' | 'Collections' | 'Datasets' | 'Metadata';
  default_displayed_layers: Array<{ type: AbstractMapLayer['type']; id: number; dataset_id: number; name: string }>;
  default_map_settings?: { location: { center: [number, number], zoom: number } };
}

export interface AbstractMapLayerListItem {
  id: number;
  name: string;
  type: AbstractMapLayer['type'];
  dataset_id: number;
  file_item: { id: number, name: string }[];
  processing_tasks?: null | ProcessingTask[]
}
