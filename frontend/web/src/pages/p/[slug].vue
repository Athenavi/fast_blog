<script lang="ts" setup>
/**
 * 独立页面（按 slug）
 *
 * 对应 astro 的 `p/[slug].astro`：渲染后台「页面」里已发布的内容，
 * 适合「关于」「隐私政策」「服务条款」这类静态页。
 */
import type {PageItem} from '@/types/content'

const {t} = useI18n()
const route = useRoute()
const slug = String(route.params.slug)

const {data: page} = await useAsyncData(`page-${slug}`, () =>
  apiGet<PageItem>(`/content/page/public/slug/${slug}`),
)

if (!page.value) {
  throw createError({statusCode: 404, statusMessage: t('page.notFoundOrUnpublished')})
}

useSeoMeta({
  title: () => page.value?.title || t('page.titleFallback'),
  description: () => page.value?.summary || '',
})
</script>

<template>
  <article class="mx-auto max-w-read px-4 py-12">
    <h1 class="text-2xl font-bold leading-tight tracking-tight text-fg sm:text-3xl">
      {{ page?.title }}
    </h1>
    <p v-if="page?.summary" class="mt-3 text-fg-muted">{{ page.summary }}</p>

    <!-- eslint-disable-next-line vue/no-v-html -- 内容由后台编辑器维护 -->
    <div class="prose-content mt-8" v-html="page?.content || `<p>${t('site.noContent')}</p>`"/>
  </article>
</template>
