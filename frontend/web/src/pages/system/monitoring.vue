<script lang="ts" setup>
/**
 * 监控中心（T5-11 批次 10，system 域）
 *
 * 对齐 v3 `/system/monitor` 的告警 / 指标 / SLA 三组（实时状态在 `/system/hub`）。
 * 数据由外部探针 / 脚本写入，本页做管理与查询：
 *  - 告警：列表 / 过滤 / 新建 / 解决 / 删除 + 统计；
 *  - 指标：时序列表 / 时间桶聚合 / 写入 / 按保留期清理；
 *  - SLA：报表列表 + **按真实告警计算**（周期内 critical 告警窗口合并 → 宕机分钟数）+ 达标统计。
 */
import {Delete, Plus, Refresh, Search, TrendCharts} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {
  type AlertItem,
  type AlertStats,
  type MetricItem,
  type MetricSeriesResult,
  monitoringApi,
  type SLAItem,
  type SLAStats,
} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.monitoring.title',
  permission: 'module_system:monitor:view',
})

const {t} = useI18n()
const activeTab = ref('alert')

const SEVERITIES = ['info', 'warning', 'error', 'critical'] as const
const BUCKETS = ['minute', 'hour', 'day'] as const
const SEVERITY_TAG: Record<string, string> = {
  info: 'info',
  warning: 'warning',
  error: 'danger',
  critical: 'danger',
}

const alertStats = ref<AlertStats | null>(null)
const slaStats = ref<SLAStats | null>(null)

const alertStatCards = computed(() => [
  {key: 'total', value: alertStats.value?.total ?? 0},
  {key: 'unresolved', value: alertStats.value?.unresolved ?? 0},
  {key: 'resolved', value: alertStats.value?.resolved ?? 0},
])

async function loadStats() {
  const [alerts, sla] = await Promise.all([
    monitoringApi.alertStats().catch(() => null),
    monitoringApi.slaStats().catch(() => null),
  ])
  alertStats.value = alerts
  slaStats.value = sla
}

// ---------------------------------------------------------------- 告警
const alertState = useAdminList<AlertItem, PageQuery & { severity?: string; is_resolved?: boolean }>({
  fetcher: (params) => monitoringApi.listAlerts(params),
  defaultQuery: {keyword: '', severity: '', is_resolved: undefined},
  syncUrl: true,
})

// 模板沿用原有变量名：把列表状态映射成同名 ref / 函数，避免整页重写带来的回归风险
const alertList = alertState.rows
const alertLoading = alertState.loading
const alertFailed = alertState.failed
const alertTotal = alertState.total
const alertPage = alertState.page
const alertPageSize = alertState.pageSize
const alertQuery = alertState.query
const alertSearch = alertState.search
const alertReset = alertState.reset
const alertLoad = alertState.reload
const onAlertPageChange = alertState.onPageChange
const onAlertSizeChange = alertState.onSizeChange

const alertFormVisible = ref(false)
const alertSaving = ref(false)
const alertForm = reactive({
  alert_type: '',
  severity: 'warning',
  title: '',
  message: '',
  source: '',
  metric_name: '',
  metric_value: undefined as number | undefined,
  threshold: undefined as number | undefined,
})

function openAlertCreate() {
  Object.assign(alertForm, {
    alert_type: '',
    severity: 'warning',
    title: '',
    message: '',
    source: '',
    metric_name: '',
    metric_value: undefined,
    threshold: undefined,
  })
  alertFormVisible.value = true
}

async function submitAlert() {
  if (!alertForm.alert_type.trim() || !alertForm.message.trim()) {
    ElMessage.warning(t('admin.system.monitoring.alertRequired'))
    return
  }
  alertSaving.value = true
  try {
    await monitoringApi.createAlert({
      alert_type: alertForm.alert_type.trim(),
      severity: alertForm.severity,
      title: alertForm.title.trim() || null,
      message: alertForm.message.trim(),
      source: alertForm.source.trim() || null,
      metric_name: alertForm.metric_name.trim() || null,
      metric_value: alertForm.metric_value ?? null,
      threshold: alertForm.threshold ?? null,
    })
    ElMessage.success(t('admin.common.save'))
    alertFormVisible.value = false
    await alertLoad()
    await loadStats()
  } finally {
    alertSaving.value = false
  }
}

