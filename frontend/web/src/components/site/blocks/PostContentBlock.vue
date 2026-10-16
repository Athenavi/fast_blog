<script lang="ts" setup>
/**
 * 区块：post-content —— 文章正文
 *
 * 参数：无（正文来自 `context.article.content`）。
 *
 * ## 为什么这里可以 `v-html`
 *
 * 正文在**服务端**已经过完整管线：短代码展开 → Markdown 转换（若源是 Markdown）
 * → HTML 白名单净化。也就是说进入这个字段的已经是**受控 HTML**，前端只负责摆放。
 *
 * 反过来说：**主题不该把未经服务端净化的内容塞进 `html` 类区块** ——
 * 那会绕过唯一的 XSS 防线。
 */
import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const html = computed(() => {
  const value = props.context.article?.content
  return typeof value === 'string' ? value : ''
})
</script>

<template>
  <div
    v-if="html"
    :class="['prose', props.blockClass]"
    v-html="html"
  />
</template>
