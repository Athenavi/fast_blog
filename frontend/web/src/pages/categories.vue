<script lang="ts" setup>
/** 分类总览 */
import type {CategoryItem} from '@/types/content'

const site = await useSiteInfo()

const {data: tree} = await useAsyncData('category-overview', () =>
  apiGet<CategoryItem[]>('/content/category/public/tree'),
)

const categories = computed(() => tree.value ?? [])

useSeoMeta({
  title: () => `分类 - ${site.value.site_name || 'FastBlog'}`,
  description: '按分类浏览全部文章',
})
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-10">
    <h1 class="text-2xl font-bold tracking-tight text-slate-900">分类</h1>

    <div v-if="categories.length" class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <CategoryCard v-for="category in categories" :key="category.id" :category="category"/>
    </div>
    <EmptyState v-else class="mt-6" description="在后台创建分类后，这里会自动展示。" title="还没有分类"/>
  </div>
</template>
