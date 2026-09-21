<script lang="ts" setup>
const {t} = useI18n()
/**
 * 前台媒体选择弹窗（我的媒体库）
 *
 * 供 RichEditor 插图等场景使用：浏览/选择自己上传的图片、本地上传、外链地址兜底。
 * 数据走 v3 `mobile/media`（登录即可用，只操作本人数据）：
 *  - 列表 `mobileApi.mediaList({mime_type: 'image/'})`
 *  - 上传 `mobileApi.mediaUpload(file)` → `POST /mobile/media/upload/image`
 * 后台管理员的媒体管理在 `/content/media`，与本组件无关。
 * 弹窗内容由父组件用 v-if 控制，打开后才拉数据。
 */
import {mobileApi, type MobileMediaItem} from '@/api'
import {useUserStore} from '@/store/modules/user'

const props = defineProps<{ modelValue: boolean }>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'select', url: string): void
}>()

const userStore = useUserStore()

/** 弹窗网格 3~4 列，一页 24 张大致两屏 */
const PAGE_SIZE = 24

const items = ref<MobileMediaItem[]>([])
const page = ref(1)
const pages = ref(0)
const loading = ref(false)
const loadError = ref('')

const uploading = ref(false)
const uploadError = ref('')

const urlInput = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

function close(): void {
  emit('update:modelValue', false)
}

function choose(url: string): void {
  const value = url.trim()
  if (!value) return
  emit('select', value)
  close()
}

async function load(reset: boolean): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const result = await mobileApi.mediaList({
      page: page.value,
      page_size: PAGE_SIZE,
      mime_type: 'image/',
    })
    items.value = reset ? result.items : [...items.value, ...result.items]
    pages.value = result.pages
  } catch {
    // request.ts 已统一弹过错误提示，这里只做界面降级
    loadError.value = t('site.mediaLoadFailed')
  } finally {
    loading.value = false
  }
}

function loadMore(): void {
  if (page.value >= pages.value) return
  page.value += 1
  void load(false)
}

function onPickFile(): void {
  fileInput.value?.click()
}

async function onFileChange(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  uploading.value = true
  uploadError.value = ''
  try {
    const item = await mobileApi.mediaUpload(file)
    choose(item.file_url ?? '')
  } catch {
    uploadError.value = t('site.mediaUploadFailed')
  } finally {
    uploading.value = false
  }
}

function confirmUrl(): void {
  choose(urlInput.value)
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') close()
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) {
      window.removeEventListener('keydown', onKeydown)
      return
    }
    page.value = 1
    items.value = []
    pages.value = 0
    loadError.value = ''
    uploadError.value = ''
    urlInput.value = ''
    window.addEventListener('keydown', onKeydown)
    if (userStore.isLoggedIn) void load(true)
  },
)

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-[60] flex items-center justify-center bg-canvas/80 p-4 backdrop-blur-sm"
      @click.self="close"
    >
      <div
        class="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-card border border-line bg-surface"
      >
        <!-- 头部 -->
        <div class="flex items-center justify-between border-b border-line px-4 py-3">
          <h2 class="text-sm font-semibold text-fg">{{ $t('site.pickImageTitle') }}</h2>
          <button
            class="inline-flex h-7 w-7 items-center justify-center rounded-control text-fg-muted transition-colors hover:bg-surface-soft hover:text-fg"
            type="button"
            @click="close"
          >
            <Icon class="h-4 w-4" name="x"/>
          </button>
        </div>

        <!-- 媒体网格 -->
        <div class="min-h-0 flex-1 overflow-y-auto p-4">
          <div v-if="!userStore.isLoggedIn" class="py-12 text-center text-sm text-fg-muted">
            {{ $t('site.mediaLoginHint') }}
            <NuxtLink class="ml-1 text-primary hover:underline" to="/login" @click="close">{{
                $t('site.goLogin')
              }}
            </NuxtLink>
          </div>

          <template v-else>
            <div v-if="loadError" class="py-12 text-center">
              <p class="text-sm text-danger">{{ loadError }}</p>
              <Button class="mt-3" size="sm" type="button" variant="outline" @click="load(true)">{{
                  $t('common.retry')
                }}
              </Button>
            </div>

            <div v-else-if="loading && items.length === 0" class="grid grid-cols-3 gap-2 sm:grid-cols-4">
              <Skeleton v-for="i in 8" :key="i" class="aspect-square w-full"/>
            </div>

            <div v-else-if="items.length === 0" class="py-12 text-center text-sm text-fg-muted">
              {{ $t('site.mediaEmpty') }}
            </div>

            <template v-else>
              <div class="grid grid-cols-3 gap-2 sm:grid-cols-4">
                <button
                  v-for="item in items"
                  :key="item.id"
                  :title="item.original_filename || item.filename || t('site.imageFallbackAlt')"
                  class="aspect-square overflow-hidden rounded-control border border-line transition hover:ring-2 hover:ring-primary/50"
                  type="button"
                  @click="choose(item.file_url || '')"
                >
                  <img
                    :alt="item.alt_text || item.original_filename || item.filename || t('site.imageFallbackAlt')"
                    :src="item.thumbnail_url || item.file_url || ''"
                    class="h-full w-full object-cover"
                    decoding="async" loading="lazy"
                  >
                </button>
              </div>

              <div v-if="page < pages" class="mt-3 text-center">
                <Button :disabled="loading" size="sm" type="button" variant="outline" @click="loadMore">
                  <Icon v-if="loading" class="h-4 w-4 animate-spin" name="loader-circle"/>
                  {{ $t('site.loadMore') }}
                </Button>
              </div>
            </template>
          </template>
        </div>

        <!-- 底部：上传 + 外链兜底 -->
        <div class="space-y-2 border-t border-line px-4 py-3">
          <div class="flex items-center gap-2">
            <Button :disabled="uploading || !userStore.isLoggedIn" size="sm" type="button" @click="onPickFile">
              <Icon v-if="uploading" class="h-4 w-4 animate-spin" name="loader-circle"/>
              <Icon v-else class="h-4 w-4" name="upload"/>
              {{ uploading ? t('site.uploading') : t('site.uploadImage') }}
            </Button>
            <p v-if="uploadError" class="text-xs text-danger">{{ uploadError }}</p>
            <span v-else class="text-xs text-fg-subtle">{{ $t('site.uploadHint') }}</span>
          </div>
          <div class="flex items-center gap-2">
            <Input
              v-model="urlInput"
              :placeholder="$t('site.imageUrlPlaceholder')"
              class="flex-1"
              @keyup.enter.prevent="confirmUrl"
            />
            <Button size="sm" type="button" variant="outline" @click="confirmUrl">{{ $t('site.insert') }}</Button>
          </div>
        </div>

        <input ref="fileInput" accept="image/*" class="hidden" type="file" @change="onFileChange">
      </div>
    </div>
  </Teleport>
</template>
