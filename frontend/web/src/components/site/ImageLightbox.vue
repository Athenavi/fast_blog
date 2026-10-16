<script lang="ts" setup>
/**
 * 正文图片查看器（灯箱）
 *
 * 此前正文里的图片点不动：想看大图只能另存或放大页面。这里给文章内的图片提供
 * 全屏查看，并支持左右切换（键盘 ←/→、Esc 关闭）。
 *
 * 与媒体库的 `MediaPreview` 的区别：那个面向"媒体条目"（含视频/音频/PDF），
 * 这个只服务正文插图，接受的是纯 URL 列表。
 */
import {computed, onBeforeUnmount, ref, watch} from 'vue'

const props = defineProps<{
  images: string[]
  /** 当前查看的下标；`null` 表示关闭 */
  index: number | null
}>()

const emit = defineEmits<{
  (e: 'update:index', value: number | null): void
}>()

const {t} = useI18n()

const open = computed(() => props.index !== null && props.images.length > 0)
const current = computed(() => (props.index === null ? '' : (props.images[props.index] ?? '')))
const hasMultiple = computed(() => props.images.length > 1)

function close(): void {
  emit('update:index', null)
}

function step(delta: number): void {
  if (props.index === null || !props.images.length) return
  const next = (props.index + delta + props.images.length) % props.images.length
  emit('update:index', next)
}

function onKeydown(event: KeyboardEvent): void {
  if (!open.value) return
  if (event.key === 'Escape') close()
  else if (event.key === 'ArrowRight') step(1)
  else if (event.key === 'ArrowLeft') step(-1)
}

watch(open, (value) => {
  if (!import.meta.client) return
  if (value) window.addEventListener('keydown', onKeydown)
  else window.removeEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  if (import.meta.client) window.removeEventListener('keydown', onKeydown)
})

const failed = ref(false)
watch(current, () => {
  failed.value = false
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      :aria-label="t('article.imageViewer')"
      aria-modal="true"
      class="fixed inset-0 z-[75] flex flex-col items-center justify-center bg-black/85 p-4"
      role="dialog"
      @click.self="close"
    >
      <img
        v-if="!failed"
        :alt="t('article.imageViewer')"
        :src="current"
        class="max-h-[86vh] max-w-[94vw] object-contain"
        decoding="async"
        @error="failed = true"
      >
      <p v-else class="text-sm text-white/80">{{ t('common.networkError') }}</p>

      <button
        :aria-label="t('common.close')"
        class="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-pill bg-white/10 text-white transition-colors hover:bg-white/20"
        type="button"
        @click="close"
      >
        <Icon class="h-4 w-4" name="x"/>
      </button>

      <template v-if="hasMultiple">
        <button
          :aria-label="t('article.prevImage')"
          class="absolute left-2 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-pill bg-white/10 text-white transition-colors hover:bg-white/20 sm:left-6"
          type="button"
          @click.stop="step(-1)"
        >
          <Icon class="h-5 w-5" name="chevron-left"/>
        </button>
        <button
          :aria-label="t('article.nextImage')"
          class="absolute right-2 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-pill bg-white/10 text-white transition-colors hover:bg-white/20 sm:right-6"
          type="button"
          @click.stop="step(1)"
        >
          <Icon class="h-5 w-5" name="chevron-right"/>
        </button>
        <p class="mt-3 text-xs text-white/70">{{ (props.index ?? 0) + 1 }} / {{ props.images.length }}</p>
      </template>
    </div>
  </Teleport>
</template>
