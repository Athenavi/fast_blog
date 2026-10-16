<script lang="ts" setup>
/**
 * 区块：category-nav —— 分类导航
 *
 * 参数：`limit`（最多显示几个，默认 12，1~50）、`style`（`tag` | `list`，默认 `tag`）。
 *
 * 取数用公开接口 `/content/category/public`（与内置首页、内置列表页同一套）。
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
  return Number.isFinite(raw) ? Math.min(50, Math.max(1, Math.floor(raw))) : 12
})

const style = computed(() => (props.propsData.style === 'list' ? 'list' : 'tag'))

const {data: categories} = await useAsyncData(
  () => `theme-block-category-nav-${limit.value}`,
  () => apiGet<CategoryItem[]>('/content/category/public'),
)

const list = computed(() => (categories.value ?? []).slice(0, limit.value))
</script>

<template>
  <nav v-if="list.length" :class="props.blockClass">
    <ul :class="style === 'tag' ? 'flex flex-wrap gap-2' : 'flex flex-col gap-2'">
      <li v-for="category in list" :key="category.id">
        <NuxtLink :class="style === 'tag' ? 't-tag' : 't-muted text-sm'" :to="`/category/${category.id}`">
          {{ category.name }}
        </NuxtLink>
      </li>
    </ul>
  </nav>
</template>
