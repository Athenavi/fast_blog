<script lang="ts" setup>
/**
 * 文章正文：`/articles/[slug]` 与 `/articles/id/[id]` 共用
 *
 * 阅读优先：正文限制在 `max-w-read`（约 46rem），行高与段间距放宽。
 * 正文相关样式全部基于设计令牌，因此深浅色与自定义配色会自动生效。
 */

import type {ArticleDetail} from '@/types/content'
import {useUserStore} from '@/store/modules/user'

const props = defineProps<{ article: ArticleDetail }>()

const userStore = useUserStore()
const publishedAt = computed(() => props.article.published_at || props.article.created_at)

const rewardOpen = ref(false)

/** 作者不能给自己打赏（后端会 400），本人文章不显示打赏按钮 */
const canReward = computed(
  () => Boolean(props.article.author_id) && props.article.author_id !== userStore.userInfo?.id,
)
</script>

<template>
  <article class="mx-auto max-w-read px-4 py-12">
    <header>
      <h1 class="text-2xl font-bold leading-tight tracking-tight text-fg sm:text-3xl">
        {{ props.article.title }}
      </h1>

      <div class="mt-4 flex flex-wrap items-center gap-4 text-sm text-fg-subtle">
        <span class="inline-flex items-center gap-1.5">
          <Icon class="h-4 w-4" name="calendar-days"/>
          {{ formatDate(publishedAt) }}
        </span>
        <span v-if="props.article.views" class="inline-flex items-center gap-1.5">
          <Icon class="h-4 w-4" name="eye"/>
          {{ $t('article.viewsCount', {n: props.article.views}) }}
        </span>
        <Badge v-for="tag in props.article.tags || []" :key="tag" variant="secondary">{{ tag }}</Badge>
        <LikeButton v-if="props.article.id" :article-id="props.article.id" :initial-likes="props.article.likes ?? 0"/>
        <ClientOnly>
          <Button v-if="canReward" size="sm" variant="outline" @click="rewardOpen = true">
            <Icon class="h-4 w-4" name="gift"/>
            {{ $t('tipping.rewardAuthor') }}
          </Button>
        </ClientOnly>
      </div>
    </header>

    <img
      v-if="props.article.cover_image"
      :alt="props.article.title"
      :src="props.article.cover_image"
      class="mt-7 w-full rounded-card object-cover"
    >

    <!-- eslint-disable-next-line vue/no-v-html -- 正文来自后台编辑器 -->
    <div class="prose-content mt-9" v-html="props.article.content || ('<p>' + $t('site.noContent') + '</p>')"/>

    <RewardDialog
      v-if="props.article.author_id"
      v-model="rewardOpen"
      :article-id="props.article.id"
      :author-id="props.article.author_id"
      :author-name="props.article.author_name"/>
  </article>
</template>
