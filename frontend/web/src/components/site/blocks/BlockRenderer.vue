<script lang="ts" setup>
/**
 * L1 区块渲染器 —— "主题热插拔"的执行体
 *
 * 把 `theme.json` 的 `templates` 描述**递归**渲染成页面。主题只提供**纯数据**，
 * 渲染逻辑全在站点侧，所以**改 theme.json 刷新即生效、不需要重新构建**。
 * 这就是它与 L2（`plugins/<slug>/frontend/site/*.vue`，编译期组件）的根本区别。
 *
 * ## 递归怎么实现
 *
 * 容器类区块（section / columns / container）把子区块放进默认插槽，
 * 渲染器在插槽位置再放一个自己。组件用 `defineOptions({name})` 显式命名，
 * 模板里才能自引用 —— 匿名组件无法递归。
 *
 * ## 未知区块跳过而非报错
 *
 * 后端已按白名单过滤过一遍，这里再查一次表是**防御性**的（前端版本可能比后端旧）。
 * 遇到未注册的区块只 warn 并跳过 —— 少一个区块远好过整页白屏。
 *
 * ## 为什么用动态组件而不是 v-html
 *
 * 区块是**组件**，参数走 props，天然经过 Vue 的转义与响应式系统；
 * 用字符串拼 HTML 会把主题数据当代码，那才是真正的注入面。
 */
import {BLOCK_COMPONENTS} from './registry'
import type {BlockContext, BlockNode} from './types'

defineOptions({name: 'BlockRenderer'})

const props = withDefaults(
  defineProps<{
    /** 区块节点数组（后端已校验；前端再做一次防御性查表） */
    nodes: BlockNode[]
    /** 页面上下文：透传给需要页面数据的区块（如详情页的 post-content） */
    context?: BlockContext
  }>(),
  {context: () => ({})},
)

/** 同一个未注册区块只告警一次，避免长列表把控制台刷满 */
const warned = new Set<string>()

function componentFor(name: string) {
  const component = BLOCK_COMPONENTS[name]
  if (!component && !warned.has(name)) {
    warned.add(name)
    console.warn(`[theme] 区块 "${name}" 未注册，已跳过`)
  }
  return component ?? null
}
</script>

<template>
  <template v-for="(node, index) in props.nodes" :key="`${node.block}-${index}`">
    <component
      :is="componentFor(node.block)"
      v-if="componentFor(node.block)"
      :block-class="node.class"
      :context="props.context"
      :props-data="node.props ?? {}"
    >
      <!-- 递归渲染子区块：容器类区块用默认插槽接收 -->
      <BlockRenderer
        v-if="node.children?.length"
        :context="props.context"
        :nodes="node.children"
      />
    </component>
  </template>
</template>
