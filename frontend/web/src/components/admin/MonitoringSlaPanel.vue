<script lang="ts" setup>
/**
 * 监控中心 · SLA 面板
 *
 * 从 `pages/system/monitoring.vue` 的「SLA」标签页抽出：达标统计卡片、SLA 报表列表
 * 与「计算 SLA」对话框（按真实告警窗口合并算出宕机分钟数，`computeSla`）。
 *
 * 统计卡片的数据来自页面上的 `loadStats()`：它与告警标签页的 `alertStats` 由**同一个**
 * 批量请求填充，故卡片用 `stats` 属性读入、刷新时 `emit('refresh-stats')` 交回页面。
 *
 * 加载时机与原实现一致：SLA 列表由 `useAdminList` 挂载即加载。
 */
import {Delete, Plus, Refresh} from '@element-plus/icons-vue'
import {computed, reactive, ref} from 'vue'

import {monitoringApi, type SLAItem, type SLAStats} from '@/api'
import type {PageQuery} from '@/api/types'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {useAdminList} from '@/composables/useAdminList'

const props = defineProps<{
  /** SLA 统计（由页面上的批量 loadStats 填充） */
  stats: SLAStats | null
}>()

const emit = defineEmits<{
  (e: 'refresh-stats'): void
}>()

const {t} = useI18n()

const slaStatCards = computed(() => [
  {key: 'total_reports', value: props.stats?.total_reports ?? 0},
  {key: 'compliant', value: props.stats?.compliant ?? 0},
  {key: 'breached', value: props.stats?.breached ?? 0},
  {key: 'compliance_rate', value: props.stats?.compliance_rate ?? 0},
  {key: 'avg_uptime_percentage', value: props.stats?.avg_uptime_percentage ?? '-'},
])

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
    emit('refresh-stats')
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
  emit('refresh-stats')
}
</script>

<template>
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
    @refresh="slaLoad"
    @reset="slaReset"
    @search="slaSearch"
    @page-change="onSlaPageChange"
    @size-change="onSlaSizeChange"
  >
    <template #actions>
      <el-button v-auth="'module_system:monitor:manage'" :icon="Plus" type="primary"
                 @click="openSlaCompute">
        {{ $t('admin.system.monitoring.computeSla') }}
      </el-button>
      <el-button :icon="Refresh" @click="emit('refresh-stats')">{{ $t('admin.common.refresh') }}</el-button>
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
</template>

<style scoped>
.mb-3 {
  margin-bottom: 12px;
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
