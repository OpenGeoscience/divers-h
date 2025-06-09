<script lang="ts">
import {
  PropType, computed, defineComponent, onMounted, onUnmounted, ref, watch,
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

    const lockZoom = computed({
      get: () => fmvStore.value?.lockZoom ?? false,
      set: (val) => {
        if (fmvStore.value) {
          fmvStore.value.lockZoom = val;
        }
      },
    });

    const zoomBounds = computed({
      get: () => fmvStore.value?.zoomBounds ?? 1.5,
      set: (val) => {
        if (fmvStore.value) {
          fmvStore.value.zoomBounds = val;
        }
      },
    });

    const opacity = computed({
      get: () => fmvStore.value?.opacity ?? 0,
      set: (val) => {
        if (fmvStore.value) {
          fmvStore.value.opacity = val;
          updateFMVLayer(props.layer);
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

    const isPlaying = computed(() => fmvStore.value?.videoState === 'playing');

    function togglePlayback() {
      if (fmvStore.value) {
        const newState = fmvStore.value.videoState === 'playing' ? 'pause' : 'playing';
        fmvStore.value.setVideoState(newState);
      }
    }

    function seekOffset(offset: number) {
      const store = fmvStore.value;
      if (!store) return;
      store.seekOffset(offset);
      updateFMVVideoMapping(props.layer);
    }

    let keyHoldInterval: ReturnType<typeof setInterval> | null = null;
    let keyHoldStartTime = 0;

    function getFrameJump(): number {
      const heldDuration = Date.now() - keyHoldStartTime;
      const secondsHeld = heldDuration / 1000;

      // Increase jump size linearly, maxing out at 100 frames after ~20s
      return Math.min(100, Math.floor(1 + secondsHeld * 5));
    }

    function stopFrameJump() {
      if (keyHoldInterval) {
        clearInterval(keyHoldInterval);
        keyHoldInterval = null;
      }
    }

    function jumpFrame(direction: 'left' | 'right', jump: number = 1) {
      if (!fmvStore.value) return;

      const total = fmvStore.value.videoData.totalFrames;
      let newFrameId = fmvStore.value.frameId + (direction === 'right' ? jump : -jump);

      // Wrap around
      if (newFrameId < 0) newFrameId = total - 1;
      if (newFrameId >= total) newFrameId = 0;

      fmvStore.value.frameId = newFrameId;
      updateFMVLayer(props.layer);
      updateFMVVideoMapping(props.layer);
    }

    function startFrameJump(direction: 'left' | 'right') {
      if (!fmvStore.value) return;

      keyHoldStartTime = Date.now();
      stopFrameJump(); // In case it's already running

      // Start the accelerating jump loop
      keyHoldInterval = setInterval(() => {
        const jump = getFrameJump();
        jumpFrame(direction, jump);
      }, 100); // Tune this for responsiveness
    }

    function handleKeydown(event: KeyboardEvent) {
      if (!fmvStore.value) return;

      switch (event.code) {
        case 'Space':
          event.preventDefault();
          togglePlayback();
          break;
        case 'ArrowLeft':
          if (!keyHoldInterval) {
            // Do one frame step immediately
            jumpFrame('left', 1);
            startFrameJump('left');
          }
          break;
        case 'ArrowRight':
          if (!keyHoldInterval) {
            // Do one frame step immediately
            jumpFrame('right', 1);
            startFrameJump('right');
          }
          break;
        default:
          break;
      }
    }

    function handleKeyup(event: KeyboardEvent) {
      if (event.code === 'ArrowLeft' || event.code === 'ArrowRight') {
        stopFrameJump();
      }
    }

    onMounted(() => {
      window.addEventListener('keydown', handleKeydown);
      window.addEventListener('keyup', handleKeyup);
    });

    onUnmounted(() => {
      window.removeEventListener('keydown', handleKeydown);
      window.removeEventListener('keyup', handleKeyup);
      stopFrameJump();
    });

    return {
      frameId,
      visibleProperties,
      filterFrameStatus,
      totalFrames,
      allProperties,
      loaded,
      isPlaying,
      togglePlayback,
      seekOffset,
      opacity,
      lockZoom,
      zoomBounds,
    };
  },
});
</script>

<template>
  <v-card-title>FMV Layer Controls</v-card-title>
  <v-card-text v-if="loaded">
    <v-row dense align="center" class="icon-row mb-2">
      <v-col class="d-flex align-center gap-2">
        <v-btn icon variant="plain" size="small" @click="seekOffset(-frameId)">
          <v-icon>mdi-skip-backward</v-icon>
        </v-btn>
        <v-btn icon variant="plain" size="small" @click="seekOffset(-1)">
          <v-icon>mdi-step-backward</v-icon>
        </v-btn>
        <v-btn icon variant="plain" size="small" @click="togglePlayback">
          <v-icon>{{ isPlaying ? 'mdi-pause' : 'mdi-play' }}</v-icon>
        </v-btn>
        <v-btn icon variant="plain" size="small" @click="seekOffset(1)">
          <v-icon>mdi-step-forward</v-icon>
        </v-btn>
        <v-btn icon variant="plain" size="small" @click="seekOffset(totalFrames - frameId)">
          <v-icon>mdi-skip-forward</v-icon>
        </v-btn>
        <v-chip>{{ frameId }}</v-chip>
        <v-btn
          v-tooltip="'Filter Frames by frameId'"
          icon
          variant="plain"
          size="small"
          @click="filterFrameStatus = !filterFrameStatus"
        >
          <v-icon :color="filterFrameStatus ? 'primary' : ''">
            mdi-filter
          </v-icon>
        </v-btn>
      </v-col>
    </v-row>
    <v-row dense align="center">
      <v-slider
        v-model="frameId"
        :min="0"
        :max="totalFrames"
        step="1"
        thumb-label
        :disabled="totalFrames === 0"
      />
    </v-row>
    <v-divider />

    <v-row dense align="center">
      <v-col cols="1">
        <v-tooltip text="Opacity">
          <template #activator="{ props }">
            <v-icon
              class="pl-3"
              v-bind="props"
            >
              mdi-square-opacity
            </v-icon>
          </template>
        </v-tooltip>
      </v-col>
      <v-col>
        <v-slider
          v-model="opacity"
          density="compact"
          hide-details
          class="opacity-slider"
          min="0"
          max="1.0"
        />
      </v-col>
    </v-row>
    <v-row dense align="center">
      <v-col cols="1">
        <v-tooltip text="Lock Camera to Video, Bounds multiple Value">
          <template #activator="{ props }">
            <v-icon
              class="px-3"
              v-bind="props"
              :color="lockZoom ? 'primary' : ''"
              @click="lockZoom = !lockZoom"
            >
              {{ lockZoom ? 'mdi-lock-outline' : 'mdi-lock-open-outline' }}
            </v-icon>
          </template>
        </v-tooltip>
      </v-col>
      <v-col>
        <v-slider
          v-model="zoomBounds"
          density="compact"
          hide-details
          :min="1"
          :max="5"
          step="0.25"
        />
      </v-col>
      <v-col cols="2">
        {{ zoomBounds }}
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
          hide-details
          label="Visible Properties"
          multiple
          chips
          clearable
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
