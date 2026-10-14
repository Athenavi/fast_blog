<script lang="ts" setup>
const {t} = useI18n()
/**
 * 首页（阅读优先）
 *
 * 数据源（均为 v3 公开接口）：
 *  - `/content/article/public/list` 最新文章
 *  - `/content/category/public`     分类
 *  - `/system/setting/public`       站点信息（见 useSiteInfo）
 *
 * 说明：astro 旧版的「推荐 / 热门」依赖 `/home/featured`、`/home/popular`（v2），
 * v3 的公开列表暂不支持按推荐位/热度排序，故首页先只呈现最新文章与分类；
 * 后端补上排序参数后，这里只需增加一次请求。
 */

import {usePreferredReducedMotion} from '@vueuse/core'

import type {ArticleItem, CategoryItem} from '@/types/content'

const site = await useSiteInfo()

const {data: articlePage, error, refresh: refreshList} = await useAsyncData('home-articles', () =>
  apiPage<ArticleItem>('/content/article/public/list', {page: 1, page_size: 6}),
)
const {data: categories} = await useAsyncData('home-categories', () =>
  apiGet<CategoryItem[]>('/content/category/public'),
)

const articles = computed(() => articlePage.value?.items ?? [])

/** 线框背景：跟随系统的「减少动态效果」偏好 */
const prefersReducedMotion = usePreferredReducedMotion()
const reducedMotion = computed(() => prefersReducedMotion.value === 'reduce')

// 线框背景（WireframeScene）由 Nuxt 自动导入，**不再**用 defineAsyncComponent 包一层。
// 它现在是纯 Canvas 2D 实现（不到 1 KB，见组件注释），单独切一个 chunk 反而多一次请求；
// 让它进首页自己的 chunk 即可。原来的 three.js 版必须异步加载（184 KB gzip）。

const requestUrl = useRequestURL()
useWebsiteJsonLd({
  name: site.value.site_name || 'FastBlog',
  description: site.value.site_description,
  url: requestUrl.origin,
})

useSeoMeta({
  title: site.value.site_name || 'FastBlog',
  description: site.value.site_description || t('home.tagline'),
  ogTitle: site.value.site_name || 'FastBlog',
  ogDescription: site.value.site_description || '',
})
</script>

<template>
  <div>
    <!-- Hero：留白优先，避免任何装饰性硬编码色 -->
    <section class="relative overflow-hidden border-b border-line">
      <!-- 线框背景：纯 Canvas 2D，由 Nuxt 自动导入（见 script 里的说明） -->
      <ClientOnly>
        <WireframeScene :reduced-motion="reducedMotion"/>
      </ClientOnly>

      <div class="relative mx-auto max-w-wide px-4 py-20 sm:py-28">
        <h1 class="max-w-read text-3xl font-bold tracking-tight text-fg sm:text-4xl">
          {{ site.site_name || 'FastBlog' }}
        </h1>
        <p class="mt-4 max-w-read text-base leading-relaxed text-fg-muted">
          {{ site.site_description || t('home.description') }}
        </p>
        <div class="mt-8 flex flex-wrap gap-3">
          <NuxtLink to="/articles">
            <Button size="lg">{{ $t('home.browseArticles') }}
              <Icon class="h-4 w-4" name="arrow-right"/>
            </Button>
          </NuxtLink>
          <NuxtLink to="/about">
            <Button size="lg" variant="outline">{{ $t('home.aboutLink') }}</Button>
          </NuxtLink>
        </div>
      </div>
    </section>

    <!-- 最新文章 -->
    <section class="mx-auto max-w-wide px-4 py-14">
      <div class="mb-8 flex items-end justify-between">
        <h2 class="text-lg font-semibold tracking-tight text-fg">{{ $t('home.latestArticles') }}</h2>
        <NuxtLink
          class="inline-flex items-center gap-1 text-sm text-fg-muted transition-colors hover:text-primary"
          to="/articles"
        >
          {{ $t('home.allArticles') }}
          <Icon class="h-3.5 w-3.5" name="arrow-right"/>
        </NuxtLink>
      </div>

      <ArticleListSection

        :error="Boolean(error)"

        @retry="refreshList"
        :articles="articles"
        :page="1"
        :pages="0"
        :empty-description="$t('home.emptyArticlesDesc')"
        :empty-title="$t('home.emptyArticlesTitle')"
      />
    </section>

    <!-- 分类 -->
    <section v-if="(categories || []).length" class="border-t border-line bg-surface-soft">
      <div class="mx-auto max-w-wide px-4 py-14">
        <h2 class="mb-6 text-lg font-semibold tracking-tight text-fg">{{ $t('home.categoriesLink') }}</h2>
        <div class="flex flex-wrap gap-2">
          <NuxtLink v-for="category in categories || []" :key="category.id" :to="`/category/${category.id}`">
            <Badge class="bg-surface px-3 py-1 text-sm" variant="outline">
              {{ category.name }}
              <span v-if="category.article_count" class="ml-1 text-fg-subtle">{{ category.article_count }}</span>
            </Badge>
          </NuxtLink>
        </div>
      </div>
    </section>
  </div>
</template>
