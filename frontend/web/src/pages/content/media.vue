<script lang="ts" setup>
const {t} = useI18n()
/**
 * 媒体库（文件夹 + 网格/列表双视图 + 拖拽上传 + 详情侧栏 + 批量操作）
 *
 * 对齐 v3：`/content/media`（列表/详情/更新/删除/批量删除/上传）、
 * `/content/media/folders*`（文件夹树与增删改）。
 *
 * 交互约定：
 *  - 拖文件到内容区任意位置即上传（上传后自动归入当前选中的文件夹）；
 *  - 网格视图单击选中、双击打开详情；列表视图用表格多选，两种视图共用同一份选中集合；
 *  - 批量"移动到/设为公开/设为私有"逐条调用更新接口（后端无批量端点），并如实汇报失败数。
 */
import {
  Delete,
  Document,
  Edit,
  FolderAdd,
  Grid,
  Headset,
  List,
  Picture,
  Search,
  Upload,
  VideoCamera,
  View,
} from '@element-plus/icons-vue'
import {computed, reactive, ref, watch} from 'vue'

import {mediaApi, type MediaFolder, type MediaItem, type MediaQuery} from '@/api'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {formatDateTime, formatFileSize, splitTags} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.media.mediaLibrary',
  permission: 'module_content:media:view',
})

const VIEW_STORAGE_KEY = 'fastblog.media.view'

const list = useAdminList<MediaItem, MediaQuery>({
  fetcher: (params) => mediaApi.list(params),
  defaultQuery: {keyword: '', mime_type: undefined, is_public: undefined, folder_id: undefined},
  pageSize: 24,
  syncUrl: true,
})

const MIME_OPTIONS = computed(() => [
  {label: t('admin.content.media.image'), value: 'image/'},
  {label: t('admin.content.media.video'), value: 'video/'},
  {label: t('admin.content.media.audio'), value: 'audio/'},
  {label: t('admin.content.media.document'), value: 'application/'},
])

// ---------------------------------------------------------------- 视图模式
const viewMode = ref<'grid' | 'list'>('grid')

onMounted(() => {
  const saved = localStorage.getItem(VIEW_STORAGE_KEY)
  if (saved === 'grid' || saved === 'list') viewMode.value = saved
})
watch(viewMode, (mode) => localStorage.setItem(VIEW_STORAGE_KEY, mode))

// ---------------------------------------------------------------- 文件夹
const folders = ref<MediaFolder[]>([])
const activeFolderId = computed({
  get: () => list.query.folder_id as number | undefined,
  set: (value: number | undefined) => {
    list.query.folder_id = value
    void list.search()
  },
})

async function loadFolders(): Promise<void> {
  try {
    folders.value = await mediaApi.folderTree()
  } catch {
    folders.value = []
  }
}

const folderDialogVisible = ref(false)
const folderSaving = ref(false)
const folderForm = reactive({
  id: null as number | null,
  name: '',
  parent_id: null as number | null,
  description: '',
})

function openFolderDialog(folder?: MediaFolder, parentId?: number | null): void {
  folderForm.id = folder?.id ?? null
  folderForm.name = folder?.name ?? ''
  folderForm.parent_id = folder?.parent_id ?? parentId ?? null
  folderForm.description = folder?.description ?? ''
  folderDialogVisible.value = true
}

async function submitFolder(): Promise<void> {
  const name = folderForm.name.trim()
  if (!name) {
    ElMessage.warning(t('admin.content.media.folderNameRequired'))
    return
  }
  folderSaving.value = true
  try {
    if (folderForm.id) {
      await mediaApi.updateFolder(folderForm.id, {
        name,
        parent_id: folderForm.parent_id,
        description: folderForm.description,
      })
    } else {
      await mediaApi.createFolder({
        name,
        parent_id: folderForm.parent_id,
        description: folderForm.description,
      })
    }
    ElMessage.success(t('admin.content.media.folderSaved'))
    folderDialogVisible.value = false
    await loadFolders()
  } finally {
    folderSaving.value = false
  }
}

