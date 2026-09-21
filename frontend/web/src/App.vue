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
      // 首屏前同步解析 system 偏好，避免闪色；同时维护 `html.dark`（Element Plus 暗色主题的挂载点）
      innerHTML: `(function(){try{var el=document.documentElement;var s=localStorage.getItem('fb-theme-mode');var m=el.dataset.theme;var d;if(s==='system'||!s){d=window.matchMedia('(prefers-color-scheme: dark)').matches;}else if(s==='dark'||s==='light'){d=(s==='dark');}else{d=(m==='dark');}el.dataset.theme=d?'dark':'light';el.classList.toggle('dark',d);}catch(e){}})()`,
      tagPosition: 'head',
    },
  ],
})
</script>

<template>
  <NuxtLayout>
    <NuxtPage/>
  </NuxtLayout>

  <!-- 全局提示宿主：登录/注册等 layout:false 的页面同样需要 -->
  <ToastHost/>
</template>
