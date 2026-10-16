<script lang="ts" setup>
const {t} = useI18n()
import {computed, onBeforeUnmount, onMounted, reactive, ref, watch} from 'vue'

import {type LyricLine, tokenizeText} from './helpers'

/**
 * 桌面歌词浮层
 *
 * 对应 astro 版 `components/audio/DesktopLyrics.tsx`：页面右上角（可拖拽）的
 * 独立歌词窗，带渐变配色、字体、字号、不透明度、宽度与入场/出场动画设置，
 * 全部持久化到 localStorage（键 `fastblog_desktop_lyrics`，与原来一致）。
 *
 * 与 astro 版的两点实现差异（行为等价）：
 *  1. 原实现用 framer-motion 的 variants 做入场/出场，这里改用 Vue 的
 *     `<Transition>` + 按预设生成的 CSS keyframes，**不引入动画库**。
 *  2. 原实现的横向滚动（长行跟随当前高亮字平移）用 `transform` 平滑逼近，
 *     这里同样用 `requestAnimationFrame` 逼近，手感一致。
 */

type AnimPreset = 'fade-up' | 'fade-scale' | 'slide-left' | 'slide-right' | 'typewriter'

interface LyricsSettings {
  x: number
  y: number
  fontSize: number
  fontFamily: string
  opacity: number
  gradientId: string
  boxWidth: number
  entryAnim: AnimPreset
  exitAnim: AnimPreset
}

const GRADIENTS: Array<{
  id: string
  label: string
  from: string
  via: string
  to: string
  shadow: string
}> = [
  {
    id: 'purple-pink',
    label: t('audio.schemePurplePink'),
    from: '#a855f7',
    via: '#d946ef',
    to: '#ec4899',
    shadow: 'rgba(168,85,247,0.5)'
  },
  {
    id: 'cyan-blue',
    label: t('audio.schemeCyanBlue'),
    from: '#06b6d4',
    via: '#3b82f6',
    to: '#6366f1',
    shadow: 'rgba(59,130,246,0.5)'
  },
  {
    id: 'green-emerald',
    label: t('audio.schemeEmerald'),
    from: '#34d399',
    via: '#10b981',
    to: '#059669',
    shadow: 'rgba(16,185,129,0.5)'
  },
  {
    id: 'orange-rose',
    label: t('audio.schemeWarmOrange'),
    from: '#fb923c',
    via: '#f43f5e',
    to: '#e11d48',
    shadow: 'rgba(244,63,94,0.5)'
  },
  {
    id: 'white-glow',
    label: t('audio.schemeWhiteGlow'),
    from: '#ffffff',
    via: '#e2e8f0',
    to: '#94a3b8',
    shadow: 'rgba(255,255,255,0.4)'
  },
  {
    id: 'gold-amber',
    label: t('audio.schemeGold'),
    from: '#fbbf24',
    via: '#f59e0b',
    to: '#d97706',
    shadow: 'rgba(245,158,11,0.5)'
  },
]

const FONTS: Array<{ value: string; label: string }> = [
  {value: 'system-ui, sans-serif', label: t('audio.fontSystem')},
  {value: '"PingFang SC", "Microsoft YaHei", sans-serif', label: t('audio.fontYahei')},
  {value: '"Noto Sans SC", sans-serif', label: 'Noto'},
  {value: '"Songti SC", "SimSun", serif', label: t('audio.fontSong')},
  {value: '"STKaiti", "KaiTi", serif', label: t('audio.fontKai')},
  {value: 'monospace', label: t('audio.fontMono')},
]

const ANIM_PRESETS: Array<{ value: AnimPreset; label: string; desc: string }> = [
  {value: 'fade-up', label: t('audio.animFadeUp'), desc: 'opacity 0→1 + y 20→0'},
  {value: 'fade-scale', label: t('audio.animFadeScale'), desc: 'opacity 0→1 + scale 0.8→1'},
  {value: 'slide-left', label: t('audio.animSlideRight'), desc: 'x 40→0 + opacity'},
  {value: 'slide-right', label: t('audio.animSlideLeft'), desc: 'x -40→0 + opacity'},
  {value: 'typewriter', label: t('audio.animTypewriter'), desc: t('audio.animClipPath')},
]

