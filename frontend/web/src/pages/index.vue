<script lang="ts" setup>
/** 首页：站点简介 + 最新文章 + 分类入口 */
import {ArrowRight} from '@lucide/vue'

import type {ArticleItem, CategoryItem} from '@/types/content'

const site = await useSiteInfo()

const {data: articlePage} = await useAsyncData('home-articles', () =>
  apiPage<ArticleItem>('/content/article/public/list', {page: 1, page_size: 6}),
)
const {data: categories} = await useAsyncData('home-categories', () =>
  apiGet<CategoryItem[]>('/content/category/public'),
)

const articles = computed(() => articlePage.value?.items ?? [])

useSeoMeta({
  title: site.value.site_name || 'FastBlog',
  description: site.value.site_description || '一个基于 FastAPI 与 Nuxt 的博客',
  ogTitle: site.value.site_name || 'FastBlog',
  ogDescription: site.value.site_description || '',
})
</script>

<template>
  <div>
    <!-- Hero -->
    <section class="border-b border-slate-100 bg-gradient-to-b from-slate-50 to-white">
      <div class="mx-auto max-w-5xl px-4 py-16 sm:py-24">
        <h1 class="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          {{ site.site_name || 'FastBlog' }}
        </h1>
        <p class="mt-3 max-w-2xl text-base text-slate-600">
          {{ site.site_description || '记录技术、思考与生活。' }}
        </p>
        <div class="mt-6 flex flex-wrap gap-3">
          <NuxtLink to="/articles">
            <Button>浏览文章
              <ArrowRight class="h-4 w-4"/>
            </Button>
          </NuxtLink>
          <NuxtLink to="/about">
            <Button variant="outline">关于本站</Button>
          </NuxtLink>
        </div>
      </div>
    </section>

    <!-- 最新文章 -->
    <section class="mx-auto max-w-5xl px-4 py-12">
      <div class="mb-6 flex items-end justify-between">
        <h2 class="text-xl font-semibold text-slate-900">最新文章</h2>
        <NuxtLink class="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900" to="/articles">
          全部文章
          <ArrowRight class="h-3.5 w-3.5"/>
        </NuxtLink>
      </div>

      <div v-if="articles.length" class="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
        <ArticleCard v-for="article in articles" :key="article.id" :article="article"/>
      </div>
      <EmptyState v-else description="发布第一篇文章后，它会出现在这里。" title="还没有已发布的文章"/>
    </section>

    <!-- 分类 -->
    <section v-if="(categories || []).length" class="border-t border-slate-100 bg-slate-50">
      <div class="mx-auto max-w-5xl px-4 py-12">
        <h2 class="mb-6 text-xl font-semibold text-slate-900">分类</h2>
        <div class="flex flex-wrap gap-2">
          <NuxtLink v-for="category in categories || []" :key="category.id" :to="`/category/${category.id}`">
            <Badge class="bg-white px-3 py-1 text-sm" variant="outline">
              {{ category.name }}
              <span v-if="category.article_count" class="ml-1 text-slate-400">{{ category.article_count }}</span>
            </Badge>
          </NuxtLink>
        </div>
      </div>
    </section>
  </div>
</template>
