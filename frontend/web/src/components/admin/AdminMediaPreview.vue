<script lang="ts" setup>
import {computed, onBeforeUnmount, onMounted, ref, watch} from 'vue'

import type {MediaItem} from '@/api'
import type {IconName} from '@/lib/icons'
import {ElMessage} from '@/utils/feedback'
import {formatDateTime, formatFileSize} from '@/utils/format'

/**
 * 后台媒体预览（全类型）
 *
 * 对应原 astro 的 `pages/admin/media/AdminMediaPreview.tsx`。原实现依赖
 * `fslightbox-react`（图片画廊）与 `@flyfish-group/file-viewer-react`（其它类型），
 * 这里按 Nuxt 原生方式重写，**不新增任何依赖**：
 *
 *   - image/*       → 原生 `<img>` 全屏 + 底部缩略图导航
 *   - video/* audio/* → 原生 `<video>` / `<audio>`（带 controls）
 *   - application/pdf → 原生 `<iframe>`
 *   - text/*、json   → `$fetch` 取文本后 `<pre>` 展示（>512KB 不拉取）
 *   - 其余           → 下载入口
 *
 * 与前台 `MediaPreview` 的区别：这是后台语境下的版本，额外提供类型图标、
 * 文件元信息（mime / 大小 / 上传时间）、复制链接与「编辑」入口。
 */
const props = withDefaults(
  defineProps<{
    open?: boolean
    /** 当前列表（用于左右切换与缩略图导航） */
    files?: MediaItem[]
    /** 当前项 id；切换由父组件回写 */
    activeId?: number | null
  }>(),
  {open: false, files: () => [], activeId: null},
)

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'navigate', file: MediaItem): void
  (e: 'edit', file: MediaItem): void
}>()

const KIND_ICONS: Record<string, IconName> = {
  image: 'image',
  video: 'video',
  audio: 'music',
  pdf: 'file-text',
  text: 'file-text',
  other: 'file-text',
}

const currentIndex = computed(() => props.files.findIndex((file) => file.id === props.activeId))
const current = computed(() => (currentIndex.value >= 0 ? props.files[currentIndex.value] : null))

const kind = computed(() => {
  const mime = current.value?.mime_type || ''
  if (mime.startsWith('image/')) return 'image'
  if (mime.startsWith('video/')) return 'video'
  if (mime.startsWith('audio/')) return 'audio'
  if (mime === 'application/pdf') return 'pdf'
  if (mime.startsWith('text/') || mime === 'application/json') return 'text'
  return 'other'
})

const typeIcon = computed<IconName>(() => KIND_ICONS[kind.value] ?? 'file-text')

const canPrev = computed(() => currentIndex.value > 0)
const canNext = computed(
  () => currentIndex.value >= 0 && currentIndex.value < props.files.length - 1,
)

/** 文本预览：只在 ≤ 512 KB 时拉取，避免大文件阻塞界面 */
const TEXT_LIMIT = 512 * 1024
const textContent = ref('')

watch(
  () => [props.open, props.activeId, kind.value] as const,
  async () => {
    textContent.value = ''
    const file = current.value
    if (!props.open || !file || kind.value !== 'text' || !file.file_url) return
    if ((file.file_size || 0) > TEXT_LIMIT) return
    try {
      textContent.value = await $fetch<string>(file.file_url, {responseType: 'text'})
    } catch {
      textContent.value = ''
    }
  },
  {immediate: true},
)

function go(delta: number): void {
  const next = props.files[currentIndex.value + delta]
  if (next) emit('navigate', next)
}

async function copyLink(): Promise<void> {
  const url = current.value?.file_url
  if (!url) return
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.success('链接已复制')
  } catch {
    ElMessage.warning('复制失败，请手动复制')
  }
}

