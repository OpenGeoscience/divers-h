<script lang="ts">
import { PropType, defineComponent } from 'vue';
import MapStore from '../MapStore';
import { ClickedProps } from '../types';

export default defineComponent({
  components: {
  },
  props: {
    data: {
      type: Object as PropType<ClickedProps>,
      required: true,
    },
  },
  setup(props) {
    const deselectFeature = () => {
      MapStore.removeSelectedFeature(props.data.id as number);
    };
    return {
      deselectFeature,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      <v-row>
        Feature Id: {{ data.id }}
        <v-spacer />
        <v-icon
          size="x-small"
          @click="deselectFeature()"
        >
          mdi-close
        </v-icon>
      </v-row>
    </v-card-title>
    <v-card-text>
      <v-row
        v-for="(item, key) in data.properties"
        :key="`${data.id}_${key}`"
      >
        <v-col>
          {{ key }}
        </v-col>
        <v-col>
          {{ item }}
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.main-area {
  position: absolute;
  top: 65px;
  height: calc(100% - 70px);
  width: 100%;
}
</style>
