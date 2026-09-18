<script lang="ts" setup>
/**
 * 操作日志
 *
 * 对齐 v3：`/system/log/audit`（分页查询）、`/audit/export`（导出）、
 * `/audit/cleanup`（按天清理）。后端所有写操作都经由 `OperationLogRoute` 记录。
 */
import {Delete, Download, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {reactive, ref} from 'vue'

import {type AuditLogItem, logApi} from '@/api'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '日志',
  permission: 'module_system:log:view',
})

const LEVELS = [
  {label: '信息', value: 'info'},
  {label: '警告', value: 'warning'},
  {label: '错误', value: 'error'},
]

const loading = ref(false)
const list = ref<AuditLogItem[]>([])
const total = ref(0)

const query = reactive({
  page: 1,
  page_size: 20,
  user_id: undefined as number | undefined,
  action: '',
  level: undefined as string | undefined,
  resource_type: '',
})

/** el-date-picker 的范围是数组，需要拆成后端要的 start_date / end_date */
const dateRange = ref<[string, string] | null>(null)

function buildParams() {
  return {
    page: query.page,
    page_size: query.page_size,
    ...(query.user_id === undefined ? {} : {user_id: query.user_id}),
    ...(query.action ? {action: query.action} : {}),
    ...(query.level ? {level: query.level} : {}),
    ...(query.resource_type ? {resource_type: query.resource_type} : {}),
    ...(dateRange.value?.[0] ? {start_date: dateRange.value[0]} : {}),
    ...(dateRange.value?.[1] ? {end_date: dateRange.value[1]} : {}),
  }
}

async function loadList(): Promise<void> {
  loading.value = true
  try {
    const data = await logApi.audit(buildParams())
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

function onReset(): void {
  query.user_id = undefined
  query.action = ''
  query.level = undefined
  query.resource_type = ''
  dateRange.value = null
  query.page = 1
  loadList()
}

function levelTag(level?: string | null): 'success' | 'warning' | 'danger' | 'info' {
  if (level === 'error') return 'danger'
  if (level === 'warning') return 'warning'
  if (level === 'info') return 'success'
  return 'info'
}

async function exportLogs(): Promise<void> {
  const data = await logApi.exportAudit(buildParams())
  if (!data?.content) {
    ElMessage.warning('没有可导出的日志')
    return
  }
  const isJson = data.format === 'json'
  const blob = new Blob([data.content], {
    type: isJson ? 'application/json' : 'text/csv;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `audit-logs.${isJson ? 'json' : 'csv'}`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success(`已导出 ${data.count} 条日志`)
}

async function cleanup(): Promise<void> {
  const input = await ElMessageBox.prompt('删除多少天之前的日志？', '清理日志', {
    inputValue: '90',
    inputPattern: /^\d+$/,
    inputErrorMessage: '请输入正整数天数',
    type: 'warning',
  })
  const days = Number(input.value)
  await logApi.cleanup(days)
  ElMessage.success(`已清理 ${days} 天前的日志`)
  await loadList()
}

onMounted(loadList)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="用户 ID">
          <el-input-number v-model="query.user_id" :min="1" controls-position="right" style="width: 120px"/>
        </el-form-item>
        <el-form-item label="动作">
          <el-input v-model="query.action" clearable placeholder="如 create" style="width: 140px"
                    @keyup.enter="onSearch"/>
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="query.level" clearable placeholder="全部" style="width: 120px">
            <el-option v-for="item in LEVELS" :key="item.value" :label="item.label" :value="item.value"/>
          </el-select>
        </el-form-item>
        <el-form-item label="资源类型">
          <el-input v-model="query.resource_type" clearable placeholder="如 article" style="width: 140px"
                    @keyup.enter="onSearch"/>
        </el-form-item>
        <el-form-item label="时间">
          <el-date-picker
            v-model="dateRange"
            end-placeholder="结束"
            start-placeholder="开始"
            style="width: 250px"
            type="daterange"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="onSearch">查询</el-button>
          <el-button :icon="Refresh" @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar">
        <el-button :icon="Download" @click="exportLogs">导出</el-button>
        <el-button v-auth="'module_system:log:edit'" :icon="Delete" plain type="danger" @click="cleanup">
          清理历史日志
        </el-button>
        <el-button :icon="Refresh" circle class="ml-auto" @click="loadList"/>
      </div>

      <el-table v-loading="loading" :data="list" row-key="id">
        <el-table-column label="ID" prop="id" width="80"/>
        <el-table-column label="用户" width="150">
          <template #default="{row}">
            {{ row.user_name || (row.user_id ? `#${row.user_id}` : '-') }}
          </template>
        </el-table-column>
        <el-table-column label="动作" prop="action" width="120"/>
        <el-table-column label="级别" width="90">
          <template #default="{row}">
            <el-tag :type="levelTag(row.level)" size="small">{{ row.level || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="资源" width="180">
          <template #default="{row}">
            <span v-if="row.resource_type">
              {{ row.resource_type }}<span v-if="row.resource_id">#{{ row.resource_id }}</span>
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="描述" min-width="240" prop="description" show-overflow-tooltip/>
        <el-table-column label="IP" prop="ip_address" width="140"/>
        <el-table-column label="时间" width="170">
          <template #default="{row}">{{ formatDateTime(row.created_at) }}</template>
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

.pagination {
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
