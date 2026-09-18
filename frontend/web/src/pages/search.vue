<script lang="ts" setup>
/** 搜索：关键词作为查询参数，便于分享与回退 */
import {Search} from '@lucide/vue'

import type {ArticleItem} from '@/types/content'

const route = useRoute()
const router = useRouter()
const site = await useSiteInfo()

const keyword = computed(() => String(route.query.q || '').trim())
const page = computed(() => Number(route.query.page || 1))

const {data: pageData, pending} = await useAsyncData(
  () => `search-${keyword.value}-${page.value}`,
  () =>
    keyword.value
      ? apiPage<ArticleItem>('/content/article/public/list', {
        page: page.value,
        page_size: 9,
        keyword: keyword.value,
      })
      : Promise.resolve({items: [], total: 0, page: 1, pageSize: 9, pages: 0}),
  {watch: [keyword, page]},
)

const articles = computed(() => pageData.value?.items ?? [])
const input = ref(keyword.value)

function submit() {
  const q = input.value.trim()
  router.push(q ? {query: {q}} : {query: {}})
}

function changePage(next: number) {
  router.push({query: {q: keyword.value, page: next}})
}

useSeoMeta({
  title: () =>
    (keyword.value ? `搜索“${keyword.value}” - ${site.value.site_name}` : `搜索 - ${site.value.site_name}`) ||
    '搜索 - FastBlog',
  description: '站内文章搜索',
  robots: 'noindex',
})
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-10">
    <h1 class="text-2xl font-bold tracking-tight text-slate-900">搜索</h1>

    <form class="mt-5 flex max-w-xl gap-2" @submit.prevent="submit">
      <Input v-model="input" placeholder="输入关键词后回车"/>
      <Button class="shrink-0" type="submit">
        <Search class="h-4 w-4"/>
        搜索
      </Button>
    </form>

    <p v-if="keyword" class="mt-6 text-sm text-slate-500">
      关键词 “<span class="font-medium text-slate-900">{{ keyword }}</span>” 共
      {{ pageData?.total ?? 0 }} 条结果
    </p>

    <ArticleListSection
      v-if="keyword"
      :articles="articles"
      :loading="pending"
      :page="page"
      :pages="pageData?.pages ?? 0"
      class="mt-6"
      empty-description="试试更短或更通用的关键词。"
      empty-title="没有匹配的文章"
      @change="changePage"
    />

    <EmptyState v-else class="mt-6" description="支持标题与正文摘要匹配。" title="输入关键词开始搜索"/>
  </div>
</template>
