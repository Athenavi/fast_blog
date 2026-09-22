/**
 * 全局快捷键（客户端插件）
 *
 * 对应 astro 版 `GlobalShortcuts.tsx`（T1-1 迁移）：
 *  - Ctrl/Cmd + K → 跳转搜索页。
 * 与原版的差异：用 `navigateTo` 走 SPA 导航，替代原来的 `window.location` 整页刷新。
 *
 * **后台不接管这个键**：后台的 ⌘K 是命令面板（`components/admin/CommandPalette.vue`），
 * 语义完全不同。两个监听器都挂在 window 上，若这里不主动让开，
 * 后台按 ⌘K 会同时跳搜索页并弹面板。后台页面统一声明了 `layout: 'admin'`，据此判断。
 */
export default defineNuxtPlugin((nuxtApp) => {
  const handleKeydown = (event: KeyboardEvent): void => {
    if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== 'k') return

    const layout = nuxtApp.$router?.currentRoute.value.meta.layout
    if (layout === 'admin') return

    event.preventDefault()
    void navigateTo('/search')
  }

  window.addEventListener('keydown', handleKeydown)
})
