<script lang="ts" setup>
/**
 * 监控中心 · 指标面板
 *
 * 从 `pages/system/monitoring.vue` 的「指标」标签页抽出：指标时序列表
 * （过滤 / 分页 / 写入 / 按保留期清理）、「写入指标」对话框，以及下段的
 * 时序聚合查询（`metricSeries`，与上面的列表不是同一份数据）。
 *
 * 加载时机与原实现一致：指标列表由 `useAdminList` 挂载即加载；时序聚合是
 * 手动触发，挂载不发请求。
 */
import {Delete, Plus, TrendCharts} from '@element-plus/icons-vue'
import {reactive, ref} from 'vue'

import {type MetricItem, type MetricSeriesResult, monitoringApi} from '@/api'
import type {PageQuery} from '@/api/types'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {useAdminList} from '@/composables/useAdminList'

const {t} = useI18n()

const BUCKETS = ['minute', 'hour', 'day'] as const

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
</script>

<template>
  <AdminListShell
    :failed="metricFailed"
    :loading="metricLoading"
    :page="metricPage"
    :page-size="metricPageSize"
    :rows="metricList"
    :selectable="false"
    :total="metricTotal"
    @refresh="metricLoad"
    @reset="metricReset"
    @search="metricSearch"
    @page-change="onMetricPageChange"
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
</template>
