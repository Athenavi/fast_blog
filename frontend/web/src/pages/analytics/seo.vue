<script lang="ts" setup>
const {t} = useI18n()
/**
 * SEO 分析
 *
 * 对齐 v3 `/analytics/seo`：综合报告、批量检查、关键词、孤立文章、内容分析器。
 * 全部为只读分析接口（`analyze` 不落库），因此只需 view 权限。
 */
import {Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage} from '@/utils/feedback'
import {reactive, ref} from 'vue'

import {seoApi} from '@/api'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: t('admin.analytics.seo.seoAnalysis'),
  permission: 'module_analytics:seo:view',
})

interface SeoReport {
  generated_at: string
  total_articles: number
  average_score: number
  grade_distribution: Record<string, number>
  common_suggestions: Array<{ suggestion: string; count: number }>
  orphan_count: number
  top_keywords: Array<{ keyword: string; count: number }>
}

interface BulkResult {
  checked: number
  average_score: number
  grade_distribution: Record<string, number>
  items: Array<{
    article_id: number
    title?: string | null
    slug?: string | null
    score: number
    grade?: string | null
    suggestion_count: number
    top_suggestions: string[]
  }>
}

const activeTab = ref('report')

function gradeTag(grade?: string | null): 'success' | 'warning' | 'danger' | 'info' {
  if (grade === 'A' || grade === 'B') return 'success'
  if (grade === 'C') return 'warning'
  if (grade === 'D' || grade === 'E') return 'danger'
  return 'info'
}

function scoreColor(score: number): string {
  if (score >= 80) return '#16a34a'
  if (score >= 60) return '#d97706'
  return '#dc2626'
}

// ---------------------------------------------------------------- 综合报告
const reportLoading = ref(false)
const report = ref<SeoReport | null>(null)

async function loadReport(): Promise<void> {
  reportLoading.value = true
  try {
    report.value = (await seoApi.report(200)) as unknown as SeoReport
  } finally {
    reportLoading.value = false
  }
}

// ---------------------------------------------------------------- 批量检查
const bulkLoading = ref(false)
const bulk = ref<BulkResult | null>(null)

async function runBulk(): Promise<void> {
  bulkLoading.value = true
  try {
    bulk.value = (await seoApi.bulkCheck({limit: 50, only_published: true})) as unknown as BulkResult
    ElMessage.success(t('admin.analytics.seo.checkedArticles', {n: bulk.value.checked}))
  } finally {
    bulkLoading.value = false
  }
}

// ---------------------------------------------------------------- 关键词 / 孤立文章
const keywords = ref<Array<{ keyword: string; count: number }>>([])
const orphans = ref<Array<{ article_id: number; title?: string; slug?: string; inbound_links: number }>>([])

async function loadKeywords(): Promise<void> {
  const data = await seoApi.keywords({limit: 50})
  keywords.value = data.keywords
}

async function loadOrphans(): Promise<void> {
  const data = await seoApi.orphans(100)
  orphans.value = data.items
}

// ---------------------------------------------------------------- 内容分析器
const analyzeForm = reactive({title: '', description: '', content: '', keywords: ''})
const analyzeLoading = ref(false)
const analyzeResult = ref<{
  overall_score: number
  grade?: string | null
  suggestions: string[]
  metrics: Record<string, unknown>
} | null>(null)

