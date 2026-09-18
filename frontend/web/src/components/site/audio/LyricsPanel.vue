<script lang="ts" setup>
const {t} = useI18n()
import {ref, watch} from 'vue'

import {type LyricLine, tokenizeText} from './helpers'

/**
 * 歌词面板（逐字卡拉 OK 高亮）
 *
 * 对应 astro 版 `AudioPlayer/LyricsPanel.tsx`：
 * - 当前行自动滚动到视口中央
 * - 当前行放大加粗，已唱过的行变淡
 * - 逐字高亮：已唱完的 token 用渐变文字，正在唱的 token 用 `clip-path` 做过渡
 * - 下一个 token 呼吸脉冲提示
 *
 * 原实现用 framer-motion 做进度条宽度与脉冲；这里改成 CSS 过渡 + keyframes。
 */
const props = withDefaults(
  defineProps<{
    name?: string
    coverImage?: string | null
    lyrics?: LyricLine[]
    showLyrics?: boolean
    activeLineIndex?: number
    karaokeProgress?: number
  }>(),
  {
    name: '',
    coverImage: null,
    lyrics: () => [],
    showLyrics: false,
    activeLineIndex: -1,
    karaokeProgress: 0,
  },
)

const emit = defineEmits<{
  (e: 'toggle-lyrics'): void
  (e: 'minimize'): void
}>()

const containerRef = ref<HTMLElement | null>(null)

/** 当前行滚到视口中央（顺滑） */
watch(
  () => props.activeLineIndex,
  (index) => {
    if (!props.showLyrics || index < 0) return
    const container = containerRef.value
    if (!container) return
    const line = container.children[index] as HTMLElement | undefined
    if (!line) return
    container.scrollTo({
      top: line.offsetTop - container.clientHeight / 2 + line.clientHeight / 2,
      behavior: 'smooth',
    })
  },
)

/** 每行已高亮的 token 数 */
function highlightCount(index: number, tokenCount: number): number {
  if (index < props.activeLineIndex) return tokenCount
  if (index > props.activeLineIndex) return 0
  return Math.floor(tokenCount * props.karaokeProgress)
}
</script>

