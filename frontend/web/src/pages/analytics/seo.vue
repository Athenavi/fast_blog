<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'SEO 分析',
  permission: 'module_analytics:seo:view',
})
</script>

<template>
  <Placeholder title="SEO 分析"/>
</template>
