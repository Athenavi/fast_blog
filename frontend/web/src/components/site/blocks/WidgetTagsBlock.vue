<script lang="ts" setup>
/**
 * 区块：widget-tags —— 标签云小工具（WP 右侧栏的经典项）
 *
 * 参数：`title`（默认「标签」）、`limit`（默认 20）、`showCount`（布尔，默认 false）。
 *
 * 取数用**公开**接口 `GET /content/tag/public`（本轮新增）—— 与后台的
 * `GET /content/tag` 复用同一个 `TagService.list_tags`，只是去掉鉴权并调低上限。
 * 之所以要新增这个端点：原来唯一公开的标签接口是
 * `/content/tag/public/{tag}/articles`（**按标签查文章**），**没有"标签列表"**，
 * 而这个区块恰恰需要列表 —— 用别的数据凑出标签列表就是虚拟实现。
 */
import type {TagItem} from '@/api/modules/tag'

import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const limit = computed(() => {
  const raw = Number(props.propsData.limit)
  return Number.isFinite(raw) ? Math.min(100, Math.max(1, Math.floor(raw))) : 20
})

const title = computed(() => {
  const raw = props.propsData.title
  return typeof raw === 'string' && raw.trim() ? raw : '标签'
})

const showCount = computed(() => props.propsData.showCount === true)

const {data: pageData} = await useAsyncData(
  () => `theme-block-widget-tags-${limit.value}`,
  () => apiPage<TagItem>('/content/tag/public', {page: 1, page_size: limit.value}),
)

const tags = computed(() => pageData.value?.items ?? [])
</script>

<template>
  <nav v-if="tags.length" :class="['t-widget', props.blockClass]">
    <h2 class="t-widget__title">{{ title }}</h2>
    <ul class="t-widget__tags">
      <li v-for="tag in tags" :key="tag.name">
        <NuxtLink :to="`/tag/${encodeURIComponent(tag.name)}`" class="t-tag">
          {{ tag.name }}
          <span v-if="showCount && tag.count" class="t-widget__count">{{ tag.count }}</span>
        </NuxtLink>
      </li>
    </ul>
  </nav>
</template>
