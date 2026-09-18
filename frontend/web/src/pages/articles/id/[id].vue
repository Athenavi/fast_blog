<script lang="ts" setup>
/** 文章详情（按 id）：兼容无 slug 的历史文章 */
import type {ArticleDetail} from '@/types/content'

const route = useRoute()
const id = Number(route.params.id)

const {data: article} = await useAsyncData(`article-id-${id}`, () =>
  apiGet<ArticleDetail>(`/content/article/public/detail/${id}`),
)

if (!article.value) {
  throw createError({statusCode: 404, statusMessage: '文章不存在或未发布'})
}

useSeoMeta({
  title: () => article.value?.title || '文章',
  description: () => article.value?.summary || '',
})
</script>

<template>
  <ArticleDetailView v-if="article" :article="article"/>
</template>
