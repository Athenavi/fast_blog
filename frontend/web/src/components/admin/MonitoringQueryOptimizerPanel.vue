<script lang="ts" setup>
/**
 * 监控中心 · 查询优化面板
 *
 * 从 `pages/system/monitoring.vue` 的「查询优化」标签页抽出：指纹聚合、N+1 检测、
 * 优化建议与 `EXPLAIN` 分析（`queryOptimizerExplain`）。
 *
 * 加载时机与原实现一致：原页面在 `onMounted` 里 `runAnalysis()`，即挂载即加载。
 */
import {MagicStick, TrendCharts} from '@element-plus/icons-vue'
import {computed, onMounted, reactive, ref} from 'vue'

import type {QueryExplainResult, QueryOptimizerAnalysis} from '@/api'
import {monitoringApi} from '@/api'
import {ElMessage} from '@/utils/feedback'

const {t} = useI18n()

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

onMounted(() => {
  runAnalysis().catch(() => undefined)
})
</script>

<template>
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
</template>

<style scoped>
.mt-3 {
  margin-top: 12px;
}
</style>
