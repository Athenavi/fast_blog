<script lang="ts" setup>
/** 文章详情（按 slug） */
import type {ArticleDetail} from '@/types/content'

const route = useRoute()
const slug = String(route.params.slug)

const {data: article} = await useAsyncData(`article-${slug}`, () =>
  apiGet<ArticleDetail>(`/content/article/public/slug/${slug}`),
)

if (!article.value) {
  throw createError({statusCode: 404, statusMessage: '文章不存在或未发布'})
}

// 浏览量上报：仅客户端、失败静默（统计不应影响阅读）
onMounted(() => {
  const id = article.value?.id
  if (!id) return
  $fetch(`${API_PREFIX}/content/article/public/${id}/views`, {method: 'POST'}).catch(() => {
  })
})

useSeoMeta({
  title: () => article.value?.title || '文章',
  description: () => article.value?.summary || '',
  ogTitle: () => article.value?.title || '',
  ogDescription: () => article.value?.summary || '',
  ogImage: () => article.value?.cover_image || undefined,
  ogType: 'article',
})
</script>

<template>
  <ArticleDetailView v-if="article" :article="article"/>
</template>
