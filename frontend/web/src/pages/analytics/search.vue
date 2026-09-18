<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '搜索分析',
  permission: 'module_analytics:search:view',
})
</script>

<template>
  <Placeholder title="搜索分析"/>
</template>