async function onResolveAlert(row: AlertItem) {
  await monitoringApi.resolveAlert(row.id)
  ElMessage.success(t('admin.system.monitoring.resolved'))
  await alertLoad()
  await loadStats()
}

async function onDeleteAlert(row: AlertItem) {
  await ElMessageBox.confirm(
    t('admin.system.monitoring.deleteAlertConfirm', {name: row.title || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await monitoringApi.removeAlert(row.id)
  ElMessage.success(t('admin.common.delete'))
  await alertLoad()
  await loadStats()
}

// ---------------------------------------------------------------- 指标
const metricState = useAdminList<MetricItem, PageQuery & { metric_type?: string }>({
  fetcher: (params) => monitoringApi.listMetrics(params),
  defaultQuery: {keyword: '', metric_type: ''},
})

const metricList = metricState.rows
const metricLoading = metricState.loading
const metricFailed = metricState.failed
const metricTotal = metricState.total
const metricPage = metricState.page
const metricPageSize = metricState.pageSize
const metricQuery = metricState.query
const metricSearch = metricState.search
const metricReset = metricState.reset
const metricLoad = metricState.reload
const onMetricPageChange = metricState.onPageChange
const onMetricSizeChange = metricState.onSizeChange

const metricFormVisible = ref(false)
const metricSaving = ref(false)
const metricForm = reactive({
  metric_name: '',
  metric_value: undefined as number | undefined,
  metric_type: '',
  labelsText: '',
})

function openMetricCreate() {
  Object.assign(metricForm, {metric_name: '', metric_value: undefined, metric_type: '', labelsText: ''})
  metricFormVisible.value = true
}

function parseLabels(text: string): Record<string, unknown> | null {
  const trimmed = text.trim()
  if (!trimmed) return null
  const parsed: unknown = JSON.parse(trimmed)
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    throw new Error('labels must be a JSON object')
  }
  return parsed as Record<string, unknown>
}

async function submitMetric() {
  if (!metricForm.metric_name.trim() || metricForm.metric_value === undefined) {
    ElMessage.warning(t('admin.system.monitoring.metricRequired'))
    return
  }
  let labels: Record<string, unknown> | null = null
  try {
    labels = parseLabels(metricForm.labelsText)
  } catch {
    ElMessage.warning(t('admin.system.monitoring.labelsInvalid'))
    return
  }
  metricSaving.value = true
  try {
    await monitoringApi.createMetric({
      metric_name: metricForm.metric_name.trim(),
      metric_value: metricForm.metric_value,
      metric_type: metricForm.metric_type.trim() || null,
      labels,
    })
    ElMessage.success(t('admin.common.save'))
    metricFormVisible.value = false
    await metricLoad()
  } finally {
    metricSaving.value = false
  }
}

async function onPruneMetrics() {
  try {
    const result = await ElMessageBox.prompt(
      t('admin.system.monitoring.prunePrompt'),
      t('admin.common.notice'),
      {inputValue: '30', inputPattern: /^\d+$/, type: 'warning'},
    )
    const days = Number((result as { value?: string }).value || 30)
    const outcome = await monitoringApi.pruneMetrics(days)
    ElMessage.success(t('admin.system.monitoring.pruned', {n: outcome.deleted ?? 0}))
    await metricLoad()
  } catch {
    /* 取消或失败都由 request 层提示 */
  }
}

async function onDeleteMetric(row: MetricItem) {
  await ElMessageBox.confirm(
    t('admin.system.monitoring.deleteMetricConfirm', {name: row.metric_name || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await monitoringApi.removeMetric(row.id)
  ElMessage.success(t('admin.common.delete'))
  await metricLoad()
}

const seriesForm = reactive({metric_name: '', bucket: 'hour' as string})
const seriesLoading = ref(false)
const series = ref<MetricSeriesResult | null>(null)

async function loadSeries() {
  if (!seriesForm.metric_name.trim()) {
    ElMessage.warning(t('admin.system.monitoring.metricNameRequired'))
    return
  }
  seriesLoading.value = true
  try {
    series.value = await monitoringApi.metricSeries({
      metric_name: seriesForm.metric_name.trim(),
      bucket: seriesForm.bucket as never,
    })
  } finally {
    seriesLoading.value = false
  }
}

// ---------------------------------------------------------------- SLA
const slaState = useAdminList<SLAItem, PageQuery & { license_id?: number; is_compliant?: boolean }>({
  fetcher: (params) => monitoringApi.listSlaReports(params),
  defaultQuery: {license_id: undefined, is_compliant: undefined},
})

const slaList = slaState.rows
const slaLoading = slaState.loading
const slaFailed = slaState.failed
const slaTotal = slaState.total
const slaPage = slaState.page
const slaPageSize = slaState.pageSize
const slaQuery = slaState.query
const slaSearch = slaState.search
const slaReset = slaState.reset
const slaLoad = slaState.reload
const onSlaPageChange = slaState.onPageChange
const onSlaSizeChange = slaState.onSizeChange

const slaFormVisible = ref(false)
const slaSaving = ref(false)
const slaForm = reactive({
  license_id: undefined as number | undefined,
  period_start: '',
  period_end: '',
  target_percentage: 99.9,
})

function openSlaCompute() {
  Object.assign(slaForm, {license_id: undefined, period_start: '', period_end: '', target_percentage: 99.9})
  slaFormVisible.value = true
}

async function submitSlaCompute() {
  if (slaForm.license_id === undefined || !slaForm.period_start || !slaForm.period_end) {
    ElMessage.warning(t('admin.system.monitoring.slaRequired'))
    return
  }
  slaSaving.value = true
  try {
    await monitoringApi.computeSla({
      license_id: slaForm.license_id,
      period_start: slaForm.period_start,
      period_end: slaForm.period_end,
      target_percentage: slaForm.target_percentage,
    })
    ElMessage.success(t('admin.system.monitoring.slaComputed'))
    slaFormVisible.value = false
    await slaLoad()
    await loadStats()
  } finally {
    slaSaving.value = false
  }
}

async function onDeleteSla(row: SLAItem) {
  await ElMessageBox.confirm(
    t('admin.system.monitoring.deleteSlaConfirm', {name: row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await monitoringApi.removeSlaReport(row.id)
  ElMessage.success(t('admin.common.delete'))
  await slaLoad()
  await loadStats()
}

const slaStatCards = computed(() => [
  {key: 'total_reports', value: slaStats.value?.total_reports ?? 0},
  {key: 'compliant', value: slaStats.value?.compliant ?? 0},
  {key: 'breached', value: slaStats.value?.breached ?? 0},
  {key: 'compliance_rate', value: slaStats.value?.compliance_rate ?? 0},
  {key: 'avg_uptime_percentage', value: slaStats.value?.avg_uptime_percentage ?? '-'},
])

onMounted(() => {
  loadStats().catch(() => undefined)
})
</script>

<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- 告警 -->
      <el-tab-pane :label="$t('admin.system.monitoring.alerts')" name="alert">
        <el-card shadow="never">
          <div class="stats-grid">
            <div v-for="card in alertStatCards" :key="card.key" class="stats-card">
              <div class="stats-card__label">{{ $t(`admin.system.monitoring.alertStat_${card.key}`) }}</div>
              <div class="stats-card__value">{{ card.value }}</div>
            </div>
          </div>

          <el-form :inline="true" :model="alertQuery" class="mt-3" @submit.prevent="alertSearch()">
            <el-form-item :label="$t('admin.system.monitoring.keyword')">
              <el-input v-model="alertQuery.keyword" clearable style="width: 180px"
                        @keyup.enter="alertSearch()"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.monitoring.severity')">
              <el-select v-model="alertQuery.severity" clearable style="width: 140px">
                <el-option v-for="item in SEVERITIES" :key="item" :label="item" :value="item"/>
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('admin.system.monitoring.isResolved')">
              <el-select v-model="alertQuery.is_resolved" clearable style="width: 120px">
                <el-option :label="$t('admin.common.yes')" :value="true"/>
                <el-option :label="$t('admin.common.no')" :value="false"/>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="alertSearch()">
                {{ $t('admin.common.search') }}
              </el-button>
              <el-button :icon="Refresh" @click="alertReset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>

          <div class="table-toolbar">
            <el-button v-auth="'module_system:monitor:manage'" :icon="Plus" type="primary"
                       @click="openAlertCreate">
              {{ $t('admin.system.monitoring.createAlert') }}
            </el-button>
            <el-button :icon="Refresh" @click="loadStats()">{{ $t('admin.common.refresh') }}</el-button>
            <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: alertTotal}) }}</span>
          </div>

          <AdminTableSkeleton v-if="alertLoading && !alertList.length" :rows="5"/>

          <AdminEmpty
            v-else-if="!alertLoading && !alertList.length"
            :title="alertFailed ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
            :variant="alertFailed ? 'error' : 'default'"
          >
            <el-button v-if="alertFailed" :icon="Refresh" @click="alertLoad()">
              {{ $t('admin.common.retry') }}
            </el-button>
          </AdminEmpty>
          <el-table v-else v-loading="alertLoading" :data="alertList" border stripe>
            <el-table-column :label="$t('admin.system.monitoring.alertType')" min-width="140"
                             prop="alert_type"/>
            <el-table-column :label="$t('admin.system.monitoring.severity')" align="center" width="110">
              <template #default="{ row }">
                <el-tag :type="(SEVERITY_TAG[(row as AlertItem).severity || ''] || 'info') as never"
                        size="small">
                  {{ (row as AlertItem).severity }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.system.monitoring.alertTitle')" min-width="160" prop="title"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.system.monitoring.alertMessage')" min-width="200"
                             prop="message" show-overflow-tooltip/>
            <el-table-column :label="$t('admin.system.monitoring.source')" min-width="120" prop="source"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.system.monitoring.isResolved')" align="center" width="100">
              <template #default="{ row }">
                <el-tag :type="(row as AlertItem).is_resolved ? 'success' : 'warning'" size="small">
                  {{ (row as AlertItem).is_resolved ? $t('admin.common.yes') : $t('admin.common.no') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.system.monitoring.createdAt')" min-width="170"
                             prop="created_at"/>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="160">
              <template #default="{ row }">
                <el-button v-auth="'module_system:monitor:manage'" :disabled="(row as AlertItem).is_resolved"
                           link type="success" @click="onResolveAlert(row as AlertItem)">
                  {{ $t('admin.system.monitoring.resolve') }}
                </el-button>
                <el-button v-auth="'module_system:monitor:manage'" :icon="Delete" link type="danger"
                           @click="onDeleteAlert(row as AlertItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination :current-page="alertPage" :page-size="alertPageSize"
                         :page-sizes="[10, 20, 50, 100]" :total="alertTotal" background
                         class="table-pagination" layout="total, sizes, prev, pager, next, jumper"
                         @current-change="onAlertPageChange" @size-change="onAlertSizeChange"/>
        </el-card>
      </el-tab-pane>

      <!-- 指标 -->
      <el-tab-pane :label="$t('admin.system.monitoring.metrics')" name="metric">
        <el-card shadow="never">
          <el-form :inline="true" :model="metricQuery" @submit.prevent="metricSearch()">
            <el-form-item :label="$t('admin.system.monitoring.keyword')">
              <el-input v-model="metricQuery.keyword" clearable style="width: 180px"
                        @keyup.enter="metricSearch()"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.monitoring.metricType')">
              <el-input v-model="metricQuery.metric_type" clearable style="width: 140px"
                        @keyup.enter="metricSearch()"/>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="metricSearch()">
                {{ $t('admin.common.search') }}
              </el-button>
              <el-button :icon="Refresh" @click="metricReset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>

          <div class="table-toolbar">
            <el-button v-auth="'module_system:monitor:manage'" :icon="Plus" type="primary"
                       @click="openMetricCreate">
              {{ $t('admin.system.monitoring.createMetric') }}
            </el-button>
            <el-button v-auth="'module_system:monitor:manage'" :icon="Delete" @click="onPruneMetrics">
              {{ $t('admin.system.monitoring.prune') }}
            </el-button>
            <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: metricTotal}) }}</span>
          </div>

          <AdminTableSkeleton v-if="metricLoading && !metricList.length" :rows="5"/>

          <AdminEmpty
            v-else-if="!metricLoading && !metricList.length"
            :title="metricFailed ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
            :variant="metricFailed ? 'error' : 'default'"
          >
            <el-button v-if="metricFailed" :icon="Refresh" @click="metricLoad()">
              {{ $t('admin.common.retry') }}
            </el-button>
          </AdminEmpty>

          <el-table v-else v-loading="metricLoading" :data="metricList" border stripe>
            <el-table-column :label="$t('admin.system.monitoring.metricName')" min-width="180"
                             prop="metric_name"/>
            <el-table-column :label="$t('admin.system.monitoring.metricValue')" align="right" prop="metric_value"
                             width="130"/>
            <el-table-column :label="$t('admin.system.monitoring.metricType')" prop="metric_type"
                             width="140"/>
            <el-table-column :label="$t('admin.system.monitoring.timestamp')" min-width="170"
                             prop="timestamp"/>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="100">
              <template #default="{ row }">
                <el-button v-auth="'module_system:monitor:manage'" :icon="Delete" link type="danger"
                           @click="onDeleteMetric(row as MetricItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination :current-page="metricPage" :page-size="metricPageSize"
                         :page-sizes="[10, 20, 50, 100]" :total="metricTotal" background
                         class="table-pagination" layout="total, sizes, prev, pager, next, jumper"
                         @current-change="onMetricPageChange" @size-change="onMetricSizeChange"/>

          <el-divider/>
          <div class="table-toolbar">
            <span class="table-toolbar__title">{{ $t('admin.system.monitoring.series') }}</span>
            <el-input v-model="seriesForm.metric_name"
                      :placeholder="$t('admin.system.monitoring.metricNamePlaceholder')"
                      style="width: 220px"/>
            <el-select v-model="seriesForm.bucket" style="width: 120px">
              <el-option v-for="item in BUCKETS" :key="item" :label="item" :value="item"/>
            </el-select>
            <el-button :icon="TrendCharts" :loading="seriesLoading" @click="loadSeries">
              {{ $t('admin.system.monitoring.showSeries') }}
            </el-button>
          </div>
          <el-table :data="series?.points ?? []" border size="small" stripe>
            <el-table-column :label="$t('admin.system.monitoring.bucket')" min-width="180" prop="bucket"/>
            <el-table-column :label="$t('admin.system.monitoring.avg')" prop="avg" width="110"/>
            <el-table-column :label="$t('admin.system.monitoring.min')" prop="min" width="110"/>
            <el-table-column :label="$t('admin.system.monitoring.max')" prop="max" width="110"/>
            <el-table-column :label="$t('admin.system.monitoring.count')" prop="count" width="90"/>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- SLA -->
      <el-tab-pane :label="$t('admin.system.monitoring.sla')" name="sla">
        <el-card shadow="never">
          <div class="stats-grid">
            <div v-for="card in slaStatCards" :key="card.key" class="stats-card">
              <div class="stats-card__label">{{ $t(`admin.system.monitoring.slaStat_${card.key}`) }}</div>
              <div class="stats-card__value">{{ card.value }}</div>
            </div>
          </div>

          <div class="table-toolbar mt-3">
            <el-button v-auth="'module_system:monitor:manage'" :icon="Plus" type="primary"
                       @click="openSlaCompute">
              {{ $t('admin.system.monitoring.computeSla') }}
            </el-button>
            <el-button :icon="Refresh" @click="loadStats()">{{ $t('admin.common.refresh') }}</el-button>
            <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: slaTotal}) }}</span>
          </div>

          <AdminTableSkeleton v-if="slaLoading && !slaList.length" :rows="5"/>

          <AdminEmpty
            v-else-if="!slaLoading && !slaList.length"
            :title="slaFailed ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
            :variant="slaFailed ? 'error' : 'default'"
          >
            <el-button v-if="slaFailed" :icon="Refresh" @click="slaLoad()">
              {{ $t('admin.common.retry') }}
            </el-button>
          </AdminEmpty>

          <el-table v-else v-loading="slaLoading" :data="slaList" border stripe>
            <el-table-column :label="$t('admin.system.monitoring.licenseId')" prop="license_id"
                             width="110"/>
            <el-table-column :label="$t('admin.system.monitoring.periodStart')" min-width="170"
                             prop="period_start"/>
            <el-table-column :label="$t('admin.system.monitoring.periodEnd')" min-width="170"
                             prop="period_end"/>
            <el-table-column :label="$t('admin.system.monitoring.uptime')" align="right" prop="uptime_percentage"
                             width="110"/>
            <el-table-column :label="$t('admin.system.monitoring.target')" align="right" prop="target_percentage"
                             width="100"/>
            <el-table-column :label="$t('admin.system.monitoring.downtime')" align="right" prop="downtime_minutes"
                             width="120"/>
            <el-table-column :label="$t('admin.system.monitoring.isCompliant')" align="center" width="110">
              <template #default="{ row }">
                <el-tag :type="(row as SLAItem).is_compliant ? 'success' : 'danger'" size="small">
                  {{ (row as SLAItem).is_compliant ? $t('admin.common.yes') : $t('admin.common.no') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="100">
              <template #default="{ row }">
                <el-button v-auth="'module_system:monitor:manage'" :icon="Delete" link type="danger"
                           @click="onDeleteSla(row as SLAItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination :current-page="slaPage" :page-size="slaPageSize"
                         :page-sizes="[10, 20, 50, 100]" :total="slaTotal" background
                         class="table-pagination" layout="total, sizes, prev, pager, next, jumper"
                         @current-change="onSlaPageChange" @size-change="onSlaSizeChange"/>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 新建告警 -->
    <el-drawer v-model="alertFormVisible" :title="$t('admin.system.monitoring.createAlert')"
               destroy-on-close size="480px">
      <el-form :model="alertForm" label-width="120px">
        <el-form-item :label="$t('admin.system.monitoring.alertType')" required>
          <el-input v-model="alertForm.alert_type" placeholder="cpu / memory / disk …"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.severity')" required>
          <el-select v-model="alertForm.severity" style="width: 100%">
            <el-option v-for="item in SEVERITIES" :key="item" :label="item" :value="item"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.alertTitle')">
          <el-input v-model="alertForm.title"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.alertMessage')" required>
          <el-input v-model="alertForm.message" :autosize="{minRows: 3, maxRows: 8}" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.source')">
          <el-input v-model="alertForm.source"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.metricName')">
          <el-input v-model="alertForm.metric_name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.metricValue')">
          <el-input-number v-model="alertForm.metric_value" :precision="2" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.threshold')">
          <el-input-number v-model="alertForm.threshold" :precision="2" style="width: 100%"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="alertFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="alertSaving" type="primary" @click="submitAlert">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-drawer>

    <!-- 写入指标 -->
    <el-dialog v-model="metricFormVisible" :title="$t('admin.system.monitoring.createMetric')" width="460px">
      <el-form :model="metricForm" label-width="120px">
        <el-form-item :label="$t('admin.system.monitoring.metricName')" required>
          <el-input v-model="metricForm.metric_name" placeholder="cpu.usage / disk.free …"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.metricValue')" required>
          <el-input-number v-model="metricForm.metric_value" :precision="2" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.metricType')">
          <el-input v-model="metricForm.metric_type" placeholder="cpu / memory / disk …"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.labels')">
          <el-input v-model="metricForm.labelsText" :autosize="{minRows: 2, maxRows: 5}"
                    :placeholder="$t('admin.system.monitoring.labelsPlaceholder')" type="textarea"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="metricFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="metricSaving" type="primary" @click="submitMetric">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 计算 SLA -->
    <el-dialog v-model="slaFormVisible" :title="$t('admin.system.monitoring.computeSla')" width="520px">
      <el-alert :closable="false" :title="$t('admin.system.monitoring.computeHint')" class="mb-3"
                show-icon type="info"/>
      <el-form :model="slaForm" label-width="130px">
        <el-form-item :label="$t('admin.system.monitoring.licenseId')" required>
          <el-input-number v-model="slaForm.license_id" :min="1" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.periodStart')" required>
          <el-date-picker v-model="slaForm.period_start" style="width: 100%" type="datetime"
                          value-format="YYYY-MM-DD HH:mm:ss"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.periodEnd')" required>
          <el-date-picker v-model="slaForm.period_end" style="width: 100%" type="datetime"
                          value-format="YYYY-MM-DD HH:mm:ss"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.target')">
          <el-input-number v-model="slaForm.target_percentage" :max="100" :min="0" :precision="2"
                           :step="0.1" style="width: 100%"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="slaFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="slaSaving" type="primary" @click="submitSlaCompute">
          {{ $t('admin.system.monitoring.computeSla') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.mb-3 {
  margin-bottom: 12px;
}

.mt-3 {
  margin-top: 12px;
}

.table-toolbar__title {
  margin-right: 12px;
  font-weight: 600;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.stats-card {
  padding: 14px 16px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
}

.stats-card__label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.stats-card__value {
  margin-top: 6px;
  font-size: 20px;
  font-weight: 600;
}
</style>
