<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '标签',
  permission: 'module_content:tag:view',
})
</script>

<template>
  <Placeholder title="标签"/>
</template>