async function removeFolder(): Promise<void> {
  if (!folderForm.id) return
  await ElMessageBox.confirm(
    t('admin.content.media.deleteFolderConfirm', {name: folderForm.name}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await mediaApi.removeFolder(folderForm.id)
  ElMessage.success(t('admin.content.media.folderDeleted'))
  folderDialogVisible.value = false
  if (activeFolderId.value === folderForm.id) activeFolderId.value = undefined
  await Promise.all([loadFolders(), list.reload()])
}

/** 文件夹下拉（详情/移动用）：把树拍平成带缩进的选项 */
const folderOptions = computed(() => {
  const out: Array<{ id: number; label: string }> = []
  const walk = (nodes: MediaFolder[], depth = 0): void => {
    for (const node of nodes) {
      out.push({id: node.id, label: `${'　'.repeat(depth)}${node.name}`})
      if (node.children?.length) walk(node.children, depth + 1)
    }
  }
  walk(folders.value)
  return out
})

// ---------------------------------------------------------------- 上传（按钮 + 拖拽）
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const dragging = ref(false)
let dragDepth = 0

function pickFiles(): void {
  fileInput.value?.click()
}

async function doUpload(files: File[]): Promise<void> {
  if (!files.length) return
  uploading.value = true
  try {
    const result = await mediaApi.upload(files)
    // 上传接口不带文件夹参数：落库后按当前选中的文件夹归档（真实写库，失败如实提示）
    const folderId = activeFolderId.value
    if (folderId && result?.files?.length) {
      const results = await Promise.allSettled(
        result.files.map((file) => mediaApi.update(file.id, {folder_id: folderId})),
      )
      const failed = results.filter((item) => item.status === 'rejected').length
      if (failed) ElMessage.warning(t('admin.content.media.batchPartialFailed', {n: failed}))
    }
    ElMessage.success(t('admin.content.media.uploadComplete'))
    await Promise.all([list.reload(), loadFolders()])
  } finally {
    uploading.value = false
  }
}

async function onFilesPicked(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  await doUpload(files)
}

function onDragEnter(): void {
  dragDepth += 1
  dragging.value = true
}

function onDragLeave(): void {
  dragDepth = Math.max(0, dragDepth - 1)
  if (!dragDepth) dragging.value = false
}

function onDrop(event: DragEvent): void {
  dragDepth = 0
  dragging.value = false
  const files = Array.from(event.dataTransfer?.files ?? [])
  if (files.length) void doUpload(files)
}

// ---------------------------------------------------------------- 选中与批量
const selectedIds = ref<number[]>([])
const selectedSet = computed(() => new Set(selectedIds.value))

function isSelected(item: MediaItem): boolean {
  return selectedSet.value.has(item.id)
}

function toggleSelect(item: MediaItem): void {
  const next = new Set(selectedIds.value)
  if (next.has(item.id)) next.delete(item.id)
  else next.add(item.id)
  selectedIds.value = [...next]
}

function onTableSelection(rows: MediaItem[]): void {
  selectedIds.value = rows.map((row) => row.id)
}

function clearSelection(): void {
  selectedIds.value = []
}

function selectAllPage(): void {
  selectedIds.value = list.rows.value.map((row) => row.id)
}

/** 批量更新（设为公开/私有、移动到文件夹）：后端单次请求内逐条处理 */
async function bulkPatch(patch: { is_public?: boolean; folder_id?: number | null }): Promise<void> {
  if (!selectedIds.value.length) {
    ElMessage.warning(t('admin.content.media.selectFirst'))
    return
  }
  const ids = [...selectedIds.value]
  const result = await mediaApi.batchUpdate({ids, ...patch})
  ElMessage.success(t('admin.common.batchDone', {n: result.affected}))
  clearSelection()
  await Promise.all([list.reload(), loadFolders()])
}

const moveDialogVisible = ref(false)
const moveTarget = ref<number | null>(null)

async function submitMove(): Promise<void> {
  moveDialogVisible.value = false
  await bulkPatch({folder_id: moveTarget.value})
}

async function bulkDelete(): Promise<void> {
  if (!selectedIds.value.length) {
    ElMessage.warning(t('admin.content.media.selectFirst'))
    return
  }
  const ids = [...selectedIds.value]
  await list.remove(
    () => mediaApi.batchDelete(ids),
    t('admin.content.media.deleteSelectedConfirm', {n: ids.length}),
    t('admin.common.notice'),
    t('admin.content.media.deleted'),
  )
  clearSelection()
  await loadFolders()
}

// ---------------------------------------------------------------- 详情侧栏
const detailVisible = ref(false)
const detailItem = ref<MediaItem | null>(null)
const detailSaving = ref(false)
const detailForm = reactive({
  description: '',
  alt_text: '',
  category: '',
  tags: [] as string[],
  folder_id: null as number | null,
  is_public: true,
})

function openDetail(item: MediaItem): void {
  detailItem.value = item
  detailForm.description = item.description ?? ''
  detailForm.alt_text = item.alt_text ?? ''
  detailForm.category = item.category ?? ''
  detailForm.tags = splitTags(item.tags)
  detailForm.folder_id = item.folder_id ?? null
  detailForm.is_public = item.is_public ?? true
  detailVisible.value = true
}

async function submitDetail(): Promise<void> {
  if (!detailItem.value) return
  detailSaving.value = true
  try {
    await mediaApi.update(detailItem.value.id, {...detailForm})
    ElMessage.success(t('admin.content.media.saved'))
    detailVisible.value = false
    await Promise.all([list.reload(), loadFolders()])
  } finally {
    detailSaving.value = false
  }
}

async function removeDetail(): Promise<void> {
  if (!detailItem.value) return
  const item = detailItem.value
  await ElMessageBox.confirm(
    t('admin.content.media.deleteConfirm', {name: item.original_filename || item.filename}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await mediaApi.remove(item.id)
  ElMessage.success(t('admin.content.media.deleted'))
  detailVisible.value = false
  await Promise.all([list.reload(), loadFolders()])
}

async function copyLink(url?: string | null): Promise<void> {
  if (!url) return
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.success(t('admin.content.media.linkCopied'))
  } catch {
    ElMessage.warning(t('admin.content.media.copyFailedCopyItManually'))
  }
}

// ---------------------------------------------------------------- 展示辅助
function isImage(item: MediaItem | null): boolean {
  return (item?.mime_type || '').startsWith('image/')
}

function isVideo(item: MediaItem | null): boolean {
  return (item?.mime_type || '').startsWith('video/')
}

function isAudio(item: MediaItem | null): boolean {
  return (item?.mime_type || '').startsWith('audio/')
}

function thumbOf(item: MediaItem): string {
  return item.thumbnail_url || item.file_url || ''
}

function typeIcon(item: MediaItem) {
  if (isImage(item)) return Picture
  if (isVideo(item)) return VideoCamera
  if (isAudio(item)) return Headset
  return Document
}

onMounted(loadFolders)
</script>

<template>
  <AdminPage :desc="$t('admin.content.media.desc')" :title="$t('admin.content.media.mediaLibrary')">
    <template #actions>
      <el-button v-auth="'module_content:media:upload'" :icon="FolderAdd" @click="openFolderDialog()">
        {{ $t('admin.content.media.newFolder') }}
      </el-button>
      <el-button v-auth="'module_content:media:upload'" :icon="Upload" :loading="uploading" type="primary"
                 @click="pickFiles">
        {{ $t('admin.content.media.upload') }}
      </el-button>
    </template>

    <div class="media-layout">
      <!-- 文件夹树 -->
      <aside class="admin-card media-side">
        <div class="media-side__head">{{ $t('admin.content.media.folders') }}</div>
        <ul class="media-side__list">
          <li :class="{active: activeFolderId === undefined}" @click="activeFolderId = undefined">
            <el-icon>
              <View/>
            </el-icon>
            <span>{{ $t('admin.content.media.allMedia') }}</span>
            <span class="media-side__count">{{ list.total.value }}</span>
          </li>
        </ul>
        <el-tree
          v-if="folders.length"
          :current-node-key="activeFolderId"
          :data="folders"
          :expand-on-click-node="false"
          :props="{label: 'name', children: 'children'}"
          highlight-current
          node-key="id"
          @node-click="(node: MediaFolder) => (activeFolderId = node.id)"
        >
          <template #default="{node, data}">
            <span class="media-folder">
              <span class="media-folder__name">{{ data.name }}</span>
              <span class="media-folder__count">{{ data.media_count ?? 0 }}</span>
              <span class="media-folder__ops">
                <el-button :icon="FolderAdd" link size="small" @click.stop="openFolderDialog(undefined, data.id)"/>
                <el-button :icon="Edit" link size="small" @click.stop="openFolderDialog(data as MediaFolder)"/>
                <el-button :icon="Delete" link size="small"
                           @click.stop="openFolderDialog(data as MediaFolder), removeFolder()"/>
              </span>
            </span>
          </template>
        </el-tree>
        <p v-else class="media-side__empty">{{ $t('admin.content.media.folderEmpty') }}</p>
      </aside>

      <!-- 内容区（拖拽上传区） -->
      <section
        class="admin-card media-main"
        @dragenter.prevent="onDragEnter"
        @dragleave.prevent="onDragLeave"
        @dragover.prevent
        @drop.prevent="onDrop"
      >
        <div v-if="dragging" class="media-drop">{{ $t('admin.content.media.dropHint') }}</div>

        <div class="admin-toolbar">
          <el-input
            v-model="list.query.keyword"
            :placeholder="$t('admin.content.media.searchPlaceholder')"
            clearable
            style="width: 200px"
            @keyup.enter="list.search()"
          />
          <el-select v-model="list.query.mime_type" :placeholder="$t('admin.content.media.allTypes')" clearable
                     style="width: 140px">
            <el-option v-for="item in MIME_OPTIONS" :key="item.value" :label="item.label" :value="item.value"/>
          </el-select>
          <el-select v-model="list.query.is_public" :placeholder="$t('admin.content.media.visibility')" clearable
                     style="width: 140px">
            <el-option :label="$t('admin.content.media.publicLabel')" :value="true"/>
            <el-option :label="$t('admin.content.media.privateLabel')" :value="false"/>
          </el-select>
          <el-button :icon="Search" type="primary" @click="list.search()">
            {{ $t('admin.common.search') }}
          </el-button>

          <span class="admin-toolbar__spacer"/>

          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button value="grid">
              <el-icon>
                <Grid/>
              </el-icon>
            </el-radio-button>
            <el-radio-button value="list">
              <el-icon>
                <List/>
              </el-icon>
            </el-radio-button>
          </el-radio-group>
          <span class="admin-toolbar__total">{{ $t('admin.common.totalItems', {n: list.total.value}) }}</span>
        </div>

        <AdminSelectionBar :count="selectedIds.length" @clear="clearSelection">
          <el-button plain @click="moveDialogVisible = true">{{ $t('admin.content.media.moveTo') }}</el-button>
          <el-button v-auth="'module_content:media:upload'" plain
                     @click="bulkPatch({is_public: true})">
            {{ $t('admin.content.media.setPublic') }}
          </el-button>
          <el-button v-auth="'module_content:media:upload'" plain
                     @click="bulkPatch({is_public: false})">
            {{ $t('admin.content.media.setPrivate') }}
          </el-button>
          <el-button v-auth="'module_content:media:delete'" plain type="danger" @click="bulkDelete">
            {{ $t('admin.common.delete') }}
          </el-button>
        </AdminSelectionBar>

        <AdminTableSkeleton v-if="list.loading.value && !list.rows.value.length" :rows="4"/>

        <AdminEmpty
          v-else-if="!list.loading.value && !list.rows.value.length"
          :desc="list.hasFilters.value ? $t('admin.content.media.emptyFiltered') : $t('admin.content.media.emptyDesc')"
          :title="list.hasFilters.value ? $t('admin.content.media.emptyFiltered') : $t('admin.content.media.emptyTitle')"
        >
          <el-button v-auth="'module_content:media:upload'" :icon="Upload" type="primary" @click="pickFiles">
            {{ $t('admin.content.media.upload') }}
          </el-button>
        </AdminEmpty>

        <!-- 网格视图 -->
        <template v-else-if="viewMode === 'grid'">
          <div class="admin-grid media-grid">
            <div
              v-for="item in list.rows.value"
              :key="item.id"
              :class="{selected: isSelected(item)}"
              class="media-card"
              @click="toggleSelect(item)"
              @dblclick="openDetail(item)"
            >
              <div class="media-card__thumb">
                <img v-if="isImage(item) && thumbOf(item)" :alt="item.alt_text || ''" :src="thumbOf(item)"
                     decoding="async" loading="lazy"/>
                <el-icon v-else class="media-card__icon">
                  <component :is="typeIcon(item)"/>
                </el-icon>
                <el-tag v-if="!item.is_public" class="media-card__badge" size="small" type="info">
                  {{ $t('admin.content.media.privateLabel') }}
                </el-tag>
              </div>
              <div class="media-card__meta">
                <span class="media-card__name">{{ item.original_filename || item.filename }}</span>
                <span class="media-card__size">{{ formatFileSize(item.file_size) }}</span>
              </div>
              <div class="media-card__ops">
                <el-button :icon="Edit" link size="small" @click.stop="openDetail(item)"/>
                <el-button :icon="Delete" link size="small" type="danger" @click.stop="openDetail(item)"/>
              </div>
            </div>
          </div>

          <el-pagination
            :current-page="list.page.value"
            :page-size="list.pageSize.value"
            :page-sizes="[12, 24, 48, 96]"
            :total="list.total.value"
            background
            class="admin-pagination"
            layout="total, sizes, prev, pager, next"
            @current-change="list.onPageChange"
            @size-change="list.onSizeChange"
          />
        </template>

        <!-- 列表视图 -->
        <template v-else>
          <div class="media-listbar">
            <el-button link type="primary" @click="selectAllPage">
              {{ $t('admin.content.media.selectAllPage') }}
            </el-button>
          </div>
          <el-table :data="list.rows.value" row-key="id" @selection-change="onTableSelection">
            <el-table-column type="selection" width="46"/>
            <el-table-column width="72">
              <template #default="{row}">
                <img v-if="isImage(row) && thumbOf(row)" :src="thumbOf(row)" alt="" class="admin-thumb" decoding="async"
                     loading="lazy"/>
                <el-icon v-else class="media-card__icon">
                  <component :is="typeIcon(row)"/>
                </el-icon>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.content.media.filename')" min-width="220">
              <template #default="{row}">
                <div class="admin-cell-title">{{ row.original_filename || row.filename }}</div>
                <div class="admin-cell-sub">{{ row.mime_type || '-' }}</div>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.content.media.size')" width="110">
              <template #default="{row}">{{ formatFileSize(row.file_size) }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.content.media.dimensions')" width="120">
              <template #default="{row}">
                {{ row.width && row.height ? `${row.width}×${row.height}` : '-' }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.content.media.visibility')" width="100">
              <template #default="{row}">
                <el-tag :type="row.is_public ? 'success' : 'info'" size="small">
                  {{ row.is_public ? $t('admin.content.media.publicLabel') : $t('admin.content.media.privateLabel') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.content.media.uploadTime')" width="170">
              <template #default="{row}">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="170">
              <template #default="{row}">
                <el-button :icon="Edit" link type="primary" @click="openDetail(row as MediaItem)">
                  {{ $t('admin.common.edit') }}
                </el-button>
                <el-button :icon="Delete" link type="danger" @click="openDetail(row as MediaItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            :current-page="list.page.value"
            :page-size="list.pageSize.value"
            :page-sizes="[20, 50, 100]"
            :total="list.total.value"
            background
            class="admin-pagination"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="list.onPageChange"
            @size-change="list.onSizeChange"
          />
        </template>
      </section>
    </div>

    <input ref="fileInput" class="media-file-input" multiple type="file" @change="onFilesPicked"/>

    <!-- 详情侧栏 -->
    <AdminFormDrawer
      v-model="detailVisible"
      :loading="detailSaving"
      :size="600"
      :title="detailItem?.original_filename || detailItem?.filename || ''"
      @confirm="submitDetail"
    >
      <template #footer-extra>
        <el-button v-auth="'module_content:media:delete'" plain type="danger" @click="removeDetail">
          {{ $t('admin.common.delete') }}
        </el-button>
      </template>

      <div v-if="detailItem" class="media-detail">
        <div class="media-detail__preview">
          <img v-if="isImage(detailItem) && thumbOf(detailItem)" :alt="detailItem.alt_text || ''"
               :src="thumbOf(detailItem)" decoding="async"/>
          <video v-else-if="isVideo(detailItem) && detailItem.file_url" :src="detailItem.file_url" controls/>
          <audio v-else-if="isAudio(detailItem) && detailItem.file_url" :src="detailItem.file_url" controls/>
          <el-icon v-else class="media-detail__icon">
            <component :is="typeIcon(detailItem)"/>
          </el-icon>
        </div>

        <el-descriptions :column="2" border size="small">
          <el-descriptions-item :label="$t('admin.content.media.size')">
            {{ formatFileSize(detailItem.file_size) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.content.media.dimensions')">
            {{ detailItem.width && detailItem.height ? `${detailItem.width}×${detailItem.height}` : '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.content.media.fileType')">
            {{ detailItem.mime_type || '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.content.media.downloadCount')">
            {{ detailItem.download_count ?? 0 }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.content.media.uploadTime')" :span="2">
            {{ formatDateTime(detailItem.created_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="media-detail__url">
          <el-input :model-value="detailItem.file_url || ''" readonly>
            <template #append>
              <el-button :icon="View" @click="copyLink(detailItem.file_url)">
                {{ $t('admin.content.media.copyLink') }}
              </el-button>
            </template>
          </el-input>
        </div>

        <el-form label-position="top">
          <el-form-item :label="$t('admin.common.description')">
            <el-input v-model="detailForm.description" :rows="2" type="textarea"/>
          </el-form-item>
          <el-form-item :label="$t('admin.content.media.altText')">
            <el-input v-model="detailForm.alt_text"
                      :placeholder="$t('admin.content.media.forAccessibilityAndSeo')"/>
          </el-form-item>
          <el-form-item :label="$t('admin.content.media.mediaCategory')">
            <el-input v-model="detailForm.category"/>
          </el-form-item>
          <el-form-item label="Tags">
            <el-select v-model="detailForm.tags" allow-create default-first-option filterable multiple
                       style="width: 100%"/>
          </el-form-item>
          <el-form-item :label="$t('admin.content.media.folder')">
            <el-select v-model="detailForm.folder_id" :placeholder="$t('admin.content.media.noFolder')" clearable
                       style="width: 100%">
              <el-option v-for="item in folderOptions" :key="item.id" :label="item.label" :value="item.id"/>
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('admin.content.media.publicLabel')">
            <el-switch v-model="detailForm.is_public"/>
          </el-form-item>
        </el-form>
      </div>
    </AdminFormDrawer>

    <!-- 移动到文件夹 -->
    <el-dialog v-model="moveDialogVisible" :title="$t('admin.content.media.moveTo')" width="420px">
      <el-select v-model="moveTarget" :placeholder="$t('admin.content.media.noFolder')" clearable
                 style="width: 100%">
        <el-option v-for="item in folderOptions" :key="item.id" :label="item.label" :value="item.id"/>
      </el-select>
      <template #footer>
        <el-button @click="moveDialogVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button type="primary" @click="submitMove">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- 新建 / 编辑文件夹 -->
    <el-dialog
      v-model="folderDialogVisible"
      :title="folderForm.id ? $t('admin.content.media.renameFolder') : $t('admin.content.media.newFolder')"
      width="420px"
    >
      <el-form label-position="top">
        <el-form-item :label="$t('admin.content.media.folderName')" required>
          <el-input v-model="folderForm.name" maxlength="60"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.media.folder')">
          <el-select v-model="folderForm.parent_id" :placeholder="$t('admin.content.media.noFolder')" clearable
                     style="width: 100%">
            <el-option v-for="item in folderOptions" :key="item.id" :label="item.label" :value="item.id"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="folderForm.description" :rows="2" type="textarea"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button v-if="folderForm.id" plain type="danger" @click="removeFolder">
          {{ $t('admin.common.delete') }}
        </el-button>
        <el-button @click="folderDialogVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="folderSaving" type="primary" @click="submitFolder">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-dialog>
  </AdminPage>
</template>

<style scoped>
.media-layout {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: var(--admin-gap);
  align-items: start;
}

@media (max-width: 1100px) {
  .media-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}

.media-side {
  padding: var(--admin-gap-sm) 0;
}

.media-side__head {
  padding: 0 var(--admin-gap) var(--admin-gap-sm);
  font-weight: 600;
  color: var(--admin-fg);
}

.media-side__list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.media-side__list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px var(--admin-gap);
  cursor: pointer;
  font-size: 13.5px;
  color: var(--admin-fg-muted);
}

.media-side__list li.active,
.media-side__list li:hover {
  background: var(--admin-surface-hover);
  color: var(--admin-fg);
}

.media-side__count,
.media-folder__count {
  margin-left: auto;
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

.media-side__empty {
  margin: 0;
  padding: 0 var(--admin-gap);
  font-size: 12.5px;
  color: var(--admin-fg-subtle);
}

.media-folder {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  font-size: 13.5px;
}

.media-folder__ops {
  margin-left: auto;
  display: none;
}

.media-folder:hover .media-folder__ops {
  display: inline-flex;
}

.media-main {
  position: relative;
  padding: var(--admin-gap-lg);
  min-height: 420px;
}

.media-drop {
  position: absolute;
  inset: 8px;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed var(--admin-primary);
  border-radius: var(--admin-radius-lg);
  background: color-mix(in oklab, var(--admin-primary) 8%, var(--admin-surface));
  color: var(--admin-primary);
  font-weight: 600;
  pointer-events: none;
}

.media-grid {
  margin-bottom: var(--admin-gap);
}

.media-card {
  position: relative;
  border: 1px solid var(--admin-line);
  border-radius: var(--admin-radius);
  overflow: hidden;
  cursor: pointer;
  background: var(--admin-surface);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.media-card:hover {
  border-color: var(--admin-line-strong);
  box-shadow: var(--admin-shadow-card);
}

.media-card.selected {
  border-color: var(--admin-primary);
  box-shadow: 0 0 0 2px color-mix(in oklab, var(--admin-primary) 25%, transparent);
}

.media-card__thumb {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 130px;
  background: var(--admin-surface-soft);
}

.media-card__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.media-card__icon {
  font-size: 30px;
  color: var(--admin-fg-subtle);
}

.media-card__badge {
  position: absolute;
  top: 6px;
  right: 6px;
}

.media-card__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
}

.media-card__name {
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12.5px;
  color: var(--admin-fg);
}

.media-card__size {
  font-size: 11.5px;
  color: var(--admin-fg-subtle);
}

.media-card__ops {
  position: absolute;
  top: 6px;
  left: 6px;
  display: none;
  gap: 2px;
  padding: 2px 4px;
  border-radius: var(--admin-radius-sm);
  background: color-mix(in oklab, var(--admin-surface) 88%, transparent);
}

.media-card:hover .media-card__ops {
  display: inline-flex;
}

.media-listbar {
  margin-bottom: 4px;
}

.media-detail {
  display: flex;
  flex-direction: column;
  gap: var(--admin-gap);
}

.media-detail__preview {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 180px;
  padding: var(--admin-gap-sm);
  border: 1px solid var(--admin-line);
  border-radius: var(--admin-radius);
  background: var(--admin-surface-soft);
}

.media-detail__preview img,
.media-detail__preview video {
  max-width: 100%;
  max-height: 260px;
  border-radius: var(--admin-radius-sm);
}

.media-detail__icon {
  font-size: 48px;
  color: var(--admin-fg-subtle);
}

.media-file-input {
  display: none;
}
</style>
