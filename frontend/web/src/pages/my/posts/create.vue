<script lang="ts" setup>
/**
 * 旧投稿入口 → 统一后的编辑页
 *
 * 新建与编辑原先是两套（`/my/posts/create` 一个壳 + `/my/posts/edit/[id]` 一个壳），
 * 现在合并成一条路由：`/my/posts/edit/new` 新建、`/my/posts/edit/{id}` 编辑。
 * 保留这个跳转是为了已经存下的书签与外链 —— 让它直接 404 的话，用户看到的
 * 是"页面不存在"，而不是他想去的那个页面。
 */
definePageMeta({
  layout: 'default',
  middleware: 'auth',
  redirect: '/my/posts/edit/new',
})
</script>

<template>
  <div/>
</template>
