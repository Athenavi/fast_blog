<script lang="ts" setup>
const {t} = useI18n()
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: t('admin.content.page.pages'),
  permission: 'module_content:page:view',
})
</script>

<template>
  <Placeholder :title="$t('admin.content.page.pages2')"/>
</template>
