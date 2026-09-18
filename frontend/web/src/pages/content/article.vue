<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '文章',
  permission: 'module_content:article:view',
})
</script>

<template>
  <Placeholder title="文章"/>
</template>
