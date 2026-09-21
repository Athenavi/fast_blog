<script lang="ts" setup>
/**
 * 报表中心（T5-11 批次 8，analytics 域）
 *
 * 对齐 v3 `/analytics/report`：报表生成 / 定时报表 / 报表历史（三标签）。
 * 报表正文由后端**真实聚合**产出（结构随类型变化），因此这里用通用渲染：
 * 标量对象走 `el-descriptions`、对象数组走动态列 `el-table`。
 * 导出与历史下载是**文件下载**（服务端 `Content-Disposition`）。
 */
import {Delete, Download, EditPen, Plus, Refresh, Search, VideoPlay} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {
  reportApi,
  type ReportFormat,
  type ReportHistoryItem,
  type ReportTemplate,
  type ScheduledReportItem,
} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.analytics.report.title',
  permission: 'module_analytics:report:view',
})

const {t} = useI18n()
const activeTab = ref('generate')

const REPORT_TYPES = ['content', 'user-activity', 'traffic', 'custom'] as const
const CUSTOM_METRICS = ['content', 'users', 'traffic', 'engagement'] as const
const FREQUENCIES = ['daily', 'weekly', 'monthly'] as const

// ---------------------------------------------------------------- 生成
const genType = ref<string>('content')
const genDays = ref(30)
const genMetrics = ref<string[]>(['content', 'users'])
const generating = ref(false)
const report = ref<Record<string, unknown> | null>(null)

async function generate() {
  generating.value = true
  try {
    if (genType.value === 'content') {
      report.value = (await reportApi.content(genDays.value)) as unknown as Record<string, unknown>
    } else if (genType.value === 'user-activity') {
      report.value = (await reportApi.userActivity(genDays.value)) as unknown as Record<
        string,
        unknown
      >
    } else if (genType.value === 'traffic') {
      report.value = (await reportApi.traffic(genDays.value)) as unknown as Record<
        string,
        unknown
      >
    } else {
      if (!genMetrics.value.length) {
        ElMessage.warning(t('admin.analytics.report.metricsRequired'))
        return
      }
      report.value = (await reportApi.custom({
        metrics: genMetrics.value,
        days: genDays.value,
      })) as unknown as Record<string, unknown>
    }
  } finally {
    generating.value = false
  }
}

async function exportReport(format: ReportFormat) {
  try {
    await reportApi.exportReport({
      report_type: genType.value,
      format,
      days: genDays.value,
      metrics: genType.value === 'custom' ? genMetrics.value : null,
    })
    ElMessage.success(t('admin.analytics.report.exported'))
  } catch {
    ElMessage.error(t('admin.analytics.report.exportFailed'))
  }
}

// ---------------------------------------------------------------- 通用渲染
function isFlatObject(value: unknown): boolean {
  return (
    typeof value === 'object' &&
    value !== null &&
    !Array.isArray(value) &&
    Object.values(value as Record<string, unknown>).every(
      (item) => item === null || typeof item !== 'object',
    )
  )
}

function isObjectArray(value: unknown): boolean {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    typeof value[0] === 'object' &&
    value[0] !== null &&
    !Array.isArray(value[0])
  )
}

function tableColumns(rows: unknown[]): string[] {
  const first = rows[0]
  return first && typeof first === 'object'
    ? Object.keys(first as Record<string, unknown>)
    : []
}

