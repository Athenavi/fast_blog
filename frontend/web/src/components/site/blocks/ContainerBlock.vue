<script lang="ts" setup>
/**
 * 区块：container —— 定宽内容容器
 *
 * 参数：`width`（`narrow` | `default` | `wide`），默认 `default`。
 * 用站点既有宽度令牌（`max-w-read` / `max-w-wide`），不引入主题私有尺寸。
 */
import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const WIDTH_CLASS: Record<string, string> = {
  narrow: 'max-w-read',
  default: 'max-w-4xl',
  wide: 'max-w-wide',
}

const widthClass = computed(() => {
  const raw = props.propsData.width
  return (typeof raw === 'string' && WIDTH_CLASS[raw]) || WIDTH_CLASS.default
})
</script>

<template>
  <div :class="[widthClass, 'mx-auto w-full px-4', props.blockClass]">
    <slot/>
  </div>
</template>
