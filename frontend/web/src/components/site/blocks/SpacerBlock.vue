<script lang="ts" setup>
/**
 * 区块：spacer —— 垂直留白
 *
 * 参数：`size`（`sm` | `md` | `lg`，默认 `md`）。
 *
 * 用固定像素值而不是 Tailwind 类名：留白高度是主题的**数值**表达，
 * 编译期类名（`h-8` 之类）没法承载运行时的主题数据。
 */
import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const HEIGHT: Record<string, string> = {
  sm: '1.5rem',
  md: '3rem',
  lg: '5rem',
}

const height = computed(() => {
  const raw = props.propsData.size
  return (typeof raw === 'string' && HEIGHT[raw]) || HEIGHT.md
})
</script>

<template>
  <div
    :class="props.blockClass"
    :style="{height}"
    aria-hidden="true"
  />
</template>