const LS_KEY = 'fastblog_desktop_lyrics'

const DEFAULT_SETTINGS: LyricsSettings = {
  x: 50,
  y: 50,
  fontSize: 18,
  fontFamily: 'system-ui, sans-serif',
  opacity: 90,
  gradientId: 'purple-pink',
  boxWidth: 520,
  entryAnim: 'fade-up',
  exitAnim: 'fade-scale',
}

const props = withDefaults(
  defineProps<{
    lyrics?: LyricLine[]
    activeLineIndex?: number
    karaokeProgress?: number
    visible?: boolean
  }>(),
  {lyrics: () => [], activeLineIndex: -1, karaokeProgress: 0, visible: false},
)

const emit = defineEmits<{ (e: 'visibility-change', visible: boolean): void }>()

function loadSettings(): LyricsSettings {
  try {
    const raw = localStorage.getItem(LS_KEY)
    return raw ? {...DEFAULT_SETTINGS, ...(JSON.parse(raw) as Partial<LyricsSettings>)} : {...DEFAULT_SETTINGS}
  } catch {
    return {...DEFAULT_SETTINGS}
  }
}

const settings = reactive<LyricsSettings>(loadSettings())
const showSettings = ref(false)

/** 设置变更即持久化（与 astro 版一致） */
watch(
  () => ({...settings}),
  (value) => {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(value))
    } catch {
      // 隐私模式下忽略
    }
  },
  {deep: true},
)

const gradient = computed(
  () => GRADIENTS.find((item) => item.id === settings.gradientId) ?? GRADIENTS[0]!,
)

const currentLyric = computed<LyricLine | null>(
  () => props.lyrics[props.activeLineIndex] ?? null,
)

const tokens = computed(() => (currentLyric.value ? tokenizeText(currentLyric.value.text) : []))

const highlightCount = computed(() =>
  Math.floor(tokens.value.length * props.karaokeProgress),
)

/* ---------------------------------------------------------------- 横向滚动 */

const textRef = ref<HTMLElement | null>(null)
const scrollOffset = ref(0)
let rafId = 0

function tickScroll(): void {
  const textEl = textRef.value
  if (!textEl) {
    scrollOffset.value = 0
    return
  }

  const containerWidth = settings.boxWidth
  const textWidth = textEl.scrollWidth

  if (textWidth <= containerWidth || highlightCount.value <= 0) {
    scrollOffset.value *= 0.85
    if (Math.abs(scrollOffset.value) < 0.5) scrollOffset.value = 0
    return
  }

  const avgTokenWidth = textWidth / Math.max(tokens.value.length, 1)
  const highlightCenter = highlightCount.value * avgTokenWidth
  const maxOffset = Math.max(0, textWidth - containerWidth)
  const target = Math.min(Math.max(0, highlightCenter - containerWidth / 2), maxOffset)

  // 平滑逼近（原实现同样用 0.15 的插值系数）
  scrollOffset.value += (target - scrollOffset.value) * 0.15
}

function loop(): void {
  if (!props.visible) return
  tickScroll()
  rafId = window.requestAnimationFrame(loop)
}

watch(
  () => props.visible,
  (visible) => {
    window.cancelAnimationFrame(rafId)
    if (visible) {
      scrollOffset.value = 0
      rafId = window.requestAnimationFrame(loop)
    }
  },
  {immediate: true},
)

/* ---------------------------------------------------------------- 拖拽 */

const dragging = ref(false)
let drag: { startX: number; startY: number; origX: number; origY: number; moved: boolean } | null = null

function onPointerDown(event: PointerEvent): void {
  if (showSettings.value) return
  drag = {
    startX: event.clientX,
    startY: event.clientY,
    origX: settings.x,
    origY: settings.y,
    moved: false,
  }
  ;(event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId)
}

function onPointerMove(event: PointerEvent): void {
  if (!drag) return
  const dx = event.clientX - drag.startX
  const dy = event.clientY - drag.startY
  if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
    drag.moved = true
    dragging.value = true
  }
  if (!drag.moved) return
  settings.x = Math.max(0, Math.min(95, drag.origX + (dx / window.innerWidth) * 100))
  settings.y = Math.max(0, Math.min(90, drag.origY + (dy / window.innerHeight) * 100))
}

