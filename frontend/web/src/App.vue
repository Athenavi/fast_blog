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

/**
 * 文档语言与书写方向必须跟随实际语言：
 * 否则切到 English 后 `<html lang>` 仍是 `zh-CN`，读屏软件会用中文语音朗读英文内容
 * （WCAG 3.1.1），搜索引擎的语言判断也会错。`dir` 为将来接入 RTL 语言预留。
 */
const {locale, locales} = useI18n()

const currentDir = computed<'ltr' | 'rtl'>(() => {
  const found = (locales.value as Array<{ code: string; dir?: string }>).find(
    (item) => item.code === locale.value,
  )
  return found?.dir === 'rtl' ? 'rtl' : 'ltr'
})

useHead({
  htmlAttrs: {
    lang: computed(() => String(locale.value)),
    dir: currentDir,
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
