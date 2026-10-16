<script lang="ts" setup>
const {t} = useI18n()
/**
 * 操作日志
 *
 * 对齐 v3：`/system/log/audit`（分页查询）、`/audit/export`（导出）、
 * `/audit/cleanup`（按天清理）。后端所有写操作都经由 `OperationLogRoute` 记录。
 *
 * 日期范围在内部拆成 `start_date` / `end_date` 两个扁平字段，这样筛选条件
 * 才能整体进入 URL（刷新/分享后保持原状）。
 */
import {Delete, Download} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed} from 'vue'

import {type AuditLogItem, type AuditLogQuery, logApi} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.log.title',
  permission: 'module_system:log:view',
})

const LEVELS = [
  {label: t('admin.system.log.levelInfo'), value: 'info'},
  {label: t('admin.system.log.levelWarning'), value: 'warning'},
  {label: t('admin.system.log.levelError'), value: 'error'},
]

interface AuditQueryForm extends AuditLogQuery, PageQuery {
  start_date?: string
  end_date?: string
}

const list = useAdminList<AuditLogItem, AuditQueryForm>({
  fetcher: (params) => logApi.audit(params),
  defaultQuery: {
    user_id: undefined,
    action: '',
    level: undefined,
    resource_type: '',
    start_date: undefined,
    end_date: undefined,
  },
  syncUrl: true,
})

/** el-date-picker 需要数组，这里与两个扁平字段互转 */
const dateRange = computed<[string, string] | null>({
  get: (): [string, string] | null =>
    list.query.start_date && list.query.end_date
      ? [list.query.start_date, list.query.end_date]
      : null,
  set: (value: [string, string] | null) => {
    list.query.start_date = value?.[0]
    list.query.end_date = value?.[1]
  },
})

function levelTag(level?: string | null): 'success' | 'warning' | 'danger' | 'info' {
  if (level === 'error') return 'danger'
  if (level === 'warning') return 'warning'
  if (level === 'info') return 'success'
  return 'info'
}

/** 导出沿用当前筛选条件（与列表请求同一套判空规则） */
function currentFilters(): AuditLogQuery {
  const params: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(list.query as Record<string, unknown>)) {
    if (value === undefined || value === null || value === '') continue
    params[key] = value
  }
  return params as AuditLogQuery
}

async function exportLogs(): Promise<void> {
  const data = await logApi.exportAudit(currentFilters())
  if (!data?.content) {
    ElMessage.warning(t('admin.system.log.nothingToExport'))
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
  ElMessage.success(t('admin.system.log.exported', {n: data.count}))
}

async function cleanup(): Promise<void> {
  const input = await ElMessageBox.prompt(t('admin.system.log.purgePrompt'), t('admin.system.log.purgeTitle'), {
    inputValue: '90',
    inputPattern: /^\d+$/,
    inputErrorMessage: t('admin.system.log.purgeInvalid'),
    type: 'warning',
  })
  const days = Number(input.value)
  await logApi.cleanup(days)
  ElMessage.success(t('admin.system.log.cleaned', {n: days}))
  await list.reload()
}
</script>

<template>
  <AdminPage :desc="$t('admin.system.log.desc')" :title="$t('admin.system.log.title')">
    <AdminListShell
      :empty-desc="list.hasFilters.value
        ? $t('admin.system.log.emptyFiltered')
        : $t('admin.system.log.emptyDesc')"
      :empty-title="$t('admin.system.log.emptyTitle')"
      :failed="list.failed.value"
      :loading="list.loading.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      :page-sizes="[20, 50, 100]"
      :rows="list.rows.value"
      :selectable="false"
      :total="list.total.value"
      @refresh="list.reload"
      @reset="list.reset"
      @search="list.search"
      @page-change="list.onPageChange"
      @size-change="list.onSizeChange"
    >
      <template #filters>
        <el-form-item :label="$t('admin.system.log.userId')">
          <el-input-number v-model="list.query.user_id" :min="1" controls-position="right" style="width: 120px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.log.action')">
          <el-input v-model="list.query.action" :placeholder="$t('admin.system.log.actionPlaceholder')" clearable
                    style="width: 140px" @keyup.enter="list.search()"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.log.level')">
          <el-select v-model="list.query.level" :placeholder="$t('admin.common.all')" clearable style="width: 120px">
            <el-option v-for="item in LEVELS" :key="item.value" :label="item.label" :value="item.value"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.system.log.resourceType')">
          <el-input v-model="list.query.resource_type" :placeholder="$t('admin.system.log.resourcePlaceholder')"
                    clearable style="width: 140px"
                    @keyup.enter="list.search()"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.log.time')">
          <el-date-picker
            v-model="dateRange"
            :end-placeholder="$t('admin.system.log.endPlaceholder')"
            :start-placeholder="$t('admin.system.log.startPlaceholder')"
            style="width: 250px"
            type="daterange"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
      </template>

      <template #actions>
        <el-button :icon="Download" @click="exportLogs">{{ $t('admin.system.log.export') }}</el-button>
        <el-button v-auth="'module_system:log:edit'" :icon="Delete" plain type="danger" @click="cleanup">
          {{ $t('admin.system.log.purgeAction') }}
        </el-button>
      </template>

      <el-table-column label="ID" prop="id" width="80"/>
      <el-table-column :label="$t('admin.system.log.user')" width="150">
        <template #default="{row}">
          {{ row.user_name || (row.user_id ? `#${row.user_id}` : '-') }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.system.log.action')" prop="action" width="120"/>
      <el-table-column :label="$t('admin.system.log.level')" width="90">
        <template #default="{row}">
          <el-tag :type="levelTag(row.level)" size="small">{{ row.level || '-' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.system.log.resource')" width="180">
        <template #default="{row}">
          <span v-if="row.resource_type">
            {{ row.resource_type }}<span v-if="row.resource_id">#{{ row.resource_id }}</span>
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.description')" min-width="240" prop="description"
                       show-overflow-tooltip/>
      <el-table-column label="IP" prop="ip_address" width="140"/>
      <el-table-column :label="$t('admin.system.log.time')" width="170">
        <template #default="{row}">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
    </AdminListShell>
  </AdminPage>
</template>
