<script lang="ts" setup>
const {t} = useI18n()
/**
 * 离线下载
 *
 * 对应原 astro 的 `pages/media/OfflineDownloadDialog.tsx`（那边 27KB，走了独立的任务队列与 IndexedDB）。
 *
 * 这里用**浏览器原生 Cache API** 重写：
 *  - 选中文件后逐个 `cache.add(url)`，逐个报进度，单个失败不影响其余
 *  - 缓存名与 `nuxt.config.ts` 里 Workbox 的 `media-assets` 保持一致——
 *    这样离线下载的内容与 PWA 运行时缓存共用一份存储，前台浏览时命中的也是它
 *  - 已缓存列表通过 `cache.keys()` 得出，可单独清理
 *
 * 无任何第三方依赖。
 */

import type {OfflineCandidate} from '@/types/media'
import {formatFileSize} from '@/utils/format'

const CACHE_NAME = 'media-assets'

const props = withDefaults(
  defineProps<{
    items: OfflineCandidate[]
    open?: boolean
  }>(),
  {open: false},
)

const emit = defineEmits<{ (e: 'close'): void }>()

const selected = ref<number[]>([])
const busy = ref(false)
const done = ref(0)
const failed = ref(0)
const cachedUrls = ref<string[]>([])
const error = ref('')

const supported = computed(() => typeof caches !== 'undefined')

const selectedItems = computed(() => props.items.filter((item) => selected.value.includes(item.id)))
const selectedSize = computed(() =>
  selectedItems.value.reduce((sum, item) => sum + (item.size ?? 0), 0),
)

function toggle(id: number): void {
  const index = selected.value.indexOf(id)
  if (index === -1) selected.value.push(id)
  else selected.value.splice(index, 1)
}

async function loadCached(): Promise<void> {
  if (!supported.value) return
  try {
    const cache = await caches.open(CACHE_NAME)
    const keys = await cache.keys()
    cachedUrls.value = keys.map((req) => req.url)
  } catch {
    cachedUrls.value = []
  }
}

function isCached(url?: string | null): boolean {
  if (!url) return false
  return cachedUrls.value.some((item) => item === url || item.endsWith(url))
}

async function startDownload(): Promise<void> {
  if (!supported.value) {
    error.value = t('media.unsupportedOffline')
    return
  }
  if (!selectedItems.value.length) {
    error.value = t('media.selectFirst')
    return
  }

  busy.value = true
  done.value = 0
  failed.value = 0
  error.value = ''

  try {
    const cache = await caches.open(CACHE_NAME)
    for (const item of selectedItems.value) {
      if (!item.url) {
        failed.value += 1
        continue
      }
      try {
        await cache.add(item.url)
        done.value += 1
      } catch {
        failed.value += 1
      }
    }
    await loadCached()
  } finally {
    busy.value = false
  }
}

/** 清空缓存做两步确认：原生 confirm 的按钮文案无法本地化，也与本站浮层风格不符 */
const confirmClear = ref(false)

async function clearCache(): Promise<void> {
  if (!supported.value) return
  if (!confirmClear.value) {
    confirmClear.value = true
    return
  }
  confirmClear.value = false
  try {
    await caches.delete(CACHE_NAME)
    cachedUrls.value = []
    done.value = 0
    failed.value = 0
  } catch {
    error.value = t('media.clearFailed')
  }
}

watch(
  () => props.open,
  (value) => {
    if (value) {
      error.value = ''
      loadCached()
    }
  },
  {immediate: true},
)
</script>

<template>
  <div
    v-if="props.open"
    aria-modal="true"
    class="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 px-4"
    role="dialog"
  >
    <Card class="w-full max-w-2xl">
      <CardHeader class="flex-row items-center justify-between">
        <div>
          <CardTitle class="text-base">{{ $t('media.offlineSave') }}</CardTitle>
          <CardDescription>
            {{ $t('media.offlineHint') }}
            <span v-if="cachedUrls.length">{{ $t('media.cachedCount', {n: cachedUrls.length}) }}</span>
          </CardDescription>
        </div>
        <button
          :aria-label="$t('admin.common.close')"
          class="inline-flex h-8 w-8 items-center justify-center rounded-control text-fg-subtle transition-colors hover:bg-surface-soft hover:text-fg"
          type="button"
          @click="emit('close')"
        >
          <Icon class="h-4 w-4" name="x"/>
        </button>
      </CardHeader>

      <CardContent class="space-y-3">
        <p v-if="!supported" class="rounded-control bg-warning-soft px-3 py-2 text-sm text-warning">
          {{ $t('media.noCacheApi') }}
        </p>

        <div v-else class="max-h-72 space-y-1 overflow-y-auto rounded-control border border-line p-2">
          <label
            v-for="item in props.items"
            :key="item.id"
            class="flex cursor-pointer items-center gap-3 rounded-control px-2 py-1.5 transition-colors hover:bg-surface-soft"
          >
            <input
              :checked="selected.includes(item.id)"
              class="h-4 w-4 rounded border-line"
              type="checkbox"
              @change="toggle(item.id)"
            >
            <span class="min-w-0 flex-1 truncate text-sm text-fg">{{ item.name || t('media.unnamed') }}</span>
            <span v-if="item.size" class="text-xs text-fg-subtle">{{ formatFileSize(item.size) }}</span>
            <span v-if="isCached(item.url)" class="text-xs text-success">{{ $t('media.cachedLabel') }}</span>
          </label>

          <p v-if="!props.items.length" class="px-2 py-3 text-center text-sm text-fg-subtle">
            {{ $t('media.nothingToSave') }}
          </p>
        </div>

        <div v-if="busy || done || failed" class="space-y-1">
          <div class="h-1.5 overflow-hidden rounded-pill bg-surface-soft">
            <div
              :style="{width: `${selectedItems.length ? ((done + failed) / selectedItems.length) * 100 : 0}%`}"
              class="h-full bg-primary transition-all"
            />
          </div>
          <p class="text-xs text-fg-subtle">
            {{ $t('media.progressCount', {done, total: selectedItems.length}) }}
            <span v-if="failed" class="text-danger">{{ $t('media.failedCount', {n: failed}) }}</span>
          </p>
        </div>

        <p v-if="error" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

        <p v-if="selected.length" class="text-xs text-fg-muted">
          {{ $t('media.selectedSummary', {n: selected.length, size: formatFileSize(selectedSize)}) }}
        </p>
      </CardContent>

      <CardFooter class="justify-between gap-2">
        <div v-if="confirmClear" class="flex items-center gap-2">
          <span class="text-xs text-danger">{{ $t('media.confirmClearOffline') }}</span>
          <Button class="text-danger" size="sm" variant="ghost" @click="clearCache">
            {{ $t('common.confirm') }}
          </Button>
          <Button size="sm" variant="ghost" @click="confirmClear = false">{{ $t('admin.common.cancel') }}</Button>
        </div>
        <Button v-else :disabled="busy || !cachedUrls.length" class="text-danger" variant="ghost" @click="clearCache">
          <Icon class="h-4 w-4" name="trash-2"/>
          {{ $t('media.clearCache') }}
        </Button>
        <div class="flex gap-2">
          <Button variant="outline" @click="emit('close')">{{ $t('admin.common.close') }}</Button>
          <Button :disabled="busy || !supported || !selected.length" @click="startDownload">
            <Icon v-if="busy" class="h-4 w-4 animate-spin" name="loader-circle"/>
            <Icon v-else class="h-4 w-4" name="download"/>
            {{ busy ? t('media.saving') : t('media.startSave') }}
          </Button>
        </div>
      </CardFooter>
    </Card>
  </div>
</template>
