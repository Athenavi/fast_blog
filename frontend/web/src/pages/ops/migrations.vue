<script lang="ts" setup>
/**
 * 数据迁移任务（T5-11 批次 2；真实导入批次 18）
 *
 * 对齐 v3 `/ops/migration`：任务档案 + 启动/取消 + 日志。
 * **start 会真的导入** `config.file_path` 指向的 WordPress WXR（进度与日志实时可查）；
 * 平台没有导入器 / 文件不存在 / 文件过大都会直接报错，不会留下"看着在跑"的假任务。
 */
import {Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {migrationApi, type MigrationLogItem, type MigrationTaskItem} from '@/api'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ops.migration.title',
  permission: 'module_ops:migration:view',
})

const {t} = useI18n()

const statusTag = (s?: string | null) =>
  s === 'running' ? 'warning' : s === 'completed' ? 'success' : s === 'failed' ? 'danger' : 'info'
const statusLabel = (s?: string | null) =>
  s === 'running' ? t('admin.ops.migration.statusRunning')
    : s === 'completed' ? t('admin.ops.migration.statusCompleted')
      : s === 'failed' ? t('admin.ops.migration.statusFailed')
        : s === 'cancelled' ? t('admin.ops.migration.statusCancelled')
          : t('admin.ops.migration.statusPending')

const migrationState = useAdminList<MigrationTaskItem, { keyword?: string; status?: string }>({

  fetcher: (params) => migrationApi.list(params),
  defaultQuery: {keyword: '', status: ''},
  syncUrl: true,
})

// 模板沿用原有变量名：映射为同名 ref / 函数，避免整页重写带来的回归风险
const list = migrationState.rows
const loading = migrationState.loading
const total = migrationState.total
const page = migrationState.page
const pageSize = migrationState.pageSize
const query = migrationState.query
const search = migrationState.search
const reset = migrationState.reset
const load = migrationState.reload
const onPageChange = migrationState.onPageChange
const onSizeChange = migrationState.onSizeChange
const failed = migrationState.failed

// ---- 新建 / 编辑 ----
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({
  task_name: '', source_platform: 'wordpress', config_text: '', total_items: 0,
})

const formTitle = computed(() =>
  editingId.value ? t('admin.ops.migration.editTask') : t('admin.ops.migration.createTask'))

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    task_name: '',
    source_platform: 'wordpress',
    config_text: '{\n  "file_path": ""\n}',
    total_items: 0
  })
  formVisible.value = true
}

function openEdit(row: MigrationTaskItem) {
  editingId.value = row.id
  Object.assign(form, {
    task_name: row.task_name || '',
    source_platform: row.source_platform || 'wordpress',
    config_text: row.config ? JSON.stringify(row.config, null, 2) : '{\n  \n}',
    total_items: row.total_items ?? 0,
  })
  formVisible.value = true
}

