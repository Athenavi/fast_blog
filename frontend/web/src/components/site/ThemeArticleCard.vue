<script lang="ts" setup>
/**
 * 主题化文章卡片
 *
 * 对应原 astro 的 `theme/ThemeArticleCard.tsx`：卡片样式由主题的
 * `componentSlots.articleCard` 决定（`default` 标准 / `compact` 紧凑），
 * 并支持 `grid`（竖向卡片）与 `list`（横向条目）两种布局。
 *
 * 与 `ArticleCard` 的关系：后者是固定样式的通用卡片；本组件在它之上增加了
 * 「主题可切换变体」这一层。默认变体下渲染效果与 `ArticleCard` 一致。
 */

import {useThemeSlots} from '@/composables/useThemeSlots'
import type {ArticleItem} from '@/types/content'
import {formatDate} from '@/utils/format'

const props = withDefaults(
  defineProps<{
    article: ArticleItem
    layout?: 'grid' | 'list'
    index?: number
  }>(),
  {layout: 'grid', index: 0},
)

const {slot} = useThemeSlots()

const variant = computed(() => slot('articleCard', 'default'))

const to = computed(() =>
  props.article.slug ? `/articles/${props.article.slug}` : `/articles/id/${props.article.id}`,
)
</script>

<template>
  <!-- 紧凑变体：小封面 + 横向信息，适合侧栏或密度高的列表 -->
  <article v-if="variant === 'compact'" class="group relative">
    <NuxtLink :to="to"
              class="flex items-center gap-3 rounded-card border border-line bg-surface p-3 transition-colors hover:border-line-strong">
      <DeferredImage
        v-if="props.article.cover_image"
        :alt="props.article.title"
        :src="props.article.cover_image"
        aspect="4/3"
        class="w-20 flex-shrink-0 rounded-control"
      />
      <div v-else class="flex h-16 w-20 flex-shrink-0 items-center justify-center rounded-control bg-surface-soft">
        <Icon class="h-5 w-5 text-fg-subtle" name="file-text"/>
      </div>

      <div class="min-w-0 flex-1">
        <h3 class="line-clamp-2 text-sm font-medium leading-snug text-fg transition-colors group-hover:text-primary">
          {{ props.article.title }}
        </h3>
        <div class="mt-1 flex items-center gap-3 text-xs text-fg-subtle">
          <span>{{ formatDate(props.article.published_at || props.article.created_at) }}</span>
          <span v-if="props.article.views" class="inline-flex items-center gap-1">
            <Icon class="h-3 w-3" name="eye"/>{{ props.article.views }}
          </span>
        </div>
      </div>
    </NuxtLink>
  </article>

  <!-- 标准变体 · 横向条目 -->
  <article v-else-if="props.layout === 'list'" class="group">
    <NuxtLink :to="to" class="flex gap-4">
      <DeferredImage
        v-if="props.article.cover_image"
        :alt="props.article.title"
        :src="props.article.cover_image"
        aspect="16/9"
        class="w-40 flex-shrink-0 rounded-card"
      />
      <div class="min-w-0 flex-1">
        <h3 class="text-base font-semibold leading-snug text-fg transition-colors group-hover:text-primary">
          {{ props.article.title }}
        </h3>
        <p v-if="props.article.summary" class="mt-1.5 line-clamp-2 text-sm leading-relaxed text-fg-muted">
          {{ props.article.summary }}
        </p>
        <div class="mt-2 flex items-center gap-4 text-xs text-fg-subtle">
          <span class="inline-flex items-center gap-1">
            <Icon class="h-3.5 w-3.5" name="calendar-days"/>
            {{ formatDate(props.article.published_at || props.article.created_at) }}
          </span>
          <Badge v-for="tag in (props.article.tags || []).slice(0, 2)" :key="tag" variant="secondary">{{ tag }}</Badge>
        </div>
      </div>
    </NuxtLink>
  </article>

  <!-- 标准变体 · 竖向卡片（默认） -->
  <article v-else class="group">
    <NuxtLink :to="to" class="block">
      <DeferredImage
        v-if="props.article.cover_image"
        :alt="props.article.title"
        :src="props.article.cover_image"
        class="mb-3 rounded-card"
      />
      <h3 class="text-base font-semibold leading-snug text-fg transition-colors group-hover:text-primary">
        {{ props.article.title }}
      </h3>
    </NuxtLink>

    <p v-if="props.article.summary" class="mt-1.5 line-clamp-2 text-sm leading-relaxed text-fg-muted">
      {{ props.article.summary }}
    </p>

    <div class="mt-2.5 flex items-center gap-4 text-xs text-fg-subtle">
      <span class="inline-flex items-center gap-1">
        <Icon class="h-3.5 w-3.5" name="calendar-days"/>
        {{ formatDate(props.article.published_at || props.article.created_at) }}
      </span>
      <span v-if="props.article.views" class="inline-flex items-center gap-1">
        <Icon class="h-3.5 w-3.5" name="eye"/>{{ props.article.views }}
      </span>
      <Badge v-for="tag in (props.article.tags || []).slice(0, 2)" :key="tag" variant="secondary">{{ tag }}</Badge>
    </div>
  </article>
</template>
