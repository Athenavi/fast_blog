<script lang="ts" setup>
/**
 * 后台媒体选择器（从媒体库挑图 / 本地上传 / 外链兜底）
 *
 * 为什么需要它：文章编辑器的封面此前只是一个 URL 输入框，而正文插图却能走媒体库
 * （`components/site/RichEditor.vue` + `MediaPickerDialog`）——同一个页面两套取图方式，
 * 且封面完全无法复用已上传的素材。
 *
 * 与前台 `MediaPickerDialog` 的区别：这里走后台媒体库接口 `mediaApi`（能看到全站素材、
 * 按相册/公开性过滤），前台那个只看"我的上传"。
 */
import {Refresh, Search, Upload} from '@element-plus/icons-vue'
import {computed, ref, watch} from 'vue'

import {mediaApi, type MediaItem} from '@/api'
import {ElMessage} from '@/utils/feedback'
import {formatFileSize} from '@/utils/format'

const props = defineProps<{ modelValue: boolean }>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'select', url: string): void
}>()

const {t} = useI18n()

/** 一屏两行（3 列 / 4 列）刚好 */
const PAGE_SIZE = 24

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const items = ref<MediaItem[]>([])
const page = ref(1)
const pages = ref(0)
const loading = ref(false)
const failed = ref(false)
const uploading = ref(false)

const keyword = ref('')
const urlInput = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

function nameOf(item: MediaItem): string {
  return item.original_filename || item.filename || String(item.id)
}

function thumbOf(item: MediaItem): string {
  return item.thumbnail_url || item.file_url || ''
}

async function load(reset: boolean): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    const result = await mediaApi.list({
      page: page.value,
      page_size: PAGE_SIZE,
      mime_type: 'image/',
      keyword: keyword.value.trim() || undefined,
    })
    items.value = reset ? result.items : [...items.value, ...result.items]
    pages.value = result.pages
  } catch {
    // request 拦截器已统一提示，这里只做界面降级
    failed.value = true
    if (reset) items.value = []
  } finally {
    loading.value = false
  }
}

function search(): void {
  page.value = 1
  void load(true)
}

function loadMore(): void {
  if (page.value >= pages.value) return
  page.value += 1
  void load(false)
}

function close(): void {
  visible.value = false
}

function choose(url: string | null | undefined): void {
  const value = (url ?? '').trim()
  if (!value) {
    ElMessage.warning(t('admin.content.media.noUrlToUse'))
    return
  }
  emit('select', value)
  close()
}

function chooseUrl(): void {
  choose(urlInput.value)
}

function pickFiles(): void {
  fileInput.value?.click()
}

async function onFilesPicked(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  if (!files.length) return

  uploading.value = true
  try {
    const result = await mediaApi.upload(files)
    const first = result?.files?.[0]
    if (first) {
      choose(first.file_url)
    } else {
      ElMessage.warning(t('admin.content.media.uploadComplete'))
      search()
    }
  } finally {
    uploading.value = false
  }
}

// 每次打开都回到干净状态并重新拉取（素材是高频变化的数据）
watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    page.value = 1
    items.value = []
    pages.value = 0
    failed.value = false
    keyword.value = ''
    urlInput.value = ''
    void load(true)
  },
  {immediate: true},
)
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="$t('admin.content.media.mediaLibrary')"
    append-to-body
    class="media-picker"
    width="min(720px, 94vw)"
  >
    <div class="media-picker__toolbar">
      <el-input
        v-model="keyword"
        :placeholder="$t('admin.content.media.searchPlaceholder')"
        clearable
        style="width: 220px"
        @keyup.enter="search"
      />
      <el-button :icon="Search" type="primary" @click="search">{{ $t('admin.common.search') }}</el-button>
      <span class="media-picker__spacer"/>
      <el-button v-auth="'module_content:media:upload'" :icon="Upload" :loading="uploading" @click="pickFiles">
        {{ $t('admin.content.media.upload') }}
      </el-button>
    </div>

    <el-skeleton v-if="loading && !items.length" :rows="5" animated/>

    <AdminEmpty
      v-else-if="!items.length"
      :desc="failed ? '' : $t('admin.content.media.emptyDesc')"
      :title="failed ? $t('admin.common.loadFailed') : $t('admin.content.media.emptyTitle')"
      :variant="failed ? 'error' : 'default'"
    >
      <el-button v-if="failed" :icon="Refresh" @click="load(true)">
        {{ $t('admin.common.retry') }}
      </el-button>
    </AdminEmpty>

    <template v-else>
      <p class="media-picker__hint">{{ $t('admin.content.media.pickHint') }}</p>
      <div class="media-picker__grid">
        <button
          v-for="item in items"
          :key="item.id"
          :aria-label="nameOf(item)"
          :title="`${nameOf(item)}（${formatFileSize(item.file_size)}）`"
          class="media-picker__card"
          type="button"
          @click="choose(item.file_url)"
        >
          <img :alt="item.alt_text || nameOf(item)" :src="thumbOf(item)" decoding="async" loading="lazy">
        </button>
      </div>

      <div v-if="page < pages" class="media-picker__more">
        <el-button :loading="loading" @click="loadMore">{{ $t('site.loadMore') }}</el-button>
      </div>
    </template>

    <template #footer>
      <div class="media-picker__footer">
        <el-input
          v-model="urlInput"
          :placeholder="$t('admin.content.media.externalUrlPlaceholder')"
          class="media-picker__url"
          @keyup.enter="chooseUrl"
        />
        <el-button @click="chooseUrl">{{ $t('admin.content.media.useThisUrl') }}</el-button>
        <el-button @click="close">{{ $t('admin.common.cancel') }}</el-button>
      </div>
    </template>

    <input ref="fileInput" accept="image/*" class="media-picker__file" multiple type="file" @change="onFilesPicked">
  </el-dialog>
</template>

<style scoped>
.media-picker__toolbar {
  display: flex;
  gap: var(--admin-gap-sm);
  align-items: center;
  margin-bottom: var(--admin-gap);
}

.media-picker__spacer {
  flex: 1 1 auto;
}

.media-picker__hint {
  margin: 0 0 var(--admin-gap-sm);
  font-size: var(--admin-font-sm);
  color: var(--admin-fg-subtle);
}

.media-picker__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: var(--admin-gap-sm);
}

.media-picker__card {
  padding: 0;
  overflow: hidden;
  cursor: pointer;
  background: var(--admin-surface-soft);
  border: 1px solid var(--admin-line);
  border-radius: var(--admin-radius-sm);
  transition: border-color 0.12s ease, box-shadow 0.12s ease;
}

.media-picker__card:hover {
  border-color: var(--admin-primary);
  box-shadow: 0 0 0 2px color-mix(in oklab, var(--admin-primary) 25%, transparent);
}

.media-picker__card:focus-visible {
  outline: 2px solid var(--admin-primary);
  outline-offset: 2px;
}

.media-picker__card img {
  display: block;
  width: 100%;
  height: 96px;
  object-fit: cover;
}

.media-picker__more {
  margin-top: var(--admin-gap);
  text-align: center;
}

.media-picker__footer {
  display: flex;
  gap: var(--admin-gap-sm);
  align-items: center;
}

.media-picker__url {
  flex: 1;
}

.media-picker__file {
  display: none;
}
</style>
