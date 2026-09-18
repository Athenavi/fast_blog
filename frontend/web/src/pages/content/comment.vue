<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '评论',
  permission: 'module_content:comment:view',
})
</script>

<template>
  <Placeholder title="评论"/>
</template>
