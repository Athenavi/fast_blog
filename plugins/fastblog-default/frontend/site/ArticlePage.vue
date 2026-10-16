<script lang="ts" setup>
/**
 * 主题级文章详情页（示例实现）
 *
 * 这个文件证明"页面级接管"真的可用：它位于主题的 `frontend/site/` 下，
 * `scripts/scan-plugin-frontend.mjs` 会把整个 `frontend/**` 复制到
 * `src/.plugin-pages/fastblog-default/site/`，于是它自动进入 `_loader.ts` 的
 * `import.meta.glob` 表；前台 `<ThemePage page="ArticlePage">` 宿主按**当前激活主题**
 * 取到它，从而**整页替换**内置的文章详情页。
 *
 * 换句话说：主题要接管某个页面，只需在这里放一个同名组件 ——
 * 不需要改构建配置、不需要改前台页面代码、不需要重启构建脚本。
 *
 * 组件收到的 props 由宿主 `v-bind="$attrs"` 透传（与内置页同一份数据）。
 */
defineProps<{
  article: Record<string, unknown>
}>()
</script>

<template>
  <article class="mx-auto max-w-3xl px-4 py-10">
    <h1 class="text-3xl font-bold tracking-tight text-fg">{{ article.title }}</h1>

    <p v-if="article.excerpt" class="mt-3 text-fg-muted">{{ article.excerpt }}</p>

    <!-- 正文由服务端渲染成 HTML（Markdown 已转换、已净化），这里只负责摆放 -->
    <div class="prose mt-8" v-html="article.content"/>
  </article>
</template>