async function submitForm() {
  if (!form.task_name.trim()) {
    ElMessage.warning(t('admin.ops.migration.nameRequired'))
    return
  }
  let config = null
  if (form.config_text.trim()) {
    try {
      config = JSON.parse(form.config_text)
    } catch {
      ElMessage.warning(t('admin.ops.migration.configInvalid'))
      return
    }
  }
  saving.value = true
  try {
    if (editingId.value) {
      await migrationApi.update(editingId.value, {
        task_name: form.task_name.trim(),
        config,
        total_items: form.total_items,
      })
    } else {
      await migrationApi.create({
        task_name: form.task_name.trim(),
        source_platform: form.source_platform,
        config,
        total_items: form.total_items,
      })
    }
    ElMessage.success(t('admin.common.save'))
    formVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function startTask(row: MigrationTaskItem) {
  await migrationApi.start(row.id)
  ElMessage.success(t('admin.ops.migration.started'))
  await load()
}

async function cancelTask(row: MigrationTaskItem) {
  await migrationApi.cancel(row.id)
  ElMessage.success(t('admin.ops.migration.cancelled'))
  await load()
}

async function onDelete(row: MigrationTaskItem) {
  await ElMessageBox.confirm(t('admin.ops.migration.deleteConfirm'), t('admin.common.notice'), {type: 'warning'})
  await migrationApi.remove(row.id)
  ElMessage.success(t('admin.common.delete'))
  await load()
}

// ---- 日志 ----
const logsVisible = ref(false)
const logsTaskId = ref<number | null>(null)
const logsTitle = ref('')
const logList = ref<MigrationLogItem[]>([])
const logsLoading = ref(false)

async function openLogs(row: MigrationTaskItem) {
  logsTaskId.value = row.id
  logsTitle.value = `${t('admin.ops.migration.logs')} - ${row.task_name}`
  logsVisible.value = true
  logsLoading.value = true
  try {
    const result = await migrationApi.logs(row.id, {page: 1, page_size: 100})
    logList.value = result.items
  } finally {
    logsLoading.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-alert
        :closable="false" :title="$t('admin.ops.migration.engineHint')"
        class="mb-3"
        type="info"
      />
      <el-form :inline="true" @submit.prevent="search()">
        <el-form-item :label="$t('admin.system.sensitiveWord.keyword')">
          <el-input v-model="query.keyword" clearable style="width: 180px" @keyup.enter="search()"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="query.status" clearable style="width: 140px">
            <el-option :label="$t('admin.ops.migration.statusPending')" value="pending"/>
            <el-option :label="$t('admin.ops.migration.statusRunning')" value="running"/>
            <el-option :label="$t('admin.ops.migration.statusCompleted')" value="completed"/>
            <el-option :label="$t('admin.ops.migration.statusFailed')" value="failed"/>
            <el-option :label="$t('admin.ops.migration.statusCancelled')" value="cancelled"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="search()">{{ $t('admin.common.search') }}</el-button>
          <el-button :icon="Refresh" @click="reset()">{{ $t('admin.common.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <div class="table-toolbar">
        <el-button v-auth="'module_ops:migration:create'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.ops.migration.createTask') }}
        </el-button>
        <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: total}) }}</span>
      </div>

      <AdminTableSkeleton v-if="loading && !list.length" :rows="5"/>

      <AdminEmpty
        v-else-if="!loading && !list.length"
        :title="failed ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
        :variant="failed ? 'error' : 'default'"
      >
        <el-button v-if="failed" :icon="Refresh" @click="load()">
          {{ $t('admin.common.retry') }}
        </el-button>
      </AdminEmpty>
      <el-table v-else v-loading="loading" :data="list" border stripe>
        <el-table-column :label="$t('admin.common.name')" min-width="160" prop="task_name"/>
        <el-table-column :label="$t('admin.ops.migration.platform')" prop="source_platform" width="120"/>
        <el-table-column :label="$t('admin.common.status')" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag((row as MigrationTaskItem).status)" size="small">
              {{ statusLabel((row as MigrationTaskItem).status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.ops.migration.progress')" width="170">
          <template #default="{ row }">
            <el-progress
              :percentage="(row as MigrationTaskItem).total_items ? Math.round((row as MigrationTaskItem).migrated_items / (row as MigrationTaskItem).total_items * 100) : 0"
            />
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.ops.migration.startedAt')" prop="started_at" width="170"/>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="280">
          <template #default="{ row }">
            <el-button link type="primary" @click="openLogs(row as MigrationTaskItem)">
              {{ $t('admin.ops.migration.logs') }}
            </el-button>
            <el-button
              v-if="(row as MigrationTaskItem).status === 'pending'"
              v-auth="'module_ops:migration:edit'" link type="success" @click="startTask(row as MigrationTaskItem)"
            >
              {{ $t('admin.ops.migration.start') }}
            </el-button>
            <el-button
              v-if="(row as MigrationTaskItem).status === 'running'"
              v-auth="'module_ops:migration:edit'" link type="warning" @click="cancelTask(row as MigrationTaskItem)"
            >
              {{ $t('admin.ops.migration.cancel') }}
            </el-button>
            <el-button v-auth="'module_ops:migration:edit'" link type="primary"
                       @click="openEdit(row as MigrationTaskItem)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button v-auth="'module_ops:migration:delete'" link type="danger"
                       @click="onDelete(row as MigrationTaskItem)">
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        :current-page="page" :page-size="pageSize" :total="total"
        background class="table-pagination" layout="total, sizes, prev, pager, next"
        @current-change="onPageChange" @size-change="onSizeChange"
      />
    </el-card>

    <!-- 任务编辑 -->
    <el-drawer v-model="formVisible" :title="formTitle" destroy-on-close size="480px">
      <el-form :model="form" label-width="100px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="form.task_name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.migration.platform')" required>
          <el-select v-model="form.source_platform" :disabled="!!editingId" style="width: 100%">
            <el-option label="WordPress" value="wordpress"/>
            <el-option label="Jekyll" value="jekyll"/>
            <el-option label="Hexo" value="hexo"/>
            <el-option label="Typecho" value="typecho"/>
            <el-option label="RSS" value="rss"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.migration.totalItems')">
          <el-input-number v-model="form.total_items" :min="0" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.migration.configLabel')">
          <el-input v-model="form.config_text" :autosize="{minRows: 6, maxRows: 14}" type="textarea"/>
          <div class="config-hint">{{ $t('admin.ops.migration.filePathHint') }}</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-drawer>

    <!-- 日志 -->
    <el-dialog v-model="logsVisible" :title="logsTitle" destroy-on-close width="680px">
      <el-table v-loading="logsLoading" :data="logList" border max-height="420" size="small">
        <el-table-column :label="$t('admin.content.approval.createdAt')" prop="created_at" width="170"/>
        <el-table-column :label="$t('admin.ops.migration.logLevel')" prop="log_level" width="90"/>
        <el-table-column :label="$t('admin.common.description')" min-width="260" prop="message" show-overflow-tooltip/>
      </el-table>
    </el-dialog>
  </div>
</template>

<style scoped>
.config-hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
