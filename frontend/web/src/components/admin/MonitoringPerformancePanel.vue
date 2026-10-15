<script lang="ts" setup>
/**
 * 监控中心 · 性能综合报告面板
 *
 * 从 `pages/system/monitoring.vue` 的「性能综合报告」标签页抽出：RUM、数据库、
 * 服务器与持久态（告警 / 指标 / SLA）的汇总视图（`performanceReport`）。
 *
 * 加载时机与原实现一致：原页面在 `onMounted` 里 `loadPerformanceReport()`，即挂载即加载。
 */
import {TrendCharts} from '@element-plus/icons-vue'
import {onMounted, reactive, ref} from 'vue'

import type {PerformanceReport} from '@/api'
import {monitoringApi} from '@/api'

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

onMounted(() => {
  loadPerformanceReport().catch(() => undefined)
})
</script>

<template>
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
</template>

<style scoped>
.mt-3 {
  margin-top: 12px;
}
</style>
