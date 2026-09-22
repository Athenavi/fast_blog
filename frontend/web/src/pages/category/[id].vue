<script lang="ts" setup>
/** 分类文章列表：复用 ArticleListSection */
import type {ArticleItem, CategoryItem} from '@/types/content'

const {t} = useI18n()
const route = useRoute()
const router = useRouter()
const site = await useSiteInfo()

const categoryId = Number(route.params.id)
const page = computed(() => Number(route.query.page || 1))

const {data: categories} = await useAsyncData('all-categories', () =>
  apiGet<CategoryItem[]>('/content/category/public'),
)
const category = computed(() => (categories.value || []).find((item) => item.id === categoryId))

const {data: pageData, pending, error, refresh: refreshList} = await useAsyncData(
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
  title: () => `${category.value?.name || t('category.fallback')} - ${site.value.site_name || 'FastBlog'}`,
  description: () => category.value?.description || '',
})
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-10">
    <h1 class="text-2xl font-bold tracking-tight text-fg">{{ category?.name || t('category.fallback') }}</h1>
    <p v-if="category?.description" class="mt-2 text-fg-muted">{{ category.description }}</p>

    <ArticleListSection

      :error="Boolean(error)"

      @retry="refreshList"
      :articles="articles"
      :loading="pending"
      :page="page"
      :pages="pageData?.pages ?? 0"
      class="mt-8"
      :empty-description="t('category.emptyPublished')"
      @change="changePage"
    />
  </div>
</template>
