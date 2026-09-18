<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '页面',
  permission: 'module_content:page:view',
})
</script>

<template>
  <Placeholder title="页面"/>
</template>
