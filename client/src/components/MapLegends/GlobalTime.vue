<script lang="ts">
import { computed, defineComponent } from 'vue';
import MapStore from '../../MapStore';

export default defineComponent({
  name: 'GlobalTime',
  components: {
  },
  props: {
  },
  setup() {
    const minMax = computed(() => MapStore.graphChartsMinMax.value);

    const updateGlobalTime = (time: number) => {
      let updateTime = time;
      if (time > minMax.value.max) {
        updateTime = minMax.value.max;
      } else if (time < minMax.value.min) {
        updateTime = minMax.value.min;
      }
      MapStore.globalTime.value = updateTime;
    };
    const dateString = computed(() => {
      const date = new Date(MapStore.globalTime.value * 1000);
      return date.toISOString().split('T')[0];
    });

    return {
      minMax,
      globalTime: MapStore.globalTime,
      updateGlobalTime,
      dateString,
    };
  },
});
</script>

<template>
  <v-row>
    <v-col cols="1">
      <v-tooltip text="Global Time">
        <template #activator="{ props }">
          <v-icon
            class="pl-3"
            v-bind="props"
            color="primary"
          >
            mdi-timer-outline
          </v-icon>
        </template>
      </v-tooltip>
    </v-col>
    <v-col cols="6">
      <v-slider
        :model-value="globalTime"
        :min="minMax.min"
        :max="minMax.max"
        step="1"
        hide-details
        thumb-size="12"
        track-size="4"
        color="primary"
        track-color="grey lighten-3"
        density="compact"
        @update:model-value="updateGlobalTime($event)"
      />
    </v-col>
    <v-col
      cols="5"
      class="text-right pr-1"
    >
      <span class="text-xs">{{ dateString }}</span>
    </v-col>
  </v-row>
</template>