function onPointerUp(): void {
  drag = null
  dragging.value = false
}

/* ---------------------------------------------------------------- 交互 */

function stopEvent(event: Event): void {
  event.stopPropagation()
}

function resetPosition(): void {
  settings.x = DEFAULT_SETTINGS.x
  settings.y = DEFAULT_SETTINGS.y
}

function resetAll(): void {
  Object.assign(settings, DEFAULT_SETTINGS)
  showSettings.value = false
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Escape' || !props.visible) return
  event.stopPropagation()
  if (showSettings.value) showSettings.value = false
  else emit('visibility-change', false)
}

/** 当前行的入场/出场动画名（对应 astro 版的 entry/exit variants） */
const transitionName = computed(() => `lyric-${settings.entryAnim}`)

onMounted(() => window.addEventListener('keydown', onKeydown, true))

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown, true)
  window.cancelAnimationFrame(rafId)
})
</script>

<template>
  <div v-if="visible" class="pointer-events-none fixed inset-0 z-[80]">
    <!-- 歌词条 -->
    <div
      :style="{
        left: `${settings.x}%`,
        top: `${settings.y}%`,
        width: `${settings.boxWidth}px`,
        transform: 'translate(-50%, -50%)',
        opacity: settings.opacity / 100,
        padding: '14px 18px',
      }"
      class="pointer-events-auto absolute cursor-move select-none rounded-2xl border border-white/10 bg-black/70 shadow-2xl backdrop-blur-xl"
      @pointercancel="onPointerUp"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
    >
      <!-- 工具条：拖拽时显示，避免遮挡 -->
      <div
        v-if="!dragging"
        class="mb-2 flex items-center justify-between gap-2 text-[11px] text-white/40"
      >
        <span>{{ $t('audio.desktopLyrics') }}</span>
        <div class="flex items-center gap-1">
          <button class="rounded px-1.5 py-0.5 hover:bg-white/10 hover:text-white/80" type="button"
                  @click.stop="showSettings = !showSettings">
            {{ $t('audio.settings') }}
          </button>
          <button class="rounded px-1.5 py-0.5 hover:bg-white/10 hover:text-white/80" type="button"
                  @click.stop="emit('visibility-change', false)">
            {{ $t('common.close') }}
          </button>
        </div>
      </div>

      <!-- 歌词正文 -->
      <Transition :name="transitionName" mode="out-in">
        <div
          v-if="currentLyric"
          :key="props.activeLineIndex"
          :style="{
            fontFamily: settings.fontFamily,
            fontSize: `${settings.fontSize}px`,
            lineHeight: 1.5,
          }"
          class="overflow-hidden whitespace-nowrap text-center font-bold"
        >
          <div
            ref="textRef"
            :style="{
              transform: `translateX(${-scrollOffset}px)`,
              transition: dragging ? 'none' : 'transform 120ms linear',
            }"
            class="inline-block"
          >
            <span
              v-for="(token, index) in tokens"
              :key="index"
              :style="
                index < highlightCount
                  ? {
                      backgroundImage: `linear-gradient(to right, ${gradient.from}, ${gradient.via}, ${gradient.to})`,
                      WebkitBackgroundClip: 'text',
                      backgroundClip: 'text',
                      color: 'transparent',
                      filter: `drop-shadow(0 0 10px ${gradient.shadow})`,
                    }
                  : {color: 'rgba(255,255,255,0.5)'}
              "
            >{{ token === ' ' ? ' ' : token }}</span>
          </div>
        </div>

        <div v-else class="py-3 text-center text-sm text-white/40">{{ $t('audio.noLyrics') }}</div>
      </Transition>

      <!-- 设置面板 -->
      <div
        v-if="showSettings"
        class="mt-3 space-y-3 border-t border-white/10 pt-3 text-[11px] text-white/60"
        @pointerdown.stop
      >
        <div>
          <p class="mb-1.5">{{ $t('audio.schemeLabel') }}</p>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="item in GRADIENTS"
              :key="item.id"
              :class="item.id === settings.gradientId ? 'ring-2 ring-white/60' : 'ring-1 ring-white/15'"
              :style="{backgroundImage: `linear-gradient(to right, ${item.from}, ${item.via}, ${item.to})`}"
              :title="item.label"
              class="h-6 w-6 rounded-full"
              type="button"
              @click="settings.gradientId = item.id"
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-2">
          <label class="flex flex-col gap-1">
            {{ $t('audio.fontSize', {size: settings.fontSize}) }}
            <input v-model.number="settings.fontSize" class="w-full" max="48" min="12" step="1" type="range">
          </label>
          <label class="flex flex-col gap-1">
            {{ $t('audio.opacityLabel', {n: settings.opacity}) }}
            <input v-model.number="settings.opacity" class="w-full" max="100" min="20" step="1" type="range">
          </label>
          <label class="flex flex-col gap-1">
            {{ $t('audio.boxWidth', {n: settings.boxWidth}) }}
            <input v-model.number="settings.boxWidth" class="w-full" max="1200" min="280" step="20" type="range">
          </label>
          <label class="flex flex-col gap-1">
            {{ $t('audio.fontLabel') }}
            <select v-model="settings.fontFamily" class="w-full rounded bg-white/10 px-1 py-0.5">
              <option v-for="font in FONTS" :key="font.value" :value="font.value">{{ font.label }}</option>
            </select>
          </label>
          <label class="flex flex-col gap-1">
            {{ $t('audio.enterAnim') }}
            <select v-model="settings.entryAnim" class="w-full rounded bg-white/10 px-1 py-0.5">
              <option v-for="preset in ANIM_PRESETS" :key="preset.value" :value="preset.value">{{
                  preset.label
                }}
              </option>
            </select>
          </label>
          <label class="flex flex-col gap-1">
            {{ $t('audio.exitAnim') }}
            <select v-model="settings.exitAnim" class="w-full rounded bg-white/10 px-1 py-0.5">
              <option v-for="preset in ANIM_PRESETS" :key="preset.value" :value="preset.value">{{
                  preset.label
                }}
              </option>
            </select>
          </label>
        </div>

        <div class="flex justify-end gap-2 pt-1">
          <button class="rounded border border-white/15 px-2 py-1 hover:bg-white/10" type="button"
                  @click="resetPosition">{{ $t('audio.resetPosition') }}
          </button>
          <button class="rounded border border-white/15 px-2 py-1 hover:bg-white/10" type="button" @click="resetAll">
            {{ $t('audio.resetDefaults') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 入场动画（对应 astro 版 entryVariants 的 5 种预设） */
.lyric-fade-up-enter-from {
  opacity: 0;
  transform: translateY(20px);
  filter: blur(4px);
}

.lyric-fade-scale-enter-from {
  opacity: 0;
  transform: scale(0.8);
  filter: blur(3px);
}

.lyric-slide-left-enter-from {
  opacity: 0;
  transform: translateX(40px);
}

.lyric-slide-right-enter-from {
  opacity: 0;
  transform: translateX(-40px);
}

.lyric-typewriter-enter-from {
  opacity: 0;
  clip-path: inset(0 100% 0 0);
}

.lyric-fade-up-enter-active,
.lyric-fade-scale-enter-active,
.lyric-slide-left-enter-active,
.lyric-slide-right-enter-active,
.lyric-typewriter-enter-active {
  transition: all 320ms ease;
}

/* 出场统一为轻微淡出，避免不同预设交错时抖动 */
.lyric-fade-up-leave-to,
.lyric-fade-scale-leave-to,
.lyric-slide-left-leave-to,
.lyric-slide-right-leave-to,
.lyric-typewriter-leave-to {
  opacity: 0;
}

.lyric-fade-up-leave-active,
.lyric-fade-scale-leave-active,
.lyric-slide-left-leave-active,
.lyric-slide-right-leave-active,
.lyric-typewriter-leave-active {
  transition: opacity 200ms ease;
}

@media (prefers-reduced-motion: reduce) {
  [class*='lyric-'][class*='-enter-active'],
  [class*='lyric-'][class*='-leave-active'] {
    transition: none;
  }
}
</style>
