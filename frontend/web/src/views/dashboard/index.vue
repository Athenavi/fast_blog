<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col v-for="card in cards" :key="card.label" :xs="12" :sm="8" :md="6" :lg="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-card__label">{{ card.label }}</div>
          <div class="stat-card__value">{{ card.value }}</div>
          <div v-if="card.hint" class="stat-card__hint">{{ card.hint }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mt-4">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>最近文章</span>
              <el-button link type="primary" @click="router.push('/content/article')">
                全部
              </el-button>
            </div>
          </template>
          <el-table :data="recentArticles" v-loading="loading" size="small">
            <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip/>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small">
                  {{ statusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="views" label="浏览" width="80"/>
            <el-table-column label="创建时间" width="160">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="mt-4-mobile">
          <template #header>
            <div class="card-header">
              <span>最近评论</span>
              <el-button link type="primary" @click="router.push('/content/comment')">
                全部
              </el-button>
            </div>
          </template>
          <el-table :data="recentComments" v-loading="loading" size="small">
            <el-table-column prop="author_name" label="作者" width="120" show-overflow-tooltip/>
            <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip/>
            <el-table-column label="审核" width="90">
              <template #default="{ row }">
                <el-tag :type="row.is_approved ? 'success' : 'warning'" size="small">
                  {{ row.is_approved ? '已通过' : '待审核' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="mt-4">
      <template #header>
        <div class="card-header"><span>浏览量排行</span></div>
      </template>
      <el-table :data="topArticles" v-loading="loading" size="small">
        <el-table-column type="index" label="#" width="60"/>
        <el-table-column prop="title" label="标题" min-width="240" show-overflow-tooltip/>
        <el-table-column prop="views" label="浏览量" width="120" sortable/>
        <el-table-column prop="likes" label="点赞" width="100"/>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import dayjs from 'dayjs'
import {computed, onMounted, ref} from 'vue'
import {useRouter} from 'vue-router'

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
      label: '文章总数',
      value: data?.total_articles ?? 0,
      hint: `已发布 ${data?.published_articles ?? 0} / 草稿 ${data?.draft_articles ?? 0}`
    },
    {label: '用户总数', value: data?.total_users ?? 0, hint: `启用 ${data?.active_users ?? 0}`},
    {label: '评论总数', value: data?.total_comments ?? 0, hint: `待审核 ${data?.pending_comments ?? 0}`},
    {label: '总浏览量', value: data?.total_views ?? 0},
    {label: '分类数', value: data?.total_categories ?? 0},
    {label: '媒体数', value: data?.total_media ?? 0},
  ]
})

function statusText(status?: number | null): string {
  if (status === 1) return '已发布'
  if (status === 0) return '草稿'
  if (status === -1) return '已删除'
  return '未知'
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
  color: #6b7280;
}

.stat-card__value {
  font-size: 24px;
  font-weight: 600;
  margin: 6px 0 2px;
}

.stat-card__hint {
  font-size: 12px;
  color: #9ca3af;
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
