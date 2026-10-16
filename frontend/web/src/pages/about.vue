<script lang="ts" setup>
const {t} = useI18n()
/** 关于页：读取后台“页面”中 slug 为 about 的内容，便于运营自行维护 */
import type {PageItem} from '@/types/content'

const site = await useSiteInfo()
const {data: page} = await useAsyncData('page-about', () =>
  apiGet<PageItem>('/content/page/public/slug/about'),
)

/** 结构化数据（对齐 astro 旧版 about 页的 SEO 处理，改用统一的 useJsonLd） */
// 注意：useRequestURL 必须在 setup 顶层调用——放进 useHead 的响应式回调里会丢失 Nuxt 上下文
const origin = useRequestURL().origin
useJsonLd('AboutPage', () => ({
  name: page.value?.title || t('about.title'),
  description: page.value?.summary || site.value.site_description || '',
  url: `${origin}/about`,
}))

useSeoMeta({
  title: () => `${page.value?.title || t('about.title')} - ${site.value.site_name || 'FastBlog'}`,
  description: () => page.value?.summary || '',
})
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-10">
    <h1 class="text-2xl font-bold tracking-tight text-fg">{{ page?.title || t('about.title') }}</h1>

    <!-- eslint-disable-next-line vue/no-v-html -- 页面内容由后台编辑器维护 -->
    <div v-if="page?.content" class="prose-content mt-6" v-html="page.content"/>
    <p v-else class="mt-6 text-fg-muted">
      {{ $t('about.missingPre') }} <code class="rounded bg-surface-soft px-1">about</code> {{ $t('about.missingPost') }}
    </p>
  </div>
</template>