async function runAnalyze(): Promise<void> {
  if (!analyzeForm.title.trim() && !analyzeForm.content.trim()) {
    ElMessage.warning(t('admin.analytics.seo.enterATitleOrContent'))
    return
  }
  analyzeLoading.value = true
  try {
    analyzeResult.value = (await seoApi.analyze({
      title: analyzeForm.title,
      description: analyzeForm.description,
      content: analyzeForm.content,
      keywords: analyzeForm.keywords
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    })) as unknown as typeof analyzeResult.value
  } finally {
    analyzeLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadReport(), loadKeywords(), loadOrphans()])
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-tabs v-model="activeTab">
        <!-- 综合报告 -->
        <el-tab-pane :label="$t('admin.analytics.seo.overallReport')" name="report">
          <div v-loading="reportLoading">
            <el-row v-if="report" :gutter="12" class="stats">
              <el-col :span="6">
                <el-statistic :title="$t('admin.analytics.seo.totalArticles')" :value="report.total_articles"/>
              </el-col>
              <el-col :span="6">
                <el-statistic :title="$t('admin.analytics.seo.averageScore')"
                              :value="Number(report.average_score.toFixed(1))"/>
              </el-col>
              <el-col :span="6">
                <el-statistic :title="$t('admin.analytics.seo.orphanArticlesNoInboundLinks')"
                              :value="report.orphan_count"/>
              </el-col>
              <el-col :span="6">
                <div class="generated">
                  {{ $t('admin.analytics.seo.generatedAt') }}<br>{{ formatDateTime(report.generated_at) }}
                </div>
              </el-col>
            </el-row>

            <el-row v-if="report" :gutter="12" class="mt-4">
              <el-col :span="10">
                <h4 class="sub-title">{{ $t('admin.analytics.seo.scoreDistribution') }}</h4>
                <div class="grade-list">
                  <div v-for="(count, grade) in report.grade_distribution" :key="grade" class="grade-row">
                    <el-tag :type="gradeTag(String(grade))" class="grade-tag" size="small">{{ grade }}</el-tag>
                    <div class="bar">
                      <div
                        :style="{width: `${report.total_articles ? (count / report.total_articles) * 100 : 0}%`}"
                        class="bar__fill"
                      />
                    </div>
                    <span class="grade-count">{{ count }}</span>
                  </div>
                </div>
              </el-col>

              <el-col :span="14">
                <h4 class="sub-title">{{ $t('admin.analytics.seo.mostCommonIssues') }}</h4>
                <el-table :data="report.common_suggestions" border size="small">
                  <el-table-column :label="$t('admin.analytics.seo.recommendation')" min-width="260" prop="suggestion"/>
                  <el-table-column :label="$t('admin.analytics.seo.occurrences')" prop="count" width="100"/>
                </el-table>
              </el-col>
            </el-row>

            <div v-if="report?.top_keywords.length" class="mt-4">
              <h4 class="sub-title">{{ $t('admin.analytics.seo.frequentKeywords') }}</h4>
              <div class="tags">
                <el-tag v-for="item in report.top_keywords.slice(0, 30)" :key="item.keyword" class="tag" size="small">
                  {{ item.keyword }}<span class="tag-count">{{ item.count }}</span>
                </el-tag>
              </div>
            </div>

            <div class="toolbar mt-4">
              <el-button :icon="Refresh" @click="loadReport">{{ $t('admin.analytics.seo.refreshReport') }}</el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- 批量检查 -->
        <el-tab-pane :label="$t('admin.analytics.seo.bulkCheck')" name="bulk">
          <div class="toolbar">
            <el-button :loading="bulkLoading" type="primary" @click="runBulk">
              {{ $t('admin.analytics.seo.checkRecent') }}
            </el-button>
            <span v-if="bulk" class="hint">
              {{ $t('admin.analytics.seo.bulkSummary', {checked: bulk.checked, score: bulk.average_score.toFixed(1)}) }}
            </span>
          </div>

          <el-table v-if="bulk" v-loading="bulkLoading" :data="bulk.items" row-key="article_id">
            <el-table-column label="ID" prop="article_id" width="80"/>
            <el-table-column :label="$t('admin.system.menu.itemTitle')" min-width="240" prop="title"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.analytics.seo.score')" width="110">
              <template #default="{row}">
                <span :style="{color: scoreColor(row.score), fontWeight: 600}">{{ row.score }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('vip.level')" width="80">
              <template #default="{row}">
                <el-tag :type="gradeTag(row.grade)" size="small">{{ row.grade || '-' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.analytics.seo.issues')" prop="suggestion_count" width="90"/>
            <el-table-column :label="$t('admin.analytics.seo.mainIssues')" min-width="280">
              <template #default="{row}">
                <span class="suggestion">{{ (row.top_suggestions || []).join('；') || '-' }}</span>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-else :description="$t('admin.analytics.seo.clickTheButtonAboveToStartABulkCheck')"/>
        </el-tab-pane>

        <!-- 关键词 -->
        <el-tab-pane :label="$t('admin.analytics.seo.keyword')" name="keywords">
          <el-table :data="keywords" max-height="560" row-key="keyword">
            <el-table-column label="#" type="index" width="70"/>
            <el-table-column :label="$t('admin.analytics.seo.keyword')" min-width="200" prop="keyword"/>
            <el-table-column :label="$t('admin.analytics.seo.occurrences')" prop="count" sortable width="120"/>
          </el-table>
        </el-tab-pane>

        <!-- 孤立文章 -->
        <el-tab-pane :label="$t('admin.analytics.seo.orphanArticles')" name="orphans">
          <el-alert
            :closable="false"
            class="mb-3"
            :title="$t('admin.analytics.seo.orphanArticlesHaveNoInboundLinksFromOtherArticlesSoSearchEnginesMayMissThemAddInternalLinksToImproveDiscoverability')"
            type="info"
          />
          <el-table :data="orphans" max-height="520" row-key="article_id">
            <el-table-column label="ID" prop="article_id" width="80"/>
            <el-table-column :label="$t('admin.system.menu.itemTitle')" min-width="260" prop="title"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.analytics.seo.alias')" min-width="160" prop="slug"/>
            <el-table-column :label="$t('admin.analytics.seo.inboundLinks')" prop="inbound_links" width="100"/>
          </el-table>
        </el-tab-pane>

        <!-- 内容分析器 -->
        <el-tab-pane :label="$t('admin.analytics.seo.contentAnalyzer')" name="analyzer">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form :model="analyzeForm" label-width="80px">
                <el-form-item :label="$t('admin.system.menu.itemTitle')">
                  <el-input v-model="analyzeForm.title" :placeholder="$t('admin.analytics.seo.titleToAnalyze')"/>
                </el-form-item>
                <el-form-item :label="$t('admin.common.description')">
                  <el-input v-model="analyzeForm.description" :rows="2" type="textarea"/>
                </el-form-item>
                <el-form-item :label="$t('admin.analytics.seo.keyword')">
                  <el-input v-model="analyzeForm.keywords" :placeholder="$t('admin.analytics.seo.separateWithCommas')"/>
                </el-form-item>
                <el-form-item :label="$t('admin.analytics.seo.content')">
                  <el-input v-model="analyzeForm.content" :placeholder="$t('admin.analytics.seo.pasteContent')"
                            :rows="10" type="textarea"/>
                </el-form-item>
                <el-form-item>
                  <el-button :icon="Search" :loading="analyzeLoading" type="primary" @click="runAnalyze">
                    {{ $t('admin.analytics.seo.startAnalysis') }}
                  </el-button>
                </el-form-item>
              </el-form>
            </el-col>

            <el-col :span="12">
              <div v-if="analyzeResult" class="result">
                <div class="result__score">
                  <span :style="{color: scoreColor(analyzeResult.overall_score)}">
                    {{ analyzeResult.overall_score }}
                  </span>
                  <el-tag :type="gradeTag(analyzeResult.grade)" class="ml-2">{{ analyzeResult.grade || '-' }}</el-tag>
                </div>
                <h4 class="sub-title">{{ $t('admin.analytics.seo.improvementSuggestions') }}</h4>
                <ul v-if="analyzeResult.suggestions.length" class="suggestions">
                  <li v-for="(item, index) in analyzeResult.suggestions" :key="index">{{ item }}</li>
                </ul>
                <el-empty v-else :description="$t('admin.analytics.seo.noIssuesFound')"/>
              </div>
              <el-empty v-else :description="$t('admin.analytics.seo.fillInTheContentOnTheLeftToAnalyzeIt')"/>
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.stats {
  margin-bottom: 8px;
}

.generated {
  font-size: 12px;
  line-height: 1.6;
  color: #909399;
}

.sub-title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 600;
}

.grade-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.grade-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.grade-tag {
  width: 28px;
  justify-content: center;
}

.bar {
  flex: 1;
  height: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  overflow: hidden;
}

.bar__fill {
  height: 100%;
  background: #409eff;
}

.grade-count {
  width: 36px;
  font-size: 12px;
  color: #606266;
  text-align: right;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-count {
  margin-left: 4px;
  opacity: 0.7;
}

.suggestion {
  font-size: 13px;
  color: #606266;
}

.hint {
  font-size: 13px;
  color: #909399;
}

.mt-4 {
  margin-top: 16px;
}

.mb-3 {
  margin-bottom: 12px;
}

.result__score {
  display: flex;
  align-items: center;
  font-size: 40px;
  font-weight: 700;
  line-height: 1;
}

.suggestions {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.9;
  color: #606266;
}
</style>
