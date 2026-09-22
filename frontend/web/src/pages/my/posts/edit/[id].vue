<script lang="ts" setup>
/**
 * 编辑文章
 *
 * 对应原 astro 的 `my/posts/edit.astro`，编辑逻辑复用 `ArticleEditor`
 * （它内部会校验归属——非本人的文章后端返回 404）。
 */
definePageMeta({layout: 'default', middleware: 'auth', title: 'myPosts.editTitle'})

const route = useRoute()
const articleId = computed(() => Number(route.params.id))

const {t} = useI18n()

const message = ref('')

function onSaved(): void {
  message.value = t('myPosts.saved')
}
</script>

<template>
  <div>
    <ArticleEditor :article-id="articleId" @saved="onSaved"/>
  </div>
</template>
