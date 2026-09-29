<script lang="ts" setup>
const {t} = useI18n()
/** 加载失败（用于错误态与重试） */
const loadFailed = ref(false)
/**
 * SEO 分析
 *
 * 对齐 v3 `/analytics/seo`：综合报告、批量检查、关键词、孤立文章、内容分析器。
 * 全部为只读分析接口（`analyze` 不落库），因此只需 view 权限。
 *
 * 另承载 `/content/redirect`（SEO 跳转规则）：列表、新建/编辑/删除、批量导入、
 * 路径解析测试、统计。跳转规则复用同一权限码 `module_analytics:seo:view/edit`。
 *
 * 并承载 `/content/amp`（AMP 工具）：按文章生成 AMP 文档、HTML 元素级转换、
 * 规范校验。生成/校验需 `module_content:article:view`，转换需 `module_content:article:edit`。
 */
import {CopyDocument, Delete, Edit, Plus, Refresh, Search, Upload} from '@element-plus/icons-vue'
import {ElMessage} from '@/utils/feedback'
import {reactive, ref} from 'vue'

import {
  ampApi,
  redirectApi,
  seoApi,
  type AmpArticleDocument,
  type AmpConvertPayload,
  type AmpConvertResult,
  type AmpValidationResult,
  type PageQuery,
  type RedirectBatchResult,
  type RedirectCreatePayload,
  type RedirectItem,
  type RedirectResolveResult,
  type RedirectStats,
} from '@/api'
import {useAdminList} from '@/composables/useAdminList'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.analytics.seo.seoAnalysis',
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

/** SEO 分数配色（语义令牌：深浅色与自选主色都会跟随，不再写死十六进制） */
function scoreColor(score: number): string {
  if (score >= 80) return 'var(--admin-success)'
  if (score >= 60) return 'var(--admin-warning)'
  return 'var(--admin-danger)'
}

// ---------------------------------------------------------------- 综合报告
const reportLoading = ref(false)
const report = ref<SeoReport | null>(null)

