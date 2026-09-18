<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '菜单',
  permission: 'module_system:navmenu:view',
})
</script>

<template>
  <Placeholder title="菜单"/>
</template>
