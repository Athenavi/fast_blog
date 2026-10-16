<script lang="ts" setup>
import {ref, watch} from 'vue'

import type {LyricLine} from './helpers'

/**
 * 全屏播放器视图：左黑胶 + 右歌词 + 底部控制条
 *
 * 对应 astro 版 `AudioPlayer/PlayerView.tsx`。
 * **一处结构改进**：原实现自己在 `PlayerView` 里又请求了一次音频元数据
 * （`AudioLayer` 和 `MiniPlayerWrapper` 也各请求一次，共 3 次）；
 * 现在由 `AudioLayer` 统一加载后向下传递，行为不变但少两次请求。
 */
const props = withDefaults(
  defineProps<{
    name?: string
    coverImage?: string | null
    loadingMetadata?: boolean
    lyrics?: LyricLine[]
    isPlaying?: boolean
    currentTime?: number
    duration?: number
    volume?: number
    activeLineIndex?: number
    karaokeProgress?: number
  }>(),
  {
    name: '',
    coverImage: null,
    loadingMetadata: false,
    lyrics: () => [],
    isPlaying: false,
    currentTime: 0,
    duration: 0,
    volume: 1,
    activeLineIndex: -1,
    karaokeProgress: 0,
  },
)

const emit = defineEmits<{
  (e: 'seek', time: number): void
  (e: 'toggle-play'): void
  (e: 'volume-change', volume: number): void
  (e: 'minimize'): void
}>()

const showLyrics = ref(false)

/** 歌词一就位就自动展开（与 astro 版一致） */
watch(
  () => props.lyrics.length,
  (length) => {
    if (length > 0) showLyrics.value = true
  },
)

function toggleLyrics(): void {
  showLyrics.value = !showLyrics.value
}
</script>

<template>
  <div class="flex h-full flex-col bg-black select-none">
    <!-- 主体：黑胶 + 歌词 -->
    <div class="flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row">
      <!-- 最小化（桌面左上角） -->
      <button
        :aria-label="$t('audio.minimizeAria')"
        class="absolute left-4 top-4 z-20 hidden h-8 w-8 items-center justify-center rounded-full bg-white/5 backdrop-blur transition-colors hover:bg-white/15 lg:flex"
        :title="$t('audio.minimizeTitle')"
        type="button"
        @click="emit('minimize')"
      >
        <Icon class="h-4 w-4 text-white/70" name="chevron-down"/>
      </button>

      <VinylRecord
        :cover-image="coverImage"
        :is-playing="isPlaying"
        :loading="loadingMetadata"
        @minimize="emit('minimize')"
      />

      <LyricsPanel
        :active-line-index="activeLineIndex"
        :cover-image="coverImage"
        :karaoke-progress="karaokeProgress"
        :lyrics="lyrics"
        :name="name"
        :show-lyrics="showLyrics"
        @minimize="emit('minimize')"
        @toggle-lyrics="toggleLyrics"
      />
    </div>

    <!-- 底部控制条 -->
    <ControlsBar
      :cover-image="coverImage"
      :current-time="currentTime"
      :duration="duration"
      :is-playing="isPlaying"
      :name="name"
      :volume="volume"
      @minimize="emit('minimize')"
      @seek="emit('seek', $event)"
      @toggle-play="emit('toggle-play')"
      @volume-change="emit('volume-change', $event)"
    />
  </div>
</template>