<template>
  <div class="relative flex min-h-0 flex-1 flex-col">
    <!-- 移动端：顶部封面 + 歌名 -->
    <div class="flex items-center gap-4 border-b border-white/10 p-5 lg:hidden">
      <button
        :aria-label="$t('audio.minimize')"
        class="shrink-0 active:scale-90"
        type="button"
        @click="emit('minimize')"
      >
        <Icon class="h-5 w-5 text-white/50" name="chevron-down"/>
      </button>

      <div class="h-14 w-14 shrink-0 overflow-hidden rounded-xl shadow-lg">
        <img v-if="coverImage" :alt="t('audio.cover')" :src="coverImage" class="h-full w-full object-cover">
        <span v-else
              class="flex h-full w-full items-center justify-center bg-gradient-to-br from-purple-600 to-pink-600">
          <Icon class="h-6 w-6 text-white/80" name="music"/>
        </span>
      </div>

      <div class="min-w-0 flex-1">
        <p class="truncate text-base font-semibold text-white">{{ name }}</p>
        <p class="truncate text-xs text-white/50">FastBlog Audio</p>
      </div>
    </div>

    <!-- 歌词标题 -->
    <div class="flex items-center justify-between px-6 pb-2 pt-5">
      <button
        :class="showLyrics ? 'text-purple-500' : 'text-white/40'"
        class="flex items-center gap-2 text-sm font-medium transition-colors"
        type="button"
        @click="emit('toggle-lyrics')"
      >
        <Icon class="h-4 w-4" name="mic-vocal"/>
        {{ $t('audio.lyricsToggle') }}
      </button>
      <span v-if="showLyrics && lyrics.length"
            class="text-xs text-white/30">{{ $t('audio.linesCount', {n: lyrics.length}) }}</span>
    </div>

    <!-- 歌词内容 -->
    <div class="flex-1 overflow-hidden px-4">
      <div
        v-if="showLyrics"
        ref="containerRef"
        class="h-full space-y-3 overflow-y-auto py-2"
        style="scrollbar-width: thin"
      >
        <template v-if="lyrics.length">
          <div
            v-for="(line, index) in lyrics"
            :key="index"
            :style="{
              opacity: index < activeLineIndex ? 0.5 : index === activeLineIndex ? 1 : 0.35,
              transform: index === activeLineIndex ? 'scale(1)' : 'scale(0.96)',
            }"
            class="relative min-h-[2.5rem] px-4 py-2 transition-all duration-300"
          >
            <!-- 背景进度条（仅当前行） -->
            <div
              v-if="index === activeLineIndex"
              :style="{width: `${karaokeProgress * 100}%`, transition: 'width 80ms linear'}"
              class="pointer-events-none absolute inset-0 rounded-xl bg-gradient-to-r from-purple-500/8 via-pink-500/8 to-transparent"
            />

            <div
              :class="index === activeLineIndex ? 'text-xl font-bold tracking-wide' : 'text-sm'"
              class="text-center leading-relaxed"
            >
              <template
                v-for="(token, ti) in tokenizeText(line.text)"
                :key="ti"
              >
                <span v-if="token === ' '" class="inline-block" style="width: 0.3em">&nbsp;</span>

                <span v-else class="relative mx-[0.5px] inline-block">
                  <!-- 未高亮层 -->
                  <span
                    :class="ti < highlightCount(index, tokenizeText(line.text).length) ? 'text-transparent' : 'text-white/50'"
                    class="transition-all duration-150"
                  >{{ token }}</span>

                  <!-- 高亮渐变层 -->
                  <span
                    v-if="ti < highlightCount(index, tokenizeText(line.text).length)"
                    :style="{
                      filter: index === activeLineIndex ? 'drop-shadow(0 0 10px rgba(168,85,247,0.5))' : 'none',
                    }"
                    class="absolute inset-0 bg-gradient-to-r from-purple-400 via-fuchsia-300 to-pink-300 bg-clip-text text-transparent"
                  >{{ token }}</span>

                  <!-- 正在唱的 token：clip-path 过渡 -->
                  <span
                    v-if="
                      index === activeLineIndex &&
                      ti === highlightCount(index, tokenizeText(line.text).length) - 1 &&
                      karaokeProgress < 1
                    "
                    class="absolute inset-0 overflow-hidden"
                    style="color: transparent"
                  >
                    <span
                      :style="{
                        clipPath: `inset(0 ${(1 - (karaokeProgress * tokenizeText(line.text).length - ti)) * 100}% 0 0)`,
                        filter: 'drop-shadow(0 0 12px rgba(168,85,247,0.7))',
                      }"
                      class="absolute inset-0 bg-gradient-to-r from-purple-400 via-fuchsia-300 to-pink-300 bg-clip-text text-transparent"
                    >{{ token }}</span>
                  </span>

                  <!-- 下一个 token：呼吸脉冲 -->
                  <span
                    v-if="index === activeLineIndex && ti === highlightCount(index, tokenizeText(line.text).length)"
                    class="lyric-next-pulse absolute inset-0 text-white/50"
                  >{{ token }}</span>
                </span>
              </template>
            </div>
          </div>
        </template>

        <div v-else class="flex h-full flex-col items-center justify-center text-white/30">
          <Icon class="mb-4 h-12 w-12 opacity-40" name="music"/>
          <p class="text-sm">{{ $t('audio.noLyrics') }}</p>
          <p class="mt-1 text-xs">{{ $t('audio.lyricsHint') }}</p>
        </div>
      </div>

      <div v-else class="flex h-full flex-col items-center justify-center text-white/20">
        <Icon class="mb-4 h-16 w-16 opacity-30" name="mic-vocal"/>
        <p class="text-sm">{{ $t('audio.lyricsPanelHint') }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.lyric-next-pulse {
  animation: lyric-pulse 1.2s ease-in-out infinite;
}

@keyframes lyric-pulse {
  0%,
  100% {
    opacity: 0.3;
  }

  50% {
    opacity: 0.7;
  }
}

@media (prefers-reduced-motion: reduce) {
  .lyric-next-pulse {
    animation: none;
  }
}
</style>
