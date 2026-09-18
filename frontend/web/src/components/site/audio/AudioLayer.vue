<script lang="ts" setup>
import {computed, onBeforeUnmount, onMounted, ref} from 'vue'

import {useAudioMetadata} from '@/composables/useAudioMetadata'

import {calcKaraokeProgress} from './helpers'

/**
 * 全屏音频播放器（持久音频层）
 *
 * 对应 astro 版 `AudioPlayer/AudioLayer.tsx`：本组件**始终持有同一个 `<audio>` 元素**
 * 与全部播放状态，全屏视图与迷你播放器只是它的两种呈现，因此最小化/展开不会
 * 中断播放（这也是原实现把 audio 放在条件分支之外的原因）。
 *
 * 与 astro 版的差异（行为等价、结构更干净）：
 *  - 原实现 `AudioLayer` / `PlayerView` / `MiniPlayerWrapper` **各请求了一次**
 *    `/api/v2/media/{id}/metadata`；这里统一由 `useAudioMetadata` 加载一次后下传。
 *  - 音量状态上提到本层，最小化再展开后音量不会丢。
 *  - Esc 切换最小化（与原来一致）。
 */
const props = defineProps<{
  /** 当前音轨（由 /media 列表映射而来） */
  track: { id: number; name: string; url: string }
}>()

const emit = defineEmits<{ (e: 'close'): void }>()

const audioEl = ref<HTMLAudioElement | null>(null)

const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(1)

/** 最小化 → 迷你播放器 */
const minimized = ref(false)
/** 桌面歌词默认关闭，由用户主动开启（与 astro 版一致，不读 localStorage 的 visible） */
const showDesktopLyrics = ref(false)

const {coverImage, lyrics, loading: loadingMetadata} = useAudioMetadata(
  computed(() => props.track.id),
)

/** 当前高亮行索引 */
const activeLineIndex = computed(() => {
  if (!lyrics.value.length) return -1
  return lyrics.value.findIndex((line, index) => {
    const next = lyrics.value[index + 1]
    return currentTime.value >= line.time && (!next || currentTime.value < next.time)
  })
})

/** 当前行的逐字高亮进度 */
const karaokeProgress = computed(() => {
  const index = activeLineIndex.value
  if (index < 0) return 0
  const line = lyrics.value[index]
  if (!line) return 0
  return calcKaraokeProgress(currentTime.value, line.time, lyrics.value[index + 1]?.time ?? null)
})

function togglePlay(): void {
  const audio = audioEl.value
  if (!audio) return
  if (isPlaying.value) audio.pause()
  else void audio.play().catch(() => {
    // 浏览器自动播放策略拦截时忽略（用户再点一次即可）
  })
}

function seek(time: number): void {
  const audio = audioEl.value
  if (audio) audio.currentTime = time
}

function changeVolume(value: number): void {
  volume.value = value
  const audio = audioEl.value
  if (audio) audio.volume = value
}

function onTimeUpdate(event: Event): void {
  currentTime.value = (event.target as HTMLAudioElement).currentTime
}

function onLoadedMetadata(event: Event): void {
  const value = (event.target as HTMLAudioElement).duration
  duration.value = Number.isFinite(value) ? value : 0
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') minimized.value = !minimized.value
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div>
    <!-- audio 固定在此处，不被任何条件分支卸载（保证切换视图不打断播放） -->
    <audio
      ref="audioEl"
      :src="props.track.url"
      preload="auto"
      @ended="isPlaying = false"
      @loadedmetadata="onLoadedMetadata"
      @pause="isPlaying = false"
      @play="isPlaying = true"
      @timeupdate="onTimeUpdate"
    />

    <template v-if="minimized">
      <!-- 桌面歌词开关（阻止冒泡，避免误触迷你播放器的播放/暂停） -->
      <button
        v-if="lyrics.length"
        :title="showDesktopLyrics ? '关闭桌面歌词' : '打开桌面歌词'"
        aria-label="桌面歌词"
        class="fixed bottom-24 right-4 z-[66] flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-black/60 backdrop-blur transition-colors hover:bg-white/10"
        type="button"
        @click.stop="showDesktopLyrics = !showDesktopLyrics"
        @pointerdown.stop
      >
        <Icon
          :class="showDesktopLyrics ? 'text-purple-500' : 'text-white/70'"
          class="h-4 w-4"
          name="mic-vocal"
        />
      </button>

      <DesktopLyrics
        :active-line-index="activeLineIndex"
        :karaoke-progress="karaokeProgress"
        :lyrics="lyrics"
        :visible="showDesktopLyrics"
        @visibility-change="showDesktopLyrics = $event"
      />

      <MiniPlayer
        :cover-image="coverImage"
        :current-time="currentTime"
        :duration="duration"
        :is-playing="isPlaying"
        :name="props.track.name"
        @close="emit('close')"
        @restore="minimized = false"
        @toggle-play="togglePlay"
      />
    </template>

    <div v-else class="fixed inset-0 z-50 flex flex-col bg-black">
      <PlayerView
        :active-line-index="activeLineIndex"
        :cover-image="coverImage"
        :current-time="currentTime"
        :duration="duration"
        :is-playing="isPlaying"
        :karaoke-progress="karaokeProgress"
        :loading-metadata="loadingMetadata"
        :lyrics="lyrics"
        :name="props.track.name"
        :volume="volume"
        @minimize="minimized = true"
        @seek="seek"
        @toggle-play="togglePlay"
        @volume-change="changeVolume"
      />
    </div>
  </div>
</template>
