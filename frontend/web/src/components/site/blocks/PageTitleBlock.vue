<script lang="ts" setup>
/**
 * 区块：page-title —— 页面标题
 *
 * 参数：`text`（标题文字；不填时由 `context.title` 兜底，再不行留空）。
 *
 * 刻意不自动推断标题（比如读路由）——页面标题属于**主题的表达**，
 * 让它显式声明比猜更可控。
 */
import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const text = computed(() => {
  const raw = props.propsData.text ?? props.context.title
  return typeof raw === 'string' ? raw : ''
})
</script>

<template>
  <h1 v-if="text" :class="['text-2xl font-bold tracking-tight text-fg', props.blockClass]">
    {{ text }}
  </h1>
</template>
