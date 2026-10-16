<script lang="ts" setup>
/**
 * 区块：widget-recent —— 最新文章小工具（WP 右侧栏的经典项）
 *
 * 参数：`title`（默认「最新文章」）、`limit`（默认 5）。
 *
 * 取数用公开接口 `/content/article/public/list` —— 与内置页同一套，
 * 可见性过滤（已发布 / 未隐藏 / 站点 / 定时发布 / VIP）由接口保证。
 */
import type {ArticleItem} from '@/types/content'

import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const limit = computed(() => {
  const raw = Number(props.propsData.limit)
  return Number.isFinite(raw) ? Math.min(20, Math.max(1, Math.floor(raw))) : 5
})

const title = computed(() => {
  const raw = props.propsData.title
  return typeof raw === 'string' && raw.trim() ? raw : '最新文章'
})

const {data: pageData} = await useAsyncData(
  () => `theme-block-widget-recent-${limit.value}`,
  () =>
    apiPage<ArticleItem>('/content/article/public/list', {
      page: 1,
      page_size: limit.value,
    }),
)

const articles = computed(() => pageData.value?.items ?? [])
</script>

<template>
  <section v-if="articles.length" :class="['t-widget', props.blockClass]">
    <h2 class="t-widget__title">{{ title }}</h2>
    <ul class="t-widget__list">
      <li v-for="article in articles" :key="article.id" class="t-widget__item">
        <NuxtLink :to="`/articles/${article.slug}`" class="t-widget__link">
          {{ article.title }}
        </NuxtLink>
      </li>
    </ul>
  </section>
</template>
