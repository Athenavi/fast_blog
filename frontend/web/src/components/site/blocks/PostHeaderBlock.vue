<script lang="ts" setup>
/**
 * 区块：post-header —— 文章标题区
 *
 * 参数：`showSummary`（布尔，默认 true）、`showMeta`（布尔，默认 false）。
 *
 * 文章来自 `context.article`（**父级已取好**，见 ThemePage 的取数分工说明）——
 * 区块不自己取数，避免"页头标题与正文不是同一篇"。
 */
import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const article = computed(() => props.context.article ?? null)
const title = computed(() => {
  const value = article.value?.title
  return typeof value === 'string' ? value : ''
})
const summary = computed(() => {
  const value = article.value?.summary
  return typeof value === 'string' ? value : ''
})
const publishedAt = computed(() => {
  const value = article.value?.published_at ?? article.value?.created_at
  return typeof value === 'string' ? value.slice(0, 10) : ''
})

const showSummary = computed(() => props.propsData.showSummary !== false)
const showMeta = computed(() => props.propsData.showMeta === true)
</script>

<template>
  <header v-if="article" :class="props.blockClass">
    <h1 class="text-3xl font-bold tracking-tight text-fg sm:text-4xl">{{ title }}</h1>
    <p v-if="showSummary && summary" class="t-muted mt-3">{{ summary }}</p>
    <p v-if="showMeta && publishedAt" class="t-muted mt-2 text-sm">{{ publishedAt }}</p>
  </header>
</template>
