<script lang="ts">
import {
  Ref, defineComponent, onMounted, ref, computed,
} from 'vue';
import { TableSummary, VectorFeatureTableGraph } from '../../types';
import UVdatApi from '../../api/UVDATApi';
import MapStore from '../../MapStore';

export default defineComponent({
  name: 'VectorTableSummary',
  props: {
    layerId: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const summaryData = ref<TableSummary | null>(null);
    const loading = ref(true);
    const error = ref<string | null>(null);
    const tableChartDialog = ref(false);
    const activeTab: Ref<'summary' | 'graphs'> = ref('summary'); // Track active tab (0 for summary, 1 for graphing)
    const selectedTableName = ref<string>('Table Name');
    const selectedTableType = ref<string | null>(null);
    const selectedXColumn = ref<string | null>(null);
    const selectedYColumn = ref<string | null>(null);
    const selectedIndexerColumn = ref<string>('');
    const graphs = ref<VectorFeatureTableGraph[]>([]);

    const getStyleVectorFeatureGraphs = () => {
      const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.layerId);
      if (found && found.default_style.vectorFeatureTableGraphs) {
        graphs.value = found.default_style.vectorFeatureTableGraphs;
      }
    };

    const updateStyleGraphs = (updatedGraphs: VectorFeatureTableGraph[]) => {
      const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.layerId);
      if (found && found.default_style) {
        found.default_style.vectorFeatureTableGraphs = updatedGraphs;
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
      selectedIndexerColumn.value = '';
    };

    const addSaveGraph = () => {
      if (selectedTableType.value && selectedXColumn.value && selectedYColumn.value) {
        const graph: VectorFeatureTableGraph = {
          name: selectedTableName.value,
          type: selectedTableType.value,
          xAxis: selectedXColumn.value,
          yAxis: selectedYColumn.value,
          indexer: selectedIndexerColumn.value ? selectedIndexerColumn.value : undefined,
        };

        if (editingGraphIndex.value !== null) {
          // If editing, update the existing graph
          graphs.value[editingGraphIndex.value] = graph;
          editingGraphIndex.value = null;
        } else {
          // Otherwise, add a new graph
          graphs.value.push(graph);
        }

        updateStyleGraphs(graphs.value);
        // Clear the form after adding/updating the graph
        resetGraphForm();
      }
    };

    const availableColumns = computed(() => {
      const baseColumns = selectedTableType ? summaryData?.tables[selectedTableType]?.columns : [];
      if (baseColumns.length) {
        const takenVals = [selectedXColumn.value, selectedYColumn.value, selectedIndexerColumn].filter((item) => item !== null);
        return baseColumns.filter((item) => !takenVals.includes(item))
      }
      return baseColumns;
    })

    const editGraph = (index: number) => {
      const graph = graphs.value[index];
      // eslint-disable-next-line prefer-destructuring
      selectedTableType.value = graph.type; // Assuming the table name is part of the graph name
      selectedTableName.value = graph.name;
      selectedXColumn.value = graph.xAxis;
      selectedYColumn.value = graph.yAxis;
      selectedIndexerColumn.value = graph.indexer || '';
      editingGraphIndex.value = index;
    };

    const deleteGraph = (index: number) => {
      graphs.value.splice(index, 1);
    };

    onMounted(() => {
      vectorTableSummary(props.layerId);
      getStyleVectorFeatureGraphs();
    });

    return {
      summaryData,
      loading,
      error,
      tableChartDialog,
      activeTab,
      availableColumns,
      selectedTableName,
      selectedTableType,
      selectedXColumn,
      selectedYColumn,
      selectedIndexerColumn,
      editingGraphIndex,
      graphs,
      addSaveGraph,
      editGraph,
      deleteGraph,
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
  <v-row v-for="(graph, index) in graphs" :key="index">
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
        <v-tab value="summary">
          Summary
        </v-tab>
        <v-tab value="graphs">
          Graphs
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

      <v-card-text v-if="activeTab === 'graphs'">
        <v-card-text>
          <v-form>
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
              label="Select X Axis"
            />
            <v-select
              v-model="selectedYColumn"
              :items="availableColumns"
              label="Select Y Axis"
            />
            <v-select
              v-model="selectedIndexerColumn"
              :items="availableColumns"
              label="Select Indexer Column"
            />
            <v-btn :disabled="!selectedTableType || !selectedXColumn || !selectedYColumn" color="primary" @click="addSaveGraph">
              {{ editingGraphIndex !== null ? 'Update' : 'Add' }} Graph
            </v-btn>
          </v-form>
          <v-divider />
          <v-list>
            <v-list-item v-for="(graph, index) in graphs" :key="index">
              <v-list-item-title>{{ graph.name }}</v-list-item-title>
              <v-list-item-subtitle>
                <div>{{ graph.type }}</div>
                <div>{{ graph.xAxis }} vs {{ graph.yAxis }} {{ graph.indexer ? `(Indexer - ${graph.indexer}` : '' }})</div>
              </v-list-item-subtitle>
              <v-list-item-subtitle v-if="graph.inexer">
                Indexer: {{ graph.indexer }}
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
