<script lang="ts" setup>
/**
 * 区块：columns —— 多列容器
 *
 * 参数：`columns`（2 | 3 | 4，默认 2）、`gap`（`sm` | `md` | `lg`，默认 `md`）。
 *
 * ## 子区块怎么分列
 *
 * 每个**直接子区块**占一列（`<slot>` 由 BlockRenderer 递归填充）。
 * 这里不能把子内容按索引切开 —— BlockRenderer 传进来的是整段渲染结果，
 * 所以实际做法是：**用 CSS 把直接子元素排成网格**（`grid` + 自动流）。
 * 子区块内部若要再分组，由它自己用 section 包。
 *
 * 窄屏一律退化为单列：主题声明的列数不应把手机屏撑破。
 */
import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const GAP_CLASS: Record<string, string> = {
  sm: 'gap-4',
  md: 'gap-6',
  lg: 'gap-10',
}

const columnCount = computed(() => {
  const raw = Number(props.propsData.columns)
  return Number.isFinite(raw) && raw >= 2 && raw <= 4 ? Math.floor(raw) : 2
})

/** 用内联 grid-template-columns 表达列数：Tailwind 的列数是编译期固定的，主题给的值是运行时数据 */
const gridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${columnCount.value}, minmax(0, 1fr))`,
}))

const gapClass = computed(() => {
  const raw = props.propsData.gap
  return (typeof raw === 'string' && GAP_CLASS[raw]) || GAP_CLASS.md
})
</script>

<template>
  <!-- 窄屏单列：`md:` 断点以下固定 1 列，避免主题声明的 3~4 列挤爆手机 -->
  <div
    :class="['grid grid-cols-1 md:[grid-template-columns:var(--cols)]', gapClass, props.blockClass]"
    :style="{'--cols': gridStyle.gridTemplateColumns}"
  >
    <slot/>
  </div>
</template>
