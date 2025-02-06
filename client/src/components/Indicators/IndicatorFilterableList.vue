<script setup lang="ts">
import {
  computed, ref, shallowRef, triggerRef,
  watch,
} from 'vue';
import { Indicator } from '../../types';
import IndicatorListItem from './IndicatorListItem.vue';

const props = defineProps<{
  indicators: Array<Indicator>
}>();

function doesIndicatorMatchFilter(indicator: Indicator, filter: string) {
  if (!filter.length) return true;
  // O(N*G*K) for N indicators, max G hierarchy length, and K terms
  const filterTerms = filter.split(/\s+/);
  return filterTerms.every(
    (term) => (
      indicator.short_name.toLowerCase().includes(term)
      || indicator.long_name.toLowerCase().includes(term)
      || indicator.hierarchy.some((group) => group.toLowerCase().includes(term))
    ),
  );
}

const userFilterInput = ref<string | undefined>('');
const filteredIndicators = computed(() => {
  const cleanedFilter = (userFilterInput.value ?? '').trim().toLowerCase();
  return props.indicators.filter((indicator) => doesIndicatorMatchFilter(indicator, cleanedFilter));
});
const expanded = shallowRef(new Set<string>());
const NO_GROUP_CATEGORY: string = '';
const groupedIndicators = computed(() => Object.entries(filteredIndicators.value.reduce((acc, indicator) => {
  const groupName = indicator.hierarchy[0] || NO_GROUP_CATEGORY;
  return {
    ...acc,
    [groupName]: [...(acc[groupName] ?? []), indicator],
  };
}, {} as Record<string, Indicator[]>)).map(([groupName, groupItems]) => ({
  name: groupName,
  expanded: expanded.value.has(groupName),
  items: groupItems,
})).sort((a, b) => {
  if (a.name === NO_GROUP_CATEGORY) return 1;
  return a.name.localeCompare(b.name);
}));

// if the indicator list changes, then clear `expanded
watch(() => props.indicators, () => {
  expanded.value.clear();
  triggerRef(expanded);
});

function toggleGroup(groupName: string) {
  if (expanded.value.has(groupName)) {
    expanded.value.delete(groupName);
  } else {
    expanded.value.add(groupName);
  }
  triggerRef(expanded);
}
</script>

<template>
  <v-container class="d-flex flex-column overflow-hidden h-100">
    <v-text-field
      v-model="userFilterInput"
      label="Filter by Indicator"
      prepend-inner-icon="mdi-magnify"
      variant="outlined"
      hide-details
      single-line
      density="compact"
      clearable
      class="flex-grow-0"
    />
    <div class="flex-grow-1 overflow-y-auto">
      <v-table class="list">
        <thead>
          <tr>
            <th class="text-left">
              Indicator
            </th>
            <th class="text-left value-col">
              Value
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-for="group in groupedIndicators">
            <template v-if="group.name !== NO_GROUP_CATEGORY">
              <tr :key="`${group.name}_group`" class="row">
                <td colspan="2">
                  <v-btn
                    :icon="group.expanded ? '$expand' : '$next'"
                    variant="text"
                    size="small"
                    @click="toggleGroup(group.name)"
                  />
                  {{ group.name }}
                </td>
              </tr>
              <template v-if="group.expanded">
                <indicator-list-item v-for="indicator in group.items" :key="indicator.long_name" :indicator="indicator" />
              </template>
            </template>
            <template v-else>
              <indicator-list-item v-for="indicator in group.items" :key="indicator.long_name" :indicator="indicator" />
            </template>
          </template>
        </tbody>
      </v-table>
      <div
        v-if="!filteredIndicators.length"
        class="text-center py-6 text-grey-darken-2"
      >
        No indicators
      </div>
    </div>
  </v-container>
</template>

<style scoped>
.list >>> table {
  table-layout: fixed;
}

.row:nth-child(odd) {
  background-color: #E1F5FE44;
}

.row {
  background-color: transparent;
  transition: background-color 0.3s;
}

.row:hover {
  background-color: #B3E5FC;
}

.value-col {
  width: 30%;
}
</style>
