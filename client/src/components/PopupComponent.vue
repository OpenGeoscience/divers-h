<script setup lang="ts">
import { computed, onMounted } from 'vue';
import MapStore from '../MapStore';

const props = defineProps<{
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data:Record<string, any>[];
}>();

const headers = computed(() => {
  // inject headers into the system
  const subHeaders: string[] = [];
  props.data.forEach((item) => {
    Object.keys(item).forEach((key) => {
      if (!subHeaders.includes(key) && MapStore.toolTipDisplay.value[key] !== false) {
        subHeaders.push(key);
      }
    });
  });
  const resultHeaders = subHeaders.map((item) => ({ title: item, key: item, sortable: true }));
  return resultHeaders;
});

onMounted(() => {
  const localHeaders: string[] = [];
  props.data.forEach((item) => {
    Object.keys(item).forEach((key) => {
      if (!localHeaders.includes(key)) {
        localHeaders.push(key);
      }
    });
  });
  localHeaders.forEach((header) => {
    if (MapStore.toolTipDisplay.value[header] === undefined) {
      MapStore.toolTipDisplay.value[header] = true;
    }
  });
});
const items = computed(() => props.data);

const toolTipDisplayVals = computed(() => MapStore.toolTipDisplay.value);

const toggleColumn = (column: string, val: boolean) => {
  if (MapStore.toolTipDisplay.value[column]) {
    MapStore.toolTipDisplay.value[column] = val;
  }
};
</script>

<template>
  <v-card
    dense
    variant="flat"
  >
    <v-row class="py-4">
      <v-spacer />
      <v-menu
        id="tooltip-menu"
        v-model="MapStore.toolTipMenuOpen.value"
        open-delay="20"
        :close-on-content-click="false"
        location="start"
      >
        <template #activator="{ props }">
          <v-icon
            color="primary"
            v-bind="props"
            size="20"
            class="mr-5"
          >
            mdi-cog
          </v-icon>
        </template>
        <v-card
          class="pa-4"
          style="overflow-y: hidden;"
        >
          <v-row
            v-for="(column, key) in toolTipDisplayVals"
            :key="`${column}_${key}`"
            density="compact"
          >
            <v-checkbox
              v-model="toolTipDisplayVals[key]"
              style="max-height: 30px;"
              color="primary"
              density="compact"
              :label="key"
              @change="toggleColumn(key, $event)"
            />
          </v-row>
        </v-card>
      </v-menu>
    </v-row>
    <v-row dense>
      <v-card dense>
        <v-data-table
          density="compact"
          :headers="headers"
          :items="items"
          class="tooltip"
        >
          <template #bottom />
        </v-data-table>
      </v-card>
    </v-row>
  </v-card>
</template>

<style scoped>
.tooltip {
  font-size: 0.75em;
}
.smallDisplay {
  font-size: 0.75em;
}
</style>
