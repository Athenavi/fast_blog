<script lang="ts" setup>
const {t} = useI18n()
/**
 * 备份与还原
 *
 * 对齐 v3 `/ops/backup`：备份列表、按类型创建（数据库/文件/完整/**增量/差异**）、
 * 还原（增量/差异走**恢复链**：基准 → 依次覆盖）、**校验**（真读文件）、
 * 删除、按天清理、容量统计、定时策略。
 *
 * ⚠️ 还原会覆盖当前数据，因此需要二次确认并单独使用 restore 权限；
 * 增量/差异备份不能单独还原，会先拉恢复链并在确认框里列出每一步。
 * 样式统一使用 Element Plus 的 CSS 变量。
 */
import {CircleCheck, Connection, Delete, Download, Refresh, Upload} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {h, reactive, ref} from 'vue'

import {
  backupApi,
  type BackupChainItem,
  type BackupChainPlan,
  type BackupItem,
  type BackupSchedule,
  type BackupVerifyResult,
} from '@/api'
import {formatDateTime, formatFileSize} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ops.backup.backups',
  permission: 'module_ops:backup:view',
})

const TYPE_LABELS: Record<string, string> = {
  database: t('admin.ops.backup.database'),
  files: t('admin.ops.backup.files'),
  full: t('admin.ops.backup.full'),
  incremental: t('admin.ops.backup.incremental'),
  differential: t('admin.ops.backup.differential'),
}

/** 增量 / 差异备份不能单独还原，要走恢复链 */
function isChainBackup(row: BackupItem | BackupChainItem): boolean {
  const kind = row.type || (row as BackupItem).backup_type || ''
  return kind === 'incremental' || kind === 'differential'
}

const loading = ref(false)
const list = ref<BackupItem[]>([])
const total = ref(0)
const stats = ref<Record<string, unknown> | null>(null)
const creating = ref(false)

const query = reactive({page: 1, page_size: 20, backup_type: ''})

