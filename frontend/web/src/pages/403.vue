<script lang="ts" setup>
const {t} = useI18n()
/**
 * 403 无权限
 *
 * 用前台风格渲染：本页可能在未加载 Element Plus 的情况下打开
 * （例如直接访问 /403），因此不依赖 el-* 组件。
 */
definePageMeta({layout: false, title: 'error.forbiddenTitle', robots: 'noindex'})
</script>

<template>
  <div class="flex min-h-dvh flex-col items-center justify-center gap-3 px-4 text-center">
    <p class="text-5xl font-bold tracking-tight text-fg">403</p>
    <p class="max-w-read text-fg-muted">{{ $t('error.forbiddenDesc') }}</p>
    <div class="mt-3 flex gap-3">
      <NuxtLink to="/dashboard">
        <Button>{{ $t('error.backToDashboard') }}</Button>
      </NuxtLink>
      <NuxtLink to="/">
        <Button variant="outline">{{ $t('error.backHome') }}</Button>
      </NuxtLink>
    </div>
  </div>
</template>
