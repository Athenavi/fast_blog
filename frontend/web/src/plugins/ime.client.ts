/**
 * 输入法（IME）回车防护
 *
 * **问题**：全项目有 38 处 `@keyup.enter` / `@keydown.enter` 用于"回车即搜索/提交"
 * （例如文章列表的搜索框、加标签输入、图片地址输入）。中文（以及日文、韩文）输入法在
 * 组合状态下按回车是"确认候选词"，而 Vue 的按键修饰符**不区分是否处于合成态**，
 * 于是用户每输入一个词按回车确认，都会顺带触发一次搜索或提交。
 *
 * **做法**：在 window 的**捕获阶段**拦截合成态的回车，`stopImmediatePropagation()` 之后
 * 事件不会继续传播到元素上，因此元素上的 `@keyup.enter`（含 `.prevent`）都不会执行。
 * 这里刻意**不**调用 `preventDefault()`：输入法自身的候选词确认由浏览器/IPC 处理，
 * 我们不介入，文本框内的换行等默认行为也不受影响。
 *
 * 为什么用全局插件而不是逐个改调用点：38 处分散在 30+ 文件里，逐个改既容易漏，
 * 也会让后续新代码继续踩同一个坑；在平台层修正一次，新页面自动受益。
 */
export default defineNuxtPlugin(() => {
  if (!import.meta.client) return

  /** 是否处于输入法合成态 */
  function isComposing(event: KeyboardEvent): boolean {
    // Chrome/Edge 在"组合结束"的那次事件里 `isComposing` 可能已为 false，
    // 但 `keyCode === 229` 表示该按键由输入法处理中，两者一起判断才完整。
    return event.isComposing || event.keyCode === 229
  }

  function blockComposingEnter(event: KeyboardEvent): void {
    if (event.key !== 'Enter' && event.keyCode !== 13) return
    if (!isComposing(event)) return
    event.stopImmediatePropagation()
  }

  window.addEventListener('keydown', blockComposingEnter, true)
  window.addEventListener('keyup', blockComposingEnter, true)
})
