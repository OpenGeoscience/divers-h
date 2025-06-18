/* eslint-disable no-console */
/* eslint-disable no-underscore-dangle */
import { Ref, reactive, toRefs } from 'vue';
import { VideoSource } from 'maplibre-gl';
import UVdatApi from '../api/UVDATApi';

export type FMVVectorTypes = 'flight_path' | 'ground_frame' | 'ground_union';
export interface FMVVideoState {
  frameId: number;
  videoFrame: number;
  videoElement: HTMLVideoElement | null;
  frameIdToBounds: Record<number, [[number, number], [number, number], [number, number], [number, number]]>
  visibleProperties: (FMVVectorTypes | 'video')[];
  filterFrameStatus: boolean;
  videoState: 'pause' | 'playing';
  opacity: number;
  lockZoom: boolean;
  zoomBounds: number;
}
const createFMVStore = () => {
  const state: FMVVideoState = reactive({
    frameId: 0,
    videoFrame: 0,
    videoElement: null as HTMLVideoElement | null,
    frameIdToBounds: {} as Record<number, [[number, number], [number, number], [number, number], [number, number]]>,
    filterFrameStatus: true,
    visibleProperties: ['flight_path', 'video'] as (FMVVectorTypes | 'video')[],
    videoState: 'pause',
    opacity: 0.85,
    lockZoom: false,
    zoomBounds: 2,
  });

  let videoSource: VideoSource | null = null;

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
      const video = state.videoElement;
      if (video) {
        video.currentTime = frame / videoData.frameFps;
      }
      videoSource?.seek(frame / videoData.frameFps);
      state.frameId = frame;
    } else {
      console.error(`Frame ${frame} is out of bounds. Total frames: ${videoData.totalFrames}`);
    }
  };

  const seekToFrame = (frame: number) => {
    const setTime = frame / videoData.frameFps;
    if (state.videoElement) {
      state.videoFrame = frame;
      videoSource?.seek(setTime);
    }
  };

  const seekOffset = (offset: number) => {
    const newFrame = Math.max(0, Math.min(videoData.totalFrames - 1, state.videoFrame + offset));
    seekToFrame(newFrame);
  };

  const startAnimationLoop = () => {
    const video = state.videoElement;
    if (!video) return;

    const updateFrame = () => {
      if (!video.paused && !video.ended) {
        const currentFrame = Math.floor(video.currentTime * videoData.frameFps);
        state.videoFrame = currentFrame;
        state.frameId = state.videoFrame;
        animationFrameId = requestAnimationFrame(updateFrame);
      } else {
        if (animationFrameId) {
          cancelAnimationFrame(animationFrameId);
        }
        animationFrameId = null;
      }
    };

    updateFrame();
  };

  const setVideoSource = (baseSource: VideoSource) => {
    if (state.videoElement && animationFrameId) {
      cancelAnimationFrame(animationFrameId);
    }
    videoSource = baseSource;
    state.videoElement = baseSource.getVideo();

    if (state.videoElement) {
      state.videoElement.autoplay = false;
      state.videoElement.pause();

      state.videoElement.onplay = () => {
        startAnimationLoop();
        state.videoState = 'playing';
      };

      state.videoElement.onpause = () => {
        if (animationFrameId) {
          cancelAnimationFrame(animationFrameId);
          animationFrameId = null;
          state.videoState = 'pause';
        }
      };
    }
  };

  const setVideoState = (val: 'playing' | 'pause') => {
    if (val === 'pause') {
      state.videoElement?.pause();
      state.videoState = val;
    } else if (val === 'playing') {
      if (state.videoElement) {
        state.videoElement.currentTime = state.frameId / videoData.frameFps;
      }
      state.videoElement?.play();
      state.videoState = 'pause';
    }
  };

  const baseVectorTypes: FMVVectorTypes[] = ['flight_path', 'ground_frame', 'ground_union'];
  const layerTypeVectorTypeMap: Record<FMVVectorTypes, 'circle' | 'fill'> = {
    flight_path: 'circle',
    ground_frame: 'fill',
    ground_union: 'fill',
  };

  const setPlaybackSpeed = (speed: number) => {
    if (state.videoElement) {
      state.videoElement.playbackRate = speed;
    }
  };

  return {
    ...toRefs(state),
    videoData,
    baseVectorTypes,
    layerTypeVectorTypeMap,
    getBoundsAtFrame,
    getFMVLayerInfo,
    setVideoFrame,
    setVideoSource,
    seekOffset,
    seekToFrame,
    setVideoState,
    setPlaybackSpeed,
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
  videoElement: Ref<HTMLVideoElement | null>;
  frameIdToBounds: Ref<Record<number, [[number, number], [number, number], [number, number], [number, number]]>>;
  visibleProperties: Ref<(FMVVectorTypes | 'video')[]>;
  filterFrameStatus: Ref<boolean>;
  videoState: Ref<'pause' | 'playing'>;
  opacity: Ref<number>;
  lockZoom: Ref<boolean>;
  zoomBounds: Ref<number>;

  videoData: {
    frameFps: number;
    frameWidth: number;
    frameHeight: number;
    totalFrames: number;
    videoUrl: string;
  };

  baseVectorTypes: FMVVectorTypes[];
  layerTypeVectorTypeMap: Record<FMVVectorTypes, 'circle' | 'fill'>;

  setVideoSource: (baseSource: VideoSource) => void;
  setVideoFrame: (frame: number) => void;
  setPlaybackSpeed: (speed: number) => void;
  seekOffset: (offset: number) => void;
  seekToFrame: (offset: number) => void;
  getFMVLayerInfo: (id: number) => Promise<void>;
  setVideoState: (val: 'playing' | 'pause') => void;
  getBoundsAtFrame: (
    id: number
  ) => [[number, number], [number, number], [number, number], [number, number]];
}
