<script lang="ts" setup>
/**
 * 区块：post-meta —— 文章元信息
 *
 * 参数：`showAuthor`（默认 true）、`showDate`（默认 true）、`showViews`（默认 false）。
 * 数据来自 `context.article`（父级已取好）。
 */
import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const article = computed(() => props.context.article ?? null)

function textOf(key: string): string {
  const value = article.value?.[key]
  return typeof value === 'string' ? value : ''
}

const author = computed(() => textOf('author_name') || textOf('author'))
const publishedAt = computed(() =>
  (textOf('published_at') || textOf('created_at')).slice(0, 10),
)
const views = computed(() => {
  const value = article.value?.views
  return typeof value === 'number' ? value : null
})

const showAuthor = computed(() => props.propsData.showAuthor !== false)
const showDate = computed(() => props.propsData.showDate !== false)
const showViews = computed(() => props.propsData.showViews === true)

const parts = computed(() => {
  const items: string[] = []
  if (showAuthor.value && author.value) items.push(author.value)
  if (showDate.value && publishedAt.value) items.push(publishedAt.value)
  if (showViews.value && views.value !== null) items.push(`${views.value} 次阅读`)
  return items
})
</script>

<template>
  <p v-if="parts.length" :class="['t-muted text-sm', props.blockClass]">
    {{ parts.join(' · ') }}
  </p>
</template>
