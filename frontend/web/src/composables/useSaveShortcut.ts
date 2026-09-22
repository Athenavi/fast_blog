import {onBeforeUnmount, onMounted, type Ref} from 'vue'

/**
 * Ctrl / Cmd + S 保存
 *
 * 为什么不做成全局插件：保存动作是**页面级**的——只有正在编辑的页面知道该保存什么、
 * 能不能保存。因此由页面注册处理函数：没有注册时不拦截按键，浏览器的原生"保存网页"
 * 在非编辑页仍然可用。
 *
 * 约定：
 *  - 拦截 `Ctrl/Cmd + S`（不带 Shift/Alt），阻止浏览器默认保存对话框；
 *  - 处理函数执行期间忽略重复触发，避免连按产生并发保存。
 */
export interface SaveShortcutOptions {
  /** 是否允许保存（例如保存进行中、或必填项未通过校验时可置为 false） */
  enabled?: Ref<boolean> | (() => boolean)
}

export function useSaveShortcut(
  handler: () => void | Promise<void>,
  options: SaveShortcutOptions = {},
): void {
  let running = false

  function isEnabled(): boolean {
    const flag = options.enabled
    if (flag === undefined) return true
    return typeof flag === 'function' ? flag() : flag.value
  }

  function onKeydown(event: KeyboardEvent): void {
    if (!(event.ctrlKey || event.metaKey) || event.shiftKey || event.altKey) return
    if (event.key.toLowerCase() !== 's') return

    event.preventDefault()
    if (running || !isEnabled()) return

    running = true
    void Promise.resolve(handler()).finally(() => {
      running = false
    })
  }

  onMounted(() => window.addEventListener('keydown', onKeydown))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
}
