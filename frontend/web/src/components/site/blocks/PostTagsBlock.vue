<script lang="ts" setup>
/**
 * 区块：post-tags —— 文章标签
 *
 * 参数：`limit`（最多几个，默认 10）。
 * 标签来自 `context.article.tags`（父级已取好；可能是字符串数组或对象数组，两种都兼容）。
 */
import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const limit = computed(() => {
  const raw = Number(props.propsData.limit)
  return Number.isFinite(raw) ? Math.min(50, Math.max(1, Math.floor(raw))) : 10
})

interface TagItem {
  id?: number | string
  name: string
}

const tags = computed<TagItem[]>(() => {
  const raw = props.context.article?.tags
  if (!Array.isArray(raw)) return []
  const out: TagItem[] = []
  for (const item of raw) {
    if (typeof item === 'string' && item.trim()) {
      out.push({name: item.trim()})
    } else if (item && typeof item === 'object') {
      const record = item as Record<string, unknown>
      const name = record.name
      if (typeof name === 'string' && name.trim()) {
        out.push({
          id: typeof record.id === 'number' || typeof record.id === 'string' ? record.id : undefined,
          name: name.trim(),
        })
      }
    }
    if (out.length >= limit.value) break
  }
  return out
})
</script>

<template>
  <div v-if="tags.length" :class="['flex flex-wrap gap-2', props.blockClass]">
    <span v-for="tag in tags" :key="String(tag.id ?? tag.name)" class="t-tag">
      {{ tag.name }}
    </span>
  </div>
</template>
