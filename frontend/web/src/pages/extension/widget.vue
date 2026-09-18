<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '小部件',
  permission: 'module_extension:widget:view',
})
</script>

<template>
  <Placeholder title="小部件"/>
</template>
