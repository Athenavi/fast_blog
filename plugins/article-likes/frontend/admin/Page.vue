<script lang="ts" setup>
import {onMounted, ref} from 'vue'

import {pluginAction} from '@/utils/pluginAction'

/**
 * 文章点赞排行（article-likes 插件后台页）
 *
 * 对应 `plugins/article-likes/frontend/admin/Page.tsx`。
 * 原实现外层包了 `AuthGuard` + `QueryProvider` + `AdminShell`：
 * 在 Nuxt 侧这三者分别由宿主页的 `middleware: 'auth'`、Vue 响应式、admin 布局承担，
 * 所以这里只实现页面内容。
 */
interface RankItem {
  article_id: number
  likes: number
}

const loading = ref(true)
const error = ref('')
const items = ref<RankItem[]>([])

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const result = await pluginAction<{ data?: RankItem[] }>('article-likes', 'popular', {limit: 20})
    items.value = result.data?.data ?? []
    if (!result.success) error.value = result.error || '加载失败'
  } finally {
    loading.value = false
  }
}

/** 名次配色：前三名高亮（与 astro 版一致） */
function rankClass(index: number): string {
  if (index === 0) return 'bg-amber-100 text-amber-700'
  if (index === 1) return 'bg-surface-soft text-fg-muted'
  if (index === 2) return 'bg-orange-100 text-orange-700'
  return 'text-fg-subtle'
}

onMounted(load)
</script>

<template>
  <div class="p-4">
    <div class="mb-3 flex items-center gap-2 text-sm text-fg-muted">
      <Icon class="h-4 w-4 text-danger" name="heart"/>
      按点赞数排序
    </div>

    <div v-if="loading" class="space-y-3">
      <Skeleton v-for="i in 5" :key="i" class="h-14 w-full"/>
    </div>

    <p v-else-if="error" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

    <EmptyState
      v-else-if="!items.length"
      description="读者开始点赞后，这里会出现排行"
      title="还没有点赞数据"
    />

    <div v-else class="overflow-hidden rounded-card border border-line bg-surface">
      <div class="divide-y divide-line">
        <div
          v-for="(item, index) in items"
          :key="item.article_id"
          class="flex items-center gap-4 px-4 py-3 transition-colors hover:bg-surface-soft"
        >
          <span
            :class="rankClass(index)"
            class="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold"
          >{{ index + 1 }}</span>

          <NuxtLink
            :to="`/articles/id/${item.article_id}`"
            class="flex-1 text-sm text-fg hover:text-primary"
          >文章 #{{ item.article_id }}
          </NuxtLink>

          <span class="flex items-center gap-1.5 text-sm font-medium text-danger">
            <Icon class="h-3.5 w-3.5" name="heart"/>
            {{ item.likes }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
