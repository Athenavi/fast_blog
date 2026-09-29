<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col v-for="card in cards" :key="card.label" :lg="4" :md="6" :sm="8" :xs="12">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-card__label">{{ card.label }}</div>
          <div class="stat-card__value">{{ card.value }}</div>
          <div v-if="card.hint" class="stat-card__hint">{{ card.hint }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 行动：待办 + 快捷操作（放在第一屏，先回答"现在要我做什么"） -->
    <el-card class="mt-4" shadow="never">
      <template #header>
        <div class="card-header"><span>{{ $t('admin.dashboard.todo') }}</span></div>
      </template>

      <p v-if="!hasTodo" class="todo-empty">{{ $t('admin.dashboard.noTodo') }}</p>
      <ul v-else class="todo-list">
        <li v-for="entry in todos" :key="entry.key">
          <NuxtLink :to="entry.to" class="todo-item">
            <span class="todo-item__label">{{ entry.label }}</span>
            <el-tag :type="entry.count > 0 ? 'danger' : 'info'" size="small">
              {{ entry.count }}
            </el-tag>
          </NuxtLink>
        </li>
      </ul>

      <div v-if="quickActions.length" class="quick-actions">
        <p class="quick-actions__title">{{ $t('admin.dashboard.quickActions') }}</p>
        <div class="quick-actions__row">
          <el-button v-for="action in quickActions" :key="action.key" plain size="small"
                     @click="router.push(action.to)">
            {{ action.label }}
          </el-button>
        </div>
      </div>
    </el-card>

    <el-row :gutter="16" class="mt-4">
      <el-col :lg="12" :xs="24">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>{{ $t('admin.dashboard.recentArticles') }}</span>
              <el-button link type="primary" @click="router.push('/content/article')">
                {{ $t('admin.common.all') }}
              </el-button>
            </div>
          </template>
          <el-table v-loading="loading" :data="recentArticles" size="small">
            <el-table-column :label="$t('admin.system.menu.itemTitle')" min-width="200" prop="title"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.common.status')" width="90">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small">
                  {{ statusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('article.views')" prop="views" width="80"/>
            <el-table-column :label="$t('admin.common.createdAt')" width="160">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :lg="12" :xs="24">
        <el-card class="mt-4-mobile" shadow="never">
          <template #header>
            <div class="card-header"><span>{{ $t('admin.dashboard.recentComments') }}</span></div>
          </template>
          <el-table v-loading="loading" :data="recentComments" size="small">
            <el-table-column :label="$t('article.author')" prop="author_name" show-overflow-tooltip width="120"/>
            <el-table-column :label="$t('article.content')" min-width="200" prop="content" show-overflow-tooltip/>
            <el-table-column :label="$t('admin.dashboard.review')" width="90">
              <template #default="{ row }">
                <el-tag :type="row.is_approved ? 'success' : 'warning'" size="small">
                  {{ row.is_approved ? t('common.approved') : t('common.pending') }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="mt-4" shadow="never">
      <template #header>
        <div class="card-header"><span>{{ $t('admin.dashboard.topViews') }}</span></div>
      </template>
      <el-table v-loading="loading" :data="topArticles" size="small">
        <el-table-column label="#" type="index" width="60"/>
        <el-table-column :label="$t('admin.system.menu.itemTitle')" min-width="240" prop="title" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.dashboard.views')" prop="views" sortable width="120"/>
        <el-table-column :label="$t('article.likes')" prop="likes" width="100"/>
      </el-table>
    </el-card>

    <!-- 内容分布：把"总数/已发布/草稿"从数字变成占比，趋势与积压一眼可见 -->
    <el-card class="mt-4" shadow="never">
      <template #header>
        <div class="card-header"><span>{{ $t('admin.dashboard.distribution') }}</span></div>
      </template>
      <div class="dist-grid">
        <DonutChart :center-label="$t('admin.dashboard.totalArticles')" :items="articleStatusItems"/>
        <DonutChart :center-label="$t('admin.dashboard.totalComments')" :items="commentStatusItems"/>
      </div>
    </el-card>

    <!-- 访问统计（analytics/tracking 读聚合）：埋点上报产生的真实数据；按权限码门控 -->
    <el-card v-if="canViewTracking" class="mt-4" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ $t('admin.analytics.tracking.visitStats') }}</span>
          <div class="tracking-toolbar">
            <el-radio-group v-model="trackingDays" size="small" @change="loadTracking()">
              <el-radio-button :value="7">{{ $t('admin.analytics.tracking.last7Days') }}</el-radio-button>
              <el-radio-button :value="30">{{ $t('admin.analytics.tracking.last30Days') }}</el-radio-button>
              <el-radio-button :value="90">{{ $t('admin.analytics.tracking.last90Days') }}</el-radio-button>
            </el-radio-group>
            <el-button :icon="Refresh" circle size="small" @click="loadTracking()"/>
          </div>
        </div>
      </template>

      <el-tabs v-model="trackingTab" v-loading="trackingLoading">
        <!-- 会话统计 -->
        <el-tab-pane :label="$t('admin.analytics.tracking.sessions')" name="sessions">
          <el-row :gutter="12">
            <el-col :sm="8" :xs="24">
              <el-statistic :title="$t('admin.analytics.tracking.totalSessions')"
                            :value="sessionStats?.sessions ?? 0"/>
            </el-col>
            <el-col :sm="8" :xs="24">
              <el-statistic :title="$t('admin.analytics.tracking.avgViewsPerSession')"
                            :value="sessionStats?.avg_views_per_session ?? 0"/>
            </el-col>
            <el-col :sm="8" :xs="24">
              <el-statistic :title="$t('admin.analytics.tracking.maxViewsInSession')"
                            :value="sessionStats?.max_views_in_session ?? 0"/>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 流量来源 -->
        <el-tab-pane :label="$t('admin.analytics.tracking.trafficSources')" name="sources">
          <div class="tracking-summary">
            {{ $t('admin.analytics.tracking.totalViews') }}：{{ trafficSources?.total ?? 0 }}
          </div>
          <el-table v-if="trafficSources?.items.length" :data="trafficSources?.items ?? []" size="small">
            <el-table-column :label="$t('admin.analytics.tracking.source')" min-width="240">
              <template #default="{ row }">
                {{ row.source === '(direct)' ? $t('admin.analytics.tracking.direct') : row.source }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.analytics.tracking.views')" prop="views" sortable width="110"/>
            <el-table-column :label="$t('admin.analytics.tracking.share')" width="120">
              <template #default="{ row }">{{ percent(row.share) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-else :description="$t('admin.analytics.tracking.noTrafficData')"/>
        </el-tab-pane>

        <!-- 设备分布 -->
        <el-tab-pane :label="$t('admin.analytics.tracking.devices')" name="devices">
          <el-row :gutter="16">
            <el-col :md="8" :xs="24">
              <h4 class="tracking-sub-title">{{ $t('admin.analytics.tracking.deviceType') }}</h4>
              <el-table :data="deviceBreakdown?.device_type ?? []" size="small">
                <el-table-column :label="$t('admin.analytics.tracking.name')" min-width="120">
                  <template #default="{ row }">
                    {{ row.name === 'unknown' ? $t('admin.analytics.tracking.unknown') : row.name }}
                  </template>
                </el-table-column>
                <el-table-column :label="$t('admin.analytics.tracking.views')" prop="views" width="90"/>
              </el-table>
            </el-col>
            <el-col :md="8" :xs="24">
              <h4 class="tracking-sub-title">{{ $t('admin.analytics.tracking.browser') }}</h4>
              <el-table :data="deviceBreakdown?.browser ?? []" size="small">
                <el-table-column :label="$t('admin.analytics.tracking.name')" min-width="120">
                  <template #default="{ row }">
                    {{ row.name === 'unknown' ? $t('admin.analytics.tracking.unknown') : row.name }}
                  </template>
                </el-table-column>
                <el-table-column :label="$t('admin.analytics.tracking.views')" prop="views" width="90"/>
              </el-table>
            </el-col>
            <el-col :md="8" :xs="24">
              <h4 class="tracking-sub-title">{{ $t('admin.analytics.tracking.platform') }}</h4>
              <el-table :data="deviceBreakdown?.platform ?? []" size="small">
                <el-table-column :label="$t('admin.analytics.tracking.name')" min-width="120">
                  <template #default="{ row }">
                    {{ row.name === 'unknown' ? $t('admin.analytics.tracking.unknown') : row.name }}
                  </template>
                </el-table-column>
                <el-table-column :label="$t('admin.analytics.tracking.views')" prop="views" width="90"/>
              </el-table>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 热门页面 -->
        <el-tab-pane :label="$t('admin.analytics.tracking.popularPages')" name="pages">
          <el-table v-if="popularPages?.items.length" :data="popularPages?.items ?? []" size="small">
            <el-table-column :label="$t('admin.analytics.tracking.pageUrl')" min-width="260" prop="page_url"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.analytics.tracking.views')" prop="views" sortable width="110"/>
            <el-table-column :label="$t('admin.analytics.tracking.sessionsCount')" prop="sessions" width="120"/>
          </el-table>
          <el-empty v-else :description="$t('admin.analytics.tracking.noTrafficData')"/>
        </el-tab-pane>

        <!-- 搜索统计 -->
        <el-tab-pane :label="$t('admin.analytics.tracking.searches')" name="searches">
          <el-row :gutter="12">
            <el-col :sm="8" :xs="24">
              <el-statistic :title="$t('admin.analytics.tracking.totalSearches')"
                            :value="searchStats?.total_searches ?? 0"/>
            </el-col>
            <el-col :sm="8" :xs="24">
              <el-statistic :title="$t('admin.analytics.tracking.zeroResultRate')"
                            :value="percent(searchStats?.zero_result_rate ?? null)"/>
            </el-col>
          </el-row>
          <el-table :data="searchStats?.items ?? []" class="mt-2" size="small">
            <el-table-column label="#" type="index" width="60"/>
            <el-table-column :label="$t('admin.analytics.tracking.keyword')" min-width="180" prop="keyword"/>
            <el-table-column :label="$t('admin.analytics.tracking.count')" prop="count" sortable width="100"/>
            <el-table-column :label="$t('admin.analytics.tracking.avgResults')" width="120">
              <template #default="{ row }">{{ Number(row.avg_results ?? 0).toFixed(1) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 广告统计 -->
        <el-tab-pane :label="$t('admin.analytics.tracking.ads')" name="ads">
          <el-row :gutter="12">
            <el-col :sm="8" :xs="24">
              <el-statistic :title="$t('admin.analytics.tracking.impressions')"
                            :value="adStats?.impressions ?? 0"/>
            </el-col>
            <el-col :sm="8" :xs="24">
              <el-statistic :title="$t('admin.analytics.tracking.clicks')" :value="adStats?.clicks ?? 0"/>
            </el-col>
            <el-col :sm="8" :xs="24">
              <el-statistic :title="$t('admin.analytics.tracking.ctr')"
                            :value="percent(adStats?.ctr ?? null)"/>
            </el-col>
          </el-row>
          <h4 class="tracking-sub-title">{{ $t('admin.analytics.tracking.topAds') }}</h4>
          <el-table :data="adStats?.top_ads ?? []" size="small">
            <el-table-column :label="$t('admin.analytics.tracking.adId')" prop="ad_id" width="120"/>
            <el-table-column :label="$t('admin.analytics.tracking.clicks')" prop="clicks" sortable width="120"/>
          </el-table>
        </el-tab-pane>

        <!-- 文章行为 -->
        <el-tab-pane :label="$t('admin.analytics.tracking.articleEvents')" name="article">
          <el-form :inline="true" @submit.prevent="loadArticleEvents()">
            <el-form-item :label="$t('admin.analytics.tracking.articleId')">
              <el-input-number v-model="articleEventId" :min="1" style="width: 160px"/>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="loadArticleEvents()">
                {{ $t('admin.analytics.tracking.query') }}
              </el-button>
            </el-form-item>
          </el-form>
          <template v-if="articleEvents">
            <el-table v-if="articleEventRows.length" v-loading="articleEventLoading"
                      :data="articleEventRows" size="small">
              <el-table-column :label="$t('admin.analytics.tracking.activityType')" min-width="180" prop="type"/>
              <el-table-column :label="$t('admin.analytics.tracking.count')" prop="count" sortable width="120"/>
            </el-table>
            <el-empty v-else :description="$t('admin.analytics.tracking.noEvents')"/>
          </template>
          <el-empty v-else :description="$t('admin.analytics.tracking.articleIdPlaceholder')"/>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
const {t} = useI18n()

// 后台入口页此前完全没有 definePageMeta：无 auth 中间件、无 admin 布局，
// 未登录可直接打开（e2e 发现，见 HANDOVER §17）。数据权限仍由后端接口兜底。
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'menu.dashboard',
})

import {Refresh, Search} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import {computed, onMounted, ref} from 'vue'

import {
  certificationApi,
  tippingApi,
  trackingApi,
  type AdStatsResult,
  type ArticleEventsResult,
  type DeviceBreakdownResult,
  type PopularPagesResult,
  type SearchStatsResult,
  type SessionStatsResult,
  type TrafficSourcesResult,
} from '@/api'
import {
  dashboardApi,
  type DashboardOverview,
  type RecentArticle,
  type RecentComment,
  type TopArticle,
} from '@/api/modules/dashboard'
import {useUserStore} from '@/store/modules/user'
import {ElMessage} from '@/utils/feedback'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const overview = ref<DashboardOverview | null>(null)
const recentArticles = ref<RecentArticle[]>([])
const recentComments = ref<RecentComment[]>([])
const topArticles = ref<TopArticle[]>([])

const cards = computed(() => {
  const data = overview.value
  return [
    {
      label: t('admin.dashboard.totalArticles'),
      value: data?.total_articles ?? 0,
      hint: t('admin.dashboard.articleHint', {
        published: data?.published_articles ?? 0,
        draft: data?.draft_articles ?? 0
      })
    },
    {
      label: t('admin.dashboard.totalUsers'),
      value: data?.total_users ?? 0,
      hint: t('admin.dashboard.userHint', {active: data?.active_users ?? 0})
    },
    {
      label: t('admin.dashboard.totalComments'),
      value: data?.total_comments ?? 0,
      hint: t('admin.dashboard.commentHint', {pending: data?.pending_comments ?? 0})
    },
    {label: t('admin.dashboard.totalViews'), value: data?.total_views ?? 0},
    {label: t('admin.dashboard.categories'), value: data?.total_categories ?? 0},
    {label: t('admin.dashboard.mediaFiles'), value: data?.total_media ?? 0},
  ]
})

/** 内容分布（环形图）：直接用 overview 里已有的计数，不额外请求接口 */
const articleStatusItems = computed(() => [
  {label: t('common.published'), value: overview.value?.published_articles ?? 0},
  {label: t('common.draft'), value: overview.value?.draft_articles ?? 0},
])

const commentStatusItems = computed(() => {
  const total = overview.value?.total_comments ?? 0
  const pending = overview.value?.pending_comments ?? 0
  return [
    {label: t('common.approved'), value: Math.max(total - pending, 0)},
    {label: t('common.pending'), value: pending},
  ]
})

// ---------------------------------------------------------------- 待办
/**
 * 待办计数：仪表盘此前是纯数字陈列板，看不出"现在要我做什么"。
 * 认证 / 提现的统计各有专门接口，且都按权限判断是否请求（没权限就不发请求、也不占位显示）。
 */
const canViewCertification = computed(() => userStore.hasPermission('module_gamification:certification:view'))
const canViewTipping = computed(() => userStore.hasPermission('module_commerce:tipping:view'))

const pendingCertifications = ref(0)
const pendingWithdrawals = ref(0)

async function loadPending(): Promise<void> {
  const tasks: Array<Promise<void>> = []
  if (canViewCertification.value) {
    tasks.push(
      certificationApi
        .stats()
        .then((stats) => {
          pendingCertifications.value = stats.pending ?? 0
        })
        .catch(() => {
          pendingCertifications.value = 0
        }),
    )
  }
  if (canViewTipping.value) {
    tasks.push(
      tippingApi
        .stats()
        .then((stats) => {
          pendingWithdrawals.value = stats.withdrawal_pending ?? 0
        })
        .catch(() => {
          pendingWithdrawals.value = 0
        }),
    )
  }
  await Promise.all(tasks)
}

interface TodoEntry {
  key: string
  label: string
  count: number
  to: string
}

const todos = computed<TodoEntry[]>(() => {
  const list: TodoEntry[] = [
    {
      key: 'comments',
      label: t('admin.dashboard.pendingComments'),
      count: overview.value?.pending_comments ?? 0,
      to: '/content/comment',
    },
  ]
  if (canViewCertification.value) {
    list.push({
      key: 'certifications',
      label: t('admin.dashboard.pendingCertifications'),
      count: pendingCertifications.value,
      to: '/gamification/certifications',
    })
  }
  if (canViewTipping.value) {
    list.push({
      key: 'withdrawals',
      label: t('admin.dashboard.pendingWithdrawals'),
      count: pendingWithdrawals.value,
      to: '/commerce/tipping',
    })
  }
  return list
})

const hasTodo = computed(() => todos.value.some((entry) => entry.count > 0))

/** 快捷操作：按权限给出常用入口 */
const quickActions = computed(() =>
  [
    {
      key: 'newArticle',
      label: t('admin.content.article.newArticle'),
      to: '/content/article/new',
      permission: 'module_content:article:create'
    },
    {
      key: 'media',
      label: t('admin.content.media.mediaLibrary'),
      to: '/content/media',
      permission: 'module_content:media:view'
    },
    {key: 'users', label: t('menu.UserList'), to: '/system/user', permission: 'module_system:user:view'},
    {
      key: 'setting',
      label: t('admin.system.setting.title'),
      to: '/system/setting',
      permission: 'module_system:setting:view'
    },
  ].filter((action) => userStore.hasPermission(action.permission)),
)

function statusText(status?: number | null): string {
  if (status === 1) return t('common.published')
  if (status === 0) return t('common.draft')
  if (status === -1) return t('admin.dashboard.deleted')
  return t('admin.dashboard.unknown')
}

function statusTagType(status?: number | null): 'success' | 'info' | 'danger' | 'warning' {
  if (status === 1) return 'success'
  if (status === 0) return 'warning'
  if (status === -1) return 'danger'
  return 'info'
}

function formatTime(value?: string | null): string {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const [overviewData, articles, comments, tops] = await Promise.all([
      dashboardApi.overview(),
      dashboardApi.recentArticles(5),
      dashboardApi.recentComments(5),
      dashboardApi.topArticles(10),
    ])
    overview.value = overviewData
    recentArticles.value = articles
    recentComments.value = comments
    topArticles.value = tops
  } catch {
    // 拦截器已提示
  } finally {
    loading.value = false
  }
  // 待办计数与主数据互不依赖：即使失败也不该影响仪表盘主体
  await loadPending()
}

