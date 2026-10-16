<script lang="ts" setup>
/**
 * 区块：html —— 一段富文本
 *
 * 参数：`content`（HTML 字符串，默认空）、`align`（`left` | `center`）。
 *
 * ## 安全边界（重要）
 *
 * 这里 `v-html` 渲染的是**主题在 `theme.json` 里写死的静态文案** ——
 * 不是用户/访客提交的内容，也不是文章正文（那个走 `post-content`，
 * 由服务端完整净化管线处理）。
 *
 * 即便如此，后端对 prop 值仍做了 `<>` 拦截（见 `theme/blocks.py` 的
 * `_UNSAFE_TOKENS`），所以带标签的文案实际上会被过滤掉 —— 这是**有意的**：
 * 主题不该靠这个区块注入任意 HTML，需要结构化内容请用专门的区块。
 */
import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const content = computed(() => {
  const raw = props.propsData.content
  return typeof raw === 'string' ? raw : ''
})

const alignClass = computed(() =>
  props.propsData.align === 'center' ? 'text-center' : 'text-left',
)
</script>

<template>
  <div v-if="content" :class="[alignClass, props.blockClass]">{{ content }}</div>
</template>
