<script setup lang="ts">
/**
 * Nuxt 根组件
 *
 * ## 主题与配色的首屏决定权在**客户端内联脚本**，不在 SSR
 *
 * 原因：公开页开了 `swr` 边缘缓存（见 `nuxt.config.ts` 的 routeRules），要求
 * 「同一份响应可以发给任何访问者」。而主题/配色是**用户级**状态，一旦参与 SSR
 * 直出就会串号：
 *  - 缓存里某个用户的 `data-theme="dark"` 会被发给所有人；
 *  - 响应里的 `Set-Cookie`（`useCookie` 带 `default` 时会写回默认值）被缓存后，
 *    会把别人已选的配色**持久化覆盖**（365 天）。
 *
 * 所以这里：
 *  - **不读** cookie（`useTheme` 也改成了 localStorage，见该文件说明）；
 *  - **不**用 `useHead` 声明 `data-theme` / `data-accent` —— 声明了的话，水合时
 *    Vue 会用 SSR 的静态值把内联脚本刚设好的值覆盖回去；
 *  - 只下发一段内联脚本，在 `<style>` / CSS `<link>` **之前**同步写入真实值。
 *    它早于首次绘制执行，所以不会闪色；代价是禁用 JS 时呈现默认（浅色 / 蓝色）。
 *
 * ⚠️ 脚本里的两个 localStorage 键必须与 `composables/useTheme.ts` 的
 * `THEME_STORAGE_KEY` / `ACCENT_STORAGE_KEY` 保持一致。
 */
const {locale, locales} = useI18n()

/**
 * 文档语言与书写方向必须跟随实际语言：
 * 否则切到 English 后 `<html lang>` 仍是 `zh-CN`，读屏软件会用中文语音朗读英文内容
 * （WCAG 3.1.1），搜索引擎的语言判断也会错。`dir` 为将来接入 RTL 语言预留。
 */
const currentDir = computed<'ltr' | 'rtl'>(() => {
  const found = (locales.value as Array<{ code: string; dir?: string }>).find(
    (item) => item.code === locale.value,
  )
  return found?.dir === 'rtl' ? 'rtl' : 'ltr'
})

/**
 * 首屏引导脚本（拼成一行下发，它会随每个 HTML 响应走）。
 *
 * 三段逻辑：深浅色（localStorage → 跟随系统）、自选配色（localStorage → 旧 cookie 兜底）、
 * 以及 `html.dark`（Element Plus 暗色主题挂在它上面）。
 */
const THEME_BOOTSTRAP = [
  '(function(){try{',
  'var el=document.documentElement,',
  "s=localStorage.getItem('fb-theme-mode'),",
  "d=s==='dark'?!0:s==='light'?!1:window.matchMedia('(prefers-color-scheme: dark)').matches;",
  "el.dataset.theme=d?'dark':'light';el.classList.toggle('dark',d);",
  "var a=localStorage.getItem('fb-accent-name');",
  "if(!a){var m=document.cookie.match(/(?:^|;\\s*)fb-accent=([^;]+)/);a=m?decodeURIComponent(m[1]):''}",
  "el.dataset.accent=a||'blue';",
  '}catch(e){}})()',
].join('')

useHead({
  htmlAttrs: {
    lang: computed(() => String(locale.value)),
    dir: currentDir,
  },
  script: [
    {
      innerHTML: THEME_BOOTSTRAP,
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
