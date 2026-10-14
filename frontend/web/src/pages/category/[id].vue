<script lang="ts" setup>
/** 分类文章列表：复用 ArticleListSection */
import type {ArticleItem, CategoryItem} from '@/types/content'

const {t} = useI18n()
const route = useRoute()
const router = useRouter()
const categoryId = Number(route.params.id)
const page = computed(() => Number(route.query.page || 1))

// 站点信息 / 分类表 / 文章列表三者**并发**（原先一个个 await，串成 3 轮往返）
const [site, {data: categories}, {data: pageData, pending, error, refresh: refreshList}] = await Promise.all([
  useSiteInfo(),
  useAsyncData('all-categories', () =>
    apiGet<CategoryItem[]>('/content/category/public'),
  ),
  useAsyncData(
    () => `category-${categoryId}-${page.value}`,
    () =>
      apiPage<ArticleItem>('/content/article/public/list', {
        page: page.value,
        page_size: 9,
        category_id: categoryId,
      }),
    {watch: [page]},
  ),
])

const category = computed(() => (categories.value || []).find((item) => item.id === categoryId))

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
