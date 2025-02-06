<script lang="ts">
import { defineComponent, ref } from 'vue';
import { FeatureChart } from '../../types'; // Assuming FeatureChart is in a types file
import FeatureChartEditor from './FeatureChartEditor.vue';
import MapStore from '../../MapStore';

export default defineComponent({
  name: 'SelectedFeatureCharts',
  components: { FeatureChartEditor },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
    featureCharts: {
      type: Array as () => FeatureChart[],
      required: true,
    },
  },
  setup(props) {
    const editorDialog = ref(false);
    const editChart = ref<FeatureChart | null>(null);
    const editIndex = ref<number | null>(null);

    const addFeatureChart = () => {
      editChart.value = null;
      editorDialog.value = true;
    };

    const editFeatureChart = (index: number) => {
      editChart.value = { ...props.featureCharts[index] }; // clone to avoid direct modification
      editIndex.value = index;
      editorDialog.value = true;
    };

    const deleteFeatureChart = (index: number) => {
      const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.layerId);
      if (found && found.default_style.selectedFeatureCharts?.length) {
        found.default_style.selectedFeatureCharts.splice(index, 1);
      }
    };

    const saveFeatureChart = (newChart: FeatureChart) => {
      const found = MapStore.selectedVectorMapLayers.value.find((item) => item.id === props.layerId);
      if (found && found.default_style.selectedFeatureCharts) {
        if (editIndex.value !== null) {
          found.default_style.selectedFeatureCharts[editIndex.value] = newChart;
        } else {
          found.default_style.selectedFeatureCharts.push(newChart);
        }
      }
      editorDialog.value = false;
    };

    const cancelEdit = () => {
      editorDialog.value = false;
    };

    return {
      editorDialog,
      editChart,
      editIndex,
      addFeatureChart,
      editFeatureChart,
      deleteFeatureChart,
      saveFeatureChart,
      cancelEdit,
    };
  },
});
</script>

  <!-- SelectedFeatureCharts.vue -->
<template>
  <v-container>
    <v-row class="py-2">
      <v-col>
        <h2>Feature Charts</h2>
      </v-col>
      <v-spacer />
      <v-col>
        <v-btn color="success" @click="addFeatureChart">
          Add Feature Chart
        </v-btn>
      </v-col>
    </v-row>
    <!-- List of Feature Charts -->
    <v-list>
      <v-list-item v-for="(chart, index) in featureCharts" :key="chart.name">
        <v-list-item-title>{{ chart.name }}</v-list-item-title>
        <v-list-item-subtitle>{{ chart.description }}</v-list-item-subtitle>
        <v-list-item-action>
          <v-row>
            <v-spacer />
            <v-btn icon variant="plain" color="warning" @click="editFeatureChart(index)">
              <v-icon>mdi-pencil</v-icon>
            </v-btn>
            <v-btn icon variant="plain" color="error" @click="deleteFeatureChart(index)">
              <v-icon>mdi-delete</v-icon>
            </v-btn>
          </v-row>
        </v-list-item-action>
      </v-list-item>
    </v-list>

    <!-- Editor Dialog -->
    <v-dialog v-model="editorDialog" max-width="600px">
      <v-card>
        <v-card-title>Edit Feature Chart</v-card-title>
        <v-card-text>
          <FeatureChartEditor
            :edit-feature-chart="editChart"
            :layer-id="layerId"
            @save="saveFeatureChart($event)"
            @cancel="cancelEdit()"
          />
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-container>
</template>
