<script lang="ts" setup>
/**
 * 区块：search-box —— 搜索框
 *
 * 参数：`placeholder`（占位文案）、`action`（提交目标，默认 `/search`）。
 *
 * 用原生 `form` 提交而不是 JS 跳转：这样**无 JS 也能用**，且提交后是可分享的
 * `?q=` URL，与站内搜索页的既有约定一致。
 */
import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const placeholder = computed(() => {
  const raw = props.propsData.placeholder
  return typeof raw === 'string' && raw.trim() ? raw : '搜索…'
})

const action = computed(() => {
  const raw = props.propsData.action
  return typeof raw === 'string' && raw.startsWith('/') ? raw : '/search'
})
</script>

<template>
  <form :action="action" :class="['flex w-full max-w-md gap-2', props.blockClass]" method="get" role="search">
    <input
      :placeholder="placeholder"
      aria-label="搜索"
      class="t-card w-full px-3 py-2 text-sm"
      name="q"
      type="search"
    />
    <button class="t-button px-4 py-2 text-sm" type="submit">搜索</button>
  </form>
</template>
