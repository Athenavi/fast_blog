<script lang="ts" setup>
/** 文章列表：分页 + 分类筛选（查询参数即状态，便于分享与回退） */
import type {ArticleItem, CategoryItem} from '@/types/content'

const route = useRoute()
const router = useRouter()
const site = await useSiteInfo()

const page = computed(() => Number(route.query.page || 1))
const categoryId = computed(() => (route.query.category ? Number(route.query.category) : undefined))

const {data: pageData, pending} = await useAsyncData(
  () => `articles-${page.value}-${categoryId.value ?? 'all'}`,
  () =>
    apiPage<ArticleItem>('/content/article/public/list', {
      page: page.value,
      page_size: 9,
      category_id: categoryId.value,
    }),
  {watch: [page, categoryId]},
)

const {data: categories} = await useAsyncData('article-list-categories', () =>
  apiGet<CategoryItem[]>('/content/category/public'),
)

const articles = computed(() => pageData.value?.items ?? [])

function changePage(next: number) {
  router.push({query: {...route.query, page: next}})
}

function selectCategory(id?: number) {
  router.push({query: id ? {category: id} : {}})
}

useSeoMeta({
  title: () => `文章 - ${site.value.site_name || 'FastBlog'}`,
  description: site.value.site_description || '',
})
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-10">
    <h1 class="text-2xl font-bold tracking-tight text-fg">文章</h1>

    <div v-if="(categories || []).length" class="mt-5 flex flex-wrap gap-2">
      <button @click="selectCategory()">
        <Badge :variant="categoryId ? 'outline' : 'default'" class="cursor-pointer px-3 py-1 text-sm">全部</Badge>
      </button>
      <button v-for="category in categories || []" :key="category.id" @click="selectCategory(category.id)">
        <Badge
          :variant="categoryId === category.id ? 'default' : 'outline'"
          class="cursor-pointer px-3 py-1 text-sm"
        >
          {{ category.name }}
        </Badge>
      </button>
    </div>

    <ArticleListSection
      :articles="articles"
      :loading="pending"
      :page="page"
      :pages="pageData?.pages ?? 0"
      class="mt-8"
      empty-description="换个分类看看，或者稍后再来。"
      @change="changePage"
    />
  </div>
</template>
