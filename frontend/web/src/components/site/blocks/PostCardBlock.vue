<script lang="ts" setup>
/**
 * 区块：post-card —— 单篇文章卡片
 *
 * 参数：
 *  - `article`（**必填**，文章对象；由 post-list 注入，或主题在上下文里提供）
 *  - `variant`（`grid` | `list` | `compact`，默认 `list`）
 *  - `showExcerpt`（布尔，默认 true）
 *  - `showCover`（布尔，默认 false；开启时用 ResponsiveImage 走后端变体）
 *
 * 这是**被 post-list 复用**的叶子区块，所以它接受 `article` 通过 props 传入，
 * 而不是自己去取数 —— 列表已经取过一遍，再取一次只会放大请求数。
 */
import type {ArticleItem} from '@/types/content'

import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const article = computed<ArticleItem | null>(() => {
  const raw = props.propsData.article ?? props.context.article
  return raw && typeof raw === 'object' ? (raw as ArticleItem) : null
})

const variant = computed(() => {
  const raw = props.propsData.variant
  return raw === 'grid' || raw === 'compact' ? raw : 'list'
})

const showExcerpt = computed(() => props.propsData.showExcerpt !== false)
const showCover = computed(() => props.propsData.showCover === true)

const articleUrl = computed(() => (article.value?.slug ? `/articles/${article.value.slug}` : '#'))
</script>

<template>
  <article
    v-if="article"
    :class="[
      't-card p-4',
      variant === 'compact' ? 'py-2' : '',
      props.blockClass,
    ]"
  >
    <NuxtLink :to="articleUrl" class="block">
      <img
        v-if="showCover && article.cover_image"
        :alt="article.title"
        :src="article.cover_image"
        class="mb-3 w-full object-cover"
        loading="lazy"
      />
      <h3 :class="variant === 'grid' ? 'text-lg font-semibold' : 'text-base font-semibold'">
        {{ article.title }}
      </h3>
    </NuxtLink>

    <p
      v-if="showExcerpt && variant !== 'compact' && article.summary"
      class="t-muted mt-2 text-sm"
    >
      {{ article.summary }}
    </p>
  </article>
</template>