// ---------------------------------------------------------------- 访问统计（analytics/tracking）
/**
 * 7 个读聚合端点均要求权限码 module_analytics:dashboard:view，故与仪表盘同权限：
 * 无权限的用户不请求、不占位（与上方待办的权限判断一致）。
 */
const canViewTracking = computed(() => userStore.hasPermission('module_analytics:dashboard:view'))

const trackingTab = ref('sessions')
const trackingDays = ref(7)
const trackingLoading = ref(false)
const trafficSources = ref<TrafficSourcesResult | null>(null)
const deviceBreakdown = ref<DeviceBreakdownResult | null>(null)
const popularPages = ref<PopularPagesResult | null>(null)
const sessionStats = ref<SessionStatsResult | null>(null)
const searchStats = ref<SearchStatsResult | null>(null)
const adStats = ref<AdStatsResult | null>(null)

/** 把 0–1 的小数比率格式化为百分比；null/undefined 显示 '-' */
function percent(rate: number | null | undefined): string {
  if (rate === null || rate === undefined) return '-'
  return `${(rate * 100).toFixed(1)}%`
}

async function loadTracking(): Promise<void> {
  if (!canViewTracking.value) return
  trackingLoading.value = true
  try {
    const days = trackingDays.value
    const [sources, devices, pages, sessions, searches, ads] = await Promise.all([
      trackingApi.trafficSources({days}),
      trackingApi.devices(days),
      trackingApi.popularPages({days}),
      trackingApi.sessions(days),
      trackingApi.searches({days}),
      trackingApi.ads(days),
    ])
    trafficSources.value = sources
    deviceBreakdown.value = devices
    popularPages.value = pages
    sessionStats.value = sessions
    searchStats.value = searches
    adStats.value = ads
  } catch {
    // 拦截器已提示；保留上一份数据
  } finally {
    trackingLoading.value = false
  }
}

