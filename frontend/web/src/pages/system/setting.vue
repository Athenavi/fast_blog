<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '系统设置',
  permission: 'module_system:setting:view',
})
</script>

<template>
  <Placeholder title="系统设置"/>
</template>
