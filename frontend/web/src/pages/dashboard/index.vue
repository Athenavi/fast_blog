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

import dayjs from 'dayjs'
import {computed, onMounted, ref} from 'vue'

import {certificationApi, tippingApi} from '@/api'
import {
  dashboardApi,
  type DashboardOverview,
  type RecentArticle,
  type RecentComment,
  type TopArticle,
} from '@/api/modules/dashboard'
import {useUserStore} from '@/store/modules/user'

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

onMounted(load)
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
