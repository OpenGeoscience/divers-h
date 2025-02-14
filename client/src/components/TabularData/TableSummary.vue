<script lang="ts">
import {
  Ref, computed, defineComponent, onMounted, ref,
  watch,
} from 'vue';
import { AvailablePropertyDisplay, TableSummary, VectorFeatureTableGraph } from '../../types';
import UVdatApi from '../../api/UVDATApi';
import MapStore from '../../MapStore';
import { getLayerAvailableProperties } from '../../utils';
import { index } from 'd3';

export default defineComponent({
  name: 'VectorTableSummary',
  props: {
    layerId: {
      type: Number,
      required: true,
    },
    selectedFeature: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    const summaryData = ref<TableSummary | null>(null);
    const loading = ref(true);
    const addingGraph = ref(false);
    const error = ref<string | null>(null);
    const tableChartDialog = ref(false);
    const activeTab: Ref<'summary' | 'selectedFeatureGraphs' | 'mapLayerGraphs'> = ref('summary'); // Track active tab (0 for summary, 1 for graphing)
    const selectedTableName = ref<string>('Table Name');
    const selectedTableType = ref<string | null>(null);
    const selectedXColumn = ref<string | null>(null);
    const xAxisLabel = ref('');
    const yAxisLabel = ref('');
    const selectedYColumn = ref<string | null>(null);
    const selectedIndexerColumn = ref<string>('');
    const selectedFeatureGraphs = ref<VectorFeatureTableGraph[]>([]);
    const mapLayerFeatureGraphs = ref<VectorFeatureTableGraph[]>([]);
    const availableProps: Ref<Record<string, AvailablePropertyDisplay>> = ref({});
    const getStyleVectorFeatureGraphs = () => {
      const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.layerId);
      if (found) {
        if (found.default_style.vectorFeatureTableGraphs) {
          selectedFeatureGraphs.value = found.default_style.vectorFeatureTableGraphs;
        }
        if (found.default_style.mapLayerFeatureTableGraphs) {
          mapLayerFeatureGraphs.value = found.default_style.mapLayerFeatureTableGraphs;
        }
      }
    };

    const updateStyleGraphs = (updatedGraphs: VectorFeatureTableGraph[]) => {
      const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.layerId);
      if (found?.default_style && activeTab.value === 'selectedFeatureGraphs') {
        found.default_style.vectorFeatureTableGraphs = updatedGraphs;
      }
      if (found?.default_style && activeTab.value === 'mapLayerGraphs') {
        found.default_style.mapLayerFeatureTableGraphs = updatedGraphs;
      }
    };

    const editingGraphIndex = ref<number | null>(null); // Track the index of the graph being edited

    const vectorTableSummary = async (layerId: number) => {
      try {
        loading.value = true;
        summaryData.value = await UVdatApi.getVectorTableSummary(layerId);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (err: any) {
        error.value = err.response?.data?.error || 'Failed to fetch data';
      } finally {
        loading.value = false;
      }
    };

    const resetGraphForm = () => {
      selectedXColumn.value = null;
      selectedYColumn.value = null;
      xAxisLabel.value = '';
      yAxisLabel.value = '';
      selectedIndexerColumn.value = '';
      addingGraph.value = false;
    };

    const addSaveGraph = () => {
      if (selectedTableType.value && selectedXColumn.value && selectedYColumn.value) {
        const graph: VectorFeatureTableGraph = {
          name: selectedTableName.value,
          type: selectedTableType.value,
          xAxis: selectedXColumn.value,
          yAxis: selectedYColumn.value,
          xAxisLabel: xAxisLabel.value ? xAxisLabel.value : undefined,
          yAxisLabel: yAxisLabel.value ? yAxisLabel.value : undefined,
          indexer: selectedIndexerColumn.value ? selectedIndexerColumn.value : undefined,
        };
        const editingGraphList = activeTab.value === 'selectedFeatureGraphs' ? selectedFeatureGraphs : mapLayerFeatureGraphs;

        if (editingGraphIndex.value !== null) {
          // If editing, update the existing graph
          editingGraphList.value[editingGraphIndex.value] = graph;
          editingGraphIndex.value = null;
        } else {
          // Otherwise, add a new graph
          editingGraphList.value.push(graph);
        }

        updateStyleGraphs(editingGraphList.value);
        // Clear the form after adding/updating the graph
        resetGraphForm();
      }
    };

    

    const availableColumns = computed(() => {
      const baseColumns = selectedTableType.value && summaryData.value?.tables[selectedTableType.value]?.columns
        ? summaryData.value?.tables[selectedTableType.value]?.columns : [];
      const mappedColumns = baseColumns.map((item) => {
        const summary = selectedTableType.value && summaryData.value?.tables[selectedTableType.value].summary[item];
        let subtitle = '';
        if (summary && summary.description) {
          subtitle = summary.description;
        } else if (summary && summary.type === 'number') {
          subtitle = `${summary.min} to ${summary.max}`;
        } else if (summary && summary.type === 'string') {
          subtitle = `${summary.value_count} unique values`;
        }
        return {
          title: item,
          subtitle,
        };
      });
      if (mappedColumns.length) {
        const takenVals = [selectedXColumn.value, selectedYColumn.value, selectedIndexerColumn].filter((item) => item !== null);
        return mappedColumns.filter((item) => !takenVals.includes(item.title));
      }
      return mappedColumns;
    });

    const editGraph = (index: number) => {
      const editingGraphList = activeTab.value === 'selectedFeatureGraphs' ? selectedFeatureGraphs : mapLayerFeatureGraphs;
      const graph = editingGraphList.value[index];
      // eslint-disable-next-line prefer-destructuring
      selectedTableType.value = graph.type; // Assuming the table name is part of the graph name
      selectedTableName.value = graph.name;
      selectedXColumn.value = graph.xAxis;
      selectedYColumn.value = graph.yAxis;
      xAxisLabel.value = graph.xAxisLabel || '';
      yAxisLabel.value = graph.yAxisLabel || '';
      selectedIndexerColumn.value = graph.indexer || '';
      editingGraphIndex.value = index;
      addingGraph.value = true;
    };

    const deleteGraph = (index: number) => {
      const editingGraphList = activeTab.value === 'selectedFeatureGraphs' ? selectedFeatureGraphs : mapLayerFeatureGraphs;
      editingGraphList.value.splice(index, 1);
    };

    watch(activeTab, () => {
      resetGraphForm();
    });
    const indexerVals = computed(() => {
      const keys = Object.keys(availableProps.value);
      const output: { title: string, value: string; description?: string}[] = [];
      keys.forEach((key) => {
        if (availableProps.value[key]) {
          output.push({
            value: key,
            title: availableProps.value[key].displayName,
            description: availableProps.value[key].description
          })
        }
      })
      return output;
    })

    onMounted(() => {
      vectorTableSummary(props.layerId);
      availableProps.value = getLayerAvailableProperties(props.layerId);
      getStyleVectorFeatureGraphs();
    });
    const graphs = computed(() => {
      const editingGraphList = activeTab.value === 'selectedFeatureGraphs' ? selectedFeatureGraphs : mapLayerFeatureGraphs;
      return editingGraphList.value;
    });

    return {
      summaryData,
      addingGraph,
      loading,
      error,
      tableChartDialog,
      activeTab,
      availableColumns,
      selectedTableName,
      selectedTableType,
      selectedXColumn,
      xAxisLabel,
      selectedYColumn,
      yAxisLabel,
      selectedIndexerColumn,
      editingGraphIndex,
      graphs,
      addSaveGraph,
      editGraph,
      deleteGraph,
      resetGraphForm,
      indexerVals,
      selectedFeatureGraphs,
      mapLayerFeatureGraphs,
    };
  },
});
</script>

