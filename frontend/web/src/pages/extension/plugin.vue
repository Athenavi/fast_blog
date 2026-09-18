<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '插件',
  permission: 'module_extension:plugin:view',
})
</script>

<template>
  <Placeholder title="插件"/>
</template>
