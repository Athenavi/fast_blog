<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '媒体库',
  permission: 'module_content:media:view',
})
</script>

<template>
  <Placeholder title="媒体库"/>
</template>
