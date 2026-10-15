<script lang="ts" setup>
/**
 * 监控中心（页面壳）
 *
 * 对齐 v3 `/system/monitor` 的告警 / 指标 / SLA 三组（实时状态在 `/system/hub`）。
 * 数据由外部探针 / 脚本写入，本页做管理与查询：
 *  - 告警：列表 / 过滤 / 新建 / 解决 / 删除 + 统计；
 *  - 指标：时序列表 / 时间桶聚合 / 写入 / 按保留期清理；
 *  - SLA：报表列表 + 按真实告警计算（周期内 critical 告警窗口合并 → 宕机分钟数）+ 达标统计。
 *
 * **本文件现在只负责标签容器**：八个标签页的内容（约 1400 行）已各自拆成
 * `components/admin/Monitoring*Panel.vue`。各标签页的弹出层（el-drawer / el-dialog）
 * 随所属标签页一起搬走 —— 它们由标签页内的按钮触发，没必要让页面替它们保管那份表单状态。
 *
 * 加载时机保持原样（原页面没有 `@tab-change`，只有两个 `onMounted`）：告警 / 指标 /
 * 渠道列表由 `useAdminList` 挂载即加载；慢查询 / 查询优化 / 性能报告在各自组件的
 * `onMounted` 里加载。`<el-tab-pane>` 默认 `lazy=false`（`shouldBeRender` 恒真），
 * 各面板在整页挂载时一并挂载，故"挂载即加载"的时机与原实现完全一致。
 *
 * 留在页面的只有 `activeTab` 和跨标签共享的两张统计卡片：`alertStats` / `slaStats`
 * 由同一个批量请求 `loadStats()` 填充，告警与 SLA 两个标签页的"刷新"按钮及增删改后
 * 的刷新都调用它，故不能锁进任何单个面板（面板通过 `stats` 读入、`refresh-stats` 触发刷新）。
 *
 * 无轮询 / 定时器，故各组件不需要清理逻辑（原页面同样没有 `setInterval`）。
 */
import {onMounted, ref} from 'vue'

import {type AlertStats, monitoringApi, type SLAStats} from '@/api'
import MonitoringAlertPanel from '@/components/admin/MonitoringAlertPanel.vue'
import MonitoringChannelPanel from '@/components/admin/MonitoringChannelPanel.vue'
import MonitoringDeliveriesPanel from '@/components/admin/MonitoringDeliveriesPanel.vue'
import MonitoringMetricPanel from '@/components/admin/MonitoringMetricPanel.vue'
import MonitoringPerformancePanel from '@/components/admin/MonitoringPerformancePanel.vue'
import MonitoringQueryOptimizerPanel from '@/components/admin/MonitoringQueryOptimizerPanel.vue'
import MonitoringSlaPanel from '@/components/admin/MonitoringSlaPanel.vue'
import MonitoringSlowQueryPanel from '@/components/admin/MonitoringSlowQueryPanel.vue'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.monitoring.title',
  permission: 'module_system:monitor:view',
})

const activeTab = ref('alert')

const alertStats = ref<AlertStats | null>(null)
const slaStats = ref<SLAStats | null>(null)

// 告警与 SLA 的统计卡片原由这一个函数一次并行拉取，故留在页面
async function loadStats() {
  const [alerts, sla] = await Promise.all([
    monitoringApi.alertStats().catch(() => null),
    monitoringApi.slaStats().catch(() => null),
  ])
  alertStats.value = alerts
  slaStats.value = sla
}

onMounted(() => {
  loadStats().catch(() => undefined)
})
</script>

<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- 告警 -->
      <el-tab-pane :label="$t('admin.system.monitoring.alerts')" name="alert">
        <MonitoringAlertPanel :stats="alertStats" @refresh-stats="loadStats"/>
      </el-tab-pane>

      <!-- 指标 -->
      <el-tab-pane :label="$t('admin.system.monitoring.metrics')" name="metric">
        <MonitoringMetricPanel/>
      </el-tab-pane>

      <!-- SLA -->
      <el-tab-pane :label="$t('admin.system.monitoring.sla')" name="sla">
        <MonitoringSlaPanel :stats="slaStats" @refresh-stats="loadStats"/>
      </el-tab-pane>

      <!-- 告警推送渠道 -->
      <el-tab-pane :label="$t('admin.system.monitoring.tabAlertChannel')" name="alertChannel">
        <MonitoringChannelPanel/>
      </el-tab-pane>

      <!-- 通知投递记录 -->
      <el-tab-pane :label="$t('admin.system.monitoring.tabDeliveries')" name="deliveries">
        <MonitoringDeliveriesPanel/>
      </el-tab-pane>

      <!-- 慢查询与阈值 -->
      <el-tab-pane :label="$t('admin.system.monitoring.tabSlowQuery')" name="slowQuery">
        <MonitoringSlowQueryPanel/>
      </el-tab-pane>

      <!-- 查询优化 -->
      <el-tab-pane :label="$t('admin.system.monitoring.tabQueryOptimizer')" name="queryOptimizer">
        <MonitoringQueryOptimizerPanel/>
      </el-tab-pane>

      <!-- 性能综合报告 -->
      <el-tab-pane :label="$t('admin.system.monitoring.tabPerformance')" name="performanceReport">
        <MonitoringPerformancePanel/>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>
