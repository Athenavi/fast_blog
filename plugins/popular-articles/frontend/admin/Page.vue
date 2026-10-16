<script lang="ts" setup>
import {onMounted, ref, watch} from 'vue'

import {pluginAction} from '@/utils/pluginAction'

const {t} = useI18n()

/**
 * 阅读排行（popular-articles 插件后台页）
 *
 * 对应 `plugins/popular-articles/frontend/admin/Page.tsx`。
 * 原实现的 `AuthGuard` / `QueryProvider` / `AdminShell` 在 Nuxt 侧由宿主页的
 * `middleware: 'auth'`、Vue 响应式、admin 布局承担，这里只实现内容。
 */
interface PopularArticle {
  id: number
  title?: string | null
  slug?: string | null
  views?: number | null
}

const MAX_OPTIONS = [5, 10, 15, 20]
const DAY_OPTIONS = [7, 14, 30, 90]

const maxItems = ref(5)
const days = ref(30)

const loading = ref(true)
const error = ref('')
const items = ref<PopularArticle[]>([])

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const result = await pluginAction<PopularArticle[]>('popular-articles', 'get_popular', {
      max_items: maxItems.value,
      days: days.value,
    })
    items.value = Array.isArray(result.data) ? result.data : []
    if (!result.success) error.value = result.error || t('admin.pluginPages.common.loadFailed')
  } finally {
    loading.value = false
  }
}

watch([maxItems, days], load)
onMounted(load)

/** 前三名高亮（与 astro 版一致） */
function rankClass(index: number): string {
  if (index === 0) return 'bg-amber-100 text-amber-700'
  if (index === 1) return 'bg-surface-soft text-fg-muted'
  if (index === 2) return 'bg-orange-100 text-orange-700'
  return 'text-fg-subtle'
}

function articleLink(item: PopularArticle): string {
  return item.slug ? `/articles/${item.slug}` : `/articles/id/${item.id}`
}
</script>

<template>
  <div class="p-4">
    <!-- 筛选 -->
    <div class="mb-3 flex flex-wrap items-center gap-4 text-sm text-fg-muted">
      <label class="flex items-center gap-1.5">
        <span>{{ t('admin.pluginPages.popularArticles.show') }}</span>
        <el-select v-model="maxItems" class="w-24" size="small">
          <el-option v-for="n in MAX_OPTIONS" :key="n" :label="String(n)" :value="n"/>
        </el-select>
      </label>
      <label class="flex items-center gap-1.5">
        <span>{{ t('admin.pluginPages.popularArticles.recent') }}</span>
        <el-select v-model="days" class="w-24" size="small">
          <el-option v-for="n in DAY_OPTIONS" :key="n" :label="t('admin.pluginPages.popularArticles.days', {n})"
                     :value="n"/>
        </el-select>
      </label>
      <el-button :loading="loading" link type="primary" @click="load">
        <Icon class="mr-1 h-3.5 w-3.5" name="refresh-cw"/>
        {{ t('admin.common.refresh') }}
      </el-button>
    </div>

    <div v-if="loading" class="space-y-3">
      <Skeleton v-for="i in 5" :key="i" class="h-16 w-full"/>
    </div>

    <p v-else-if="error" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

    <EmptyState
      v-else-if="!items.length"
      :description="t('admin.pluginPages.popularArticles.emptyDesc')"
      :title="t('admin.pluginPages.popularArticles.emptyTitle')"
    />

    <div v-else class="overflow-hidden rounded-card border border-line bg-surface">
      <div class="divide-y divide-line">
        <div
          v-for="(item, index) in items"
          :key="item.id"
          class="flex items-center gap-4 px-5 py-4 transition-colors hover:bg-surface-soft"
        >
          <span
            :class="rankClass(index)"
            class="flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold"
          >{{ index + 1 }}</span>

          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium text-fg">{{ item.title || `#${item.id}` }}</p>
            <p class="text-xs text-fg-subtle">{{
                t('admin.pluginPages.popularArticles.views', {n: item.views ?? 0})
              }}</p>
          </div>

          <NuxtLink
            :to="articleLink(item)"
            class="whitespace-nowrap rounded-control px-3 py-1.5 text-xs text-primary transition-colors hover:bg-primary-soft"
            target="_blank"
          >{{ t('admin.pluginPages.popularArticles.view') }}
          </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>
