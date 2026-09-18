<script lang="ts" setup>
/** 文章卡片：首页与列表页共用（组件复用，避免重复模板） */
import {Eye, CalendarDays} from '@lucide/vue'

import type {ArticleItem} from '@/types/content'
import {formatDate} from '@/utils/format'

const props = defineProps<{ article: ArticleItem }>()

const to = computed(() =>
  props.article.slug ? `/articles/${props.article.slug}` : `/articles/id/${props.article.id}`,
)
</script>

<template>
  <article class="group">
    <NuxtLink :to="to" class="block">
      <div v-if="props.article.cover_image" class="mb-3 overflow-hidden rounded-lg bg-slate-100">
        <img
          :alt="props.article.title"
          :src="props.article.cover_image"
          class="aspect-[16/9] w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
          loading="lazy"
        >
      </div>
      <h3 class="text-base font-semibold leading-snug text-slate-900 transition-colors group-hover:text-slate-600">
        {{ props.article.title }}
      </h3>
    </NuxtLink>
    <p v-if="props.article.summary" class="mt-1.5 line-clamp-2 text-sm text-slate-500">
      {{ props.article.summary }}
    </p>
    <div class="mt-2.5 flex items-center gap-4 text-xs text-slate-400">
      <span class="inline-flex items-center gap-1">
        <CalendarDays class="h-3.5 w-3.5"/>
        {{ formatDate(props.article.published_at || props.article.created_at) }}
      </span>
      <span v-if="props.article.views" class="inline-flex items-center gap-1">
        <Eye class="h-3.5 w-3.5"/>
        {{ props.article.views }}
      </span>
      <Badge v-for="tag in (props.article.tags || []).slice(0, 2)" :key="tag" variant="secondary">{{ tag }}</Badge>
    </div>
  </article>
</template>
