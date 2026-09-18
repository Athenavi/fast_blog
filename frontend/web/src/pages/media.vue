<script lang="ts" setup>
/**
 * 我的媒体库
 *
 * 对应原 astro 的 `media.astro`。接口全部走 v3 的 `mobile/media`（只操作本人数据）：
 * `/list`、`/upload/image`、`/{id}`（更新/删除）、`/batch/delete`、`/folders`、`/stats`。
 *
 * 依赖登录态，在 `nuxt.config.ts` 中已设为 `ssr: false`，由 `middleware: 'auth'` 把关。
 */

import {mobileApi, type MobileMediaFolder, type MobileMediaItem, type MobileMediaStats,} from '@/api'
import {cn} from '@/lib/utils'
import {formatDateTime, formatFileSize, splitTags} from '@/utils/format'

definePageMeta({layout: 'default', middleware: 'auth', title: '我的媒体'})

const PAGE_SIZE = 24

const list = ref<MobileMediaItem[]>([])
const folders = ref<MobileMediaFolder[]>([])
const stats = ref<MobileMediaStats | null>(null)
const total = ref(0)
const page = ref(1)

const loading = ref(false)
const uploading = ref(false)
const message = ref('')
const error = ref('')

const activeFolder = ref<number | undefined>(undefined)
const keyword = ref('')
const selected = ref<number[]>([])

const fileInput = ref<HTMLInputElement | null>(null)

// ---------------------------------------------------------------- 数据加载
async function loadFolders(): Promise<void> {
  try {
    folders.value = await mobileApi.mediaFolders()
  } catch {
    folders.value = []
  }
}

async function loadStats(): Promise<void> {
  try {
    stats.value = await mobileApi.mediaStats()
  } catch {
    stats.value = null
  }
}

async function loadList(): Promise<void> {
  loading.value = true
  try {
    const data = await mobileApi.mediaList({
      page: page.value,
      page_size: PAGE_SIZE,
      ...(activeFolder.value === undefined ? {} : {folder_id: activeFolder.value}),
      ...(keyword.value ? {keyword: keyword.value} : {}),
    })
    list.value = data.items
    total.value = data.total
    // 列表变化后清理已不存在的选中项
    const ids = new Set(data.items.map((item) => item.id))
    selected.value = selected.value.filter((id) => ids.has(id))
  } finally {
    loading.value = false
  }
}

async function refresh(): Promise<void> {
  await Promise.all([loadList(), loadFolders(), loadStats()])
}

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

function selectFolder(id?: number): void {
  activeFolder.value = id
  page.value = 1
  loadList()
}

function onSearch(): void {
  page.value = 1
  loadList()
}

function changePage(next: number): void {
  if (next < 1 || next > totalPages.value) return
  page.value = next
  loadList()
}

// ---------------------------------------------------------------- 上传
function pickFiles(): void {
  fileInput.value?.click()
}

async function onFilesPicked(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  if (!files.length) return

  uploading.value = true
  error.value = ''
  message.value = `正在上传 ${files.length} 个文件…`
  let ok = 0
  try {
    // 逐个上传，单个失败不影响其余
    for (const file of files) {
      try {
        await mobileApi.mediaUpload(file)
        ok += 1
      } catch {
        /* 单个失败继续 */
      }
    }
    message.value = ok === files.length ? `已上传 ${ok} 个文件` : `上传完成 ${ok}/${files.length}`
    if (ok < files.length) error.value = '部分文件上传失败（可能是不支持的类型或超出大小限制）'
    await refresh()
  } finally {
    uploading.value = false
    input.value = ''
  }
}

// ---------------------------------------------------------------- 选择与批量
function toggleSelect(id: number): void {
  const index = selected.value.indexOf(id)
  if (index === -1) selected.value.push(id)
  else selected.value.splice(index, 1)
}

function isSelected(id: number): boolean {
  return selected.value.includes(id)
}

const allSelected = computed(
  () => list.value.length > 0 && selected.value.length === list.value.length,
)

function toggleAll(): void {
  selected.value = allSelected.value ? [] : list.value.map((item) => item.id)
}

async function removeSelected(): Promise<void> {
  if (!selected.value.length) return
  if (!window.confirm(`确定删除选中的 ${selected.value.length} 个文件吗？`)) return
  await mobileApi.mediaBatchDelete([...selected.value])
  message.value = '已删除'
  selected.value = []
  await refresh()
}

async function removeOne(item: MobileMediaItem): Promise<void> {
  const name = item.original_filename || item.filename || String(item.id)
  if (!window.confirm(`确定删除「${name}」吗？`)) return
  await mobileApi.mediaRemove(item.id)
  message.value = '已删除'
  await refresh()
}

// ---------------------------------------------------------------- 编辑元信息
const editing = ref<MobileMediaItem | null>(null)
const editForm = reactive({description: '', alt_text: '', category: '', tags: ''})
const editSaving = ref(false)

function openEdit(item: MobileMediaItem): void {
  editing.value = item
  editForm.description = item.description ?? ''
  editForm.alt_text = item.alt_text ?? ''
  editForm.category = item.category ?? ''
  editForm.tags = splitTags(item.tags).join(', ')
}

