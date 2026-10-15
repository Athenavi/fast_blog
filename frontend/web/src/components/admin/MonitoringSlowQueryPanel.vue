<script lang="ts" setup>
/**
 * 监控中心 · 慢查询与阈值面板
 *
 * 从 `pages/system/monitoring.vue` 的「慢查询与阈值」标签页抽出：阈值读写、
 * 慢查询明细 / 按表统计 / 优化建议，以及清空进程内记录。
 *
 * 加载时机与原实现一致：原页面在 `onMounted` 里 `loadSlowQueries()`，即挂载即加载
 * （`<el-tab-pane>` 默认 `lazy=false`，各面板在整页挂载时一并挂载，时机不变）。
 */
import {Search} from '@element-plus/icons-vue'
import {computed, onMounted, reactive, ref} from 'vue'

import type {SlowQueryResult} from '@/api'
import {monitoringApi} from '@/api'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

const {t} = useI18n()

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

onMounted(() => {
  loadSlowQueries().catch(() => undefined)
})
</script>

<template>
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
</template>

<style scoped>
.mt-3 {
  margin-top: 12px;
}
</style>