function scalar(value: unknown): string {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

/** 生成区展示的段落（跳过 period / generated_at 这类元信息） */
const reportSections = computed(() => {
  const data = report.value
  if (!data) return []
  return Object.entries(data).filter(([key]) => !['report_type', 'generated_at', 'period'].includes(key))
})

// ---------------------------------------------------------------- 模板
const templates = ref<ReportTemplate[]>([])
const templatesLoading = ref(false)

async function loadTemplates() {
  templatesLoading.value = true
  try {
    templates.value = (await reportApi.templates()).templates ?? []
  } finally {
    templatesLoading.value = false
  }
}

function applyTemplate(template: ReportTemplate) {
  genType.value = template.report_type
  genDays.value = template.default_days || 30
  genMetrics.value = template.metrics?.length ? [...template.metrics] : ['content']
  activeTab.value = 'generate'
}

// ---------------------------------------------------------------- 定时报表
const scheduledState = useAdminList<ScheduledReportItem, PageQuery & { report_type?: string; is_active?: boolean }>({

  fetcher: (params) => reportApi.listScheduled(params),
  defaultQuery: {keyword: '', report_type: '', is_active: undefined},
})

// 模板沿用原有变量名：映射为同名 ref / 函数
const scheduledList = scheduledState.rows
const scheduledLoading = scheduledState.loading
const scheduledTotal = scheduledState.total
const scheduledPage = scheduledState.page
const scheduledPageSize = scheduledState.pageSize
const scheduledQuery = scheduledState.query
const scheduledSearch = scheduledState.search
const scheduledReset = scheduledState.reset
const scheduledLoad = scheduledState.reload
const onScheduledPageChange = scheduledState.onPageChange
const onScheduledSizeChange = scheduledState.onSizeChange
const scheduledFailed = scheduledState.failed

const scheduledFormVisible = ref(false)
const scheduledEditingId = ref<number | null>(null)
const scheduledSaving = ref(false)
const scheduledForm = reactive({
  name: '',
  report_type: 'content',
  frequency: 'daily',
  metrics: ['content'] as string[],
  days: 30,
  export_format: 'json',
  is_active: true,
})

const scheduledFormTitle = computed(() =>
  scheduledEditingId.value
    ? t('admin.analytics.report.editScheduled')
    : t('admin.analytics.report.createScheduled'),
)

function openScheduledCreate() {
  scheduledEditingId.value = null
  Object.assign(scheduledForm, {
    name: '',
    report_type: 'content',
    frequency: 'daily',
    metrics: ['content'],
    days: 30,
    export_format: 'json',
    is_active: true,
  })
  scheduledFormVisible.value = true
}

function openScheduledEdit(row: ScheduledReportItem) {
  scheduledEditingId.value = row.id
  Object.assign(scheduledForm, {
    name: row.name || '',
    report_type: row.report_type || 'content',
    frequency: row.frequency || 'daily',
    metrics: row.metrics?.length ? [...row.metrics] : ['content'],
    days: row.days ?? 30,
    export_format: row.export_format || 'json',
    is_active: row.is_active,
  })
  scheduledFormVisible.value = true
}

async function submitScheduled() {
  if (!scheduledForm.name.trim()) {
    ElMessage.warning(t('admin.analytics.report.nameRequired'))
    return
  }
  if (scheduledForm.report_type === 'custom' && !scheduledForm.metrics.length) {
    ElMessage.warning(t('admin.analytics.report.metricsRequired'))
    return
  }
  scheduledSaving.value = true
  try {
    const payload = {
      name: scheduledForm.name.trim(),
      report_type: scheduledForm.report_type,
      frequency: scheduledForm.frequency,
      metrics: scheduledForm.report_type === 'custom' ? scheduledForm.metrics : null,
      days: scheduledForm.days,
      export_format: scheduledForm.export_format,
      is_active: scheduledForm.is_active,
    }
    if (scheduledEditingId.value) {
      await reportApi.updateScheduled(scheduledEditingId.value, payload)
    } else {
      await reportApi.createScheduled(payload)
    }
    ElMessage.success(t('admin.common.save'))
    scheduledFormVisible.value = false
    await scheduledLoad()
  } finally {
    scheduledSaving.value = false
  }
}

async function onToggleScheduled(row: ScheduledReportItem) {
  await reportApi.toggleScheduled(row.id)
  ElMessage.success(t('admin.analytics.report.toggled'))
  await scheduledLoad()
}

async function onRunScheduled(row: ScheduledReportItem) {
  await ElMessageBox.confirm(
    t('admin.analytics.report.runConfirm', {name: row.name || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await reportApi.runScheduled(row.id)
  ElMessage.success(t('admin.analytics.report.ran'))
  await scheduledLoad()
  await historyLoad()
}

async function onDeleteScheduled(row: ScheduledReportItem) {
  await ElMessageBox.confirm(
    t('admin.analytics.report.deleteScheduledConfirm', {name: row.name || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await reportApi.removeScheduled(row.id)
  ElMessage.success(t('admin.common.delete'))
  await scheduledLoad()
}

// ---------------------------------------------------------------- 报表历史
const historyState = useAdminList<ReportHistoryItem, PageQuery & { report_type?: string }>({

  fetcher: (params) => reportApi.listHistory(params),
  defaultQuery: {keyword: '', report_type: ''},
})

// 模板沿用原有变量名：映射为同名 ref / 函数
const historyList = historyState.rows
const historyLoading = historyState.loading
const historyTotal = historyState.total
const historyPage = historyState.page
const historyPageSize = historyState.pageSize
const historyQuery = historyState.query
const historySearch = historyState.search
const historyReset = historyState.reset
const historyLoad = historyState.reload
const onHistoryPageChange = historyState.onPageChange
const onHistorySizeChange = historyState.onSizeChange
const historyFailed = historyState.failed

function downloadHistory(row: ReportHistoryItem): void {
  const token = import.meta.client ? window.localStorage.getItem('fastblog_token') : null
  const link = document.createElement('a')
  link.href = `/api/v3/analytics/report/history/${row.id}/download${token ? '' : ''}`
  // 走 fetch 以便带上 Bearer（浏览器直接打开链接不会带 Authorization）
  fetch(link.href, {headers: token ? {Authorization: `Bearer ${token}`} : {}})
    .then((resp) => (resp.ok ? resp.blob() : Promise.reject(new Error('download failed'))))
    .then((blob) => {
      const href = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = href
      anchor.download = `${row.report_name || `report-${row.id}`}.${row.format || 'json'}`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(href)
    })
    .catch(() => ElMessage.error(t('admin.analytics.report.exportFailed')))
}

onMounted(() => {
  loadTemplates().catch(() => undefined)
})
</script>

<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- 报表生成 -->
      <el-tab-pane :label="$t('admin.analytics.report.generate')" name="generate">
        <el-card shadow="never">
          <el-form :inline="true" @submit.prevent="generate()">
            <el-form-item :label="$t('admin.analytics.report.reportType')">
              <el-select v-model="genType" style="width: 170px">
                <el-option v-for="item in REPORT_TYPES" :key="item" :label="item" :value="item"/>
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('admin.analytics.report.days')">
              <el-input-number v-model="genDays" :max="90" :min="7" style="width: 130px"/>
            </el-form-item>
            <el-form-item v-if="genType === 'custom'" :label="$t('admin.analytics.report.metrics')">
              <el-select v-model="genMetrics" multiple style="width: 280px">
                <el-option v-for="item in CUSTOM_METRICS" :key="item" :label="item" :value="item"/>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="generate()">
                {{ $t('admin.analytics.report.generate') }}
              </el-button>
              <el-button :disabled="!report" :icon="Download" @click="exportReport('json')">
                JSON
              </el-button>
              <el-button :disabled="!report" :icon="Download" @click="exportReport('csv')">
                CSV
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-show="!report"
            :closable="false"
            :title="$t('admin.analytics.report.generateHint')"
            class="mb-3"
            show-icon
            type="info"
          />

          <div v-loading="generating">
            <template v-for="[key, value] in reportSections" :key="key">
              <h4 class="report-section">{{ key }}</h4>
              <el-descriptions v-if="isFlatObject(value)" :column="3" border size="small">
                <el-descriptions-item
                  v-for="[subKey, subValue] in Object.entries(value as Record<string, unknown>)"
                  :key="subKey"
                  :label="subKey"
                >
                  {{ scalar(subValue) }}
                </el-descriptions-item>
              </el-descriptions>
              <el-table v-else-if="isObjectArray(value)" :data="value as unknown[]" border size="small">
                <el-table-column
                  v-for="column in tableColumns(value as unknown[])"
                  :key="column"
                  :label="column"
                  :prop="column"
                  show-overflow-tooltip
                />
              </el-table>
              <pre v-else class="report-raw">{{ JSON.stringify(value, null, 2) }}</pre>
            </template>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- 定时报表 -->
      <el-tab-pane :label="$t('admin.analytics.report.scheduled')" name="scheduled">
        <el-card shadow="never">
          <el-form :inline="true" :model="scheduledQuery" @submit.prevent="scheduledSearch()">
            <el-form-item :label="$t('admin.analytics.report.keyword')">
              <el-input v-model="scheduledQuery.keyword" clearable style="width: 180px"
                        @keyup.enter="scheduledSearch()"/>
            </el-form-item>
            <el-form-item :label="$t('admin.analytics.report.reportType')">
              <el-select v-model="scheduledQuery.report_type" :placeholder="$t('admin.common.all')"
                         clearable style="width: 170px">
                <el-option v-for="item in REPORT_TYPES" :key="item" :label="item" :value="item"/>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="scheduledSearch()">
                {{ $t('admin.common.search') }}
              </el-button>
              <el-button :icon="Refresh" @click="scheduledReset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>

          <div class="table-toolbar">
            <el-button v-auth="'module_analytics:report:create'" :icon="Plus" type="primary"
                       @click="openScheduledCreate">
              {{ $t('admin.analytics.report.createScheduled') }}
            </el-button>
            <span class="table-toolbar__total">
              {{ $t('admin.common.totalItems', {n: scheduledTotal}) }}
            </span>
          </div>

          <AdminTableSkeleton v-if="scheduledLoading && !scheduledList.length" :rows="5"/>

          <AdminEmpty
            v-else-if="!scheduledLoading && !scheduledList.length"
            :title="scheduledFailed ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
            :variant="scheduledFailed ? 'error' : 'default'"
          >
            <el-button v-if="scheduledFailed" :icon="Refresh" @click="scheduledLoad()">
              {{ $t('admin.common.retry') }}
            </el-button>
          </AdminEmpty>

          <el-table v-else v-loading="scheduledLoading" :data="scheduledList" border stripe>
            <el-table-column :label="$t('admin.common.name')" min-width="170" prop="name"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.analytics.report.reportType')" min-width="140"
                             prop="report_type"/>
            <el-table-column :label="$t('admin.analytics.report.frequency')" prop="frequency"
                             width="110"/>
            <el-table-column :label="$t('admin.analytics.report.days')" prop="days" width="90"/>
            <el-table-column :label="$t('admin.analytics.report.nextRunAt')" min-width="170"
                             prop="next_run_at"/>
            <el-table-column :label="$t('admin.common.status')" align="center" width="100">
              <template #default="{ row }">
                <el-tag :type="(row as ScheduledReportItem).is_active ? 'success' : 'info'" size="small">
                  {{
                    (row as ScheduledReportItem).is_active ? $t('admin.common.enabled') : $t('admin.common.disabled')
                  }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="260">
              <template #default="{ row }">
                <el-button v-auth="'module_analytics:report:edit'" :icon="VideoPlay" link type="success"
                           @click="onRunScheduled(row as ScheduledReportItem)">
                  {{ $t('admin.analytics.report.runNow') }}
                </el-button>
                <el-button v-auth="'module_analytics:report:edit'" link type="primary"
                           @click="onToggleScheduled(row as ScheduledReportItem)">
                  {{
                    (row as ScheduledReportItem).is_active
                      ? $t('admin.analytics.report.disable')
                      : $t('admin.analytics.report.enable')
                  }}
                </el-button>
                <el-button v-auth="'module_analytics:report:edit'" :icon="EditPen" link type="primary"
                           @click="openScheduledEdit(row as ScheduledReportItem)">
                  {{ $t('admin.common.edit') }}
                </el-button>
                <el-button v-auth="'module_analytics:report:delete'" :icon="Delete" link type="danger"
                           @click="onDeleteScheduled(row as ScheduledReportItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination :current-page="scheduledPage" :page-size="scheduledPageSize"
                         :page-sizes="[10, 20, 50, 100]" :total="scheduledTotal" background
                         class="table-pagination" layout="total, sizes, prev, pager, next, jumper"
                         @current-change="onScheduledPageChange" @size-change="onScheduledSizeChange"/>
        </el-card>
      </el-tab-pane>

      <!-- 报表历史 -->
      <el-tab-pane :label="$t('admin.analytics.report.history')" name="history">
        <el-card shadow="never">
          <el-form :inline="true" :model="historyQuery" @submit.prevent="historySearch()">
            <el-form-item :label="$t('admin.analytics.report.keyword')">
              <el-input v-model="historyQuery.keyword" clearable style="width: 180px"
                        @keyup.enter="historySearch()"/>
            </el-form-item>
            <el-form-item :label="$t('admin.analytics.report.reportType')">
              <el-input v-model="historyQuery.report_type" clearable style="width: 170px"
                        @keyup.enter="historySearch()"/>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="historySearch()">
                {{ $t('admin.common.search') }}
              </el-button>
              <el-button :icon="Refresh" @click="historyReset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>

          <div class="table-toolbar">
            <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: historyTotal}) }}</span>
          </div>

          <el-table v-loading="historyLoading" :data="historyList" border stripe>
            <el-table-column :label="$t('admin.analytics.report.reportName')" min-width="200"
                             prop="report_name" show-overflow-tooltip/>
            <el-table-column :label="$t('admin.analytics.report.reportType')" min-width="140"
                             prop="report_type"/>
            <el-table-column :label="$t('admin.analytics.report.format')" prop="format" width="90"/>
            <el-table-column :label="$t('admin.analytics.report.generatedAt')" min-width="180"
                             prop="generated_at"/>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="120">
              <template #default="{ row }">
                <el-button :icon="Download" link type="primary"
                           @click="downloadHistory(row as ReportHistoryItem)">
                  {{ $t('admin.analytics.report.download') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination :current-page="historyPage" :page-size="historyPageSize"
                         :page-sizes="[10, 20, 50, 100]" :total="historyTotal" background
                         class="table-pagination" layout="total, sizes, prev, pager, next, jumper"
                         @current-change="onHistoryPageChange" @size-change="onHistorySizeChange"/>
        </el-card>
      </el-tab-pane>

      <!-- 模板 -->
      <el-tab-pane :label="$t('admin.analytics.report.templates')" name="templates">
        <el-card v-loading="templatesLoading" shadow="never">
          <div class="template-grid">
            <div v-for="item in templates" :key="item.id" class="template-card">
              <div class="template-card__name">{{ item.name }}</div>
              <div class="template-card__desc">{{ item.description }}</div>
              <div class="template-card__meta">
                {{ item.report_type }} · {{ $t('admin.analytics.report.days') }} {{ item.default_days }}
              </div>
              <el-button class="mt-2" size="small" type="primary" @click="applyTemplate(item)">
                {{ $t('admin.analytics.report.apply') }}
              </el-button>
            </div>
          </div>
          <el-empty v-if="!templatesLoading && !templates.length" :description="$t('admin.common.empty')"/>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 定时报表表单 -->
    <el-drawer v-model="scheduledFormVisible" :title="scheduledFormTitle" destroy-on-close size="520px">
      <el-form :model="scheduledForm" label-width="130px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="scheduledForm.name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.analytics.report.reportType')" required>
          <el-select v-model="scheduledForm.report_type" style="width: 100%">
            <el-option v-for="item in REPORT_TYPES" :key="item" :label="item" :value="item"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.analytics.report.frequency')">
          <el-select v-model="scheduledForm.frequency" style="width: 100%">
            <el-option v-for="item in FREQUENCIES" :key="item" :label="item" :value="item"/>
          </el-select>
        </el-form-item>
        <el-form-item v-if="scheduledForm.report_type === 'custom'"
                      :label="$t('admin.analytics.report.metrics')">
          <el-select v-model="scheduledForm.metrics" multiple style="width: 100%">
            <el-option v-for="item in CUSTOM_METRICS" :key="item" :label="item" :value="item"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.analytics.report.days')">
          <el-input-number v-model="scheduledForm.days" :max="90" :min="7" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.analytics.report.format')">
          <el-select v-model="scheduledForm.export_format" style="width: 100%">
            <el-option label="json" value="json"/>
            <el-option label="csv" value="csv"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="scheduledForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scheduledFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="scheduledSaving" type="primary" @click="submitScheduled">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.mb-3 {
  margin-bottom: 12px;
}

.mt-2 {
  margin-top: 8px;
}

.report-section {
  margin: 18px 0 10px;
}

.report-raw {
  max-height: 260px;
  padding: 10px 12px;
  overflow: auto;
  font-family: Menlo, Consolas, monospace;
  font-size: 12px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.template-card {
  padding: 14px 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}

.template-card__name {
  font-weight: 600;
}

.template-card__desc {
  margin-top: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.template-card__meta {
  margin-top: 6px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}
</style>
