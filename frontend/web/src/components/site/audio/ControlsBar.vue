<script lang="ts" setup>
import {computed, ref} from 'vue'

import {formatTime} from './helpers'

/**
 * 底部控制条：进度条 / 播放控制 / 音量 / 循环 / 收藏
 *
 * 对应 astro 版 `AudioPlayer/ControlsBar.tsx`。原实现用 framer-motion 的
 * `whileTap` 做按钮反馈，这里用 CSS `active:` 伪类（Tailwind `active:scale-*`）等价替代。
 *
 * 一处刻意不迁移：原实现有「播放列表」按钮（`showPlaylist`），但它**只切换状态、
 * 从不渲染任何面板**（死代码），保留一个点不动的按钮反而误导，故略去。
 */
const props = withDefaults(
  defineProps<{
    name?: string
    coverImage?: string | null
    currentTime?: number
    duration?: number
    volume?: number
    isPlaying?: boolean
  }>(),
  {name: '', coverImage: null, currentTime: 0, duration: 0, volume: 1, isPlaying: false},
)

const emit = defineEmits<{
  (e: 'seek', time: number): void
  (e: 'toggle-play'): void
  (e: 'volume-change', volume: number): void
  (e: 'minimize'): void
}>()

type RepeatMode = 'off' | 'one' | 'all'

const repeatMode = ref<RepeatMode>('off')
const isLiked = ref(false)
const showVolumeSlider = ref(false)

const progressPercent = computed(() =>
  props.duration ? (props.currentTime / props.duration) * 100 : 0,
)

const repeatLabel = computed(() =>
  repeatMode.value === 'off' ? '关闭' : repeatMode.value === 'all' ? '全部循环' : '单曲循环',
)

function onProgressInput(event: Event): void {
  emit('seek', Number((event.target as HTMLInputElement).value))
}

function onVolumeInput(event: Event): void {
  emit('volume-change', Number((event.target as HTMLInputElement).value))
}

function cycleRepeat(): void {
  repeatMode.value =
    repeatMode.value === 'off' ? 'all' : repeatMode.value === 'all' ? 'one' : 'off'
}

/** 快退/快进 10 秒（夹在 [0, duration] 内） */
function skip(delta: number): void {
  const next = props.currentTime + delta
  emit('seek', Math.max(0, props.duration ? Math.min(props.duration, next) : next))
}
</script>

