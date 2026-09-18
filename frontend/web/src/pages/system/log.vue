<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '日志',
  permission: 'module_system:log:view',
})
</script>

<template>
  <Placeholder title="日志"/>
</template>
