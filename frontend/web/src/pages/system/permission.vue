<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '权限码',
  permission: 'module_system:permission:view',
})
</script>

<template>
  <Placeholder title="权限码"/>
</template>
