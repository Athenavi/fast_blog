<script lang="ts" setup>
/**
 * 备份与还原
 *
 * 对齐 v3 `/ops/backup`：备份列表、按类型创建（数据库/文件/完整）、
 * 还原、删除、按天清理、容量统计、定时策略。
 *
 * ⚠️ 还原会覆盖当前数据，因此需要二次确认并单独使用 restore 权限。
 * 样式统一使用 Element Plus 的 CSS 变量。
 */
import {Delete, Download, Refresh, Upload} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {reactive, ref} from 'vue'

import {backupApi, type BackupItem, type BackupSchedule} from '@/api'
import {formatDateTime, formatFileSize} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '备份',
  permission: 'module_ops:backup:view',
})

const TYPE_LABELS: Record<string, string> = {
  database: '数据库',
  files: '文件',
  full: '完整',
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
  await ElMessageBox.confirm(`立即创建一个${label}备份？`, '提示', {type: 'info'})
  creating.value = true
  try {
    if (kind === 'database') await backupApi.createDatabase('database')
    else if (kind === 'files') await backupApi.createFiles()
    else await backupApi.createFull()
    ElMessage.success(`${label}备份已开始`)
    await Promise.all([loadList(), loadStats()])
  } finally {
    creating.value = false
  }
}

// ---------------------------------------------------------------- 还原 / 删除 / 清理
async function restore(row: BackupItem): Promise<void> {
  const file = row.filename || row.path || ''
  if (!file) {
    ElMessage.warning('该备份缺少文件名，无法还原')
    return
  }
  await ElMessageBox.confirm(
    `确定用「${file}」还原吗？当前数据将被覆盖，此操作不可撤销。`,
    '高危操作',
    {type: 'error', confirmButtonText: '确认还原', confirmButtonClass: 'el-button--danger'},
  )
  await backupApi.restore(file, row.backup_type || row.type || 'database')
  ElMessage.success('还原指令已提交')
}

async function removeRow(row: BackupItem): Promise<void> {
  const path = row.path || row.filename || ''
  if (!path) return
  await ElMessageBox.confirm(`确定删除备份「${row.filename || path}」吗？`, '提示', {type: 'warning'})
  await backupApi.remove(path)
  ElMessage.success('已删除')
  await Promise.all([loadList(), loadStats()])
}

async function cleanup(): Promise<void> {
  const input = await ElMessageBox.prompt('保留最近多少天的备份？其余将被删除。', '清理备份', {
    inputValue: '30',
    inputPattern: /^\d+$/,
    inputErrorMessage: '请输入正整数天数',
    type: 'warning',
  })
  await backupApi.cleanup(Number(input.value))
  ElMessage.success('清理完成')
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
    ElMessage.success('定时策略已保存')
  } finally {
    scheduleSaving.value = false
  }
}

function typeLabel(row: BackupItem): string {
  const key = row.backup_type || row.type || ''
  return TYPE_LABELS[key] || key || '-'
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
              <span>备份容量</span>
              <el-button :icon="Refresh" link @click="loadStats"/>
            </div>
          </template>
          <div v-if="stats" class="stats">
            <div v-for="(value, key) in stats" :key="String(key)" class="stat">
              <p class="stat__value">{{ value ?? '-' }}</p>
              <p class="stat__label">{{ key }}</p>
            </div>
          </div>
          <el-empty v-else description="暂无统计数据"/>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>定时备份</span>
              <el-button
                v-auth="'module_ops:backup:create'"
                :loading="scheduleSaving"
                link
                type="primary"
                @click="saveSchedule"
              >
                保存
              </el-button>
            </div>
          </template>

          <el-form v-if="schedule" :model="schedule" label-width="100px" size="small">
            <el-form-item label="启用">
              <el-switch v-model="schedule.enabled"/>
            </el-form-item>
            <el-form-item label="cron 表达式">
              <el-input v-model="schedule.schedule" placeholder="如 0 3 * * *"/>
            </el-form-item>
            <el-form-item label="保留天数">
              <el-input-number v-model="schedule.retention_days" :min="1" controls-position="right"/>
            </el-form-item>
            <el-form-item label="压缩">
              <el-switch v-model="schedule.compress"/>
            </el-form-item>
            <el-form-item label="包含数据库">
              <el-switch v-model="schedule.backup_database"/>
            </el-form-item>
            <el-form-item label="包含文件">
              <el-switch v-model="schedule.backup_files"/>
            </el-form-item>
          </el-form>
          <el-empty v-else description="无法读取定时策略"/>
        </el-card>
      </el-col>
    </el-row>

    <!-- 备份列表 -->
    <el-card class="mt-4" shadow="never">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="类型">
          <el-select v-model="query.backup_type" clearable placeholder="全部" style="width: 140px">
            <el-option label="数据库" value="database"/>
            <el-option label="文件" value="files"/>
            <el-option label="完整" value="full"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Refresh" type="primary" @click="loadList">查询</el-button>
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
          备份数据库
        </el-button>
        <el-button v-auth="'module_ops:backup:create'" :icon="Download" :loading="creating"
                   @click="createBackup('files')">
          备份文件
        </el-button>
        <el-button v-auth="'module_ops:backup:create'" :icon="Download" :loading="creating"
                   @click="createBackup('full')">
          完整备份
        </el-button>
        <el-button v-auth="'module_ops:backup:delete'" :icon="Delete" plain type="danger" @click="cleanup">
          按天清理
        </el-button>
      </div>

      <el-table v-loading="loading" :data="list" row-key="path">
        <el-table-column label="文件名" min-width="240">
          <template #default="{row}">{{ row.filename || row.path }}</template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{row}">
            <el-tag size="small">{{ typeLabel(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="110">
          <template #default="{row}">{{ row.size_human || formatFileSize(row.size) }}</template>
        </el-table-column>
        <el-table-column label="状态" prop="status" width="100"/>
        <el-table-column label="创建时间" width="170">
          <template #default="{row}">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" width="170">
          <template #default="{row}">
            <el-button v-auth="'module_ops:backup:restore'" :icon="Upload" link type="warning" @click="restore(row)">
              还原
            </el-button>
            <el-button v-auth="'module_ops:backup:delete'" :icon="Delete" link type="danger" @click="removeRow(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <p class="hint">共 {{ total }} 个备份（最多显示 100 个）</p>
    </el-card>
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

.mt-4 {
  margin-top: 16px;
}
</style>
