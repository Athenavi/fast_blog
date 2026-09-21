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
            <div class="card-header">
              <span>{{ $t('admin.dashboard.recentComments') }}</span>
              <el-button link type="primary" @click="router.push('/content/comment')">
                {{ $t('admin.common.all') }}
              </el-button>
            </div>
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

import {
  dashboardApi,
  type DashboardOverview,
  type RecentArticle,
  type RecentComment,
  type TopArticle,
} from '@/api/modules/dashboard'

const router = useRouter()

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
