<script lang="ts" setup>
/**
 * 区块：post-list —— 文章列表
 *
 * 参数：
 *  - `limit`（条数，默认 6，1~50）
 *  - `layout`（`grid` | `list` | `compact`，默认 `list`）
 *  - `columns`（grid 布局时的列数，默认 3，2~4）
 *  - `paginated`（布尔，是否分页；分页用 URL query，可分享可抓取）
 *  - `category`（分类 id，可选）
 *  - `showExcerpt`（布尔，默认 true）
 *
 * ## 取数与可见性
 *
 * 用与内置列表页**同一套公开接口** `/content/article/public/list` —— 可见性过滤
 * （已发布 / 未隐藏 / 站点 / 定时发布 / VIP）由**接口**保证，主题拿到的就是该看到的。
 * 主题不需要、也不应该自己拼过滤条件。
 *
 * ## 分页状态放 URL
 *
 * 与内置列表页一致：`?page=2` 可分享、可被搜索引擎抓到，而不是组件内部状态。
 */
import type {ArticleItem} from '@/types/content'

import type {BlockContext} from './types'
import PostCardBlock from './PostCardBlock.vue'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

function numberProp(key: string, fallback: number, min: number, max: number): number {
  const raw = Number(props.propsData[key])
  if (!Number.isFinite(raw)) return fallback
  return Math.min(max, Math.max(min, Math.floor(raw)))
}

const limit = computed(() => numberProp('limit', 6, 1, 50))
const layout = computed(() => {
  const raw = props.propsData.layout
  return raw === 'grid' || raw === 'compact' ? raw : 'list'
})
const columns = computed(() => numberProp('columns', 3, 2, 4))
const showExcerpt = computed(() => props.propsData.showExcerpt !== false)
const categoryId = computed(() => {
  const raw = Number(props.propsData.category)
  return Number.isFinite(raw) && raw > 0 ? raw : undefined
})

const route = useRoute()
const paginated = computed(() => props.propsData.paginated === true)

const page = computed(() => {
  if (!paginated.value) return 1
  const raw = Number(route.query.page ?? 1)
  return Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : 1
})

const {data: pageData, pending} = await useAsyncData(
  () => `theme-block-post-list-${limit.value}-${categoryId.value ?? 'all'}-${page.value}`,
  () =>
    apiPage<ArticleItem>('/content/article/public/list', {
      page: page.value,
      page_size: limit.value,
      category_id: categoryId.value,
    }),
  {watch: paginated.value ? [page] : []},
)

const articles = computed(() => pageData.value?.items ?? [])
const totalPages = computed(() =>
  Math.max(1, Math.ceil((pageData.value?.total ?? 0) / limit.value)),
)

/** 布局类名：窄屏一律单列，避免主题声明的多列挤爆手机 */
const listClass = computed(() => {
  if (layout.value === 'grid') return `grid grid-cols-1 gap-6 md:grid-cols-${columns.value}`
  if (layout.value === 'compact') return 'flex flex-col gap-2'
  return 'flex flex-col gap-4'
})
</script>

<template>
  <div :class="props.blockClass">
    <div v-if="pending" class="t-muted py-6 text-sm">…</div>

    <div v-else-if="articles.length" :class="listClass">
      <PostCardBlock
        v-for="article in articles"
        :key="article.id"
        :context="context"
        :props-data="{article, variant: layout, showExcerpt}"
      />
    </div>

    <p v-else class="t-muted py-6 text-sm">暂无文章</p>

    <nav v-if="paginated && totalPages > 1" class="mt-8 flex items-center justify-center gap-3">
      <NuxtLink v-if="page > 1" :to="`${route.path}?page=${page - 1}`" class="t-tag">
        上一页
      </NuxtLink>
      <span class="t-muted text-sm">{{ page }} / {{ totalPages }}</span>
      <NuxtLink v-if="page < totalPages" :to="`${route.path}?page=${page + 1}`" class="t-tag">
        下一页
      </NuxtLink>
    </nav>
  </div>
</template>
