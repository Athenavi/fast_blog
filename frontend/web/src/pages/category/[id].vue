<script lang="ts" setup>
/** 分类文章列表：复用 ArticleListSection */
import type {ArticleItem, CategoryItem} from '@/types/content'

const route = useRoute()
const router = useRouter()
const site = await useSiteInfo()

const categoryId = Number(route.params.id)
const page = computed(() => Number(route.query.page || 1))

const {data: categories} = await useAsyncData('all-categories', () =>
  apiGet<CategoryItem[]>('/content/category/public'),
)
const category = computed(() => (categories.value || []).find((item) => item.id === categoryId))

const {data: pageData, pending} = await useAsyncData(
  () => `category-${categoryId}-${page.value}`,
  () =>
    apiPage<ArticleItem>('/content/article/public/list', {
      page: page.value,
      page_size: 9,
      category_id: categoryId,
    }),
  {watch: [page]},
)

const articles = computed(() => pageData.value?.items ?? [])

function changePage(next: number) {
  router.push({query: {page: next}})
}

useSeoMeta({
  title: () => `${category.value?.name || '分类'} - ${site.value.site_name || 'FastBlog'}`,
  description: () => category.value?.description || '',
})
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-10">
    <h1 class="text-2xl font-bold tracking-tight text-slate-900">{{ category?.name || '分类' }}</h1>
    <p v-if="category?.description" class="mt-2 text-slate-500">{{ category.description }}</p>

    <ArticleListSection
      :articles="articles"
      :loading="pending"
      :page="page"
      :pages="pageData?.pages ?? 0"
      class="mt-8"
      empty-description="该分类下还没有已发布的文章。"
      @change="changePage"
    />
  </div>
</template>
