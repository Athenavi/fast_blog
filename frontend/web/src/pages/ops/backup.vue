<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '备份',
  permission: 'module_ops:backup:view',
})
</script>

<template>
  <Placeholder title="备份"/>
</template>
