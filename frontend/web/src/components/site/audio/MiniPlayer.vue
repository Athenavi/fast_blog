<script lang="ts" setup>
const {t} = useI18n()
import {computed, onBeforeUnmount, ref, watch} from 'vue'

/**
 * 迷你播放器（播放器最小化后的形态）
 *
 * 对应 astro 版 `AudioPlayer/MiniPlayer.tsx`：
 * - 桌面（≥sm）：左下角卡片，含封面 / 歌名 / 进度条 / 播放暂停 / 关闭
 * - 移动端（<sm）：右上角黑胶圆片，**长按 500ms** 弹出菜单（展开播放器 / 关闭播放）
 *
 * 原实现里 `MiniPlayerWrapper` 又单独拉了一次音频封面（与 `AudioLayer`、
 * `PlayerView` 重复，3 次请求），这里封面由 `AudioLayer` 统一传入。
 */
const props = withDefaults(
  defineProps<{
    name?: string
    coverImage?: string | null
    isPlaying?: boolean
    currentTime?: number
    duration?: number
  }>(),
  {name: '', coverImage: null, isPlaying: false, currentTime: 0, duration: 0},
)

const emit = defineEmits<{
  (e: 'toggle-play'): void
  (e: 'restore'): void
  (e: 'close'): void
}>()

const showMenu = ref(false)
let pressTimer: ReturnType<typeof setTimeout> | undefined

const progressPercent = computed(() =>
  props.duration ? (props.currentTime / props.duration) * 100 : 0,
)

function closeMenu(): void {
  showMenu.value = false
}

function onTouchStart(): void {
  pressTimer = setTimeout(() => {
    showMenu.value = true
  }, 500)
}

function onTouchEnd(): void {
  if (pressTimer) clearTimeout(pressTimer)
}

/** 菜单打开时点空白处关闭 */
watch(showMenu, (open) => {
  if (open) window.addEventListener('click', closeMenu)
  else window.removeEventListener('click', closeMenu)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', closeMenu)
  if (pressTimer) clearTimeout(pressTimer)
})
</script>

<template>
  <div>
    <!-- 桌面：左下角迷你卡片 -->
    <div
      class="fixed bottom-4 left-4 z-[60] hidden overflow-hidden rounded-2xl border border-white/10 bg-black/90 shadow-2xl backdrop-blur-2xl sm:flex"
      style="padding-bottom: env(safe-area-inset-bottom, 0px)"
    >
      <div class="flex min-w-[260px] max-w-[320px] items-center gap-3 p-3">
        <button
          class="h-12 w-12 shrink-0 cursor-pointer overflow-hidden rounded-xl active:scale-90"
          :title="$t('audio.expandPlayerAria')"
          type="button"
          @click="emit('restore')"
        >
          <img v-if="coverImage" :alt="''" :src="coverImage" class="h-full w-full object-cover" decoding="async">
          <span v-else
                class="flex h-full w-full items-center justify-center bg-gradient-to-br from-purple-600 to-pink-600">
            <Icon class="h-6 w-6 text-white/70" name="music"/>
          </span>
        </button>

        <div class="min-w-0 flex-1">
          <button
            class="block w-full truncate text-left text-sm font-medium text-white"
            type="button"
            @click="emit('restore')"
          >{{ name }}
          </button>
          <div class="mt-1.5 h-0.5 w-full overflow-hidden rounded-full bg-white/10">
            <div
              :style="{width: `${progressPercent}%`}"
              class="h-full rounded-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-200"
            />
          </div>
        </div>

        <div class="flex items-center gap-1">
          <button
            :aria-label="isPlaying ? t('audio.pause') : t('audio.play')"
            class="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 transition-colors hover:bg-white/20 active:scale-90"
            type="button"
            @click="emit('toggle-play')"
          >
            <Icon :name="isPlaying ? 'pause' : 'play'" class="h-4 w-4 text-white"/>
          </button>
          <button
            :aria-label="$t('admin.common.close')"
            class="flex h-9 w-9 items-center justify-center rounded-full bg-white/5 transition-colors hover:bg-white/15 active:scale-90"
            type="button"
            @click="emit('close')"
          >
            <Icon class="h-4 w-4 text-white/60" name="x"/>
          </button>
        </div>
      </div>
    </div>

    <!-- 移动端：右上角黑胶 -->
    <div
      class="fixed right-4 top-4 z-[60] sm:hidden"
      @click="emit('toggle-play')"
      @touchend="onTouchEnd"
      @touchstart="onTouchStart"
    >
      <div
        :class="{ 'is-playing': isPlaying }"
        class="vinyl-mini-disc relative h-16 w-16 cursor-pointer overflow-hidden rounded-full border-2 border-white/20 shadow-2xl"
      >
        <img v-if="coverImage" :alt="''" :src="coverImage" class="h-full w-full object-cover" decoding="async">
        <span v-else
              class="flex h-full w-full items-center justify-center bg-gradient-to-br from-purple-600 to-pink-600">
          <Icon class="h-8 w-8 text-white/80" name="music"/>
        </span>
        <span class="absolute inset-x-0 bottom-0 flex h-5 items-center justify-center bg-black/50 px-1 backdrop-blur">
          <span class="truncate text-[9px] font-medium leading-none text-white">{{ name }}</span>
        </span>
      </div>
    </div>

    <!-- 移动端长按菜单 -->
    <div
      v-if="showMenu"
      class="fixed inset-0 z-[70] flex items-end justify-center bg-black/40 pb-20 sm:hidden"
      @click="closeMenu"
    >
      <div
        class="w-64 rounded-2xl border border-white/10 bg-neutral-900/95 p-4 shadow-2xl backdrop-blur-2xl"
        @click.stop
      >
        <p class="mb-4 truncate text-center font-semibold text-white">{{ name }}</p>
        <div class="space-y-2">
          <button
            class="flex w-full items-center gap-3 rounded-xl bg-white/10 px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-white/20"
            type="button"
            @click="closeMenu(); emit('restore')"
          >
            <Icon class="h-5 w-5" name="expand"/>
            {{ $t('audio.expandPlayerAria') }}
          </button>
          <button
            class="flex w-full items-center gap-3 rounded-xl bg-red-500/20 px-4 py-3 text-sm font-medium text-red-400 transition-colors hover:bg-red-500/30"
            type="button"
            @click="closeMenu(); emit('close')"
          >
            <Icon class="h-5 w-5" name="x"/>
            {{ $t('audio.closePlayer') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.vinyl-mini-disc.is-playing {
  animation: mini-spin 8s linear infinite;
}

@keyframes mini-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .vinyl-mini-disc.is-playing {
    animation: none;
  }
}
</style>
