/**
 * 移动端手势（客户端插件）
 *
 * 对应 astro 版 `MobileGestures.tsx`（T1-2 迁移），逻辑照搬：
 *  - 触摸起点在屏幕左缘（< 50px）且水平右滑（Δx > 80、|Δx| > |Δy|）→ `history.back()`；
 *  - passive 监听不影响滚动性能，判定放进 rAF 避免布局抖动。
 */
export default defineNuxtPlugin(() => {
  let startX = 0
  let startY = 0
  let rafId: number | null = null

  const onTouchStart = (event: TouchEvent): void => {
    startX = event.touches[0]?.clientX ?? 0
    startY = event.touches[0]?.clientY ?? 0
  }

  const onTouchEnd = (event: TouchEvent): void => {
    const touch = event.changedTouches[0]
    if (!touch) return

    if (rafId !== null) cancelAnimationFrame(rafId)
    rafId = requestAnimationFrame(() => {
      const deltaX = touch.clientX - startX
      const deltaY = touch.clientY - startY
      if (deltaX > 80 && Math.abs(deltaX) > Math.abs(deltaY) && startX < 50) {
        window.history.back()
      }
      rafId = null
    })
  }

  window.addEventListener('touchstart', onTouchStart, {passive: true})
  window.addEventListener('touchend', onTouchEnd, {passive: true})
})
