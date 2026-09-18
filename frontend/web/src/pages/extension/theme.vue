<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '主题',
  permission: 'module_extension:theme:view',
})
</script>

<template>
  <Placeholder title="主题"/>
</template>
