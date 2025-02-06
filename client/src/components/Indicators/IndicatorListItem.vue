<script setup lang="ts">
import { Indicator } from '../../types';

defineProps<{
  indicator: Indicator;
}>();

function truncateHierarchy(items: string[], cutoff = 3) {
  return items.length > cutoff ? [items[0], items[1], '...', items[items.length - 1]] : items;
}

function shortenValue(value: number | string) {
  if (typeof value === 'string') return value;
  // anything smaller than 0.01 will be converted to scientific
  if (Math.abs(value) < 0.01) return value.toExponential(2);
  return value.toFixed(2);
}
</script>

<template>
  <tr class="row">
    <td class="indicator-name pl-15">
      <template v-for="group in truncateHierarchy(indicator.hierarchy.slice(1))" :key="group">
        <span class="group-name">
          {{ group }}
        </span>
        <v-icon v-if="indicator.hierarchy.length" size="x-small">
          mdi-menu-right
        </v-icon>
      </template>
      <div class="short-name">
        {{ indicator.short_name }}
      </div>
    </td>
    <td class="indicator-value">
      {{ shortenValue(indicator.value) }} {{ indicator.units }}
    </td>
    <v-tooltip activator="parent" location="bottom" open-delay="1000">
      <div class="d-flex flex-column align-center">
        <div class="pb-2">
          <strong>{{ shortenValue(indicator.value) }}</strong> {{ indicator.units }}
        </div>
        <div>{{ indicator.long_name }}</div>
        <div v-if="indicator.hierarchy.length">
          {{ indicator.hierarchy.map((g) => `${g} >`).join(' ') }}
          {{ indicator.short_name }}
        </div>
      </div>
    </v-tooltip>
  </tr>
</template>

<style scoped>
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

.indicator-name {
  display: flex;
  flex-flow: row;
  align-items: center;
  flex-wrap: nowrap;
  justify-content: start;
  min-width: 0;
}

.indicator-value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.short-name {
  flex-shrink: 0;
}
</style>
