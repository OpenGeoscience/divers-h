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
    const minMaxSteps = computed(() => MapStore.globalTimeRange.value);
    const updateGlobalTime = (time: number) => {
      let updateTime = time;
      if (time > minMaxSteps.value.max) {
        updateTime = minMaxSteps.value.max;
      } else if (time < minMaxSteps.value.min) {
        updateTime = minMaxSteps.value.min;
      }
      MapStore.globalTime.value = updateTime;
    };
    const dateString = computed(() => {
      const date = new Date(MapStore.globalTime.value * 1000);
      return date.toISOString().split('T')[0];
    });

    const toggleLink = () => {
      MapStore.timeLinked.value = !MapStore.timeLinked.value;
    };

    return {
      minMaxSteps,
      globalTime: MapStore.globalTime,
      timeLinked: MapStore.timeLinked,
      updateGlobalTime,
      dateString,
      toggleLink,
    };
  },
});
</script>

<template>
  <v-row align="center" justify="center" dense>
    <v-col cols="1">
      <v-tooltip text="Global Time">
        <template #activator="{ props }">
          <v-icon
            class="pl-3"
            v-bind="props"
            color="primary"
            @click="toggleLink()"
          >
            mdi-timer-lock-outline
          </v-icon>
        </template>
        <span>Global Time Slider</span>
      </v-tooltip>
    </v-col>
    <v-col cols="6">
      <v-slider
        :model-value="globalTime"
        :min="minMaxSteps.min"
        :max="minMaxSteps.max"
        :step="minMaxSteps.stepSize"
        :disabled="!timeLinked"
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
