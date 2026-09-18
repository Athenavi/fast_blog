<script lang="ts" setup>
/**
 * 文章正文渲染：文章详情路由（slug 版与 id 版）共用
 *
 * 注意：`content` 按后端返回的 HTML 直接渲染。后续如需支持 Markdown
 * 或更严格的内容清洗，只需改动本组件。
 */
import {Eye, CalendarDays} from '@lucide/vue'

import type {ArticleDetail} from '@/types/content'

const props = defineProps<{ article: ArticleDetail }>()

const publishedAt = computed(() => props.article.published_at || props.article.created_at)
const cover = computed(() => props.article.cover_image || '')
</script>

<template>
  <article class="mx-auto max-w-3xl px-4 py-10">
    <header>
      <h1 class="text-2xl font-bold leading-tight tracking-tight text-slate-900 sm:text-3xl">
        {{ props.article.title }}
      </h1>
      <div class="mt-4 flex flex-wrap items-center gap-4 text-sm text-slate-400">
        <span class="inline-flex items-center gap-1.5">
          <CalendarDays class="h-4 w-4"/>
          {{ formatDate(publishedAt) }}
        </span>
        <span v-if="props.article.views" class="inline-flex items-center gap-1.5">
          <Eye class="h-4 w-4"/>
          {{ props.article.views }} 次浏览
        </span>
        <Badge v-for="tag in props.article.tags || []" :key="tag" variant="secondary">{{ tag }}</Badge>
      </div>
    </header>

    <img v-if="cover" :alt="props.article.title" :src="cover" class="mt-6 w-full rounded-lg object-cover">

    <!-- eslint-disable-next-line vue/no-v-html -- 文章内容来自后台编辑器 -->
    <div class="prose-content mt-8" v-html="props.article.content || '<p>（暂无正文）</p>'"/>
  </article>
</template>

<style scoped>
.prose-content :deep(h2) {
  margin-top: 2rem;
  margin-bottom: 0.75rem;
  font-size: 1.25rem;
  font-weight: 600;
  color: #0f172a;
}

.prose-content :deep(h3) {
  margin-top: 1.5rem;
  margin-bottom: 0.5rem;
  font-size: 1.05rem;
  font-weight: 600;
  color: #1e293b;
}

.prose-content :deep(p) {
  margin-bottom: 1rem;
  line-height: 1.8;
  color: #334155;
}

.prose-content :deep(a) {
  color: #0f172a;
  text-decoration: underline;
}

.prose-content :deep(img) {
  max-width: 100%;
  border-radius: 0.5rem;
  margin: 1rem 0;
}

.prose-content :deep(pre) {
  margin: 1rem 0;
  padding: 1rem;
  border-radius: 0.5rem;
  background: #0f172a;
  color: #e2e8f0;
  overflow-x: auto;
}

.prose-content :deep(code) {
  font-size: 0.875rem;
}

.prose-content :deep(blockquote) {
  margin: 1rem 0;
  padding-left: 1rem;
  border-left: 3px solid #e2e8f0;
  color: #64748b;
}

.prose-content :deep(ul),
.prose-content :deep(ol) {
  margin: 1rem 0 1rem 1.25rem;
  line-height: 1.8;
  color: #334155;
}

.prose-content :deep(ul) {
  list-style: disc;
}

.prose-content :deep(ol) {
  list-style: decimal;
}
</style>
