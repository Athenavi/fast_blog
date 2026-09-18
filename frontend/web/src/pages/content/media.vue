<script lang="ts" setup>
const {t} = useI18n()
/**
 * 媒体库（上传 / 列表 / 编辑元信息 / 删除）
 *
 * 对齐 v3：`/content/media` 列表、`/upload` 上传（multipart，字段名 `files`）、
 * `/{id}` 更新与删除、`/batch/delete` 批量删除。
 */
import {Delete, Edit, Refresh, Upload} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {reactive, ref} from 'vue'

import {mediaApi, type MediaItem} from '@/api'
import {formatDateTime, formatFileSize, splitTags} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: t('admin.content.media.mediaLibrary'),
  permission: 'module_content:media:view',
})

const MIME_OPTIONS = [
  {label: t('admin.content.media.image'), value: 'image/'},
  {label: t('admin.content.media.video'), value: 'video/'},
  {label: t('admin.content.media.audio'), value: 'audio/'},
  {label: t('admin.content.media.document'), value: 'application/'},
]

const loading = ref(false)
const list = ref<MediaItem[]>([])
const total = ref(0)
const selection = ref<MediaItem[]>([])

const query = reactive({
  page: 1,
  page_size: 20,
  mime_type: undefined as string | undefined,
  category: '',
})

