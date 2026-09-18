/**
 * 全局快捷键（客户端插件）
 *
 * 对应 astro 版 `GlobalShortcuts.tsx`（T1-1 迁移）：
 *  - Ctrl/Cmd + K → 跳转搜索页。
 * 与原版的差异：用 `navigateTo` 走 SPA 导航，替代原来的 `window.location` 整页刷新。
 */
export default defineNuxtPlugin(() => {
  const handleKeydown = (event: KeyboardEvent): void => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault()
      void navigateTo('/search')
    }
  }

  window.addEventListener('keydown', handleKeydown)
})