function onKeydown(event: KeyboardEvent): void {
  if (!props.open) return
  if (event.key === 'Escape') emit('close')
  else if (event.key === 'ArrowLeft') go(-1)
  else if (event.key === 'ArrowRight') go(1)
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div
    v-if="props.open && current"
    aria-modal="true"
    class="fixed inset-0 z-[100] flex flex-col bg-black/95"
    role="dialog"
  >
    <!-- 顶部信息栏 -->
    <header
      class="flex flex-shrink-0 items-center justify-between gap-3 border-b border-white/10 bg-black/50 px-4 py-2.5 backdrop-blur-sm">
      <div class="flex min-w-0 items-center gap-3">
        <Icon :name="typeIcon" class="h-4 w-4 flex-shrink-0 text-white/50"/>
        <span class="max-w-[12rem] truncate text-sm font-medium text-white/90 sm:max-w-md">
          {{ current.original_filename || current.filename || '(未命名)' }}
        </span>
        <span v-if="props.files.length > 1" class="hidden flex-shrink-0 text-xs text-white/40 sm:inline">
          {{ currentIndex + 1 }} / {{ props.files.length }}
        </span>
        <span class="hidden flex-shrink-0 rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-white/40 sm:inline">
          {{ current.mime_type || '-' }}
        </span>
        <span v-if="current.file_size" class="hidden flex-shrink-0 text-xs text-white/30 md:inline">
          {{ formatFileSize(current.file_size) }}
        </span>
        <span v-if="current.created_at" class="hidden flex-shrink-0 text-xs text-white/30 lg:inline">
          {{ formatDateTime(current.created_at) }}
        </span>
      </div>

      <div class="flex flex-shrink-0 items-center gap-1">
        <button
          v-if="current.file_url"
          class="rounded-lg p-1.5 text-white/50 transition-colors hover:bg-white/10 hover:text-white/90"
          title="复制文件链接"
          type="button"
          @click="copyLink"
        >
          <Icon class="h-4 w-4" name="link"/>
        </button>
        <button
          v-if="kind === 'image'"
          class="rounded-lg p-1.5 text-white/50 transition-colors hover:bg-white/10 hover:text-white/90"
          title="编辑图片信息"
          type="button"
          @click="emit('edit', current)"
        >
          <Icon class="h-4 w-4" name="pencil"/>
        </button>
        <a
          v-if="current.file_url"
          :href="current.file_url"
          class="rounded-lg p-1.5 text-white/50 transition-colors hover:bg-white/10 hover:text-white/90"
          download
          title="下载"
        >
          <Icon class="h-4 w-4" name="download"/>
        </a>
        <button
          class="rounded-lg p-1.5 text-white/60 transition-colors hover:bg-white/10 hover:text-white"
          title="关闭 (Esc)"
          type="button"
          @click="emit('close')"
        >
          <Icon class="h-5 w-5" name="x"/>
        </button>
      </div>
    </header>

    <!-- 预览主体 -->
    <div class="relative flex min-h-0 flex-1 items-center justify-center">
      <button
        v-if="canPrev"
        class="absolute left-2 top-1/2 z-10 -translate-y-1/2 rounded-full bg-black/40 p-2 text-white/70 transition-colors hover:bg-black/70 hover:text-white"
        title="上一个 (←)"
        type="button"
        @click="go(-1)"
      >
        <Icon class="h-6 w-6" name="chevron-left"/>
      </button>

      <img
        v-if="kind === 'image' && current.file_url"
        :alt="current.alt_text || current.original_filename || ''"
        :src="current.file_url"
        class="max-h-full max-w-full object-contain"
      >
      <video
        v-else-if="kind === 'video' && current.file_url"
        :src="current.file_url"
        class="max-h-full max-w-full"
        controls
      />
      <audio
        v-else-if="kind === 'audio' && current.file_url"
        :src="current.file_url"
        class="w-full max-w-xl px-6"
        controls
      />
      <iframe
        v-else-if="kind === 'pdf' && current.file_url"
        :src="current.file_url"
        class="h-full w-full max-w-5xl rounded border border-white/10 bg-white"
        title="PDF 预览"
      />
      <pre
        v-else-if="kind === 'text' && textContent"
        class="h-full w-full max-w-5xl overflow-auto whitespace-pre-wrap break-words bg-black/60 p-4 text-xs leading-relaxed text-white/80"
      >{{ textContent }}</pre>

      <div v-else class="flex flex-col items-center gap-3 text-center text-white/50">
        <Icon class="h-10 w-10" name="file-text"/>
        <p class="text-sm">
          {{ kind === 'text' ? '文件过大或读取失败，暂不支持在线预览' : '该类型暂不支持在线预览' }}
        </p>
        <a v-if="current.file_url" :href="current.file_url" class="text-sm text-blue-400 hover:underline" download>
          下载文件
        </a>
      </div>

      <button
        v-if="canNext"
        class="absolute right-2 top-1/2 z-10 -translate-y-1/2 rounded-full bg-black/40 p-2 text-white/70 transition-colors hover:bg-black/70 hover:text-white"
        title="下一个 (→)"
        type="button"
        @click="go(1)"
      >
        <Icon class="h-6 w-6" name="chevron-right"/>
      </button>
    </div>

    <!-- 底部缩略图导航 -->
    <footer
      v-if="props.files.length > 1"
      class="flex h-20 flex-shrink-0 items-center gap-2 overflow-x-auto border-t border-white/10 bg-black/40 px-3 backdrop-blur-sm"
    >
      <button
        v-for="file in props.files"
        :key="file.id"
        :class="
          file.id === props.activeId
            ? 'border-blue-500 ring-2 ring-blue-500/30'
            : 'border-white/10 opacity-50 hover:border-white/30 hover:opacity-90'
        "
        :title="file.original_filename || file.filename || ''"
        class="h-14 w-16 flex-shrink-0 overflow-hidden rounded-lg border-2 transition-all"
        type="button"
        @click="emit('navigate', file)"
      >
        <img
          v-if="(file.mime_type || '').startsWith('image/') && (file.thumbnail_url || file.file_url)"
          :alt="file.alt_text || ''"
          :src="file.thumbnail_url || file.file_url || ''"
          class="h-full w-full object-cover"
          loading="lazy"
        >
        <span v-else class="flex h-full w-full items-center justify-center bg-white/5">
          <Icon class="h-5 w-5 text-white/30" name="file-text"/>
        </span>
      </button>
    </footer>
  </div>
</template>