// 单篇文章行为事件：按需查询（非首屏加载）
const articleEventId = ref<number | undefined>(undefined)
const articleEvents = ref<ArticleEventsResult | null>(null)
const articleEventLoading = ref(false)

/** by_type（事件类型 → 次数）摊平成表格行 */
const articleEventRows = computed(() =>
  Object.entries(articleEvents.value?.by_type ?? {}).map(([type, count]) => ({type, count})),
)

async function loadArticleEvents(): Promise<void> {
  const id = articleEventId.value
  if (!id || id < 1) {
    ElMessage.warning(t('admin.analytics.tracking.articleIdRequired'))
    return
  }
  articleEventLoading.value = true
  try {
    articleEvents.value = await trackingApi.articleEvents(id, trackingDays.value)
  } finally {
    articleEventLoading.value = false
  }
}

onMounted(() => {
  void load()
  void loadTracking()
})
</script>

<style scoped>
.stat-card {
  margin-bottom: 16px;
}

.stat-card__label {
  font-size: 13px;
  color: var(--color-fg-muted);
}

.stat-card__value {
  font-size: 24px;
  font-weight: 600;
  margin: 6px 0 2px;
}

.stat-card__hint {
  font-size: 12px;
  color: var(--color-fg-subtle);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* 待办与快捷操作 */
.todo-list {
  padding: 0;
  margin: 0;
  list-style: none;
}

.todo-item {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 8px 2px;
  border-bottom: 1px solid var(--admin-line);
}

.todo-item:last-child {
  border-bottom: 0;
}

.todo-item__label {
  font-size: 14px;
  color: var(--admin-fg);
}

.todo-empty {
  padding: 10px 2px;
  margin: 0;
  font-size: 14px;
  color: var(--admin-fg-subtle);
}

.quick-actions {
  padding-top: 12px;
  margin-top: 14px;
  border-top: 1px dashed var(--admin-line);
}

.quick-actions__title {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

.quick-actions__row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* 内容分布：两张环形图并排，窄屏自动堆叠 */
.dist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--admin-gap-lg);
}

/* 访问统计 */
.tracking-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
}

.tracking-summary {
  margin-bottom: 10px;
  font-size: 13px;
  color: var(--color-fg-muted);
}

.tracking-sub-title {
  margin: 12px 0 8px;
  font-size: 13px;
  font-weight: 600;
}

.mt-2 {
  margin-top: 8px;
}

.mt-4 {
  margin-top: 16px;
}

.mt-4-mobile {
  margin-top: 16px;
}

@media (min-width: 1200px) {
  .mt-4-mobile {
    margin-top: 0;
  }
}
</style>
