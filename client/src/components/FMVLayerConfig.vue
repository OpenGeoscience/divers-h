<script lang="ts">
import {
  PropType, computed, defineComponent, onMounted, ref, watch,
} from 'vue';
import { FMVStore, FMVVectorTypes, getFMVStore } from '../map/fmvStore';
import { FMVLayer } from '../types';
import { updateFMVLayer, updateFMVVideoMapping } from '../map/mapFMVLayer';

export default defineComponent({
  props: {
    layer: {
      type: Object as PropType<FMVLayer>,
      required: true,
    },
  },
  setup(props) {
    const fmvStore = ref<FMVStore | null>(null);
    const loaded = ref(false);
    const totalFrames = ref(0);
    const allProperties = ['flight_path', 'ground_frame', 'ground_union', 'video'];
    watch(() => fmvStore.value?.videoFrame, (newFrame) => {
      if (newFrame && fmvStore.value) {
        fmvStore.value.frameId = newFrame;
        updateFMVVideoMapping(props.layer);
      }
    });
    const frameId = computed<number>({
      get: () => fmvStore.value?.frameId ?? 0,
      set: (val) => {
        if (fmvStore.value) {
          fmvStore.value.frameId = val;
          updateFMVLayer(props.layer);
          updateFMVVideoMapping(props.layer);
        }
      },
    });

    const visibleProperties = computed<(FMVVectorTypes | 'video')[]>({
      get: () => fmvStore.value?.visibleProperties ?? [],
      set: (val) => {
        if (fmvStore.value) {
          fmvStore.value.visibleProperties = val;
          updateFMVLayer(props.layer);
        }
      },
    });

    const filterFrameStatus = computed<boolean>({
      get: () => fmvStore.value?.filterFrameStatus ?? false,
      set: (val) => {
        if (fmvStore.value) {
          fmvStore.value.filterFrameStatus = val;
          updateFMVLayer(props.layer);
        }
      },
    });

    onMounted(async () => {
      fmvStore.value = await getFMVStore(props.layer.id);
      if (fmvStore.value) {
        totalFrames.value = fmvStore.value.videoData.totalFrames ?? 0;
        loaded.value = true;
      }
    });

    const isPlaying = computed(() => !fmvStore.value?.videoSource?.paused);

    function togglePlayback() {
      const video = fmvStore.value?.videoSource;
      if (!video) return;
      if (video.paused) {
        video.play();
      } else {
        video.pause();
      }
    }

    function seekFrames(offset: number) {
      const store = fmvStore.value;
      if (!store) return;
      store.seekFrames(offset);
      updateFMVVideoMapping(props.layer);
    }

    return {
      frameId,
      visibleProperties,
      filterFrameStatus,
      totalFrames,
      allProperties,
      loaded,
      isPlaying,
      togglePlayback,
      seekFrames,

    };
  },
});
</script>

<template>
  <v-card-title>FMV Layer Controls</v-card-title>
  <v-card-text v-if="loaded">
    <v-row dense align="center" class="icon-row mb-2">
      <v-col class="d-flex align-center gap-2">
        <v-btn icon variant="plain" size="small" @click="seekFrames(-frameId)">
          <v-icon>mdi-skip-backward</v-icon>
        </v-btn>
        <v-btn icon variant="plain" size="small" @click="seekFrames(-1)">
          <v-icon>mdi-step-backward</v-icon>
        </v-btn>
        <v-btn icon variant="plain" size="small" @click="togglePlayback">
          <v-icon>{{ isPlaying ? 'mdi-pause' : 'mdi-play' }}</v-icon>
        </v-btn>
        <v-btn icon variant="plain" size="small" @click="seekFrames(1)">
          <v-icon>mdi-step-forward</v-icon>
        </v-btn>
        <v-btn icon variant="plain" size="small" @click="seekFrames(totalFrames - frameId)">
          <v-icon>mdi-skip-forward</v-icon>
        </v-btn>
      </v-col>
    </v-row>
    <!-- Frame ID Slider -->
    <v-row dense align="center">
      <v-col cols="3">
        <span>Frame ID:</span>
      </v-col>
      <v-col>
        <v-slider
          v-model="frameId"
          :min="0"
          :max="totalFrames"
          step="1"
          thumb-label
          :disabled="totalFrames === 0"
        />
      </v-col>
      <v-col cols="2">
        <span>{{ frameId }}</span>
      </v-col>
    </v-row>

    <!-- Visible Properties Multi-select -->
    <v-row dense align="center">
      <v-col cols="3">
        <span>Visible Properties:</span>
      </v-col>
      <v-col>
        <v-select
          v-model="visibleProperties"
          :items="allProperties"
          label="Visible Properties"
          multiple
          chips
          clearable
        />
      </v-col>
    </v-row>

    <!-- Filter by Frame Checkbox -->
    <v-row dense align="center">
      <v-col cols="3">
        <span>Filter by Frame:</span>
      </v-col>
      <v-col>
        <v-checkbox
          v-model="filterFrameStatus"
          label="Enable Frame Filtering"
        />
      </v-col>
    </v-row>
  </v-card-text>
  <v-card-text v-else>
    Loading FMV Layer controls...
  </v-card-text>
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