async function loadList(): Promise<void> {
  loading.value = true
  try {
    const data = await mediaApi.list({
      page: query.page,
      page_size: query.page_size,
      ...(query.mime_type ? {mime_type: query.mime_type} : {}),
      ...(query.category ? {category: query.category} : {}),
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onSearch(): void {
  query.page = 1
  loadList()
}

function onSelectionChange(rows: MediaItem[]): void {
  selection.value = rows
}

function isImage(row: MediaItem): boolean {
  return (row.mime_type || '').startsWith('image/')
}

// ---------------------------------------------------------------- 预览
/** 后台全类型预览（AdminMediaPreview）：按 id 定位，支持列表内左右切换 */
const previewOpen = ref(false)
const previewId = ref<number | null>(null)

function openPreview(row: MediaItem): void {
  previewId.value = row.id
  previewOpen.value = true
}

// ---------------------------------------------------------------- 上传
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const progress = ref('')

function pickFiles(): void {
  fileInput.value?.click()
}

async function onFilesPicked(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  if (!files.length) return

  uploading.value = true
  progress.value = `正在上传 ${files.length} 个文件…`
  try {
    await mediaApi.upload(files)
    ElMessage.success(t('admin.content.media.uploadComplete'))
    await loadList()
  } finally {
    uploading.value = false
    progress.value = ''
    // 允许重复选择同一文件
    input.value = ''
  }
}

// ---------------------------------------------------------------- 编辑元信息
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({description: '', alt_text: '', category: '', tags: ''})

function openEdit(row: MediaItem): void {
  editingId.value = row.id
  form.description = row.description ?? ''
  form.alt_text = row.alt_text ?? ''
  form.category = row.category ?? ''
  form.tags = splitTags(row.tags).join(', ')
  dialogVisible.value = true
}

async function submitEdit(): Promise<void> {
  saving.value = true
  try {
    await mediaApi.update(editingId.value as number, {
      description: form.description,
      alt_text: form.alt_text,
      category: form.category,
      tags: form.tags
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    })
    ElMessage.success(t('admin.content.media.saved'))
    dialogVisible.value = false
    await loadList()
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------- 删除
async function removeRow(row: MediaItem): Promise<void> {
  await ElMessageBox.confirm(`确定删除「${row.original_filename || row.filename}」吗？`, t('admin.common.notice'), {
    type: 'warning',
  })
  await mediaApi.remove(row.id)
  ElMessage.success(t('admin.content.media.deleted'))
  await loadList()
}

async function removeSelected(): Promise<void> {
  if (!selection.value.length) {
    ElMessage.warning(t('admin.content.media.selectFilesToDeleteFirst'))
    return
  }
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 个文件吗？`, t('admin.common.notice'), {
    type: 'warning',
  })
  await mediaApi.batchDelete(selection.value.map((item) => item.id))
  ElMessage.success(t('admin.content.media.deleted'))
  await loadList()
}

function copyUrl(row: MediaItem): void {
  if (!row.file_url) return
  navigator.clipboard
    ?.writeText(row.file_url)
    .then(() => ElMessage.success(t('admin.content.media.linkCopied')))
    .catch(() => ElMessage.warning(t('admin.content.media.copyFailedCopyItManually')))
}

onMounted(loadList)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-form :inline="true" @submit.prevent>
        <el-form-item :label="$t('admin.cache.level')">
          <el-select v-model="query.mime_type" :placeholder="$t('admin.common.all')" clearable style="width: 130px">
            <el-option v-for="item in MIME_OPTIONS" :key="item.value" :label="item.label" :value="item.value"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('article.category')">
          <el-input v-model="query.category" :placeholder="$t('admin.content.media.mediaCategory')" clearable
                    style="width: 160px"
                    @keyup.enter="onSearch"/>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Refresh" type="primary" @click="onSearch">{{ $t('admin.common.search') }}</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar">
        <el-button v-auth="'module_content:media:upload'" :icon="Upload" :loading="uploading" type="primary"
                   @click="pickFiles">
          上传文件
        </el-button>
        <el-button
          v-auth="'module_content:media:delete'"
          :disabled="!selection.length"
          :icon="Delete"
          plain
          type="danger"
          @click="removeSelected"
        >
          批量删除
        </el-button>
        <span v-if="progress" class="progress">{{ progress }}</span>
        <el-button :icon="Refresh" circle class="ml-auto" @click="loadList"/>
      </div>

      <!-- 原生多选上传：避免 Element Plus upload 的额外状态管理 -->
      <input ref="fileInput" hidden multiple type="file" @change="onFilesPicked">

      <el-table v-loading="loading" :data="list" row-key="id" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="46"/>
        <el-table-column :label="$t('admin.content.media.preview')" width="90">
          <template #default="{row}">
            <span
              class="preview-cell"
              role="button"
              tabindex="0"
              :title="$t('admin.content.media.clickToPreview')"
              @click="openPreview(row)"
              @keyup.enter="openPreview(row)"
            >
              <img v-if="isImage(row)" :alt="row.alt_text || ''" :src="row.file_url || ''" class="thumb">
              <span v-else class="file-badge">{{ (row.file_type || 'file').toUpperCase() }}</span>
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.content.media.filename')" min-width="220">
          <template #default="{row}">
            <span class="name">{{ row.original_filename || row.filename }}</span>
            <el-button v-if="row.file_url" class="copy" link type="primary" @click="copyUrl(row)">
              {{ $t('admin.content.media.copyLink') }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.cache.level')" width="120">
          <template #default="{row}">{{ row.mime_type || '-' }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.content.media.size')" width="100">
          <template #default="{row}">{{ formatFileSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.content.media.dimensions')" width="110">
          <template #default="{row}">
            <span v-if="row.width && row.height">{{ row.width }}×{{ row.height }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.setting.publicLabel')" width="80">
          <template #default="{row}">
            <el-tag :type="row.is_public ? 'success' : 'info'" size="small">
              {{ row.is_public ? t('admin.common.yes') : t('admin.common.no') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.content.media.uploadTime')" width="170">
          <template #default="{row}">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
          <template #default="{row}">
            <el-button v-auth="'module_content:media:upload'" :icon="Edit" link type="primary" @click="openEdit(row)">
              编辑
            </el-button>
            <el-button v-auth="'module_content:media:delete'" :icon="Delete" link type="danger" @click="removeRow(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :page-sizes="[20, 50, 100]"
        :total="total"
        class="pagination"
        layout="total, sizes, prev, pager, next"
        @current-change="loadList"
        @size-change="onSearch"
      />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="$t('admin.content.media.editMediaInformation')" destroy-on-close
               width="560px">
      <el-form :model="form" label-width="90px">
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="form.description" maxlength="255" show-word-limit/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.media.altText')">
          <el-input v-model="form.alt_text" :placeholder="$t('admin.content.media.forAccessibilityAndSeo')"
                    maxlength="255" show-word-limit/>
        </el-form-item>
        <el-form-item :label="$t('article.category')">
          <el-input v-model="form.category" maxlength="100"/>
        </el-form-item>
        <el-form-item :label="$t('article.tags')">
          <el-input v-model="form.tags" :placeholder="$t('admin.content.media.separateWithCommas')"/>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitEdit">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- 全类型预览（图片/视频/音频/PDF/文本） -->
    <AdminMediaPreview
      :active-id="previewId"
      :files="list"
      :open="previewOpen"
      @close="previewOpen = false"
      @edit="openEdit"
      @navigate="previewId = $event.id"
    />
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.ml-auto {
  margin-left: auto;
}

.progress {
  font-size: 13px;
  color: #909399;
}

.preview-cell {
  display: inline-flex;
  cursor: zoom-in;
}

.thumb {
  width: 56px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
  background: #f5f7fa;
}

.file-badge {
  display: inline-block;
  padding: 2px 6px;
  font-size: 11px;
  color: #606266;
  background: #f5f7fa;
  border-radius: 4px;
}

.name {
  font-weight: 500;
}

.copy {
  margin-left: 8px;
  font-weight: 400;
}

.pagination {
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
