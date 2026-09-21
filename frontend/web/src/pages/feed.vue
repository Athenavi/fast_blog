<script lang="ts" setup>
/**
 * 关注流（personalized feed，批次 17）
 *
 * 数据源：v3 `/api/v3/mobile/feed`（**仅需认证**）—— 按当前登录用户的真实关注关系
 * 聚合**已发布**文章（后端复用公开列表的排序：置顶 → sort_order → 发布时间倒序）。
 * 关注为空时后端返回空页，本页据此展示引导文案 + 去发现作者。
 *
 * 需登录：`middleware: 'auth'`；`/feed` 在 nuxt.config.ts 里配置为 `ssr: false`，纯 CSR。
 */
import {feedApi} from '@/api'
import type {ArticleItem} from '@/types/content'

definePageMeta({layout: 'default', middleware: 'auth', title: 'feed.title'})

const {t} = useI18n()
const site = await useSiteInfo()

/** 每页条数（后端上限 50） */
const PAGE_SIZE = 20
const articles = ref<ArticleItem[]>([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const loading = ref(false)
const failed = ref(false)

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    const result = await feedApi.list({page: page.value, page_size: PAGE_SIZE})
    articles.value = result.items ?? []
    total.value = result.total ?? 0
    pages.value = result.pages ?? 0
  } catch {
    failed.value = true
    articles.value = []
    total.value = 0
    pages.value = 0
  } finally {
    loading.value = false
  }
}

function onPage(next: number): void {
  page.value = next
  void load()
}

useSeoMeta({
  title: () => t('feed.seoTitle', {name: site.value.site_name || 'FastBlog'}),
  description: () => t('feed.subtitle'),
})

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-wide px-4 py-10">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('feed.title') }}</h1>
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('feed.subtitle') }}</p>
      </div>
      <Button :disabled="loading" size="sm" variant="outline" @click="load()">
        <Icon class="h-4 w-4" name="refresh-cw"/>
        {{ $t('common.refresh') }}
      </Button>
    </div>

    <p v-if="total" class="mt-4 text-sm text-fg-muted">{{ $t('feed.total', {n: total}) }}</p>

    <ArticleListSection
      v-if="loading || articles.length"
      :articles="articles"
      :empty-description="$t('feed.emptyDesc')"
      :empty-title="$t('feed.empty')"
      :loading="loading"
      :page="page"
      :pages="pages"
      class="mt-6"
      @change="onPage"
    />

    <ErrorState
      v-else-if="failed"
      :description="$t('common.networkError')"
      :title="$t('feed.loadFailed')"
      class="mt-6"
      @retry="load()"
    />

    <EmptyState v-else :description="$t('feed.emptyDesc')" :title="$t('feed.empty')" class="mt-6">
      <NuxtLink class="mt-3" to="/experts">
        <Button size="sm">{{ $t('feed.goDiscover') }}</Button>
      </NuxtLink>
    </EmptyState>
  </div>
</template>