<template>
  <div
    class="flex-shrink-0 border-t border-white/10 bg-black/90 backdrop-blur-2xl"
    style="padding-bottom: env(safe-area-inset-bottom, 0px)"
  >
    <!-- 进度条 -->
    <div class="px-4 pb-1 pt-3">
      <div class="relative -my-1 flex h-6 items-center">
        <input
          :max="duration || 100"
          :value="currentTime"
          aria-label="播放进度"
          class="absolute inset-0 z-10 h-full w-full cursor-pointer appearance-none bg-transparent opacity-0"
          min="0"
          style="touch-action: none"
          type="range"
          @input="onProgressInput"
        >
        <div class="pointer-events-none h-1 w-full overflow-hidden rounded-full bg-white/15">
          <div
            :style="{width: `${progressPercent}%`}"
            class="h-full rounded-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-75"
          />
        </div>
      </div>
      <div class="mt-0.5 flex justify-between px-0.5 text-[11px] text-white/30">
        <span>{{ formatTime(currentTime) }}</span>
        <span>{{ formatTime(duration) }}</span>
      </div>
    </div>

    <!-- 控制行 -->
    <div class="flex items-center justify-between gap-2 px-5 pb-3">
      <!-- 左：歌曲信息 -->
      <div class="flex min-w-0 flex-1 items-center gap-3">
        <button
          aria-label="最小化播放"
          class="h-10 w-10 shrink-0 cursor-pointer overflow-hidden rounded-lg shadow active:scale-90"
          title="最小化播放 (Esc)"
          type="button"
          @click="emit('minimize')"
        >
          <img v-if="coverImage" :alt="''" :src="coverImage" class="h-full w-full object-cover">
          <span v-else
                class="flex h-full w-full items-center justify-center bg-gradient-to-br from-purple-600 to-pink-600">
            <Icon class="h-5 w-5 text-white/70" name="music"/>
          </span>
        </button>

        <div class="max-w-[140px] min-w-0">
          <p class="truncate text-sm font-medium text-white">{{ name }}</p>
          <p class="truncate text-xs text-white/40">FastBlog</p>
        </div>

        <button
          :aria-pressed="isLiked"
          aria-label="收藏"
          class="shrink-0 active:scale-85"
          type="button"
          @click="isLiked = !isLiked"
        >
          <Icon :class="isLiked ? 'text-pink-500' : 'text-white/40'" class="h-5 w-5" name="heart"/>
        </button>
      </div>

      <!-- 中：播放控制 -->
      <div class="flex items-center justify-center gap-1 sm:gap-3">
        <button
          aria-label="后退10秒"
          class="hidden min-h-[44px] min-w-[44px] items-center justify-center p-2 text-white/50 transition-colors hover:text-white sm:flex"
          type="button"
          @click="skip(-10)"
        >
          <Icon class="h-5 w-5" name="rewind"/>
        </button>

        <button
          aria-label="重新播放"
          class="flex min-h-[44px] min-w-[44px] items-center justify-center p-2 text-white/50 transition-colors hover:text-white"
          type="button"
          @click="emit('seek', 0)"
        >
          <Icon class="h-5 w-5" name="skip-back"/>
        </button>

        <button
          :aria-label="isPlaying ? '暂停' : '播放'"
          class="mx-1 flex h-12 w-12 items-center justify-center rounded-full bg-white shadow-lg transition-all hover:shadow-xl active:scale-90 sm:h-11 sm:w-11"
          type="button"
          @click="emit('toggle-play')"
        >
          <Icon :name="isPlaying ? 'pause' : 'play'" class="h-5 w-5 text-black"/>
        </button>

        <button
          aria-label="前进10秒"
          class="flex min-h-[44px] min-w-[44px] items-center justify-center p-2 text-white/50 transition-colors hover:text-white"
          type="button"
          @click="skip(10)"
        >
          <Icon class="h-5 w-5" name="fast-forward"/>
        </button>

        <button
          aria-label="快进10秒"
          class="hidden min-h-[44px] min-w-[44px] items-center justify-center p-2 text-white/50 transition-colors hover:text-white sm:flex"
          type="button"
          @click="skip(10)"
        >
          <Icon class="h-5 w-5" name="fast-forward"/>
        </button>
      </div>

      <!-- 右：音量与附加 -->
      <div class="flex flex-1 items-center justify-end gap-1 sm:gap-3">
        <button
          :aria-label="`循环模式: ${repeatLabel}`"
          class="relative hidden min-h-[44px] min-w-[44px] p-2 sm:block"
          type="button"
          @click="cycleRepeat"
        >
          <Icon
            :class="repeatMode !== 'off' ? 'text-purple-500' : 'text-white/40'"
            class="mx-auto h-4 w-4"
            name="repeat"
          />
          <span
            v-if="repeatMode === 'one'"
            class="absolute right-0 top-0 flex h-3 w-3 items-center justify-center rounded-full bg-purple-500 text-[8px] font-bold text-white"
          >1</span>
        </button>

        <div class="relative hidden items-center sm:flex">
          <button
            aria-label="音量"
            class="flex min-h-[44px] min-w-[44px] items-center justify-center p-2"
            type="button"
            @click="showVolumeSlider = !showVolumeSlider"
          >
            <Icon class="h-4 w-4 text-white/40" name="volume-2"/>
          </button>
          <div
            v-if="showVolumeSlider"
            class="absolute bottom-full right-0 mb-2 rounded-xl border border-white/10 bg-neutral-900/95 p-3 shadow-xl backdrop-blur-xl"
          >
            <input
              :style="{
                background: `linear-gradient(to right, #a855f7 ${volume * 100}%, rgba(255,255,255,0.15) ${volume * 100}%)`,
              }"
              :value="volume"
              aria-label="音量滑块"
              class="h-1.5 w-24 cursor-pointer appearance-none rounded-full accent-purple-500"
              max="1"
              min="0"
              step="0.01"
              type="range"
              @input="onVolumeInput"
            >
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
