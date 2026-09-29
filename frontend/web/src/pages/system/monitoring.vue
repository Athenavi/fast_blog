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
import {Delete, Plus, Refresh, TrendCharts} from '@element-plus/icons-vue'
import {Connection, MagicStick, Promotion, Search} from '@element-plus/icons-vue'
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
import type {
  AlertChannelItem,
  AlertChannelPayload,
  AlertDeliveriesResult,
  AlertPlatform,
  PerformanceReport,
  QueryExplainResult,
  QueryOptimizerAnalysis,
  SlowQueryResult,
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

// ================================================================ 告警推送渠道 / 投递 / 慢查询 / 查询优化 / 性能报告
// 字段来源逐条对照后端 `alert_channel_service.py` / `slow_query_logger.py` /
// `query_optimizer.py` / `performance_report.py`，无编造、无 mock。

// ---------------------------------------------------------------- 告警推送渠道（任务 9）
const PLATFORMS: AlertPlatform[] = ['telegram', 'discord', 'slack', 'webhook', 'email']

const channelState = useAdminList<AlertChannelItem, PageQuery & { platform?: string; is_active?: boolean }>({
  fetcher: (params) => monitoringApi.listAlertChannels(params),
  defaultQuery: {platform: '', is_active: undefined},
})

const channelList = channelState.rows
const channelLoading = channelState.loading
const channelFailed = channelState.failed
const channelTotal = channelState.total
const channelPage = channelState.page
const channelPageSize = channelState.pageSize
const channelQuery = channelState.query
const channelSearch = channelState.search
const channelReset = channelState.reset
const channelLoad = channelState.reload
const onChannelPageChange = channelState.onPageChange
const onChannelSizeChange = channelState.onSizeChange

const channelFormVisible = ref(false)
const channelSaving = ref(false)
const channelEditingId = ref<number | null>(null)
const channelForm = reactive({
  platform: 'telegram' as string,
  webhook_url: '',
  bot_token: '',
  channel_id: '',
  enable_new_article_notification: false,
  enable_comment_notification: false,
  enable_system_alert: true,
  notification_template: '',
  is_active: true,
})

function openChannelCreate() {
  Object.assign(channelForm, {
    platform: 'telegram',
    webhook_url: '',
    bot_token: '',
    channel_id: '',
    enable_new_article_notification: false,
    enable_comment_notification: false,
    enable_system_alert: true,
    notification_template: '',
    is_active: true,
  })
  channelEditingId.value = null
  channelFormVisible.value = true
}

function openChannelEdit(row: AlertChannelItem) {
  Object.assign(channelForm, {
    platform: row.platform || 'telegram',
    webhook_url: row.webhook_url || '',
    // bot_token 永不回显：留空即表示保持原值（与后端 update 约定一致）
    bot_token: '',
    channel_id: row.channel_id || '',
    enable_new_article_notification: row.enable_new_article_notification,
    enable_comment_notification: row.enable_comment_notification,
    enable_system_alert: row.enable_system_alert,
    notification_template: row.notification_template || '',
    is_active: row.is_active,
  })
  channelEditingId.value = row.id
  channelFormVisible.value = true
}

function buildChannelPayload(): AlertChannelPayload {
  const payload: AlertChannelPayload = {
    platform: channelForm.platform,
    webhook_url: channelForm.webhook_url.trim() || null,
    channel_id: channelForm.channel_id.trim() || null,
    enable_new_article_notification: channelForm.enable_new_article_notification,
    enable_comment_notification: channelForm.enable_comment_notification,
    enable_system_alert: channelForm.enable_system_alert,
    notification_template: channelForm.notification_template.trim() || null,
    is_active: channelForm.is_active,
  }
  // 仅当用户填了新 token 才下发；留空代表保持原值（后端 update 同语义）
  if (channelForm.bot_token.trim()) payload.bot_token = channelForm.bot_token.trim()
  return payload
}

async function submitChannel() {
  if (!channelForm.platform.trim()) {
    ElMessage.warning(t('admin.system.monitoring.channelRequired'))
    return
  }
  channelSaving.value = true
  try {
    if (channelEditingId.value === null) {
      await monitoringApi.createAlertChannel(buildChannelPayload())
    } else {
      await monitoringApi.updateAlertChannel(channelEditingId.value, buildChannelPayload())
    }
    ElMessage.success(t('admin.common.save'))
    channelFormVisible.value = false
    await channelLoad()
  } finally {
    channelSaving.value = false
  }
}

async function onTestChannel(row: AlertChannelItem) {
  const result = await monitoringApi.testAlertChannel(row.id)
  if (result.sent) {
    ElMessage.success(t('admin.system.monitoring.channelTestSent'))
  } else {
    ElMessage.warning(
      `${t('admin.system.monitoring.channelTestFailed')}：${result.status_code ?? '-'} ${result.detail || ''}`,
    )
  }
}

async function onDeleteChannel(row: AlertChannelItem) {
  await ElMessageBox.confirm(
    t('admin.system.monitoring.channelDeleteConfirm', {name: row.channel_id || row.platform || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await monitoringApi.removeAlertChannel(row.id)
  ElMessage.success(t('admin.common.delete'))
  await channelLoad()
}

// ---------------------------------------------------------------- 通知投递记录
const deliveryAlertId = ref<number | undefined>(undefined)
const deliveryLoading = ref(false)
const deliveries = ref<AlertDeliveriesResult | null>(null)
const dispatchForce = ref(false)
const dispatchLoading = ref(false)

async function loadDeliveries() {
  if (deliveryAlertId.value === undefined) {
    ElMessage.warning(t('admin.system.monitoring.deliveryAlertIdRequired'))
    return
  }
  deliveryLoading.value = true
  try {
    deliveries.value = await monitoringApi.alertDeliveries(deliveryAlertId.value)
  } finally {
    deliveryLoading.value = false
  }
}

async function onDispatchAlert() {
  if (deliveryAlertId.value === undefined) {
    ElMessage.warning(t('admin.system.monitoring.deliveryAlertIdRequired'))
    return
  }
  dispatchLoading.value = true
  try {
    const result = await monitoringApi.dispatchAlert(deliveryAlertId.value, dispatchForce.value)
    ElMessage.success(
      t('admin.system.monitoring.deliveryDispatched', {sent: result.sent, failed: result.failed}),
    )
    await loadDeliveries()
  } finally {
    dispatchLoading.value = false
  }
}

// ---------------------------------------------------------------- 慢查询与阈值
const slowForm = reactive({hours: 24, limit: 50, table: '', query_type: ''})
const slowLoading = ref(false)
const slowResult = ref<SlowQueryResult | null>(null)
const slowThreshold = ref<number | undefined>(undefined)
const slowThresholdSaving = ref(false)
const slowClearing = ref(false)

async function loadSlowQueries() {
  slowLoading.value = true
  try {
    const result = await monitoringApi.listSlowQueries({
      hours: slowForm.hours,
      limit: slowForm.limit,
      table: slowForm.table.trim() || undefined,
      query_type: slowForm.query_type.trim() || undefined,
    })
    slowResult.value = result
    slowThreshold.value = result.threshold_ms
  } finally {
    slowLoading.value = false
  }
}

async function onUpdateSlowThreshold() {
  if (slowThreshold.value === undefined || slowThreshold.value <= 0) {
    ElMessage.warning(t('admin.system.monitoring.slowThresholdInvalid'))
    return
  }
  slowThresholdSaving.value = true
  try {
    const result = await monitoringApi.updateSlowQueryThreshold(slowThreshold.value)
    ElMessage.success(t('admin.system.monitoring.slowThresholdUpdated'))
    slowThreshold.value = result.threshold_ms
  } finally {
    slowThresholdSaving.value = false
  }
}

/** 清空进程内慢查询记录（`DELETE /system/monitor/slow-queries`，需 manage 权限） */
async function onClearSlowQueries() {
  try {
    await ElMessageBox.confirm(
      t('admin.system.monitoring.slowClearConfirm'),
      t('admin.common.notice'),
      {type: 'warning'},
    )
  } catch {
    return
  }
  slowClearing.value = true
  try {
    await monitoringApi.clearSlowQueries()
    ElMessage.success(t('admin.system.monitoring.slowCleared'))
    await loadSlowQueries()
  } finally {
    slowClearing.value = false
  }
}

/** `by_table` 是对象，转成可渲染的行数组 */
const slowByTableRows = computed(() => {
  const byTable = slowResult.value?.statistics?.by_table ?? {}
  return Object.entries(byTable).map(([table, stat]) => ({table, ...stat}))
})

// ---------------------------------------------------------------- 查询优化
const qoForm = reactive({hours: 24, limit: 20, min_executions: 10, max_avg_duration: 0.5})
const qoLoading = ref(false)
const qoResult = ref<QueryOptimizerAnalysis | null>(null)
const explainSql = ref('')
const explainLoading = ref(false)
const explainResult = ref<QueryExplainResult | null>(null)

async function runAnalysis() {
  qoLoading.value = true
  try {
    qoResult.value = await monitoringApi.queryOptimizerAnalysis({
      hours: qoForm.hours,
      limit: qoForm.limit,
      min_executions: qoForm.min_executions,
      max_avg_duration: qoForm.max_avg_duration,
    })
  } finally {
    qoLoading.value = false
  }
}

async function runExplain() {
  if (!explainSql.value.trim()) {
    ElMessage.warning(t('admin.system.monitoring.qoExplainRequired'))
    return
  }
  explainLoading.value = true
  try {
    explainResult.value = await monitoringApi.queryOptimizerExplain(explainSql.value.trim())
  } finally {
    explainLoading.value = false
  }
}

/** `node_types` 是对象，转成可渲染的行数组 */
const explainNodeRows = computed(() => {
  const nodeTypes = explainResult.value?.analysis?.node_types ?? {}
  return Object.entries(nodeTypes).map(([node_type, count]) => ({node_type, count}))
})

// ---------------------------------------------------------------- 性能综合报告
const perfForm = reactive({hours: 24, top: 5})
const perfLoading = ref(false)
const perfReport = ref<PerformanceReport | null>(null)

async function loadPerformanceReport() {
  perfLoading.value = true
  try {
    perfReport.value = await monitoringApi.performanceReport({
      hours: perfForm.hours,
      top: perfForm.top,
    })
  } finally {
    perfLoading.value = false
  }
}

// 页面挂载后并行加载新的只读视图（渠道列表已由 useAdminList 自动加载）
onMounted(() => {
  loadSlowQueries().catch(() => undefined)
  runAnalysis().catch(() => undefined)
  loadPerformanceReport().catch(() => undefined)
})
</script>

<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- 告警 -->
      <el-tab-pane :label="$t('admin.system.monitoring.alerts')" name="alert">
        <div class="stats-grid">
          <div v-for="card in alertStatCards" :key="card.key" class="stats-card">
            <div class="stats-card__label">{{ $t(`admin.system.monitoring.alertStat_${card.key}`) }}</div>
            <div class="stats-card__value">{{ card.value }}</div>
          </div>
        </div>

        <AdminListShell
          :failed="alertFailed"
          :loading="alertLoading"
          :page="alertPage"
          :page-size="alertPageSize"
          :rows="alertList"
          :selectable="false"
          :total="alertTotal"
          @page-change="onAlertPageChange"
          @refresh="alertLoad"
          @reset="alertReset"
          @search="alertSearch"
          @size-change="onAlertSizeChange"
        >
          <template #filters>
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
          </template>

          <template #actions>
            <el-button v-auth="'module_system:monitor:manage'" :icon="Plus" type="primary"
                       @click="openAlertCreate">
              {{ $t('admin.system.monitoring.createAlert') }}
            </el-button>
            <el-button :icon="Refresh" @click="loadStats()">{{ $t('admin.common.refresh') }}</el-button>
          </template>

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
        </AdminListShell>
      </el-tab-pane>

      <!-- 指标 -->
      <el-tab-pane :label="$t('admin.system.monitoring.metrics')" name="metric">
        <AdminListShell
          :failed="metricFailed"
          :loading="metricLoading"
          :page="metricPage"
          :page-size="metricPageSize"
          :rows="metricList"
          :selectable="false"
          :total="metricTotal"
          @page-change="onMetricPageChange"
          @refresh="metricLoad"
          @reset="metricReset"
          @search="metricSearch"
          @size-change="onMetricSizeChange"
        >
          <template #filters>
            <el-form-item :label="$t('admin.system.monitoring.keyword')">
              <el-input v-model="metricQuery.keyword" clearable style="width: 180px"
                        @keyup.enter="metricSearch()"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.monitoring.metricType')">
              <el-input v-model="metricQuery.metric_type" clearable style="width: 140px"
                        @keyup.enter="metricSearch()"/>
            </el-form-item>
          </template>

          <template #actions>
            <el-button v-auth="'module_system:monitor:manage'" :icon="Plus" type="primary"
                       @click="openMetricCreate">
              {{ $t('admin.system.monitoring.createMetric') }}
            </el-button>
            <el-button v-auth="'module_system:monitor:manage'" :icon="Delete" @click="onPruneMetrics">
              {{ $t('admin.system.monitoring.prune') }}
            </el-button>
          </template>

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
        </AdminListShell>

        <!-- 时序聚合：与上面的指标列表不是同一份数据，单独一块 -->
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
      </el-tab-pane>

      <!-- SLA -->
      <el-tab-pane :label="$t('admin.system.monitoring.sla')" name="sla">
        <div class="stats-grid">
          <div v-for="card in slaStatCards" :key="card.key" class="stats-card">
            <div class="stats-card__label">{{ $t(`admin.system.monitoring.slaStat_${card.key}`) }}</div>
            <div class="stats-card__value">{{ card.value }}</div>
          </div>
        </div>

        <AdminListShell
          :failed="slaFailed"
          :loading="slaLoading"
          :page="slaPage"
          :page-size="slaPageSize"
          :rows="slaList"
          :selectable="false"
          :total="slaTotal"
          @page-change="onSlaPageChange"
          @refresh="slaLoad"
          @reset="slaReset"
          @search="slaSearch"
          @size-change="onSlaSizeChange"
        >
          <template #actions>
            <el-button v-auth="'module_system:monitor:manage'" :icon="Plus" type="primary"
                       @click="openSlaCompute">
              {{ $t('admin.system.monitoring.computeSla') }}
            </el-button>
            <el-button :icon="Refresh" @click="loadStats()">{{ $t('admin.common.refresh') }}</el-button>
          </template>

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
        </AdminListShell>
      </el-tab-pane>

      <!-- 告警推送渠道（追加） -->
      <el-tab-pane :label="$t('admin.system.monitoring.tabAlertChannel')" name="alertChannel">
        <AdminListShell
          :failed="channelFailed"
          :loading="channelLoading"
          :page="channelPage"
          :page-size="channelPageSize"
          :rows="channelList"
          :selectable="false"
          :total="channelTotal"
          @refresh="channelLoad"
          @reset="channelReset"
          @search="channelSearch"
          @page-change="onChannelPageChange"
          @size-change="onChannelSizeChange"
        >
          <template #filters>
            <el-form-item :label="$t('admin.system.monitoring.channelPlatform')">
              <el-select v-model="channelQuery.platform" clearable style="width: 160px">
                <el-option v-for="item in PLATFORMS" :key="item" :label="item" :value="item"/>
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('admin.system.monitoring.channelActive')">
              <el-select v-model="channelQuery.is_active" clearable style="width: 120px">
                <el-option :label="$t('admin.common.yes')" :value="true"/>
                <el-option :label="$t('admin.common.no')" :value="false"/>
              </el-select>
            </el-form-item>
          </template>

          <template #actions>
            <el-button v-auth="'module_system:monitor:manage'" :icon="Plus" type="primary"
                       @click="openChannelCreate">
              {{ $t('admin.system.monitoring.channelCreate') }}
            </el-button>
          </template>

          <el-table-column :label="$t('admin.system.monitoring.channelPlatform')" prop="platform"
                           width="120"/>
          <el-table-column :label="$t('admin.system.monitoring.channelChatId')" min-width="160"
                           prop="channel_id" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.monitoring.channelWebhookUrl')" min-width="220"
                           prop="webhook_url" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.monitoring.channelHasToken')" align="center" width="120">
            <template #default="{ row }">
              <el-tag :type="(row as AlertChannelItem).has_token ? 'success' : 'info'" size="small">
                {{ (row as AlertChannelItem).has_token ? $t('admin.common.yes') : $t('admin.common.no') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.system.monitoring.channelEnableSystemAlert')" align="center"
                           width="140">
            <template #default="{ row }">
              <el-tag :type="(row as AlertChannelItem).enable_system_alert ? 'success' : 'info'" size="small">
                {{ (row as AlertChannelItem).enable_system_alert ? $t('admin.common.yes') : $t('admin.common.no') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.system.monitoring.channelActive')" align="center" width="100">
            <template #default="{ row }">
              <el-tag :type="(row as AlertChannelItem).is_active ? 'success' : 'info'" size="small">
                {{ (row as AlertChannelItem).is_active ? $t('admin.common.yes') : $t('admin.common.no') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.common.actions')" fixed="right" width="220">
            <template #default="{ row }">
              <el-button v-auth="'module_system:monitor:manage'" :icon="Promotion" link type="primary"
                         @click="onTestChannel(row as AlertChannelItem)">
                {{ $t('admin.system.monitoring.channelTest') }}
              </el-button>
              <el-button v-auth="'module_system:monitor:manage'" link type="success"
                         @click="openChannelEdit(row as AlertChannelItem)">
                {{ $t('admin.common.edit') }}
              </el-button>
              <el-button v-auth="'module_system:monitor:manage'" :icon="Delete" link type="danger"
                         @click="onDeleteChannel(row as AlertChannelItem)">
                {{ $t('admin.common.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </AdminListShell>
      </el-tab-pane>

      <!-- 通知投递记录（追加） -->
      <el-tab-pane :label="$t('admin.system.monitoring.tabDeliveries')" name="deliveries">
        <div class="table-toolbar">
          <span class="table-toolbar__title">{{ $t('admin.system.monitoring.deliveryAlertId') }}</span>
          <el-input-number v-model="deliveryAlertId" :min="1" style="width: 160px"/>
          <el-button :icon="Search" :loading="deliveryLoading" @click="loadDeliveries">
            {{ $t('admin.system.monitoring.deliveryQuery') }}
          </el-button>
          <el-button v-auth="'module_system:monitor:manage'" :icon="Promotion" :loading="dispatchLoading"
                     type="primary" @click="onDispatchAlert">
            {{ $t('admin.system.monitoring.deliveryDispatch') }}
          </el-button>
          <el-checkbox v-model="dispatchForce" v-auth="'module_system:monitor:manage'">
            {{ $t('admin.system.monitoring.deliveryForce') }}
          </el-checkbox>
        </div>

        <el-descriptions v-if="deliveries" :border="true" :column="3" class="mt-3">
          <el-descriptions-item :label="$t('admin.system.monitoring.deliveryAlertId')">
            {{ deliveries.alert_id }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.system.monitoring.deliveryTotal')">
            {{ deliveries.total }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.system.monitoring.deliverySent')">
            {{ deliveries.sent }}
          </el-descriptions-item>
        </el-descriptions>

        <el-table v-if="deliveries" :data="deliveries.items" border class="mt-3" size="small" stripe>
          <el-table-column :label="$t('admin.system.monitoring.deliveryPlatform')" prop="platform"
                           width="120"/>
          <el-table-column :label="$t('admin.system.monitoring.deliveryStatus')" align="center" width="100">
            <template #default="{ row }">
              <el-tag :type="row.sent ? 'success' : 'danger'" size="small">
                {{ row.sent ? $t('admin.common.yes') : $t('admin.common.no') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.system.monitoring.deliveryStatusCode')" align="center"
                           prop="status_code" width="100"/>
          <el-table-column :label="$t('admin.system.monitoring.deliveryDetail')" min-width="260"
                           prop="detail" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.monitoring.deliveryAt')" min-width="180" prop="at"/>
        </el-table>
        <el-empty v-else :description="$t('admin.system.monitoring.deliveryEmpty')"/>
      </el-tab-pane>

      <!-- 慢查询与阈值 -->
      <el-tab-pane :label="$t('admin.system.monitoring.tabSlowQuery')" name="slowQuery">
        <div class="table-toolbar">
          <span class="table-toolbar__title">{{ $t('admin.system.monitoring.slowThreshold') }}</span>
          <el-input-number v-model="slowThreshold" :max="60000" :min="1" style="width: 160px"/>
          <el-button v-auth="'module_system:monitor:manage'" :loading="slowThresholdSaving"
                     @click="onUpdateSlowThreshold">
            {{ $t('admin.system.monitoring.slowThresholdUpdate') }}
          </el-button>
        </div>

        <el-divider/>

        <div class="table-toolbar">
          <el-form-item :label="$t('admin.system.monitoring.slowHours')">
            <el-input-number v-model="slowForm.hours" :max="720" :min="1" style="width: 130px"/>
          </el-form-item>
          <el-form-item :label="$t('admin.system.monitoring.slowLimit')">
            <el-input-number v-model="slowForm.limit" :max="500" :min="1" style="width: 120px"/>
          </el-form-item>
          <el-form-item :label="$t('admin.system.monitoring.slowTable')">
            <el-input v-model="slowForm.table" clearable style="width: 160px"/>
          </el-form-item>
          <el-form-item :label="$t('admin.system.monitoring.slowQueryType')">
            <el-input v-model="slowForm.query_type" clearable placeholder="SELECT / UPDATE" style="width: 160px"/>
          </el-form-item>
          <el-button :icon="Search" :loading="slowLoading" @click="loadSlowQueries">
            {{ $t('admin.system.monitoring.slowLoad') }}
          </el-button>
          <el-button v-auth="'module_system:monitor:manage'" :loading="slowClearing" type="danger"
                     @click="onClearSlowQueries">
            {{ $t('admin.system.monitoring.slowClear') }}
          </el-button>
        </div>

        <el-descriptions v-if="slowResult" :border="true" :column="4" class="mt-3">
          <el-descriptions-item :label="$t('admin.system.monitoring.slowStatTotal')">
            {{ slowResult.statistics.slow_queries }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.system.monitoring.slowStatAvg')">
            {{ slowResult.statistics.avg_duration }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.system.monitoring.slowStatMax')">
            {{ slowResult.statistics.max_duration }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.system.monitoring.slowThreshold')">
            {{ slowResult.threshold_ms }}
          </el-descriptions-item>
        </el-descriptions>

        <el-table :data="slowResult?.items ?? []" border class="mt-3" size="small" stripe>
          <el-table-column :label="$t('admin.system.monitoring.slowSql')" min-width="320" prop="sql"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.monitoring.slowDuration')" align="right" prop="duration"
                           width="110"/>
          <el-table-column :label="$t('admin.system.monitoring.slowTable')" prop="table" show-overflow-tooltip
                           width="150"/>
          <el-table-column :label="$t('admin.system.monitoring.slowQueryType')" prop="query_type"
                           width="110"/>
          <el-table-column :label="$t('admin.system.monitoring.slowTimestamp')" min-width="180"
                           prop="timestamp"/>
        </el-table>

        <el-divider/>
        <div class="table-toolbar">
          <span class="table-toolbar__title">{{ $t('admin.system.monitoring.slowByTable') }}</span>
        </div>
        <el-table :data="slowByTableRows" border size="small" stripe>
          <el-table-column :label="$t('admin.system.monitoring.slowTable')" min-width="180" prop="table"/>
          <el-table-column :label="$t('admin.system.monitoring.slowCount')" align="right" prop="count"
                           width="100"/>
          <el-table-column :label="$t('admin.system.monitoring.slowTotalTime')" align="right" prop="total_time"
                           width="130"/>
          <el-table-column :label="$t('admin.system.monitoring.slowAvgTime')" align="right" prop="avg_time"
                           width="130"/>
          <el-table-column :label="$t('admin.system.monitoring.slowMaxTime')" align="right" prop="max_time"
                           width="130"/>
        </el-table>

        <el-divider/>
        <div class="table-toolbar">
          <span class="table-toolbar__title">{{ $t('admin.system.monitoring.slowSuggestions') }}</span>
        </div>
        <el-table :data="slowResult?.suggestions ?? []" border size="small" stripe>
          <el-table-column :label="$t('admin.system.monitoring.slowSuggestionType')" prop="type"
                           width="110"/>
          <el-table-column :label="$t('admin.system.monitoring.slowSuggestionTitle')" min-width="160"
                           prop="title"/>
          <el-table-column :label="$t('admin.system.monitoring.slowSuggestionMessage')" min-width="240"
                           prop="message" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.monitoring.slowSuggestionRecommendation')" min-width="240"
                           prop="recommendation" show-overflow-tooltip/>
        </el-table>
      </el-tab-pane>

      <!-- 查询优化（追加） -->
      <el-tab-pane :label="$t('admin.system.monitoring.tabQueryOptimizer')" name="queryOptimizer">
        <div class="table-toolbar">
          <el-form-item :label="$t('admin.system.monitoring.qoHours')">
            <el-input-number v-model="qoForm.hours" :max="720" :min="1" style="width: 130px"/>
          </el-form-item>
          <el-form-item :label="$t('admin.system.monitoring.qoLimit')">
            <el-input-number v-model="qoForm.limit" :max="200" :min="1" style="width: 120px"/>
          </el-form-item>
          <el-form-item :label="$t('admin.system.monitoring.qoMinExecutions')">
            <el-input-number v-model="qoForm.min_executions" :max="1000" :min="2" style="width: 120px"/>
          </el-form-item>
          <el-form-item :label="$t('admin.system.monitoring.qoMaxAvgDuration')">
            <el-input-number v-model="qoForm.max_avg_duration" :max="60" :min="0.01" :precision="2"
                             :step="0.1" style="width: 130px"/>
          </el-form-item>
          <el-button :icon="TrendCharts" :loading="qoLoading" @click="runAnalysis">
            {{ $t('admin.system.monitoring.qoAnalyze') }}
          </el-button>
        </div>

        <el-divider/>
        <div class="table-toolbar">
          <span class="table-toolbar__title">{{ $t('admin.system.monitoring.qoFingerprints') }}</span>
        </div>
        <el-table :data="qoResult?.by_fingerprint ?? []" border size="small" stripe>
          <el-table-column :label="$t('admin.system.monitoring.qoFingerprint')" min-width="320"
                           prop="fingerprint" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.monitoring.slowTable')" prop="table" width="150"/>
          <el-table-column :label="$t('admin.system.monitoring.qoExecutions')" align="right" prop="executions"
                           width="110"/>
          <el-table-column :label="$t('admin.system.monitoring.qoTotalDuration')" align="right" prop="total_duration"
                           width="130"/>
          <el-table-column :label="$t('admin.system.monitoring.qoAvgDuration')" align="right" prop="avg_duration"
                           width="130"/>
          <el-table-column :label="$t('admin.system.monitoring.qoMaxDuration')" align="right" prop="max_duration"
                           width="130"/>
        </el-table>

        <el-divider/>
        <div class="table-toolbar">
          <span class="table-toolbar__title">{{ $t('admin.system.monitoring.qoNPlusOne') }}</span>
        </div>
        <el-table :data="qoResult?.n_plus_one ?? []" border size="small" stripe>
          <el-table-column :label="$t('admin.system.monitoring.qoFingerprint')" min-width="280"
                           prop="fingerprint" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.monitoring.qoExecutions')" align="right" prop="executions"
                           width="110"/>
          <el-table-column :label="$t('admin.system.monitoring.qoTotalDuration')" align="right" prop="total_duration"
                           width="130"/>
          <el-table-column :label="$t('admin.system.monitoring.slowSuggestionRecommendation')" min-width="260"
                           prop="hint" show-overflow-tooltip/>
        </el-table>

        <el-divider/>
        <div class="table-toolbar">
          <span class="table-toolbar__title">{{ $t('admin.system.monitoring.slowSuggestions') }}</span>
        </div>
        <el-table :data="qoResult?.suggestions ?? []" border size="small" stripe>
          <el-table-column :label="$t('admin.system.monitoring.slowSuggestionType')" prop="type"
                           width="110"/>
          <el-table-column :label="$t('admin.system.monitoring.slowSuggestionTitle')" min-width="160"
                           prop="title"/>
          <el-table-column :label="$t('admin.system.monitoring.slowSuggestionMessage')" min-width="240"
                           prop="message" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.monitoring.slowSuggestionRecommendation')" min-width="240"
                           prop="recommendation" show-overflow-tooltip/>
        </el-table>

        <el-divider/>
        <div class="table-toolbar">
          <span class="table-toolbar__title">{{ $t('admin.system.monitoring.qoExplainTitle') }}</span>
        </div>
        <el-input v-model="explainSql" :autosize="{minRows: 3, maxRows: 10}"
                  :placeholder="$t('admin.system.monitoring.qoExplainPlaceholder')" type="textarea"/>
        <div class="table-toolbar mt-3">
          <el-button v-auth="'module_system:monitor:manage'" :icon="MagicStick" :loading="explainLoading"
                     type="primary" @click="runExplain">
            {{ $t('admin.system.monitoring.qoExplainRun') }}
          </el-button>
        </div>

        <template v-if="explainResult">
          <el-descriptions :border="true" :column="3" class="mt-3">
            <el-descriptions-item :label="$t('admin.system.monitoring.qoExplainParsed')">
              {{ explainResult.analysis.parsed ? $t('admin.common.yes') : $t('admin.common.no') }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.monitoring.qoExplainExecuted')">
              {{ explainResult.executed ? $t('admin.common.yes') : $t('admin.common.no') }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.monitoring.qoExplainSeqScan')">
              {{ explainResult.analysis.uses_sequential_scan ? $t('admin.common.yes') : $t('admin.common.no') }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.monitoring.qoExplainSeqTables')" :span="3">
              {{ explainResult.analysis.sequential_scan_tables.join('、') || '-' }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="table-toolbar mt-3">
            <span class="table-toolbar__title">{{ $t('admin.system.monitoring.qoExplainNodeTypes') }}</span>
          </div>
          <el-table :data="explainNodeRows" border size="small" stripe>
            <el-table-column label="Node Type" min-width="200" prop="node_type"/>
            <el-table-column :label="$t('admin.system.monitoring.count')" align="right" prop="count"
                             width="100"/>
          </el-table>

          <div class="table-toolbar mt-3">
            <span class="table-toolbar__title">{{ $t('admin.system.monitoring.qoExplainBottlenecks') }}</span>
          </div>
          <el-table :data="explainResult.analysis.bottlenecks" border size="small" stripe>
            <el-table-column label="Node Type" min-width="160" prop="node_type"/>
            <el-table-column :label="$t('admin.system.monitoring.slowTable')" min-width="140"
                             prop="relation"/>
            <el-table-column align="right" label="Total Cost" prop="total_cost" width="120"/>
            <el-table-column align="right" label="Plan Rows" prop="plan_rows" width="120"/>
            <el-table-column align="right" label="Actual Time (ms)" prop="actual_time_ms" width="150"/>
          </el-table>

          <div class="table-toolbar mt-3">
            <span class="table-toolbar__title">{{ $t('admin.system.monitoring.qoExplainRecommendations') }}</span>
          </div>
          <ul class="mt-3">
            <li v-for="(item, idx) in explainResult.analysis.recommendations" :key="idx">{{ item }}</li>
          </ul>
        </template>
      </el-tab-pane>

      <!-- 性能综合报告（追加） -->
      <el-tab-pane :label="$t('admin.system.monitoring.tabPerformance')" name="performanceReport">
        <div class="table-toolbar">
          <el-form-item :label="$t('admin.system.monitoring.perfHours')">
            <el-input-number v-model="perfForm.hours" :max="720" :min="1" style="width: 130px"/>
          </el-form-item>
          <el-form-item :label="$t('admin.system.monitoring.perfTop')">
            <el-input-number v-model="perfForm.top" :max="50" :min="1" style="width: 120px"/>
          </el-form-item>
          <el-button :icon="TrendCharts" :loading="perfLoading" @click="loadPerformanceReport">
            {{ $t('admin.system.monitoring.perfGenerate') }}
          </el-button>
        </div>

        <template v-if="perfReport">
          <el-descriptions :border="true" :column="2" class="mt-3">
            <el-descriptions-item :label="$t('admin.system.monitoring.perfGeneratedAt')">
              {{ perfReport.generated_at }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.monitoring.perfHours')">
              {{ perfReport.period_hours }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- RUM -->
          <div class="table-toolbar mt-3">
            <span class="table-toolbar__title">{{ $t('admin.system.monitoring.perfRum') }}</span>
          </div>
          <el-descriptions :border="true" :column="4">
            <el-descriptions-item :label="$t('admin.system.monitoring.perfTotalPages')">
              {{ perfReport.runtime.overall.total_pages }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.monitoring.perfTotalSamples')">
              {{ perfReport.runtime.overall.total_samples }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.monitoring.perfAvgLoad')">
              {{ perfReport.runtime.overall.avg_load_time ?? '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.monitoring.perfCwvPassRate')">
              {{ perfReport.runtime.overall.cwv_pass_rate ?? '-' }}
            </el-descriptions-item>
          </el-descriptions>
          <el-table :data="perfReport.runtime.slowest_pages" border class="mt-3" size="small" stripe>
            <el-table-column :label="$t('admin.system.monitoring.perfUrl')" min-width="320" prop="url"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.system.monitoring.perfAvgLoad')" align="right" prop="avg_load_time"
                             width="140"/>
            <el-table-column :label="$t('admin.system.monitoring.perfTotalSamples')" align="right"
                             prop="sample_count" width="120"/>
          </el-table>

          <!-- 数据库 -->
          <div class="table-toolbar mt-3">
            <span class="table-toolbar__title">{{ $t('admin.system.monitoring.perfDatabase') }}</span>
          </div>
          <el-descriptions :border="true" :column="4">
            <el-descriptions-item :label="$t('admin.system.monitoring.slowStatTotal')">
              {{ perfReport.database.statistics.slow_queries }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.monitoring.slowThreshold')">
              {{ perfReport.database.threshold_ms }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.monitoring.qoNPlusOne')">
              {{ perfReport.database.n_plus_one.length }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.monitoring.qoFingerprints')">
              {{ perfReport.database.top_fingerprints.length }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- 服务器 -->
          <div class="table-toolbar mt-3">
            <span class="table-toolbar__title">{{ $t('admin.system.monitoring.perfServer') }}</span>
          </div>
          <el-descriptions :border="true" :column="4">
            <el-descriptions-item label="Platform">
              {{ perfReport.server?.platform }}
            </el-descriptions-item>
            <el-descriptions-item label="Hostname">
              {{ perfReport.server?.hostname }}
            </el-descriptions-item>
            <el-descriptions-item label="Python">
              {{ perfReport.server?.python_version }}
            </el-descriptions-item>
            <el-descriptions-item label="Uptime (s)">
              {{ perfReport.server?.uptime_seconds }}
            </el-descriptions-item>
            <el-descriptions-item label="CPU (%)">
              {{ perfReport.server?.cpu?.percent }}
            </el-descriptions-item>
            <el-descriptions-item label="CPU Cores">
              {{ perfReport.server?.cpu?.count }}
            </el-descriptions-item>
            <el-descriptions-item label="Memory (%)">
              {{ perfReport.server?.memory?.percent }}
            </el-descriptions-item>
            <el-descriptions-item label="PID">
              {{ perfReport.server?.process?.pid }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- 持久态：告警 / 指标 / SLA -->
          <div class="table-toolbar mt-3">
            <span class="table-toolbar__title">{{ $t('admin.system.monitoring.perfAlerts') }}</span>
          </div>
          <el-descriptions :border="true" :column="3">
            <el-descriptions-item :label="$t('admin.system.monitoring.alertStat_total')">
              {{ perfReport.alerts.total }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.monitoring.alertStat_unresolved')">
              {{ perfReport.alerts.unresolved }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.monitoring.alertStat_resolved')">
              {{ perfReport.alerts.resolved }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="table-toolbar mt-3">
            <span class="table-toolbar__title">{{ $t('admin.system.monitoring.perfMetrics') }}</span>
          </div>
          <el-table :data="perfReport.metrics.by_type" border size="small" stripe>
            <el-table-column :label="$t('admin.system.monitoring.perfMetricType')" min-width="180"
                             prop="metric_type"/>
            <el-table-column :label="$t('admin.system.monitoring.count')" align="right" prop="count"
                             width="120"/>
            <el-table-column :label="$t('admin.system.monitoring.perfAvgValue')" align="right" prop="avg_value"
                             width="140"/>
          </el-table>

          <div class="table-toolbar mt-3">
            <span class="table-toolbar__title">{{ $t('admin.system.monitoring.perfSla') }}</span>
          </div>
          <el-descriptions :border="true" :column="3">
            <el-descriptions-item :label="$t('admin.system.monitoring.slaStat_total_reports')">
              {{ perfReport.sla.total_reports }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.monitoring.slaStat_compliant')">
              {{ perfReport.sla.compliant }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.system.monitoring.slaStat_breached')">
              {{ perfReport.sla.breached }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="table-toolbar mt-3">
            <span class="table-toolbar__title">{{ $t('admin.system.monitoring.perfNotes') }}</span>
          </div>
          <ul class="mt-3">
            <li v-for="(item, idx) in perfReport.notes" :key="idx">{{ item }}</li>
          </ul>
        </template>
        <el-empty v-else :description="$t('admin.system.monitoring.perfEmpty')"/>
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

    <!-- 新建 / 编辑告警推送渠道（追加） -->
    <el-drawer v-model="channelFormVisible"
               :title="channelEditingId === null
                 ? $t('admin.system.monitoring.channelCreate')
                 : $t('admin.system.monitoring.channelEdit')"
               destroy-on-close size="480px">
      <el-form :model="channelForm" label-width="150px">
        <el-form-item :label="$t('admin.system.monitoring.channelPlatform')" required>
          <el-select v-model="channelForm.platform" style="width: 100%">
            <el-option v-for="item in PLATFORMS" :key="item" :label="item" :value="item"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.channelWebhookUrl')">
          <el-input v-model="channelForm.webhook_url"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.channelBotToken')">
          <el-input v-model="channelForm.bot_token" show-password type="password"/>
          <div class="stats-card__label mt-3">{{ $t('admin.system.monitoring.channelBotTokenHint') }}</div>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.channelChatId')">
          <el-input v-model="channelForm.channel_id"/>
          <div class="stats-card__label mt-3">{{ $t('admin.system.monitoring.channelChatIdHint') }}</div>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.channelTemplate')">
          <el-input v-model="channelForm.notification_template"
                    :autosize="{minRows: 2, maxRows: 6}" type="textarea"/>
          <div class="stats-card__label mt-3">{{ $t('admin.system.monitoring.channelTemplateHint') }}</div>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.channelEnableSystemAlert')">
          <el-switch v-model="channelForm.enable_system_alert"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.channelEnableNewArticle')">
          <el-switch v-model="channelForm.enable_new_article_notification"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.channelEnableComment')">
          <el-switch v-model="channelForm.enable_comment_notification"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.monitoring.channelActive')">
          <el-switch v-model="channelForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="channelFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="channelSaving" type="primary" @click="submitChannel">
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

.mt-3 {
  margin-top: 12px;
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
