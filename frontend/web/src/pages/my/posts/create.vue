<script lang="ts" setup>
/**
 * 写文章（投稿）
 *
 * 对应原 astro 的 `my/posts/create.astro`，编辑逻辑复用 `ArticleEditor`。
 */
definePageMeta({layout: 'default', middleware: 'auth', title: 'myPosts.createTitle'})

const router = useRouter()

function onSaved(id: number): void {
  // 新草稿创建后直接进入编辑态，方便继续补充
  router.replace(`/my/posts/edit/${id}`)
}
</script>

<template>
  <ArticleEditor @saved="onSaved"/>
</template>
