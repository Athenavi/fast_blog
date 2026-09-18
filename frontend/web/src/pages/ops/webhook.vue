<script lang="ts" setup>
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'Webhook',
  permission: 'module_ops:webhook:view',
})
</script>

<template>
  <Placeholder title="Webhook"/>
</template>
