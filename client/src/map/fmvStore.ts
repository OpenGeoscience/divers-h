import { ref, reactive, computed, toRefs, Ref } from 'vue';
import UVdatApi from '../api/UVDATApi';

export type FMVVectorTypes = 'flight_path' | 'ground_frame' | 'ground_union';

const createFMVStore = () => {
  const state = reactive({
    frameId: 0,
    videoFrame: 0,
    videoSource: null as HTMLVideoElement | null,
    frameIdToBounds: {} as Record<number, [[number, number], [number, number], [number, number], [number, number]]>,
    filterFrameStatus: false,
    visibleProperties: ['flight_path', 'video'] as (FMVVectorTypes | 'video')[],
  });

  const videoData = reactive({
    frameFps: 30,
    frameWidth: 1920,
    frameHeight: 1080,
    totalFrames: 0,
    videoUrl: '',
  });

  let animationFrameId: number | null = null;

  const getFMVLayerInfo = async (mapLayerId: number) => {
    const data = await UVdatApi.getFMVLayerData(mapLayerId);
    if (data) {
      Object.assign(videoData, {
        frameFps: data.fmvFps || videoData.frameFps,
        frameWidth: data.fmvFrameWidth || videoData.frameWidth,
        frameHeight: data.fmvFrameHeight || videoData.frameHeight,
        totalFrames: data.fmvFrameCount || videoData.totalFrames,
        videoUrl: data.fmvVideoUrl || '',
      });
      state.frameIdToBounds = data.frameIdToBBox || {};
    }
  };

  const getBoundsAtFrame = (id: number) => {
    let corners = state.frameIdToBounds[id];
    if (!corners) {
      const sortedIds = Object.keys(state.frameIdToBounds)
        .map(Number)
        .sort((a, b) => a - b);
      const nextId = sortedIds.find((existingId) => existingId > id);
      if (nextId !== undefined) {
        corners = state.frameIdToBounds[nextId];
      }
    }

    if (!corners) {
      console.error(`No bounds found for frameId ${id}`);
    }

    return corners as [[number, number], [number, number], [number, number], [number, number]];
  };

  const setVideoFrame = (frame: number) => {
    if (frame >= 0 && frame < videoData.totalFrames) {
      state.videoFrame = frame;
      const video = state.videoSource;
      if (video) {
        video.currentTime = frame / videoData.frameFps;
      }
      state.frameId = frame;
    } else {
      console.error(`Frame ${frame} is out of bounds. Total frames: ${videoData.totalFrames}`);
    }
  };

  const seekFrames = (offset: number) => {
    const newFrame = Math.max(0, Math.min(videoData.totalFrames - 1, state.videoFrame + offset));
    setVideoFrame(newFrame);
  };

  const startAnimationLoop = () => {
    const video = state.videoSource;
    if (!video) return;

    const updateFrame = () => {
      if (!video.paused && !video.ended) {
        const currentFrame = Math.floor(video.currentTime * videoData.frameFps);
        state.videoFrame = currentFrame;
        animationFrameId = requestAnimationFrame(updateFrame);
      } else {
        animationFrameId && cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
      }
    };

    updateFrame();
  };

  const setVideoElement = (videoElement: HTMLVideoElement | null) => {
    if (state.videoSource && animationFrameId) {
      cancelAnimationFrame(animationFrameId);
    }

    state.videoSource = videoElement;

    if (state.videoSource) {
      state.videoSource.autoplay = false;
      state.videoSource.pause();

      state.videoSource.onplay = () => {
        startAnimationLoop();
      };

      state.videoSource.onpause = () => {
        if (animationFrameId) {
          cancelAnimationFrame(animationFrameId);
          animationFrameId = null;
        }
      };
    }
  };

  const baseVectorTypes: FMVVectorTypes[] = ['flight_path', 'ground_frame', 'ground_union'];
  const layerTypeVectorTypeMap: Record<FMVVectorTypes, 'circle' | 'fill'> = {
    flight_path: 'circle',
    ground_frame: 'fill',
    ground_union: 'fill',
  };

  return {
    ...toRefs(state),
    videoData,
    baseVectorTypes,
    layerTypeVectorTypeMap,
    getBoundsAtFrame,
    getFMVLayerInfo,
    setVideoFrame,
    setVideoElement,
    seekFrames,
  };
};

export const fmvStores: Record<number, ReturnType<typeof createFMVStore>> = {};

export const getFMVStore = async (mapLayerId: number) => {
  if (!fmvStores[mapLayerId]) {
    console.log(`Creating new FMV store for mapLayerId ${mapLayerId}`);
    fmvStores[mapLayerId] = createFMVStore();
    await fmvStores[mapLayerId].getFMVLayerInfo(mapLayerId).catch((error) => {
      console.error(`Error fetching FMV layer data for mapLayerId ${mapLayerId}:`, error);
    });
  }
  return fmvStores[mapLayerId];
};

export interface FMVStore {
  frameId: Ref<number>;
  videoFrame: Ref<number>;
  videoSource: Ref<HTMLVideoElement | null>;
  frameIdToBounds: Ref<Record<number, [[number, number], [number, number], [number, number], [number, number]]>>;
  visibleProperties: Ref<(FMVVectorTypes | 'video')[]>;
  filterFrameStatus: Ref<boolean>;

  videoData: {
    frameFps: number;
    frameWidth: number;
    frameHeight: number;
    totalFrames: number;
    videoUrl: string;
  };

  baseVectorTypes: FMVVectorTypes[];
  layerTypeVectorTypeMap: Record<FMVVectorTypes, 'circle' | 'fill'>;

  setVideoElement: (el: HTMLVideoElement | null) => void;
  setVideoFrame: (frame: number) => void;
  seekFrames: (offset: number) => void;
  getFMVLayerInfo: (id: number) => Promise<void>;
  getBoundsAtFrame: (
    id: number
  ) => [[number, number], [number, number], [number, number], [number, number]];
}
