<script lang="ts" setup>
/**
 * 区块：sidebar —— 侧栏容器
 *
 * 参数：`width`（`narrow` | `default`，默认 `default`）、`sticky`（布尔，是否吸顶跟随）。
 *
 * ## 为什么单独有它（而不是复用 section/columns）
 *
 * WP 经典主题的核心特征就是「主栏 + 右侧栏」。只有 `columns` 时，主题只能靠
 * **列的位置**暗示哪块是侧栏；有了 `sidebar` 才能明确表达这个语义 ——
 * 既给样式一个稳定钩子（`.t-sidebar`），也让下面用 `<aside>` 获得无障碍语义：
 * 屏幕阅读器能把侧栏内容与正文区分开（WP 无障碍规范的明确要求）。
 */
import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const WIDTH_CLASS: Record<string, string> = {
  narrow: 'w-full md:w-56',
  default: 'w-full md:w-72',
}

const widthClass = computed(() => {
  const raw = props.propsData.width
  return (typeof raw === 'string' && WIDTH_CLASS[raw]) || WIDTH_CLASS.default
})

const stickyClass = computed(() =>
  props.propsData.sticky === true ? 'md:sticky md:top-20 md:self-start' : '',
)
</script>

<template>
  <aside :class="['t-sidebar shrink-0', widthClass, stickyClass, props.blockClass]">
    <slot/>
  </aside>
</template>
