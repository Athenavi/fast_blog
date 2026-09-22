<script lang="ts" setup>
const {t} = useI18n()
/** 搜索：关键词作为查询参数，便于分享与回退 */

import type {ArticleItem} from '@/types/content'

const route = useRoute()
const router = useRouter()
const site = await useSiteInfo()

const keyword = computed(() => String(route.query.q || '').trim())
const page = computed(() => Number(route.query.page || 1))

const {data: pageData, pending, error, refresh: refreshList} = await useAsyncData(
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

/** 输入即搜（350ms 防抖）：搜索页此前必须点按钮或回车，多一次操作 */
let searchTimer: ReturnType<typeof setTimeout> | null = null

watch(input, (value) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    const next = value.trim()
    if (next === keyword.value) return
    router.push(next ? {query: {q: next}} : {query: {}})
  }, 350)
})

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
})

function submit() {
  const q = input.value.trim()
  if (searchTimer) clearTimeout(searchTimer)
  router.push(q ? {query: {q}} : {query: {}})
}

function changePage(next: number) {
  router.push({query: {q: keyword.value, page: next}})
}

useSeoMeta({
  title: () =>
    keyword.value
      ? t('search.seoQuery', {query: keyword.value, name: site.value.site_name})
      : t('search.seoWithName', {name: site.value.site_name}),
  description: t('search.seoDescription'),
  robots: 'noindex',
})
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-10">
    <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('admin.common.search') }}</h1>

    <form class="mt-5 flex max-w-xl gap-2" @submit.prevent="submit">
      <Input
        v-model="input"
        :placeholder="$t('search.placeholder')"
        enterkeyhint="search"
        type="search"
      />
      <Button class="shrink-0" type="submit">
        <Icon class="h-4 w-4" name="search"/>
        {{ $t('common.search') }}
      </Button>
    </form>

    <p v-if="keyword" class="mt-6 text-sm text-fg-muted">
      {{ $t('search.resultsPre') }}“<span class="font-medium text-fg">{{ keyword }}</span>”{{
        $t('search.resultsMid')
      }}{{ pageData?.total ?? 0 }}{{ $t('search.resultsPost') }}
    </p>

    <ArticleListSection

      :error="Boolean(error)"

      @retry="refreshList"
      v-if="keyword"
      :articles="articles"
      :loading="pending"
      :page="page"
      :pages="pageData?.pages ?? 0"
      class="mt-6"
      :empty-description="$t('search.emptyDesc')"
      :empty-title="$t('search.emptyTitle')"
      @change="changePage"
    />

    <EmptyState v-else :description="$t('search.initialDesc')" :title="$t('search.initialTitle')" class="mt-6"/>
  </div>
</template>