async function saveEdit(): Promise<void> {
  if (!editing.value) return
  editSaving.value = true
  try {
    await mobileApi.mediaUpdate(editing.value.id, {
      description: editForm.description,
      alt_text: editForm.alt_text,
      category: editForm.category,
      tags: editForm.tags
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
    })
    editing.value = null
    message.value = '已保存'
    await loadList()
  } finally {
    editSaving.value = false
  }
}

// ---------------------------------------------------------------- 文件夹
const folderDialog = ref(false)
const folderName = ref('')
const folderSaving = ref(false)

function openFolderDialog(): void {
  folderName.value = ''
  folderDialog.value = true
}

async function createFolder(): Promise<void> {
  const name = folderName.value.trim()
  if (!name) {
    error.value = '请填写文件夹名称'
    return
  }
  folderSaving.value = true
  try {
    await mobileApi.mediaCreateFolder({
      name,
      parent_id: activeFolder.value ?? null,
    })
    folderDialog.value = false
    message.value = '文件夹已创建'
    await loadFolders()
  } finally {
    folderSaving.value = false
  }
}

function isImage(item: MobileMediaItem): boolean {
  return (item.mime_type || '').startsWith('image/')
}

async function copyUrl(item: MobileMediaItem): Promise<void> {
  if (!item.file_url) return
  try {
    await navigator.clipboard.writeText(item.file_url)
    message.value = '链接已复制'
  } catch {
    error.value = '复制失败，请手动复制'
  }
}

onMounted(refresh)
</script>