async function loadReport(): Promise<void> {
  reportLoading.value = true
  try {
    report.value = (await seoApi.report(200)) as unknown as SeoReport
  } catch {
    // 失败时置错误态，避免把「请求失败」显示成「暂无数据」
    loadFailed.value = true
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

// ---------------------------------------------------------------- 跳转规则
const REDIRECT_STATUS_CODES = [301, 302, 307, 308]

const redirectState = useAdminList<
  RedirectItem,
  PageQuery & { keyword?: string; is_active?: boolean; source?: string }
>({
  fetcher: (params) => redirectApi.list(params),
  defaultQuery: {keyword: '', is_active: undefined, source: undefined},
})

const redirectList = redirectState.rows
const redirectLoading = redirectState.loading
const redirectTotal = redirectState.total
const redirectPage = redirectState.page
const redirectPageSize = redirectState.pageSize
const redirectQuery = redirectState.query
const redirectSearch = redirectState.search
const redirectReset = redirectState.reset
const redirectLoad = redirectState.reload
const onRedirectPageChange = redirectState.onPageChange
const onRedirectSizeChange = redirectState.onSizeChange
const redirectFailed = redirectState.failed

const redirectStats = ref<RedirectStats | null>(null)

async function loadRedirectStats(): Promise<void> {
  try {
    redirectStats.value = await redirectApi.stats()
  } catch {
    redirectStats.value = null
  }
}

// ---- 新建 / 编辑
const redirectDialogVisible = ref(false)
const redirectEditingId = ref<number | null>(null)
const redirectSaving = ref(false)
const redirectForm = reactive<RedirectCreatePayload>({
  from_path: '',
  to_path: '',
  status_code: 301,
  is_active: true,
  notes: '',
})

function openRedirectCreate(): void {
  redirectEditingId.value = null
  Object.assign(redirectForm, {
    from_path: '',
    to_path: '',
    status_code: 301,
    is_active: true,
    notes: '',
  })
  redirectDialogVisible.value = true
}

async function openRedirectEdit(row: RedirectItem): Promise<void> {
  redirectEditingId.value = row.id
  // 编辑前拉一次详情，拿到服务端最新字段；失败则回退用列表行数据
  let target = row
  try {
    target = await redirectApi.detail(row.id)
  } catch {
    target = row
  }
  Object.assign(redirectForm, {
    from_path: target.from_path,
    to_path: target.to_path,
    status_code: target.status_code,
    is_active: target.is_active,
    notes: target.notes ?? '',
  })
  redirectDialogVisible.value = true
}

async function submitRedirect(): Promise<void> {
  const fromPath = redirectForm.from_path.trim()
  const toPath = redirectForm.to_path.trim()
  if (!fromPath || !toPath) {
    ElMessage.warning(t('admin.analytics.seo.redirectPathRequired'))
    return
  }
  const payload: RedirectCreatePayload = {
    from_path: fromPath,
    to_path: toPath,
    status_code: redirectForm.status_code,
    is_active: redirectForm.is_active,
    notes: redirectForm.notes ? redirectForm.notes : null,
  }
  redirectSaving.value = true
  try {
    if (redirectEditingId.value) {
      await redirectApi.update(redirectEditingId.value, payload)
      ElMessage.success(t('admin.analytics.seo.redirectSaved'))
    } else {
      await redirectApi.create(payload)
      ElMessage.success(t('admin.analytics.seo.redirectCreated'))
    }
    redirectDialogVisible.value = false
    await Promise.all([redirectLoad(), loadRedirectStats()])
  } finally {
    redirectSaving.value = false
  }
}

async function removeRedirect(row: RedirectItem): Promise<void> {
  const done = await redirectState.remove(
    () => redirectApi.remove(row.id),
    t('admin.analytics.seo.redirectDeleteConfirm', {path: row.from_path}),
    t('admin.common.notice'),
    t('admin.analytics.seo.redirectDeleted'),
  )
  if (done) await loadRedirectStats()
}

// ---- 批量导入
const redirectBulkVisible = ref(false)
const redirectBulkSaving = ref(false)
const redirectBulkOverwrite = ref(true)
const redirectBulkText = ref('')
const redirectBulkResult = ref<RedirectBatchResult | null>(null)

function openRedirectBulk(): void {
  redirectBulkText.value = ''
  redirectBulkOverwrite.value = true
  redirectBulkResult.value = null
  redirectBulkVisible.value = true
}

/** 每行一条：源路径,目标路径[,状态码]；以 # 开头的行视为注释跳过 */
function parseRedirectBulk(text: string): RedirectCreatePayload[] {
  const items: RedirectCreatePayload[] = []
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue
    const parts = line.split(',').map((part) => part.trim())
    const fromPath = parts[0] || ''
    const toPath = parts[1] || ''
    if (!fromPath || !toPath) continue
    const item: RedirectCreatePayload = {from_path: fromPath, to_path: toPath}
    const statusCode = parts[2] ? Number(parts[2]) : NaN
    if (Number.isFinite(statusCode)) item.status_code = statusCode
    items.push(item)
  }
  return items
}

async function submitRedirectBulk(): Promise<void> {
  const items = parseRedirectBulk(redirectBulkText.value)
  if (!items.length) {
    ElMessage.warning(t('admin.analytics.seo.redirectBulkEmpty'))
    return
  }
  redirectBulkSaving.value = true
  try {
    const result = await redirectApi.bulk({items, overwrite: redirectBulkOverwrite.value})
    redirectBulkResult.value = result
    ElMessage.success(
      t('admin.analytics.seo.redirectBulkDone', {
        created: result.created,
        updated: result.updated,
        skipped: result.skipped,
      }),
    )
    await Promise.all([redirectLoad(), loadRedirectStats()])
  } finally {
    redirectBulkSaving.value = false
  }
}

// ---- 路径解析测试
const redirectResolveVisible = ref(false)
const redirectResolveLoading = ref(false)
const redirectResolvePath = ref('')
const redirectResolveResult = ref<RedirectResolveResult | null>(null)

function openRedirectResolve(): void {
  redirectResolvePath.value = ''
  redirectResolveResult.value = null
  redirectResolveVisible.value = true
}

async function runRedirectResolve(): Promise<void> {
  const path = redirectResolvePath.value.trim()
  if (!path) {
    ElMessage.warning(t('admin.analytics.seo.redirectResolvePathRequired'))
    return
  }
  redirectResolveLoading.value = true
  try {
    const result = await redirectApi.resolve(path)
    redirectResolveResult.value = result
    if (result.matched) await loadRedirectStats()
  } finally {
    redirectResolveLoading.value = false
  }
}

// ---------------------------------------------------------------- AMP 工具
/** 按文章生成 AMP 文档 */
const ampArticleId = ref<number | undefined>(undefined)
const ampGenerateLoading = ref(false)
const ampDocument = ref<AmpArticleDocument | null>(null)

async function runAmpGenerate(): Promise<void> {
  const id = ampArticleId.value
  if (!id || id < 1) {
    ElMessage.warning(t('admin.analytics.seo.ampArticleIdRequired'))
    return
  }
  ampGenerateLoading.value = true
  try {
    ampDocument.value = await ampApi.articleDocument(id)
    ElMessage.success(t('admin.analytics.seo.ampGenerated'))
  } finally {
    ampGenerateLoading.value = false
  }
}

/** HTML → AMP 转换 */
const ampConvertForm = reactive({
  html: '',
  title: '',
  author_name: '',
  canonical_url: '',
  site_name: '',
  featured_image: '',
  published_at: '',
  extra_css: '',
})
const ampConvertLoading = ref(false)
const ampConvertResult = ref<AmpConvertResult | null>(null)

/** 只提交有值的可选字段，避免把空串当作有效元信息传给后端 */
function buildAmpConvertPayload(): AmpConvertPayload {
  const payload: AmpConvertPayload = {html: ampConvertForm.html}
  if (ampConvertForm.title.trim()) payload.title = ampConvertForm.title.trim()
  if (ampConvertForm.author_name.trim()) payload.author_name = ampConvertForm.author_name.trim()
  if (ampConvertForm.canonical_url.trim()) payload.canonical_url = ampConvertForm.canonical_url.trim()
  if (ampConvertForm.site_name.trim()) payload.site_name = ampConvertForm.site_name.trim()
  if (ampConvertForm.featured_image.trim()) payload.featured_image = ampConvertForm.featured_image.trim()
  if (ampConvertForm.published_at.trim()) payload.published_at = ampConvertForm.published_at.trim()
  if (ampConvertForm.extra_css.trim()) payload.extra_css = ampConvertForm.extra_css
  return payload
}

async function runAmpConvert(): Promise<void> {
  if (!ampConvertForm.html.trim()) {
    ElMessage.warning(t('admin.analytics.seo.ampConvertHtmlRequired'))
    return
  }
  ampConvertLoading.value = true
  try {
    ampConvertResult.value = await ampApi.convert(buildAmpConvertPayload())
    ElMessage.success(t('admin.analytics.seo.ampConverted'))
  } finally {
    ampConvertLoading.value = false
  }
}

/** AMP 违规校验 */
const ampValidateHtml = ref('')
const ampValidateLoading = ref(false)
const ampValidateResult = ref<AmpValidationResult | null>(null)

async function runAmpValidate(): Promise<void> {
  if (!ampValidateHtml.value.trim()) {
    ElMessage.warning(t('admin.analytics.seo.ampValidateHtmlRequired'))
    return
  }
  ampValidateLoading.value = true
  try {
    ampValidateResult.value = await ampApi.validate({html: ampValidateHtml.value})
    ElMessage.success(t('admin.analytics.seo.ampValidated'))
  } finally {
    ampValidateLoading.value = false
  }
}

/** 复制生成的 AMP HTML 到剪贴板 */
async function copyAmpHtml(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(t('admin.analytics.seo.ampCopied'))
  } catch {
    ElMessage.warning(t('admin.analytics.seo.ampCopyFailed'))
  }
}

