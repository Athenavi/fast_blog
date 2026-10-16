<script lang="ts" setup>
/** 文章详情（按 slug） */
import type {ArticleDetail} from '@/types/content'

const {t} = useI18n()

const route = useRoute()
const slug = String(route.params.slug)

const {data: article} = await useAsyncData(`article-${slug}`, () =>
  apiGet<ArticleDetail>(`/content/article/public/slug/${slug}`),
)

if (!article.value) {
  throw createError({statusCode: 404, statusMessage: t('article.notFoundOrUnpublished')})
}

// 浏览量上报：仅客户端、失败静默（统计不应影响阅读）
onMounted(() => {
  const id = article.value?.id
  if (!id) return
  $fetch(`${API_PREFIX}/content/article/public/${id}/views`, {method: 'POST'}).catch(() => {
  })
})

const requestUrl = useRequestURL()
const site = await useSiteInfo()

/**
 * 分享卡片配图：优先文章封面，没有封面时回退站点 Logo
 * （两者都可能是后端下发的相对路径，必须补成绝对 URL —— 否则抓取器会整张丢弃，
 * 分享出去就是空卡片。见 utils/seo.ts）
 */
const shareImage = computed(() =>
  absoluteAssetUrl(article.value?.cover_image || site.value.site_logo, requestUrl.origin),
)

const breadcrumbs = computed(() => [
  {label: t('common.home'), to: '/'},
  {label: t('article.breadcrumbArticles'), to: '/articles'},
  {label: article.value?.title || t('article.titleFallback')},
])

useBreadcrumbJsonLd(breadcrumbs.value, requestUrl.origin)

useArticleJsonLd(
  {
    headline: article.value?.title,
    description: article.value?.summary,
    image: article.value?.cover_image,
    datePublished: article.value?.published_at,
    dateModified: article.value?.updated_at,
    authorName: article.value?.author_name,
    url: `${requestUrl.origin}/articles/${slug}`,
  },
  {keywords: article.value?.tags ?? []},
)

useSeoMeta({
  title: () => article.value?.title || t('article.titleFallback'),
  description: () => article.value?.summary || '',
  ogTitle: () => article.value?.title || '',
  ogDescription: () => article.value?.summary || '',
  ogImage: () => shareImage.value,
  ogType: 'article',
  twitterCard: 'summary_large_image',
  twitterImage: () => shareImage.value,
})
</script>

<template>
  <div v-if="article">
    <div class="mx-auto max-w-read px-4 pt-8">
      <Breadcrumbs :items="breadcrumbs"/>
    </div>
    <ArticleDetailView :article="article"/>
  </div>
</template>