<template>
  <v-row dense align="center" justify="center">
    <h3>Tabular Data/Graphs</h3>
    <v-spacer />
    <v-icon @click="tableChartDialog = true">
      mdi-cog
    </v-icon>
  </v-row>
  <v-row><v-spacer />Selected Feature Graphs<v-spacer /></v-row>
  <v-row v-for="(graph, index) in selectedFeatureGraphs" :key="index" dense>
    <v-col>
      {{ graph.name }}
    </v-col>
    <v-col>
      {{ `${graph.xAxis} vs ${graph.yAxis}` }}
    </v-col>
  </v-row>
  <v-row><v-spacer />MapLayer Feature Graphs<v-spacer /></v-row>
  <v-row v-for="(graph, index) in mapLayerFeatureGraphs" :key="index" dense>
    <v-col>
      {{ graph.name }}
    </v-col>
    <v-col>
      {{ `${graph.xAxis} vs ${graph.yAxis}` }}
    </v-col>
  </v-row>

  <v-dialog v-model="tableChartDialog" max-width="800px">
    <v-card>
      <v-card-title>Vector Table Summary</v-card-title>
      <v-tabs v-model="activeTab">
        <v-tab size="small" value="summary">
          Summary
        </v-tab>
        <v-tab size="small" value="selectedFeatureGraphs">
          Selected Feature Graphs
        </v-tab>
        <v-tab size="small" value="mapLayerGraphs">
          Map LayerGraphs
        </v-tab>
      </v-tabs>
      <v-card-text v-if="activeTab === 'summary'">
        <div v-if="loading">
          Loading...
        </div>
        <div v-else-if="error" class="error-text">
          {{ error }}
        </div>
        <div v-else-if="summaryData">
          <p><strong>Vector Feature Count:</strong> {{ summaryData.vectorFeatureCount }}</p>
          <v-expansion-panels>
            <v-expansion-panel v-for="(table, type) in summaryData.tables" :key="type">
              <v-expansion-panel-title>
                {{ type }} ({{ table.tableCount }} tables)
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-expansion-panels>
                  <v-expansion-panel v-for="column in table.columns" :key="column">
                    <v-expansion-panel-title>{{ column }}</v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <p>{{ table.summary[column] }}</p>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </div>
      </v-card-text>

      <v-card-text v-if="activeTab !== 'summary'">
        <v-card-text>
          <v-form v-if="addingGraph">
            <v-text-field
              v-model="selectedTableName"
              label="Table Name"
            />
            <v-select
              v-model="selectedTableType"
              :items="Object.keys(summaryData?.tables || {})"
              label="Select Table"
            />
            <v-select
              v-model="selectedXColumn"
              :items="availableColumns"
              :item-props="true"
              label="Select X Axis"
            />
            <v-text-field
              v-model="xAxisLabel"
              label="X Axis Label"
            />
            <v-select
              v-model="selectedYColumn"
              :items="availableColumns"
              :item-props="true"
              label="Select Y Axis"
            />
            <v-text-field
              v-model="yAxisLabel"
              label="Y Axis Label"
            />
            <v-select
              v-if="activeTab === 'mapLayerGraphs'"
              v-model="selectedIndexerColumn"
              :items="indexerVals"
              :item-props="true"
              label="Select Indexer Column"
            />
            <v-row dense class="my-2">
              <v-btn :disabled="!selectedTableType || !selectedXColumn || !selectedYColumn" color="primary" @click="addSaveGraph">
                {{ editingGraphIndex !== null ? 'Update' : 'Add' }} Graph
              </v-btn>
              <v-btn color="error" class="ml-2" @click="resetGraphForm()">
                Cancel
              </v-btn>
            </v-row>
          </v-form>
          <v-divider />
          <v-row v-if="!addingGraph" dense class="my-2">
            <v-spacer />
            <v-btn size="small" color="success" @click="addingGraph = true">
              Add <v-icon>mdi-plus</v-icon>
            </v-btn>
          </v-row>
          <v-list>
            <v-list-item v-for="(graph, index) in graphs" :key="index">
              <v-list-item-title>{{ graph.name }}</v-list-item-title>
              <v-list-item-subtitle>
                <div>{{ graph.type }}</div>
                <div>{{ graph.xAxis }} vs {{ graph.yAxis }})</div>
                <div v-if="graph.xAxisLabel || graph.yAxisLabel">
                  {{ graph.xAxisLabel }} - {{ graph.yAxisLabel }}
                </div>
              </v-list-item-subtitle>
              <v-list-item-action>
                <v-icon color="warning" @click="editGraph(index)">
                  mdi-pencil
                </v-icon>
                <v-icon color="error" @click="deleteGraph(index)">
                  mdi-delete
                </v-icon>
              </v-list-item-action>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>