onMounted(async () => {
  await Promise.all([loadReport(), loadKeywords(), loadOrphans(), loadRedirectStats()])
})
</script>

<template>
  <div class="page-container">

    <!-- 加载失败提示 -->
    <div v-if="loadFailed"
         class="mb-3 flex items-center gap-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
      <span>{{ $t('admin.common.loadFailed') }}</span>
      <el-button link type="primary" @click="loadReport()">{{ $t('admin.common.retry') }}</el-button>
    </div>
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
            :title="$t('admin.analytics.seo.orphanArticlesHaveNoInboundLinksFromOtherArticlesSoSearchEnginesMayMissThemAddInternalLinksToImproveDiscoverability')"
            class="mb-3"
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

        <!-- 跳转规则 -->
        <el-tab-pane :label="$t('admin.analytics.seo.redirectRules')" name="redirect">
          <el-row v-if="redirectStats" :gutter="12" class="stats">
            <el-col :span="6">
              <el-statistic :title="$t('admin.analytics.seo.redirectTotal')" :value="redirectStats.total"/>
            </el-col>
            <el-col :span="6">
              <el-statistic :title="$t('admin.analytics.seo.redirectActive')" :value="redirectStats.active"/>
            </el-col>
            <el-col :span="6">
              <el-statistic :title="$t('admin.analytics.seo.redirectInactive')" :value="redirectStats.inactive"/>
            </el-col>
            <el-col :span="6">
              <el-statistic :title="$t('admin.analytics.seo.redirectTotalHits')" :value="redirectStats.total_hits"/>
            </el-col>
          </el-row>

          <div v-if="redirectStats && redirectStats.top_hits.length" class="mt-4">
            <h4 class="sub-title">{{ $t('admin.analytics.seo.redirectTopHits') }}</h4>
            <el-table :data="redirectStats.top_hits" border size="small">
              <el-table-column :label="$t('admin.analytics.seo.redirectFromPath')" min-width="240" prop="from_path"
                               show-overflow-tooltip/>
              <el-table-column :label="$t('admin.analytics.seo.redirectToPath')" min-width="240" prop="to_path"
                               show-overflow-tooltip/>
              <el-table-column :label="$t('admin.analytics.seo.redirectHits')" prop="hits" width="100"/>
            </el-table>
          </div>

          <AdminListShell
            :empty-desc="$t('admin.analytics.seo.redirectEmptyDesc')"
            :empty-title="$t('admin.analytics.seo.redirectEmptyTitle')"
            :failed="redirectFailed"
            :loading="redirectLoading"
            :page="redirectPage"
            :page-size="redirectPageSize"
            :rows="redirectList"
            :selectable="false"
            :total="redirectTotal"
            @refresh="redirectLoad"
            @reset="redirectReset"
            @search="redirectSearch"
            @page-change="onRedirectPageChange"
            @size-change="onRedirectSizeChange"
          >
            <template #filters>
              <el-form-item :label="$t('admin.analytics.seo.redirectKeyword')">
                <el-input v-model="redirectQuery.keyword" :placeholder="$t('admin.analytics.seo.redirectKeywordPlaceholder')"
                          clearable
                          style="width: 200px" @keyup.enter="redirectSearch()"/>
              </el-form-item>
              <el-form-item :label="$t('admin.common.status')">
                <el-select v-model="redirectQuery.is_active" :placeholder="$t('admin.common.all')" clearable
                           style="width: 130px">
                  <el-option :label="$t('admin.common.enabled')" :value="true"/>
                  <el-option :label="$t('admin.common.disabled')" :value="false"/>
                </el-select>
              </el-form-item>
              <el-form-item :label="$t('admin.analytics.seo.redirectSource')">
                <el-select v-model="redirectQuery.source" :placeholder="$t('admin.common.all')" clearable
                           style="width: 140px">
                  <el-option :label="$t('admin.analytics.seo.redirectSourceManual')" value="manual"/>
                  <el-option :label="$t('admin.analytics.seo.redirectSourceMigration')" value="migration"/>
                </el-select>
              </el-form-item>
            </template>

            <template #actions>
              <el-button v-auth="'module_analytics:seo:edit'" :icon="Plus" type="primary" @click="openRedirectCreate">
                {{ $t('admin.analytics.seo.redirectCreate') }}
              </el-button>
              <el-button v-auth="'module_analytics:seo:edit'" :icon="Upload" @click="openRedirectBulk">
                {{ $t('admin.analytics.seo.redirectBulk') }}
              </el-button>
              <el-button :icon="Search" @click="openRedirectResolve">
                {{ $t('admin.analytics.seo.redirectResolve') }}
              </el-button>
            </template>

            <el-table-column label="ID" prop="id" width="80"/>
            <el-table-column :label="$t('admin.analytics.seo.redirectFromPath')" min-width="220" prop="from_path"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.analytics.seo.redirectToPath')" min-width="220" prop="to_path"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.analytics.seo.redirectStatusCode')" prop="status_code" width="100"/>
            <el-table-column :label="$t('admin.analytics.seo.redirectSource')" width="110">
              <template #default="{row}">
                <el-tag :type="row.source === 'migration' ? 'warning' : 'info'" size="small">
                  {{
                    row.source === 'migration'
                      ? $t('admin.analytics.seo.redirectSourceMigration')
                      : $t('admin.analytics.seo.redirectSourceManual')
                  }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.analytics.seo.redirectHits')" prop="hits" width="100"/>
            <el-table-column :label="$t('admin.common.status')" width="90">
              <template #default="{row}">
                <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                  {{ row.is_active ? $t('admin.common.enabled') : $t('admin.common.disabled') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.updatedAt')" width="170">
              <template #default="{row}">{{ formatDateTime(row.updated_at || row.created_at) }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
              <template #default="{row}">
                <el-button v-auth="'module_analytics:seo:edit'" :icon="Edit" link type="primary"
                           @click="openRedirectEdit(row)">
                  {{ $t('admin.common.edit') }}
                </el-button>
                <el-button v-auth="'module_analytics:seo:edit'" :icon="Delete" link type="danger"
                           @click="removeRedirect(row)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </AdminListShell>
        </el-tab-pane>

        <!-- AMP 工具 -->
        <el-tab-pane :label="$t('admin.analytics.seo.ampTools')" name="amp">
          <el-alert :closable="false" :title="$t('admin.analytics.seo.ampHint')" class="mb-3" type="info"/>

          <el-tabs type="border-card">
            <!-- 按文章生成 AMP 文档 -->
            <el-tab-pane :label="$t('admin.analytics.seo.ampGenerate')" name="amp-generate">
              <el-form inline @submit.prevent>
                <el-form-item :label="$t('admin.analytics.seo.ampArticleId')">
                  <el-input-number v-model="ampArticleId" :controls="false" :min="1" style="width: 160px"/>
                </el-form-item>
                <el-form-item>
                  <el-button v-auth="'module_content:article:view'" :icon="Refresh" :loading="ampGenerateLoading"
                             type="primary" @click="runAmpGenerate">
                    {{ $t('admin.analytics.seo.ampGenerateRun') }}
                  </el-button>
                </el-form-item>
              </el-form>

              <template v-if="ampDocument">
                <el-descriptions :column="2" border class="mt-2">
                  <el-descriptions-item :label="$t('admin.analytics.seo.ampDocumentTitle')">
                    {{ ampDocument.title || '—' }}
                  </el-descriptions-item>
                  <el-descriptions-item :label="$t('admin.analytics.seo.ampSlug')">
                    {{ ampDocument.slug || '—' }}
                  </el-descriptions-item>
                  <el-descriptions-item :label="$t('admin.analytics.seo.ampCanonical')">
                    {{ ampDocument.canonical_url || '—' }}
                  </el-descriptions-item>
                  <el-descriptions-item :label="$t('admin.analytics.seo.ampSite')">
                    {{ ampDocument.site.name || '—' }}
                  </el-descriptions-item>
                  <el-descriptions-item :label="$t('admin.analytics.seo.ampComponents')">
                    <el-tag v-for="name in ampDocument.components" :key="name" class="mr-1" size="small">{{
                        name
                      }}
                    </el-tag>
                    <span v-if="!ampDocument.components.length">{{ $t('admin.analytics.seo.ampNone') }}</span>
                  </el-descriptions-item>
                  <el-descriptions-item :label="$t('admin.analytics.seo.ampRemovedTags')">
                    <el-tag v-for="name in ampDocument.removed_tags" :key="name" class="mr-1" size="small" type="info">
                      {{ name }}
                    </el-tag>
                    <span v-if="!ampDocument.removed_tags.length">{{ $t('admin.analytics.seo.ampNone') }}</span>
                  </el-descriptions-item>
                  <el-descriptions-item :label="$t('admin.analytics.seo.ampCss')" :span="2">
                    {{
                      $t('admin.analytics.seo.ampCssUsage', {
                        bytes: ampDocument.css.bytes,
                        limit: ampDocument.css.limit
                      })
                    }}
                    <el-tag v-if="ampDocument.css.truncated" class="ml-2" size="small" type="warning">
                      {{ $t('admin.analytics.seo.ampCssTruncated') }}
                    </el-tag>
                  </el-descriptions-item>
                </el-descriptions>

                <div class="amp-validation mt-3">
                  <div class="toolbar">
                    <span class="sub-title">{{ $t('admin.analytics.seo.ampValidation') }}</span>
                    <el-tag :type="ampDocument.validation.valid ? 'success' : 'danger'" size="small">
                      {{
                        ampDocument.validation.valid
                          ? $t('admin.analytics.seo.ampValidationValid')
                          : $t('admin.analytics.seo.ampValidationInvalid')
                      }}
                    </el-tag>
                    <span class="hint">
                      {{
                        $t('admin.analytics.seo.ampValidationSummary', {
                          errors: ampDocument.validation.summary.errors,
                          warnings: ampDocument.validation.summary.warnings,
                          elements: ampDocument.validation.summary.elements_checked,
                        })
                      }}
                    </span>
                  </div>
                  <el-table v-if="ampDocument.validation.errors.length" :data="ampDocument.validation.errors" border
                            class="mt-2" size="small">
                    <el-table-column :label="$t('admin.analytics.seo.ampRule')" prop="rule" width="200"/>
                    <el-table-column :label="$t('admin.analytics.seo.ampMessage')" min-width="260" prop="message"/>
                  </el-table>
                  <el-table v-if="ampDocument.validation.warnings.length" :data="ampDocument.validation.warnings" border
                            class="mt-2" size="small">
                    <el-table-column :label="$t('admin.analytics.seo.ampRule')" prop="rule" width="200"/>
                    <el-table-column :label="$t('admin.analytics.seo.ampMessage')" min-width="260" prop="message"/>
                  </el-table>
                  <el-empty v-if="!ampDocument.validation.errors.length && !ampDocument.validation.warnings.length"
                            :description="$t('admin.analytics.seo.ampNoErrors')" :image-size="60"/>
                </div>

                <div class="toolbar mt-3">
                  <span class="sub-title">{{ $t('admin.analytics.seo.ampHtml') }}</span>
                  <el-button :icon="CopyDocument" @click="copyAmpHtml(ampDocument.amp_html)">
                    {{ $t('admin.analytics.seo.ampCopy') }}
                  </el-button>
                </div>
                <el-input :model-value="ampDocument.amp_html" :rows="14" readonly type="textarea"/>
              </template>
              <el-empty v-else :description="$t('admin.analytics.seo.ampGenerateEmpty')"/>
            </el-tab-pane>

            <!-- HTML → AMP 转换 -->
            <el-tab-pane :label="$t('admin.analytics.seo.ampConvert')" name="amp-convert">
              <el-alert :closable="false" :title="$t('admin.analytics.seo.ampConvertHint')" class="mb-3" type="info"/>
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form :model="ampConvertForm" label-width="110px">
                    <el-form-item :label="$t('admin.analytics.seo.ampSourceHtml')">
                      <el-input v-model="ampConvertForm.html" :placeholder="$t('admin.analytics.seo.ampSourceHtmlPlaceholder')" :rows="10"
                                type="textarea"/>
                    </el-form-item>
                    <el-form-item :label="$t('admin.analytics.seo.ampTitleOptional')">
                      <el-input v-model="ampConvertForm.title" maxlength="255"/>
                    </el-form-item>
                    <el-form-item :label="$t('admin.analytics.seo.ampAuthorName')">
                      <el-input v-model="ampConvertForm.author_name" maxlength="255"/>
                    </el-form-item>
                    <el-form-item :label="$t('admin.analytics.seo.ampCanonical')">
                      <el-input v-model="ampConvertForm.canonical_url" maxlength="500"/>
                    </el-form-item>
                    <el-form-item :label="$t('admin.analytics.seo.ampSiteName')">
                      <el-input v-model="ampConvertForm.site_name" maxlength="255"/>
                    </el-form-item>
                    <el-form-item :label="$t('admin.analytics.seo.ampFeaturedImage')">
                      <el-input v-model="ampConvertForm.featured_image" maxlength="1000"/>
                    </el-form-item>
                    <el-form-item :label="$t('admin.analytics.seo.ampPublishedAt')">
                      <el-input v-model="ampConvertForm.published_at" :placeholder="$t('admin.analytics.seo.ampPublishedAtPlaceholder')"
                                maxlength="64"/>
                    </el-form-item>
                    <el-form-item :label="$t('admin.analytics.seo.ampExtraCss')">
                      <el-input v-model="ampConvertForm.extra_css" :rows="3" type="textarea"/>
                    </el-form-item>
                    <el-form-item>
                      <el-button v-auth="'module_content:article:edit'" :loading="ampConvertLoading" type="primary"
                                 @click="runAmpConvert">
                        {{ $t('admin.analytics.seo.ampConvertRun') }}
                      </el-button>
                    </el-form-item>
                  </el-form>
                </el-col>

                <el-col :span="12">
                  <template v-if="ampConvertResult">
                    <div class="toolbar">
                      <span class="sub-title">{{ $t('admin.analytics.seo.ampCanonical') }}</span>
                      <span class="hint">{{ ampConvertResult.canonical_url || '—' }}</span>
                    </div>
                    <div class="toolbar">
                      <span class="sub-title">{{ $t('admin.analytics.seo.ampComponents') }}</span>
                      <el-tag v-for="name in ampConvertResult.components" :key="name" class="mr-1" size="small">
                        {{ name }}
                      </el-tag>
                      <span v-if="!ampConvertResult.components.length" class="hint">
                        {{ $t('admin.analytics.seo.ampNone') }}
                      </span>
                    </div>
                    <div class="toolbar">
                      <span class="sub-title">{{ $t('admin.analytics.seo.ampRemovedTags') }}</span>
                      <el-tag v-for="name in ampConvertResult.removed_tags" :key="name" class="mr-1" size="small"
                              type="info">
                        {{ name }}
                      </el-tag>
                      <span v-if="!ampConvertResult.removed_tags.length" class="hint">
                        {{ $t('admin.analytics.seo.ampNone') }}
                      </span>
                    </div>
                    <div class="toolbar">
                      <span class="sub-title">{{ $t('admin.analytics.seo.ampCss') }}</span>
                      <span class="hint">
                        {{
                          $t('admin.analytics.seo.ampCssUsage', {
                            bytes: ampConvertResult.css.bytes,
                            limit: ampConvertResult.css.limit
                          })
                        }}
                      </span>
                      <el-tag v-if="ampConvertResult.css.truncated" size="small" type="warning">
                        {{ $t('admin.analytics.seo.ampCssTruncated') }}
                      </el-tag>
                    </div>

                    <div class="amp-validation mt-3">
                      <div class="toolbar">
                        <span class="sub-title">{{ $t('admin.analytics.seo.ampValidation') }}</span>
                        <el-tag :type="ampConvertResult.validation.valid ? 'success' : 'danger'" size="small">
                          {{
                            ampConvertResult.validation.valid
                              ? $t('admin.analytics.seo.ampValidationValid')
                              : $t('admin.analytics.seo.ampValidationInvalid')
                          }}
                        </el-tag>
                        <span class="hint">
                          {{
                            $t('admin.analytics.seo.ampValidationSummary', {
                              errors: ampConvertResult.validation.summary.errors,
                              warnings: ampConvertResult.validation.summary.warnings,
                              elements: ampConvertResult.validation.summary.elements_checked,
                            })
                          }}
                        </span>
                      </div>
                      <el-table v-if="ampConvertResult.validation.errors.length"
                                :data="ampConvertResult.validation.errors"
                                border class="mt-2" size="small">
                        <el-table-column :label="$t('admin.analytics.seo.ampRule')" prop="rule" width="200"/>
                        <el-table-column :label="$t('admin.analytics.seo.ampMessage')" min-width="260" prop="message"/>
                      </el-table>
                      <el-table v-if="ampConvertResult.validation.warnings.length"
                                :data="ampConvertResult.validation.warnings" border class="mt-2" size="small">
                        <el-table-column :label="$t('admin.analytics.seo.ampRule')" prop="rule" width="200"/>
                        <el-table-column :label="$t('admin.analytics.seo.ampMessage')" min-width="260" prop="message"/>
                      </el-table>
                      <el-empty
                        v-if="!ampConvertResult.validation.errors.length && !ampConvertResult.validation.warnings.length"
                        :description="$t('admin.analytics.seo.ampNoErrors')" :image-size="60"/>
                    </div>

                    <div class="toolbar mt-3">
                      <span class="sub-title">{{ $t('admin.analytics.seo.ampHtml') }}</span>
                      <el-button :icon="CopyDocument" @click="copyAmpHtml(ampConvertResult.amp_html)">
                        {{ $t('admin.analytics.seo.ampCopy') }}
                      </el-button>
                    </div>
                    <el-input :model-value="ampConvertResult.amp_html" :rows="10" readonly type="textarea"/>
                  </template>
                  <el-empty v-else :description="$t('admin.analytics.seo.ampConvertEmpty')"/>
                </el-col>
              </el-row>
            </el-tab-pane>

            <!-- AMP 违规校验 -->
            <el-tab-pane :label="$t('admin.analytics.seo.ampValidate')" name="amp-validate">
              <el-alert :closable="false" :title="$t('admin.analytics.seo.ampValidateHint')" class="mb-3" type="info"/>
              <el-input v-model="ampValidateHtml" :placeholder="$t('admin.analytics.seo.ampValidateHtmlPlaceholder')" :rows="10"
                        type="textarea"/>
              <div class="toolbar mt-2">
                <el-button v-auth="'module_content:article:view'" :icon="Search" :loading="ampValidateLoading"
                           type="primary" @click="runAmpValidate">
                  {{ $t('admin.analytics.seo.ampValidateRun') }}
                </el-button>
              </div>

              <template v-if="ampValidateResult">
                <div class="toolbar">
                  <el-tag :type="ampValidateResult.valid ? 'success' : 'danger'">
                    {{
                      ampValidateResult.valid
                        ? $t('admin.analytics.seo.ampValidationValid')
                        : $t('admin.analytics.seo.ampValidationInvalid')
                    }}
                  </el-tag>
                  <span class="hint">
                    {{
                      $t('admin.analytics.seo.ampValidationSummary', {
                        errors: ampValidateResult.summary.errors,
                        warnings: ampValidateResult.summary.warnings,
                        elements: ampValidateResult.summary.elements_checked,
                      })
                    }}
                  </span>
                </div>
                <el-row :gutter="12" class="mt-2">
                  <el-col :span="6">
                    <el-statistic :title="$t('admin.analytics.seo.ampErrors')"
                                  :value="ampValidateResult.summary.errors"/>
                  </el-col>
                  <el-col :span="6">
                    <el-statistic :title="$t('admin.analytics.seo.ampWarnings')"
                                  :value="ampValidateResult.summary.warnings"/>
                  </el-col>
                  <el-col :span="6">
                    <el-statistic :title="$t('admin.analytics.seo.ampElementsChecked')"
                                  :value="ampValidateResult.summary.elements_checked"/>
                  </el-col>
                  <el-col :span="6">
                    <el-statistic :title="$t('admin.analytics.seo.ampCssBytes')"
                                  :value="ampValidateResult.summary.css_bytes"/>
                  </el-col>
                </el-row>
                <el-table v-if="ampValidateResult.errors.length" :data="ampValidateResult.errors" border class="mt-2"
                          size="small">
                  <el-table-column :label="$t('admin.analytics.seo.ampRule')" prop="rule" width="200"/>
                  <el-table-column :label="$t('admin.analytics.seo.ampMessage')" min-width="260" prop="message"/>
                </el-table>
                <el-table v-if="ampValidateResult.warnings.length" :data="ampValidateResult.warnings" border
                          class="mt-2"
                          size="small">
                  <el-table-column :label="$t('admin.analytics.seo.ampRule')" prop="rule" width="200"/>
                  <el-table-column :label="$t('admin.analytics.seo.ampMessage')" min-width="260" prop="message"/>
                </el-table>
              </template>
              <el-empty v-else :description="$t('admin.analytics.seo.ampValidateEmpty')"/>
            </el-tab-pane>
          </el-tabs>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 新建 / 编辑跳转规则 -->
    <el-dialog
      v-model="redirectDialogVisible"
      :title="redirectEditingId
        ? $t('admin.analytics.seo.redirectEdit')
        : $t('admin.analytics.seo.redirectCreate')"
      destroy-on-close
      width="560px"
    >
      <el-form :model="redirectForm" label-width="96px">
        <el-form-item :label="$t('admin.analytics.seo.redirectFromPath')" required>
          <el-input v-model="redirectForm.from_path" :placeholder="$t('admin.analytics.seo.redirectFromPathPlaceholder')"
                    maxlength="500"/>
        </el-form-item>
        <el-form-item :label="$t('admin.analytics.seo.redirectToPath')" required>
          <el-input v-model="redirectForm.to_path" :placeholder="$t('admin.analytics.seo.redirectToPathPlaceholder')"
                    maxlength="500"/>
        </el-form-item>
        <el-form-item :label="$t('admin.analytics.seo.redirectStatusCode')">
          <el-select v-model="redirectForm.status_code" style="width: 160px">
            <el-option v-for="code in REDIRECT_STATUS_CODES" :key="code" :label="String(code)" :value="code"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.common.enabled')">
          <el-switch v-model="redirectForm.is_active"/>
        </el-form-item>
        <el-form-item :label="$t('admin.analytics.seo.redirectNotes')">
          <el-input v-model="redirectForm.notes" :rows="3" maxlength="1000" type="textarea"/>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="redirectDialogVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="redirectSaving" type="primary" @click="submitRedirect">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 批量导入跳转规则 -->
    <el-dialog v-model="redirectBulkVisible" :title="$t('admin.analytics.seo.redirectBulk')" destroy-on-close
               width="640px">
      <el-alert :closable="false" :title="$t('admin.analytics.seo.redirectBulkHint')" class="mb-3" type="info"/>
      <el-input v-model="redirectBulkText" :placeholder="$t('admin.analytics.seo.redirectBulkPlaceholder')" :rows="10"
                type="textarea"/>
      <el-checkbox v-model="redirectBulkOverwrite" class="mt-2">
        {{ $t('admin.analytics.seo.redirectBulkOverwrite') }}
      </el-checkbox>
      <div v-if="redirectBulkResult" class="hint mt-2">
        <el-tag size="small" type="success">
          {{
            $t('admin.analytics.seo.redirectBulkDone', {
              created: redirectBulkResult.created,
              updated: redirectBulkResult.updated,
              skipped: redirectBulkResult.skipped,
            })
          }}
        </el-tag>
      </div>

      <template #footer>
        <el-button @click="redirectBulkVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="redirectBulkSaving" type="primary" @click="submitRedirectBulk">
          {{ $t('admin.analytics.seo.redirectBulkSubmit') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 路径解析测试 -->
    <el-dialog v-model="redirectResolveVisible" :title="$t('admin.analytics.seo.redirectResolve')" destroy-on-close
               width="520px">
      <el-form inline>
        <el-form-item :label="$t('admin.analytics.seo.redirectResolvePath')">
          <el-input v-model="redirectResolvePath"
                    :placeholder="$t('admin.analytics.seo.redirectResolvePathPlaceholder')"
                    style="width: 280px" @keyup.enter="runRedirectResolve"/>
        </el-form-item>
      </el-form>

      <div v-if="redirectResolveResult" class="mt-2">
        <el-tag :type="redirectResolveResult.matched ? 'success' : 'info'">
          {{
            redirectResolveResult.matched
              ? $t('admin.analytics.seo.redirectResolveMatched')
              : $t('admin.analytics.seo.redirectResolveMissed')
          }}
        </el-tag>
        <el-descriptions v-if="redirectResolveResult.matched" :column="1" border class="mt-2">
          <el-descriptions-item :label="$t('admin.analytics.seo.redirectToPath')">
            {{ redirectResolveResult.to_path }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.analytics.seo.redirectStatusCode')">
            {{ redirectResolveResult.status_code }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.analytics.seo.redirectHits')">
            {{ redirectResolveResult.hits }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <template #footer>
        <el-button @click="redirectResolveVisible = false">{{ $t('admin.common.close') }}</el-button>
        <el-button :loading="redirectResolveLoading" type="primary" @click="runRedirectResolve">
          {{ $t('admin.analytics.seo.redirectResolveRun') }}
        </el-button>
      </template>
    </el-dialog>
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
  color: var(--color-fg-subtle);
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
  background: var(--color-surface-soft);
  border-radius: 4px;
  overflow: hidden;
}

.bar__fill {
  height: 100%;
  background: var(--color-primary);
}

.grade-count {
  width: 36px;
  font-size: 12px;
  color: var(--color-fg-muted);
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
  color: var(--color-fg-muted);
}

.hint {
  font-size: 13px;
  color: var(--color-fg-subtle);
}

.mt-2 {
  margin-top: 8px;
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
  color: var(--color-fg-muted);
}

.mr-1 {
  margin-right: 4px;
}

.ml-2 {
  margin-left: 8px;
}

.amp-validation {
  margin-top: 12px;
}
</style>
