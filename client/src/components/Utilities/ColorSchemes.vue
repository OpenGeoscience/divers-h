<script lang="ts">
import {
  computed,
  defineComponent,
  ref,
} from 'vue';

import {
  colorSchemes,
} from '../../utils';

export default defineComponent({
  props: {
    defaultTheme: {
      type: String,
      default: 'viridis',
    },
    displaySelected: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['chooseColorScheme'],
  setup(props, { emit }) {
    const selectedThemeName = ref('d3.viridis');
    const chooseColorScheme = (schemeName: string) => {
      emit('chooseColorScheme', schemeName);
      selectedThemeName.value = schemeName;
    };

    const selectedScheme = computed(() => colorSchemes.find((item) => item.name === selectedThemeName.value));

    return {
      d3ColorSchemes: colorSchemes,
      chooseColorScheme,
      selectedThemeName,
      selectedScheme,
    };
  },
});
</script>

<template>
  <v-menu
    offset-y
    offset-x
    nudge-left="180"
    max-width="180"
    open-on-hover
  >
    <template #activator="{ props }">
      <v-btn
        v-if="!displaySelected"
        size="x-small"
        color="primary"
        v-bind="props"
      >
        Color Schemes
      </v-btn>
      <div v-else-if="selectedScheme" align="center" class="my-2">
        <span class="mx-2">Color Scheme:</span>
        <v-btn v-bind="props" size="large" class="pa-0 ma-0 mx-2" width="150">
          <v-list-item>
            <v-list-item-title>
              {{ selectedScheme.name }}
            </v-list-item-title>
            <v-list-item-subtitle>
              <!-- Display color swatches as squares -->
              <v-avatar v-for="color in selectedScheme.colors" :key="color" size="10" :style="{ backgroundColor: color }" />
            </v-list-item-subtitle>
          </v-list-item>
        </v-btn>
      </div>
    </template>
    <v-card outlined>
      <v-list>
        <v-list-item
          v-for="(scheme, index) in d3ColorSchemes"
          :key="index"
          @click="chooseColorScheme(scheme.name)"
        >
          <v-list-item-title>
            {{ scheme.name }}
          </v-list-item-title>
          <v-list-item-subtitle>
            <!-- Display color swatches as squares -->
            <v-avatar v-for="color in scheme.colors" :key="color" size="10" :style="{ backgroundColor: color }" />
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>
    </v-card>
  </v-menu>
</template>

<style scoped>
</style>
