<script lang="ts">
import {
  Ref, defineComponent, ref,
} from 'vue';
import AvailableProperties from './Metadata/AvailableProperties.vue';
import MetadataSettings from './Metadata/MetadataSettings.vue';
import SelectedFeatureChartCard from './Metadata/SelectedFeatureChartCard.vue';
import TableSummary from './TabularData/TableSummary.vue';

export default defineComponent({
  components: {
    AvailableProperties,
    MetadataSettings,
    SelectedFeatureChartCard,
    TableSummary,
  },
  props: {
    layerId: {
      type: Number,
      required: true,
    },
  },
  setup() {
    const tab: Ref<'availableProperties' | 'settings' | 'charts' | 'tabularData'> = ref('availableProperties');

    return {
      tab,
    };
  },
});
</script>

<template>
  <v-row dense class="mt-2">
    <v-tooltip text="Properties">
      <template #activator="{ props }">
        <v-icon
          class="icon-center"
          :class="{ 'selected-tab': tab === 'availableProperties' }"
          v-bind="props"
          color="primary"
          size="x-small"
          @click="tab = 'availableProperties'"
        >
          mdi-format-list-bulleted
        </v-icon>
      </template>
    </v-tooltip>
    <v-tooltip text="Property Display Settings">
      <template #activator="{ props }">
        <v-icon
          class="icon-center"
          :class="{ 'selected-tab': tab === 'settings' }"
          v-bind="props"
          color="primary"
          size="x-small"
          @click="tab = 'settings'"
        >
          mdi-cog
        </v-icon>
      </template>
    </v-tooltip>
    <v-tooltip text="Selected Feature Charts">
      <template #activator="{ props }">
        <v-icon
          class="icon-center"
          :class="{ 'selected-tab': tab === 'charts' }"
          v-bind="props"
          color="primary"
          size="x-small"
          @click="tab = 'charts'"
        >
          mdi-chart-bar
        </v-icon>
      </template>
    </v-tooltip>
    <v-tooltip text="Tabular Data">
      <template #activator="{ props }">
        <v-icon
          class="icon-center"
          :class="{ 'selected-tab': tab === 'tabularData' }"
          v-bind="props"
          color="primary"
          size="x-small"
          @click="tab = 'tabularData'"
        >
          mdi-table
        </v-icon>
      </template>
    </v-tooltip>

    <v-spacer />
  </v-row>
  <AvailableProperties v-if="tab === 'availableProperties'" :layer-id="layerId" />
  <MetadataSettings v-else-if="tab === 'settings'" :layer-id="layerId" />
  <SelectedFeatureChartCard v-else-if="tab === 'charts'" :layer-id="layerId" />
  <TableSummary v-else-if="tab === 'tabularData'" :layer-id="layerId" />
</template>

<style scoped>
.tab {
  border: 1px solid lightgray;
}

.tab:hover {
  cursor: pointer;
}

.selected-tab {
  background-color: lightgray;
}

.icon-center {
  width: 35px;
  height: 35px;
  border: 1px solid lightgray;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
