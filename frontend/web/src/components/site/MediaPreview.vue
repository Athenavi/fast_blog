<script lang="ts" setup>
const {t} = useI18n()
/**
 * 媒体预览器
 *
 * 对应原 astro 的 `pages/media/MediaPreview.tsx`：全屏预览图片 / 视频 / 音频 / PDF / 其它文件，
 * 支持左右切换与键盘操作。
 *
 * 与 astro 版的差异：那边用 `iframe` 内嵌 PDF、`fslightbox` 之类的外部组件；
 * 这里全部用浏览器原生标签（`<img>`/`<video>`/`<audio>`/`<iframe>`），**零额外依赖**。
 */
import {onKeyStroke} from '@vueuse/core'

import type {MediaPreviewItem} from '@/types/media'
import {cn} from '@/lib/utils'
import {formatDateTime, formatFileSize} from '@/utils/format'

const props = withDefaults(
  defineProps<{
    items: MediaPreviewItem[]
    /** 当前项下标；用 v-model 双向绑定 */
    modelValue: number
    open?: boolean
  }>(),
  {open: false},
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void
  (e: 'close'): void
}>()

const current = computed(() => props.items[props.modelValue])

/** 按 MIME 判断用哪种查看器 */
const kind = computed(() => {
  const mime = current.value?.mimeType || ''
  if (mime.startsWith('image/')) return 'image'
  if (mime.startsWith('video/')) return 'video'
  if (mime.startsWith('audio/')) return 'audio'
  if (mime === 'application/pdf') return 'pdf'
  if (mime.startsWith('text/')) return 'text'
  return 'other'
})

const canPrev = computed(() => props.modelValue > 0)
const canNext = computed(() => props.modelValue < props.items.length - 1)

function go(delta: number): void {
  const next = props.modelValue + delta
  if (next < 0 || next >= props.items.length) return
  emit('update:modelValue', next)
}

function close(): void {
  emit('close')
}

onKeyStroke('Escape', () => {
  if (props.open) close()
})
onKeyStroke('ArrowLeft', () => {
  if (props.open) go(-1)
})
onKeyStroke('ArrowRight', () => {
  if (props.open) go(1)
})
</script>

<template>
  <div
    v-if="props.open && current"
    aria-modal="true"
    class="fixed inset-0 z-[60] flex flex-col bg-canvas/98 backdrop-blur-sm"
    role="dialog"
  >
    <!-- 顶栏 -->
    <header class="flex items-center gap-3 border-b border-line px-4 py-3">
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-medium text-fg">{{ current.name || t('media.unnamed') }}</p>
        <p class="mt-0.5 text-xs text-fg-subtle">
          <span v-if="current.size">{{ formatFileSize(current.size) }}</span>
          <span v-if="current.createdAt"> · {{ formatDateTime(current.createdAt) }}</span>
          <span> · {{ props.modelValue + 1 }} / {{ props.items.length }}</span>
        </p>
      </div>

      <a
        v-if="current.url"
        :href="current.url"
        class="inline-flex h-9 items-center gap-1.5 rounded-control px-3 text-sm text-fg-muted transition-colors hover:bg-surface-soft hover:text-fg"
        download
      >
        <Icon class="h-4 w-4" name="download"/>
        {{ $t('common.download') }}
      </a>
      <button
        :aria-label="$t('media.closePreviewAria')"
        class="inline-flex h-9 w-9 items-center justify-center rounded-control text-fg-muted transition-colors hover:bg-surface-soft hover:text-fg"
        type="button"
        @click="close"
      >
        <Icon class="h-4 w-4" name="x"/>
      </button>
    </header>

    <!-- 主体 -->
    <div class="relative flex flex-1 items-center justify-center overflow-hidden p-4">
      <button
        v-if="canPrev"
        :aria-label="$t('media.prevAria')"
        class="absolute left-3 z-10 inline-flex h-10 w-10 items-center justify-center rounded-pill border border-line bg-surface text-fg-muted transition-colors hover:text-fg"
        type="button"
        @click="go(-1)"
      >
        <Icon class="h-5 w-5" name="chevron-left"/>
      </button>

      <img
        v-if="kind === 'image' && current.url"
        :alt="current.name || ''"
        :src="current.url"
        class="max-h-full max-w-full rounded-card object-contain"
      >
      <video
        v-else-if="kind === 'video' && current.url"
        :src="current.url"
        class="max-h-full max-w-full rounded-card"
        controls
      />
      <audio
        v-else-if="kind === 'audio' && current.url"
        :src="current.url"
        class="w-full max-w-lg"
        controls
      />
      <iframe
        v-else-if="kind === 'pdf' && current.url"
        :src="current.url"
        class="h-full w-full max-w-4xl rounded-card border border-line bg-surface"
        :title="$t('media.pdfPreviewTitle')"
      />
      <div v-else class="flex flex-col items-center gap-3 text-center">
        <Icon class="h-10 w-10 text-fg-subtle" name="file-text"/>
        <p class="text-sm text-fg-muted">{{ $t('media.unsupportedPreview') }}</p>
        <a v-if="current.url" :href="current.url" download>
          <Button variant="outline">
            <Icon class="h-4 w-4" name="download"/>
            {{ $t('media.downloadFile') }}
          </Button>
        </a>
      </div>

      <button
        v-if="canNext"
        :aria-label="$t('media.nextAria')"
        class="absolute right-3 z-10 inline-flex h-10 w-10 items-center justify-center rounded-pill border border-line bg-surface text-fg-muted transition-colors hover:text-fg"
        type="button"
        @click="go(1)"
      >
        <Icon class="h-5 w-5" name="chevron-right"/>
      </button>
    </div>

    <!-- 缩略图条 -->
    <footer v-if="props.items.length > 1" class="border-t border-line px-4 py-3">
      <div class="flex gap-2 overflow-x-auto">
        <button
          v-for="(item, index) in props.items"
          :key="item.id"
          :class="cn(index === props.modelValue ? 'border-primary' : 'border-line hover:border-line-strong')"
          class="h-12 w-16 flex-shrink-0 overflow-hidden rounded border transition-colors"
          type="button"
          @click="emit('update:modelValue', index)"
        >
          <img
            v-if="(item.mimeType || '').startsWith('image/') && item.url"
            :alt="item.name || ''"
            :src="item.url"
            class="h-full w-full object-cover"
          >
          <span v-else class="flex h-full w-full items-center justify-center bg-surface-soft">
            <Icon class="h-4 w-4 text-fg-subtle" name="file-text"/>
          </span>
        </button>
      </div>
    </footer>
  </div>
</template>