async function loadList(): Promise<void> {
  loading.value = true
  try {
    const data = await backupApi.list({
      limit: 100,
      ...(query.backup_type ? {backup_type: query.backup_type} : {}),
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadStats(): Promise<void> {
  try {
    stats.value = await backupApi.stats()
  } catch {
    stats.value = null
  }
}

// ---------------------------------------------------------------- 创建
async function createBackup(kind: 'database' | 'files' | 'full'): Promise<void> {
  const label = TYPE_LABELS[kind]
  await ElMessageBox.confirm(t('admin.ops.backup.createConfirm', {type: label}), t('admin.common.notice'), {type: 'info'})
  creating.value = true
  try {
    if (kind === 'database') await backupApi.createDatabase('database')
    else if (kind === 'files') await backupApi.createFiles()
    else await backupApi.createFull()
    ElMessage.success(t('admin.ops.backup.backupStarted', {type: label}))
    await Promise.all([loadList(), loadStats()])
  } finally {
    creating.value = false
  }
}

/** 增量 / 差异备份：相对基准的**变化表数据快照**（没变化时后端会跳过并如实说明） */
async function createIncremental(differential: boolean): Promise<void> {
  const label = TYPE_LABELS[differential ? 'differential' : 'incremental']
  await ElMessageBox.confirm(
    t('admin.ops.backup.incrementalConfirm', {type: label}),
    t('admin.common.notice'),
    {type: 'info'},
  )
  creating.value = true
  try {
    const result = await backupApi.createIncremental({differential})
    if (result.skipped) {
      ElMessage.info(t('admin.ops.backup.incrementalSkipped'))
    } else {
      ElMessage.success(
        t('admin.ops.backup.incrementalDone', {
          type: label,
          count: (result.changed_tables || []).length,
        }),
      )
    }
    await Promise.all([loadList(), loadStats()])
  } finally {
    creating.value = false
  }
}

// ---------------------------------------------------------------- 还原 / 删除 / 清理
async function restore(row: BackupItem): Promise<void> {
  const file = row.filename || row.path || ''
  if (!file) {
    ElMessage.warning(t('admin.ops.backup.thisBackupHasNoFilenameAndCannotBeRestored'))
    return
  }
  if (isChainBackup(row)) {
    await restoreWithChain(file)
    return
  }
  await ElMessageBox.confirm(
    t('admin.ops.backup.restoreConfirm', {file}),
    t('admin.ops.backup.dangerousOperation'),
    {type: 'error', confirmButtonText: t('admin.ops.backup.confirmRestore'), confirmButtonClass: 'el-button--danger'},
  )
  await backupApi.restore(file, row.backup_type || row.type || 'database')
  ElMessage.success(t('admin.ops.backup.restoreCommandSubmitted'))
}

/** 增量 / 差异备份：先拉恢复链，把每一步列在确认框里，再按链还原 */
async function restoreWithChain(file: string): Promise<void> {
  chainLoading.value = true
  let plan: BackupChainPlan | null = null
  try {
    plan = await backupApi.chain(file)
  } finally {
    chainLoading.value = false
  }
  if (!plan || !plan.items?.length) {
    ElMessage.warning(t('admin.ops.backup.chainEmpty'))
    return
  }
  const message = h('div', [
    h('p', t('admin.ops.backup.chainRestoreConfirm', {count: plan.length})),
    h(
      'ol',
      {style: 'margin: 6px 0 0 18px; padding: 0'},
      plan.items.map((item) => h('li', `${item.filename} · ${typeLabel(item)}`)),
    ),
  ])
  await ElMessageBox.confirm(message, t('admin.ops.backup.dangerousOperation'), {
    type: 'error',
    confirmButtonText: t('admin.ops.backup.confirmRestore'),
    confirmButtonClass: 'el-button--danger',
  })
  await backupApi.restoreChain(file)
  ElMessage.success(t('admin.ops.backup.chainRestoreDone'))
}

// ---------------------------------------------------------------- 校验 / 恢复链预览
const verifyVisible = ref(false)
const verifyLoading = ref(false)
const verifyResult = ref<BackupVerifyResult | null>(null)

/** 校验备份完整性（后端真读文件：sha256 / 归档可读 / pg_restore --list） */
async function verify(row: BackupItem): Promise<void> {
  const file = row.filename || row.path || ''
  if (!file) return
  verifyResult.value = null
  verifyVisible.value = true
  verifyLoading.value = true
  try {
    verifyResult.value = await backupApi.verify(file)
  } finally {
    verifyLoading.value = false
  }
}

const chainVisible = ref(false)
const chainLoading = ref(false)
const chainItems = ref<BackupChainItem[]>([])

/** 恢复链预览：这个增量要挂在哪些备份后面 */
async function openChain(row: BackupItem): Promise<void> {
  const file = row.filename || row.path || ''
  if (!file) return
  chainItems.value = []
  chainVisible.value = true
  chainLoading.value = true
  try {
    const plan = await backupApi.chain(file)
    chainItems.value = plan.items
  } finally {
    chainLoading.value = false
  }
}

async function removeRow(row: BackupItem): Promise<void> {
  const path = row.path || row.filename || ''
  if (!path) return
  await ElMessageBox.confirm(t('admin.ops.backup.deleteConfirm', {name: row.filename || path}), t('admin.common.notice'), {type: 'warning'})
  await backupApi.remove(path)
  ElMessage.success(t('admin.ops.backup.deleted'))
  await Promise.all([loadList(), loadStats()])
}

async function cleanup(): Promise<void> {
  const input = await ElMessageBox.prompt(t('admin.ops.backup.howManyDaysOfBackupsShouldBeKeptOlderBackupsWillBeDeleted'), t('admin.ops.backup.cleanBackups'), {
    inputValue: '30',
    inputPattern: /^\d+$/,
    inputErrorMessage: t('admin.ops.backup.enterAPositiveInteger'),
    type: 'warning',
  })
  await backupApi.cleanup(Number(input.value))
  ElMessage.success(t('admin.ops.backup.cleanupComplete'))
  await Promise.all([loadList(), loadStats()])
}

// ---------------------------------------------------------------- 定时策略
const schedule = ref<BackupSchedule | null>(null)
const scheduleSaving = ref(false)

async function loadSchedule(): Promise<void> {
  try {
    schedule.value = await backupApi.schedule()
  } catch {
    schedule.value = null
  }
}

async function saveSchedule(): Promise<void> {
  if (!schedule.value) return
  scheduleSaving.value = true
  try {
    await backupApi.updateSchedule({
      enabled: schedule.value.enabled,
      schedule: schedule.value.schedule,
      retention_days: schedule.value.retention_days,
      compress: schedule.value.compress,
      backup_database: schedule.value.backup_database,
      backup_files: schedule.value.backup_files,
    })
    ElMessage.success(t('admin.ops.backup.scheduleSaved'))
  } finally {
    scheduleSaving.value = false
  }
}

function typeLabel(row: BackupItem | BackupChainItem): string {
  const key = row.type || (row as BackupItem).backup_type || ''
  return TYPE_LABELS[key] || key || '-'
}

/** 增量 / 差异行的"基准 / 变更表"副标题 */
function chainSummary(row: BackupItem): string {
  const base = (row.base_backup as string) || ''
  const count = Array.isArray(row.tables) ? row.tables.length : 0
  return base ? t('admin.ops.backup.chainSummary', {base, count}) : ''
}

onMounted(async () => {
  await Promise.all([loadList(), loadStats(), loadSchedule()])
})
</script>

<template>
  <div class="page-container">
    <!-- 概览 + 定时策略 -->
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>{{ $t('admin.ops.backup.backupSize') }}</span>
              <el-button :icon="Refresh" link @click="loadStats"/>
            </div>
          </template>
          <div v-if="stats" class="stats">
            <div v-for="(value, key) in stats" :key="String(key)" class="stat">
              <p class="stat__value">{{ value ?? '-' }}</p>
              <p class="stat__label">{{ key }}</p>
            </div>
          </div>
          <el-empty v-else :description="$t('admin.ops.backup.noStatisticsAvailable')"/>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>{{ $t('admin.ops.backup.scheduledBackup') }}</span>
              <el-button
                v-auth="'module_ops:backup:create'"
                :loading="scheduleSaving"
                link
                type="primary"
                @click="saveSchedule"
              >
                {{ $t('admin.common.save') }}
              </el-button>
            </div>
          </template>

          <el-form v-if="schedule" :model="schedule" label-width="100px" size="small">
            <el-form-item :label="$t('admin.common.enabled')">
              <el-switch v-model="schedule.enabled"/>
            </el-form-item>
            <el-form-item :label="$t('admin.ops.backup.cronExpression')">
              <el-input v-model="schedule.schedule" :placeholder="$t('admin.ops.backup.eG03')"/>
            </el-form-item>
            <el-form-item :label="$t('admin.ops.backup.retentionDays')">
              <el-input-number v-model="schedule.retention_days" :min="1" controls-position="right"/>
            </el-form-item>
            <el-form-item :label="$t('admin.ops.backup.compress')">
              <el-switch v-model="schedule.compress"/>
            </el-form-item>
            <el-form-item :label="$t('admin.ops.backup.includeDatabase')">
              <el-switch v-model="schedule.backup_database"/>
            </el-form-item>
            <el-form-item :label="$t('admin.ops.backup.includeFiles')">
              <el-switch v-model="schedule.backup_files"/>
            </el-form-item>
          </el-form>
          <el-empty v-else :description="$t('admin.ops.backup.unableToReadBackupSchedule')"/>
        </el-card>
      </el-col>
    </el-row>

    <!-- 备份列表 -->
    <el-card class="mt-4" shadow="never">
      <el-form :inline="true" @submit.prevent>
        <el-form-item :label="$t('admin.cache.level')">
          <el-select v-model="query.backup_type" :placeholder="$t('admin.common.all')" clearable style="width: 140px">
            <el-option :label="$t('admin.ops.backup.database2')" value="database"/>
            <el-option :label="$t('admin.ops.backup.files2')" value="files"/>
            <el-option :label="$t('admin.ops.backup.full2')" value="full"/>
            <el-option :label="$t('admin.ops.backup.incremental')" value="incremental"/>
            <el-option :label="$t('admin.ops.backup.differential')" value="differential"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Refresh" type="primary" @click="loadList">{{ $t('admin.common.search') }}</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar">
        <el-button
          v-auth="'module_ops:backup:create'"
          :icon="Download"
          :loading="creating"
          type="primary"
          @click="createBackup('database')"
        >
          {{ $t('admin.ops.backup.backupDatabase') }}
        </el-button>
        <el-button v-auth="'module_ops:backup:create'" :icon="Download" :loading="creating"
                   @click="createBackup('files')">
          {{ $t('admin.ops.backup.backupFiles') }}
        </el-button>
        <el-button v-auth="'module_ops:backup:create'" :icon="Download" :loading="creating"
                   @click="createBackup('full')">
          {{ $t('admin.ops.backup.backupFull') }}
        </el-button>
        <el-button v-auth="'module_ops:backup:create'" :icon="Download" :loading="creating"
                   @click="createIncremental(false)">
          {{ $t('admin.ops.backup.backupIncremental') }}
        </el-button>
        <el-button v-auth="'module_ops:backup:create'" :icon="Download" :loading="creating"
                   @click="createIncremental(true)">
          {{ $t('admin.ops.backup.backupDifferential') }}
        </el-button>
        <el-button v-auth="'module_ops:backup:delete'" :icon="Delete" plain type="danger" @click="cleanup">
          {{ $t('admin.ops.backup.cleanupByDays') }}
        </el-button>
      </div>

      <el-table v-loading="loading" :data="list" row-key="path">
        <el-table-column :label="$t('admin.ops.backup.filename')" min-width="260">
          <template #default="{row}">
            <div>{{ row.filename || row.path }}</div>
            <div v-if="isChainBackup(row)" class="hint">{{ chainSummary(row) }}</div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.cache.level')" width="100">
          <template #default="{row}">
            <el-tag size="small">{{ typeLabel(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.ops.backup.size')" width="110">
          <template #default="{row}">{{ row.size_human || formatFileSize(row.size) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.status')" prop="status" width="100"/>
        <el-table-column :label="$t('admin.common.createdAt')" width="170">
          <template #default="{row}">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="300">
          <template #default="{row}">
            <el-button v-auth="'module_ops:backup:view'" :icon="CircleCheck" link type="success" @click="verify(row)">
              {{ $t('admin.ops.backup.verify') }}
            </el-button>
            <el-button v-if="isChainBackup(row)" :icon="Connection" link type="primary" @click="openChain(row)">
              {{ $t('admin.ops.backup.chainView') }}
            </el-button>
            <el-button v-auth="'module_ops:backup:restore'" :icon="Upload" link type="warning" @click="restore(row)">
              {{ $t('admin.ops.backup.restore') }}
            </el-button>
            <el-button v-auth="'module_ops:backup:delete'" :icon="Delete" link type="danger" @click="removeRow(row)">
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <p class="hint">{{ $t('admin.ops.backup.summary', {total}) }}</p>
    </el-card>

    <!-- 校验结果（后端逐项给出检查与原因） -->
    <el-dialog v-model="verifyVisible" :title="$t('admin.ops.backup.verifyResult')" width="640px">
      <div v-loading="verifyLoading" class="verify-body">
        <el-alert
          v-if="verifyResult"
          :closable="false"
          :title="verifyResult.valid ? $t('admin.ops.backup.verifyValid') : $t('admin.ops.backup.verifyInvalid')"
          :type="verifyResult.valid ? 'success' : 'error'"
        />
        <el-table v-if="verifyResult" :data="verifyResult.checks" border size="small">
          <el-table-column :label="$t('admin.ops.backup.verifyCheckName')" min-width="150" prop="name"/>
          <el-table-column :label="$t('admin.common.status')" width="90">
            <template #default="{row}">
              <el-tag :type="row.passed ? 'success' : 'danger'" size="small">
                {{ row.passed ? $t('admin.ops.backup.verifyCheckPassed') : $t('admin.ops.backup.verifyCheckFailed') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            :label="$t('admin.ops.backup.verifyCheckDetail')"
            min-width="280"
            prop="detail"
            show-overflow-tooltip
          />
        </el-table>
      </div>
    </el-dialog>

    <!-- 恢复链预览：增量要挂在哪些备份后面 -->
    <el-dialog v-model="chainVisible" :title="$t('admin.ops.backup.chainTitle')" width="640px">
      <p class="hint chain-hint">{{ $t('admin.ops.backup.chainHint') }}</p>
      <el-table v-loading="chainLoading" :data="chainItems" border size="small">
        <el-table-column type="index" width="50"/>
        <el-table-column :label="$t('admin.ops.backup.filename')" min-width="240" prop="filename"/>
        <el-table-column :label="$t('admin.cache.level')" width="110">
          <template #default="{row}">{{ typeLabel(row) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.ops.backup.changedTables')" min-width="160">
          <template #default="{row}">{{ (row.tables || []).join(', ') || '-' }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}

.stat__value {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.stat__label {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.hint {
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.verify-body {
  min-height: 120px;
}

.chain-hint {
  margin: 0 0 10px;
}

.mt-4 {
  margin-top: 16px;
}
</style>
