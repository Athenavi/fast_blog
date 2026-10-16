<script lang="ts" setup>
/**
 * 区块：widget-categories —— 分类小工具（WP 右侧栏的经典项）
 *
 * 参数：`title`、`limit`（默认 10）、`showCount`（布尔，默认 true，显示每类文章数）。
 *
 * 取数用公开接口 `/content/category/public`（与内置首页、列表页**同一套**），
 * 可见性由接口保证 —— 主题不自己拼过滤条件，避免与站点口径分叉。
 */
import type {CategoryItem} from '@/types/content'

import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const limit = computed(() => {
  const raw = Number(props.propsData.limit)
  return Number.isFinite(raw) ? Math.min(50, Math.max(1, Math.floor(raw))) : 10
})

const title = computed(() => {
  const raw = props.propsData.title
  return typeof raw === 'string' && raw.trim() ? raw : '分类'
})

const showCount = computed(() => props.propsData.showCount !== false)

const {data: categories} = await useAsyncData(
  () => `theme-block-widget-categories-${limit.value}`,
  () => apiGet<CategoryItem[]>('/content/category/public'),
)

const list = computed(() => (categories.value ?? []).slice(0, limit.value))
</script>

<template>
  <nav v-if="list.length" :class="['t-widget', props.blockClass]">
    <h2 class="t-widget__title">{{ title }}</h2>
    <ul class="t-widget__list">
      <li v-for="category in list" :key="category.id" class="t-widget__item">
        <NuxtLink :to="`/category/${category.id}`" class="t-widget__link">
          {{ category.name }}
          <span v-if="showCount && category.article_count" class="t-widget__count">
            {{ category.article_count }}
          </span>
        </NuxtLink>
      </li>
    </ul>
  </nav>
</template>
