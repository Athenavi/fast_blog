<script lang="ts" setup>
/**
 * 区块：post-related —— 相关文章
 *
 * 参数：`limit`（默认 5）、`strategy`（`category` 当前只支持按分类）。
 *
 * 取数：用公开列表接口按**当前文章的分类**再取一批，并排除自己。
 * 复用的是同一套公开接口，可见性过滤由接口保证。
 */
import type {ArticleItem} from '@/types/content'

import type {BlockContext} from './types'
import PostCardBlock from './PostCardBlock.vue'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const limit = computed(() => {
  const raw = Number(props.propsData.limit)
  return Number.isFinite(raw) ? Math.min(20, Math.max(1, Math.floor(raw))) : 5
})

const currentId = computed(() => {
  const value = props.context.article?.id
  return typeof value === 'number' ? value : null
})

const categoryId = computed(() => {
  const value = props.context.article?.category_id
  return typeof value === 'number' && value > 0 ? value : undefined
})

// 无分类就无法"相关"，直接不请求
const enabled = computed(() => categoryId.value !== undefined)

const {data: pageData} = await useAsyncData(
  () => `theme-block-post-related-${currentId.value ?? 0}-${categoryId.value ?? 0}-${limit.value}`,
  () =>
    apiPage<ArticleItem>('/content/article/public/list', {
      // 多取一条：因为要排除当前文章
      page: 1,
      page_size: limit.value + 1,
      category_id: categoryId.value,
    }),
  {watch: [currentId, categoryId, limit]},
)

const related = computed(() =>
  (pageData.value?.items ?? [])
    .filter((item) => item.id !== currentId.value)
    .slice(0, limit.value),
)
</script>

<template>
  <section v-if="enabled && related.length" :class="props.blockClass">
    <h2 class="mb-4 text-lg font-semibold tracking-tight text-fg">相关文章</h2>
    <div class="flex flex-col gap-3">
      <PostCardBlock
        v-for="item in related"
        :key="item.id"
        :context="context"
        :props-data="{article: item, variant: 'compact'}"
      />
    </div>
  </section>
</template>
