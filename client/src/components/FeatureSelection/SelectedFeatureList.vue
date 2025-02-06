<script lang="ts">
import {
  computed, defineComponent,
} from 'vue';
import MapStore from '../../MapStore';
import SelectedFeature from './SelectedFeature.vue';

export default defineComponent({
  components: {
    SelectedFeature,
  },
  setup() {
    const selectedFeatures = computed(() => MapStore.selectedFeatures.value);
    const clearSelectedFeatures = () => {
      MapStore.clearSelectedFeatures();
    };
    return {
      selectedFeatures,
      clearSelectedFeatures,
    };
  },
});
</script>

<template>
  <v-navigation-drawer
    v-if="selectedFeatures.length"
    width="300"
  >
    <v-card>
      <v-row dense class="px-2 py-2">
        <h1>Selected Features</h1>
        <v-spacer />
        <v-btn size="x-small" color="error" @click="clearSelectedFeatures()">
          clear
        </v-btn>
      </v-row>
      <selected-feature
        v-for="item in selectedFeatures"
        :key="`${item.id}_id_selected`"
        :data="item"
      />
    </v-card>
  </v-navigation-drawer>
</template>

<style scoped>

</style>
