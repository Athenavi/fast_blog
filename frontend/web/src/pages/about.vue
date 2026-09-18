<script lang="ts" setup>
/** 关于页：读取后台“页面”中 slug 为 about 的内容，便于运营自行维护 */
import type {PageItem} from '@/types/content'

const site = await useSiteInfo()
const {data: page} = await useAsyncData('page-about', () =>
  apiGet<PageItem>('/content/page/public/slug/about'),
)

useSeoMeta({
  title: () => `${page.value?.title || '关于'} - ${site.value.site_name || 'FastBlog'}`,
  description: () => page.value?.summary || '',
})
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-10">
    <h1 class="text-2xl font-bold tracking-tight text-slate-900">{{ page?.title || '关于本站' }}</h1>

    <!-- eslint-disable-next-line vue/no-v-html -- 页面内容由后台编辑器维护 -->
    <div v-if="page?.content" class="prose-content mt-6" v-html="page.content"/>
    <p v-else class="mt-6 text-slate-500">
      还没有配置“关于”页面。在后台创建 slug 为 <code class="rounded bg-slate-100 px-1">about</code> 的页面后，这里会自动展示。
    </p>
  </div>
</template>
