<script lang="ts" setup>
/** 文章卡片：首页 / 列表 / 分类 / 搜索复用 */

import type {ArticleItem} from '@/types/content'
import {formatDate} from '@/utils/format'

const props = withDefaults(
  defineProps<{
    article: ArticleItem
    /** 首屏（LCP）卡片：跳过懒加载并给高优先级，见 ResponsiveImage 的说明 */
    eager?: boolean
  }>(),
  {eager: false},
)

const to = computed(() =>
  props.article.slug ? `/articles/${props.article.slug}` : `/articles/id/${props.article.id}`,
)
</script>

<template>
  <article class="group">
    <NuxtLink :to="to" class="block">
      <ResponsiveImage
        v-if="props.article.cover_image"
        :alt="props.article.title"
        :eager="props.eager"
        :src="props.article.cover_image"
        class="mb-3 rounded-card"
        sizes="xs:100vw sm:50vw lg:33vw"
      />
      <h3 class="text-base font-semibold leading-snug text-fg transition-colors group-hover:text-primary">
        {{ props.article.title }}
      </h3>
    </NuxtLink>

    <p v-if="props.article.summary" class="mt-1.5 line-clamp-2 text-sm leading-relaxed text-fg-muted">
      {{ props.article.summary }}
    </p>

    <div class="mt-2.5 flex items-center gap-4 text-xs text-fg-muted">
      <span class="inline-flex items-center gap-1">
        <Icon class="h-3.5 w-3.5" name="calendar-days"/>
        {{ formatDate(props.article.published_at || props.article.created_at) }}
      </span>
      <span v-if="props.article.views" class="inline-flex items-center gap-1">
        <Icon class="h-3.5 w-3.5" name="eye"/>
        {{ props.article.views }}
      </span>
      <Badge v-for="tag in (props.article.tags || []).slice(0, 2)" :key="tag" variant="secondary">{{ tag }}</Badge>
    </div>
  </article>
</template>
