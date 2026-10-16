<script lang="ts" setup>
/**
 * 主题页面宿主：**L2 组件 → L1 区块 → 内置页**
 *
 * 把「当前主题怎么交付这个页面」的判断收敛到**一处**，每个前台页面只需包一层，
 * 不必各写判断，也不会出现"某个页面忘了接主题"的不一致。
 *
 * ## 三级回退（用户拍板：L2 覆盖 L1）
 *
 * 1. **L2 —— 主题自带的编译期组件**（`plugins/<slug>/frontend/site/<page>.vue`）：
 *    表现力完整，但需要主题自行构建；
 * 2. **L1 —— 主题在 `theme.json` 里声明的区块**（本次新增）：纯数据，
 *    **改 theme.json 刷新即生效、零构建**，这是"热插拔"的关键；
 * 3. **内置页**（默认插槽）：主题两者都没给时，用站点自带实现。
 *
 * ## 用法
 *
 * ```vue
 * <ThemePage page="ArticlePage" :article="article">
 *   <!-- 内置默认实现 -->
 * </ThemePage>
 * ```
 *
 * ## 关于 `article`
 *
 * 显式声明为 prop 而不是靠 `$attrs` 透传：详情页的正文/标题来自父级已取好的数据，
 * 显式传参让区块拿到的与页头显示的是**同一份**，避免并发写入时"页头与正文不是同一篇"。
 */
import type {Component} from 'vue'

import BlockRenderer from '@/components/site/blocks/BlockRenderer.vue'
import type {BlockContext, BlockNode} from '@/components/site/blocks/types'

const props = defineProps<{
  /** 页面名（不带扩展名），如 `HomePage` / `ArchivePage` / `ArticlePage` */
  page: string
  /**
   * 详情页传文章对象
   *
   * 类型声明为 `unknown` 而不是 `Record<string, unknown>`：调用方传的是
   * `ArticleDetail` 这类**具名接口**，它没有索引签名、与 `Record` 不兼容。
   * 主题宿主不该约束页面的数据形状 —— 那是调用方的类型。
   */
  article?: unknown
  /** 页面上下文（列表页可传 page/totalPages 供 pagination 区块使用） */
  context?: BlockContext
}>()

// ── L2：主题自带的编译期组件（优先级最高）
const loader = useThemePage(props.page)

/**
 * `import.meta.glob` 返回的是**加载器函数**而非组件本身，必须包一层
 * `defineAsyncComponent`；主题没提供该页面时为 null，继续往下回退。
 */
const impl = computed(() =>
  loader.value ? defineAsyncComponent(loader.value) : null,
)

// ── L1：主题声明的区块
const templates = useThemeTemplates()

const nodes = computed<BlockNode[]>(() => {
  const raw = templates.value[props.page]
  return Array.isArray(raw) ? (raw as BlockNode[]) : []
})

/** 空数组视为"主题没声明这个页面"，继续回退（而不是渲染一个空页） */
const hasBlocks = computed(() => nodes.value.length > 0)

// ── 传给区块的上下文：页面级 context 优先，article 兜底
const blockContext = computed<BlockContext>(() => {
  const base: BlockContext = {...(props.context ?? {})}
  if (props.article !== null && props.article !== undefined && typeof props.article === 'object') {
    base.article = props.article as Record<string, unknown>
  }
  return base
})
</script>

<template>
  <!-- L2：主题自带组件（用户拍板：覆盖 L1） -->
  <component :is="impl" v-if="impl" v-bind="$attrs"/>
  <!-- L1：主题声明的区块（热插拔路径，零构建） -->
  <BlockRenderer v-else-if="hasBlocks" :context="blockContext" :nodes="nodes"/>
  <!-- 都没有：内置页 -->
  <slot v-else/>
</template>
