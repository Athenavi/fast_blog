<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '分类',
  permission: 'module_content:category:view',
})
</script>

<template>
  <Placeholder title="分类"/>
</template>
