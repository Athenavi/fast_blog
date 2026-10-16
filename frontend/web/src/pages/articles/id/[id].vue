<script lang="ts" setup>
/** 文章详情（按 id）：兼容无 slug 的历史文章 */
import type {ArticleDetail} from '@/types/content'

const {t} = useI18n()

const route = useRoute()
const id = Number(route.params.id)

const {data: article} = await useAsyncData(`article-id-${id}`, () =>
  apiGet<ArticleDetail>(`/content/article/public/detail/${id}`),
)

if (!article.value) {
  throw createError({statusCode: 404, statusMessage: t('article.notFoundOrUnpublished')})
}

const requestUrl = useRequestURL()
const site = await useSiteInfo()

/** 与 `/articles/[slug]` 同一口径：封面（或站点 Logo）必须补成绝对 URL 才可用于分享卡片 */
const shareImage = computed(() =>
  absoluteAssetUrl(article.value?.cover_image || site.value.site_logo, requestUrl.origin),
)

useArticleJsonLd({
  headline: article.value?.title,
  description: article.value?.summary,
  image: article.value?.cover_image,
  datePublished: article.value?.published_at,
  dateModified: article.value?.updated_at,
  authorName: article.value?.author_name,
  url: `${requestUrl.origin}/articles/id/${id}`,
})

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
  <ArticleDetailView v-if="article" :article="article"/>
</template>
