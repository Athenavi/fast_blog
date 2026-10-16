<script lang="ts" setup>
const {t} = useI18n()
/** 分类总览 */
import type {CategoryItem} from '@/types/content'

const site = await useSiteInfo()

const {data: tree, pending, error, refresh: refreshList} = await useAsyncData('category-overview', () =>
  apiGet<CategoryItem[]>('/content/category/public/tree'),
)

const categories = computed(() => tree.value ?? [])

useSeoMeta({
  title: () => t('category.seoTitle', {name: site.value.site_name || 'FastBlog'}),
  description: t('category.subtitle'),
})
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-10">
    <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('category.title') }}</h1>

    <div v-if="pending" class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <Skeleton v-for="i in 6" :key="i" class="h-24 w-full"/>
    </div>

    <ErrorState v-else-if="error" class="mt-6" @retry="refreshList"/>

    <div v-else-if="categories.length" class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <CategoryCard v-for="category in categories" :key="category.id" :category="category"/>
    </div>
    <EmptyState v-else :description="$t('category.emptyDesc')" :title="$t('category.emptyTitle')" class="mt-6"/>
  </div>
</template>
