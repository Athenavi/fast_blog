<script lang="ts" setup>
/**
 * 监控中心 · 告警面板
 *
 * 从 `pages/system/monitoring.vue` 的「告警」标签页抽出：统计卡片、告警列表
 * （过滤 / 分页 / 解决 / 删除）与「新建告警」抽屉（原页面把抽屉放在 `</el-tabs>`
 * 之外，但触发它的按钮就在本标签页的工具栏里，所以跟着一起搬过来）。
 *
 * 统计卡片的数据来自页面上的 `loadStats()`：它与 SLA 标签页的 `slaStats` 由**同一个**
 * 批量请求填充，故卡片用 `stats` 属性读入、刷新时 `emit('refresh-stats')` 交回页面，
 * 保持原实现"一次请求同时刷新两组卡片"的行为。
 *
 * 加载时机与原实现一致：原页面没有 `@tab-change`，告警列表由 `useAdminList` 挂载即加载。
 */
import {Delete, Plus, Refresh} from '@element-plus/icons-vue'
import {computed, reactive, ref} from 'vue'

import {type AlertItem, type AlertStats, monitoringApi} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

const props = defineProps<{
  /** 告警统计（由页面上的批量 loadStats 填充） */
  stats: AlertStats | null
}>()

const emit = defineEmits<{
  (e: 'refresh-stats'): void
}>()

const {t} = useI18n()

const SEVERITIES = ['info', 'warning', 'error', 'critical'] as const
const SEVERITY_TAG: Record<string, string> = {
  info: 'info',
  warning: 'warning',
  error: 'danger',
  critical: 'danger',
}

const alertStatCards = computed(() => [
  {key: 'total', value: props.stats?.total ?? 0},
  {key: 'unresolved', value: props.stats?.unresolved ?? 0},
  {key: 'resolved', value: props.stats?.resolved ?? 0},
])

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
    emit('refresh-stats')
  } finally {
    alertSaving.value = false
  }
}

async function onResolveAlert(row: AlertItem) {
  await monitoringApi.resolveAlert(row.id)
  ElMessage.success(t('admin.system.monitoring.resolved'))
  await alertLoad()
  emit('refresh-stats')
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
  emit('refresh-stats')
}
</script>

<template>
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
    @refresh="alertLoad"
    @reset="alertReset"
    @search="alertSearch"
    @page-change="onAlertPageChange"
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
      <el-button :icon="Refresh" @click="emit('refresh-stats')">{{ $t('admin.common.refresh') }}</el-button>
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
</template>

<style scoped>
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
