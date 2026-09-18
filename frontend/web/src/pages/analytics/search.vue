<script lang="ts" setup>
/**
 * 搜索分析
 *
 * 对齐 v3 `/analytics/search`：概况、热门关键词、无结果关键词、搜索趋势。
 * 数据来自搜索行为日志，用于发现内容缺口（无结果词 = 读者想找但没有的内容）。
 */
import {Refresh} from '@element-plus/icons-vue'
import {ref} from 'vue'

import {searchAnalyticsApi} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '搜索分析',
  permission: 'module_analytics:search:view',
})

const DAY_OPTIONS = [
  {label: '近 7 天', value: 7},
  {label: '近 30 天', value: 30},
  {label: '近 90 天', value: 90},
]

const days = ref(30)
const loading = ref(false)

const summary = ref<{
  total_searches: number
  unique_keywords: number
  zero_result_searches: number
  zero_result_rate: number | null
} | null>(null)

const popular = ref<Array<{ keyword: string; count: number; avg_results: number }>>([])
const zeroResult = ref<Array<{ keyword: string; count: number }>>([])
const trend = ref<{ days: number; points: Array<{ day: string; searches: number; zero_result: number }> } | null>(null)

/** 趋势条的最大值，用于把数值换算成条形宽度 */
const trendMax = computed(() =>
  Math.max(1, ...(trend.value?.points ?? []).map((p) => p.searches)),
)

async function loadAll(): Promise<void> {
  loading.value = true
  try {
    const [s, p, z, t] = await Promise.all([
      searchAnalyticsApi.summary(days.value),
      searchAnalyticsApi.popular({limit: 20, days: days.value}),
      searchAnalyticsApi.zeroResult({limit: 20, days: days.value}),
      searchAnalyticsApi.trend(days.value),
    ])
    summary.value = s
    popular.value = p
    zeroResult.value = z
    trend.value = t
  } finally {
    loading.value = false
  }
}

function rateText(rate: number | null): string {
  if (rate === null || rate === undefined) return '-'
  // 后端可能返回 0-1 的小数或百分比，这里统一按小数处理
  const percent = rate <= 1 ? rate * 100 : rate
  return `${percent.toFixed(1)}%`
}

function barWidth(value: number, max: number): string {
  return `${max > 0 ? Math.max(2, (value / max) * 100) : 0}%`
}

onMounted(loadAll)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="toolbar">
        <el-radio-group v-model="days" @change="loadAll">
          <el-radio-button v-for="item in DAY_OPTIONS" :key="item.value" :value="item.value">
            {{ item.label }}
          </el-radio-button>
        </el-radio-group>
        <el-button :icon="Refresh" circle class="ml-auto" @click="loadAll"/>
      </div>

      <el-row v-loading="loading" :gutter="12" class="stats">
        <el-col :span="6">
          <el-card class="stat-card" shadow="never">
            <el-statistic :value="summary?.total_searches ?? 0" title="搜索总次数"/>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card" shadow="never">
            <el-statistic :value="summary?.unique_keywords ?? 0" title="不同关键词"/>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card" shadow="never">
            <el-statistic :value="summary?.zero_result_searches ?? 0" title="无结果搜索"/>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card" shadow="never">
            <el-statistic :value="rateText(summary?.zero_result_rate ?? null)" title="无结果占比"/>
          </el-card>
        </el-col>
      </el-row>

      <!-- 趋势：用 CSS 条形展示，避免为一张图引入图表库 -->
      <div class="section">
        <h4 class="sub-title">搜索趋势</h4>
        <div v-if="trend?.points.length" class="trend">
          <div v-for="point in trend.points" :key="point.day" :title="`${point.day}：${point.searches} 次`"
               class="trend__col">
            <div class="trend__bar-wrap">
              <div :style="{height: barWidth(point.searches, trendMax)}" class="trend__bar"/>
            </div>
            <span class="trend__label">{{ point.day.slice(5) }}</span>
          </div>
        </div>
        <el-empty v-else description="该时间段没有搜索记录"/>
      </div>

      <el-row :gutter="16" class="section">
        <el-col :span="12">
          <h4 class="sub-title">热门关键词</h4>
          <el-table :data="popular" max-height="420" row-key="keyword">
            <el-table-column label="#" type="index" width="60"/>
            <el-table-column label="关键词" min-width="140" prop="keyword"/>
            <el-table-column label="次数" prop="count" sortable width="90"/>
            <el-table-column label="平均结果数" width="120">
              <template #default="{row}">{{ Number(row.avg_results ?? 0).toFixed(1) }}</template>
            </el-table-column>
          </el-table>
        </el-col>

        <el-col :span="12">
          <h4 class="sub-title">
            无结果关键词
            <span class="sub-hint">——读者想找但站内没有的内容</span>
          </h4>
          <el-table :data="zeroResult" max-height="420" row-key="keyword">
            <el-table-column label="#" type="index" width="60"/>
            <el-table-column label="关键词" min-width="160" prop="keyword"/>
            <el-table-column label="次数" prop="count" sortable width="90"/>
          </el-table>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 14px;
}

.ml-auto {
  margin-left: auto;
}

.stats {
  margin-bottom: 6px;
}

.stat-card {
  background: #fafcff;
}

.section {
  margin-top: 20px;
}

.sub-title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 600;
}

.sub-hint {
  font-size: 12px;
  font-weight: 400;
  color: #909399;
}

.trend {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 140px;
  padding: 8px 4px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow-x: auto;
}

.trend__col {
  display: flex;
  flex: 1 0 14px;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.trend__bar-wrap {
  display: flex;
  align-items: flex-end;
  width: 100%;
  height: 100%;
}

.trend__bar {
  width: 100%;
  min-height: 2px;
  background: #409eff;
  border-radius: 2px 2px 0 0;
  transition: height 0.2s;
}

.trend__label {
  margin-top: 4px;
  font-size: 10px;
  color: #c0c4cc;
  white-space: nowrap;
  transform: rotate(-45deg);
}
</style>
