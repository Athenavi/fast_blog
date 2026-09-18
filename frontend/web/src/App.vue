<script setup lang="ts">
/**
 * Nuxt 根组件
 *
 * 主题与配色在**服务端**就写进 `<html>`，因此首屏不会闪白/闪黑；
 * 用户的显式选择存于 cookie（`fb-theme` / `fb-accent`）。
 */
const theme = useCookie<string>('fb-theme', {default: () => 'system'})
const accent = useCookie<string>('fb-accent', {default: () => 'blue'})

/** system 模式：由内联脚本在客户端尽早解析为 light/dark */
const resolvedTheme = computed(() => {
  const value = theme.value
  return value === 'light' || value === 'dark' ? value : 'light'
})

useHead({
  htmlAttrs: {
    'data-theme': resolvedTheme.value,
    'data-accent': accent.value,
  },
  script: [
    {
      // 首屏前同步解析 system 偏好，避免闪色
      innerHTML: `(function(){try{var m=document.documentElement.dataset.theme;var s=localStorage.getItem('fb-theme-mode');if(s==='system'||!s){document.documentElement.dataset.theme=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}else if(s==='dark'||s==='light'){document.documentElement.dataset.theme=s;}}catch(e){}})()`,
      tagPosition: 'head',
    },
  ],
})
</script>

<template>
  <NuxtLayout>
    <NuxtPage/>
  </NuxtLayout>
</template>