<template>
  <div class="mx-auto max-w-wide px-4 py-10">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fg">我的媒体</h1>
        <p class="mt-1.5 text-sm text-fg-muted">
          上传与管理自己的图片、文档。发布文章时可从这里选择封面与插图。
        </p>
      </div>

      <div class="flex items-center gap-2">
        <Button :disabled="uploading" @click="pickFiles">
          <Icon v-if="uploading" class="h-4 w-4 animate-spin" name="loader-circle"/>
          <Icon v-else class="h-4 w-4" name="upload"/>
          上传文件
        </Button>
        <Button variant="outline" @click="openFolderDialog">
          <Icon class="h-4 w-4" name="folder-plus"/>
          新建文件夹
        </Button>
      </div>
    </div>

    <input ref="fileInput" hidden multiple type="file" @change="onFilesPicked">

    <!-- 统计 -->
    <div v-if="stats" class="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Card>
        <CardContent class="p-4">
          <p class="text-xl font-semibold text-fg">{{ stats.total }}</p>
          <p class="mt-0.5 text-xs text-fg-subtle">文件总数</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="p-4">
          <p class="text-xl font-semibold text-fg">{{ formatFileSize(stats.total_size) }}</p>
          <p class="mt-0.5 text-xs text-fg-subtle">占用空间</p>
        </CardContent>
      </Card>
      <Card v-for="(count, type) in stats.by_type" :key="type">
        <CardContent class="p-4">
          <p class="text-xl font-semibold text-fg">{{ count }}</p>
          <p class="mt-0.5 text-xs text-fg-subtle">{{ type }}</p>
        </CardContent>
      </Card>
    </div>

    <p v-if="message" class="mt-4 rounded-control bg-success-soft px-3 py-2 text-sm text-success">
      {{ message }}
    </p>
    <p v-if="error" class="mt-4 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
      {{ error }}
    </p>

    <div class="mt-6 grid gap-6 lg:grid-cols-[200px_1fr]">
      <!-- 文件夹 -->
      <aside class="space-y-1">
        <button
          :class="activeFolder === undefined ? 'bg-surface-soft font-medium text-fg' : 'text-fg-muted hover:bg-surface-soft'"
          class="flex w-full items-center gap-2 rounded-control px-3 py-2 text-sm transition-colors"
          type="button"
          @click="selectFolder(undefined)"
        >
          全部文件
        </button>
        <button
          v-for="folder in folders"
          :key="folder.id"
          :class="activeFolder === folder.id ? 'bg-surface-soft font-medium text-fg' : 'text-fg-muted hover:bg-surface-soft'"
          class="flex w-full items-center gap-2 rounded-control px-3 py-2 text-sm transition-colors"
          type="button"
          @click="selectFolder(folder.id)"
        >
          <span class="truncate">{{ folder.name }}</span>
          <span class="ml-auto text-xs text-fg-subtle">{{ folder.media_count }}</span>
        </button>
        <p v-if="!folders.length" class="px-3 py-2 text-xs text-fg-subtle">还没有文件夹</p>
      </aside>

      <!-- 媒体网格 -->
      <section>
        <div class="mb-4 flex flex-wrap items-center gap-2">
          <div class="relative">
            <Icon class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" name="search"/>
            <Input v-model="keyword" class="w-56 pl-9" placeholder="按文件名搜索" @keyup.enter="onSearch"/>
          </div>
          <Button size="sm" variant="outline" @click="onSearch">搜索</Button>
          <Button v-if="selected.length" size="sm" variant="danger" @click="removeSelected">
            <Icon class="h-4 w-4" name="trash-2"/>
            删除选中（{{ selected.length }}）
          </Button>
          <label v-if="list.length" class="ml-auto flex items-center gap-1.5 text-sm text-fg-muted">
            <input :checked="allSelected" class="h-4 w-4 rounded border-line" type="checkbox" @change="toggleAll">
            全选
          </label>
        </div>

        <div v-if="loading" class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          <Skeleton v-for="i in 8" :key="i" class="h-32 w-full"/>
        </div>

        <div v-else-if="list.length" class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          <div
            v-for="item in list"
            :key="item.id"
            :class="cn('transition-colors', isSelected(item.id) ? 'border-primary' : 'border-line hover:border-line-strong')"
            class="group relative overflow-hidden rounded-card border bg-surface"
          >
            <button
              :aria-label="'选择 ' + (item.original_filename || item.filename)"
              class="absolute left-2 top-2 z-10 flex h-5 w-5 items-center justify-center rounded border border-line bg-surface/90"
              type="button"
              @click="toggleSelect(item.id)"
            >
              <span v-if="isSelected(item.id)" class="text-xs text-primary">✓</span>
            </button>

            <div class="flex h-32 items-center justify-center bg-surface-soft">
              <img
                v-if="isImage(item) && item.file_url"
                :alt="item.alt_text || item.original_filename || ''"
                :src="item.thumbnail_url || item.file_url"
                class="h-full w-full object-cover"
                loading="lazy"
              >
              <Icon v-else class="h-8 w-8 text-fg-subtle" name="image"/>
            </div>

            <div class="p-2.5">
              <p :title="item.original_filename || item.filename || ''" class="truncate text-xs font-medium text-fg">
                {{ item.original_filename || item.filename }}
              </p>
              <p class="mt-0.5 text-[11px] text-fg-subtle">
                {{ formatFileSize(item.file_size) }} · {{ formatDateTime(item.created_at).slice(0, 10) }}
              </p>
              <div class="mt-2 flex items-center gap-2 text-[11px]">
                <button class="text-primary hover:underline" type="button" @click="copyUrl(item)">复制链接</button>
                <button class="text-fg-muted hover:underline" type="button" @click="openEdit(item)">编辑</button>
                <button class="ml-auto text-danger hover:underline" type="button" @click="removeOne(item)">删除</button>
              </div>
            </div>
          </div>
        </div>

        <EmptyState
          v-else
          description="点击右上角「上传文件」开始，支持图片与常见文档。"
          title="这里还没有文件"
        />

        <nav v-if="totalPages > 1" class="flex items-center justify-center gap-2 pt-8">
          <Button :disabled="page <= 1" size="sm" variant="outline" @click="changePage(page - 1)">上一页</Button>
          <span class="text-sm text-fg-muted">{{ page }} / {{ totalPages }}</span>
          <Button :disabled="page >= totalPages" size="sm" variant="outline" @click="changePage(page + 1)">下一页
          </Button>
        </nav>
      </section>
    </div>

    <!-- 编辑元信息 -->
    <div v-if="editing" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <Card class="w-full max-w-lg">
        <CardHeader>
          <CardTitle class="text-base">编辑文件信息</CardTitle>
          <CardDescription>{{ editing.original_filename || editing.filename }}</CardDescription>
        </CardHeader>
        <CardContent class="space-y-3">
          <div>
            <label class="mb-1.5 block text-sm font-medium text-fg">描述</label>
            <Input v-model="editForm.description" placeholder="简短描述"/>
          </div>
          <div>
            <label class="mb-1.5 block text-sm font-medium text-fg">替代文本</label>
            <Input v-model="editForm.alt_text" placeholder="用于无障碍与 SEO"/>
          </div>
          <div>
            <label class="mb-1.5 block text-sm font-medium text-fg">分类</label>
            <Input v-model="editForm.category"/>
          </div>
          <div>
            <label class="mb-1.5 block text-sm font-medium text-fg">标签</label>
            <Input v-model="editForm.tags" placeholder="用英文逗号分隔"/>
          </div>
        </CardContent>
        <CardFooter class="justify-end gap-2">
          <Button variant="outline" @click="editing = null">取消</Button>
          <Button :disabled="editSaving" @click="saveEdit">
            <Icon v-if="editSaving" class="h-4 w-4 animate-spin" name="loader-circle"/>
            <Icon v-else class="h-4 w-4" name="save"/>
            保存
          </Button>
        </CardFooter>
      </Card>
    </div>

    <!-- 新建文件夹 -->
    <div v-if="folderDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <Card class="w-full max-w-sm">
        <CardHeader>
          <CardTitle class="text-base">新建文件夹</CardTitle>
        </CardHeader>
        <CardContent>
          <Input v-model="folderName" placeholder="文件夹名称" @keyup.enter="createFolder"/>
        </CardContent>
        <CardFooter class="justify-end gap-2">
          <Button variant="outline" @click="folderDialog = false">取消</Button>
          <Button :disabled="folderSaving" @click="createFolder">创建</Button>
        </CardFooter>
      </Card>
    </div>
  </div>
</template>
