/**
 * 防抖与节流
 *
 * ## 为什么需要
 *
 * 编辑页每次按键都触发一次"暂存"是浪费：一篇 5000 字的文章会写几千次
 * localStorage；如果那条链路改成打接口，就是几千次数据库写入 —— 这正是
 * "智能保存防抖"要解决的问题。
 *
 * ## 两者取哪个
 *
 * - **防抖（debounce）**：停止操作 N 毫秒后才执行。适合"保存草稿" ——
 *   用户还在打字时不该保存，停下来才保存。
 * - **节流（throttle）**：每 N 毫秒最多执行一次（保证执行）。适合"上报进度" ——
 *   持续输入时也要定期上报，不能一直等到停下。
 *
 * 编辑器暂存用**防抖**；如果要"边打字边提示已保存"，用节流。
 *
 * ## 关于 `flush` 与 `cancel`
 *
 * 页面卸载时（`beforeunload`）必须 `flush()`：防抖的默认行为是"取消未执行的调用"，
 * 如果用户打完最后一个字立刻关页面，那次保存会**被丢掉** —— 这是数据丢失，
 * 不是省事。所以两者都提供，并明确语义。
 */

export interface DebouncedFn<T extends (...args: never[]) => unknown> {
  /** 立刻执行尚未触发的那次调用（若存在） */
  flush: () => void
  /** 丢弃尚未触发的那次调用 */
  cancel: () => void
  /** 是否有等待中的调用 */
  pending: () => boolean

  (...args: Parameters<T>): void
}

/**
 * 防抖：停止调用 `wait` 毫秒后才真正执行。
 *
 * 每次新调用都会重置计时器。
 */
export function debounce<T extends (...args: never[]) => unknown>(
  fn: T,
  wait: number,
): DebouncedFn<T> {
  let timer: ReturnType<typeof setTimeout> | null = null
  let lastArgs: Parameters<T> | null = null

  const invoke = (): void => {
    timer = null
    if (!lastArgs) return
    const args = lastArgs
    lastArgs = null
    fn(...args)
  }

  const wrapped = ((...args: Parameters<T>): void => {
    lastArgs = args
    if (timer) clearTimeout(timer)
    timer = setTimeout(invoke, wait)
  }) as DebouncedFn<T>

  wrapped.flush = (): void => {
    if (timer) {
      clearTimeout(timer)
      invoke()
    }
  }

  wrapped.cancel = (): void => {
    if (timer) clearTimeout(timer)
    timer = null
    lastArgs = null
  }

  wrapped.pending = (): boolean => timer !== null

  return wrapped
}

/**
 * 节流：每 `wait` 毫秒**最多**执行一次，且**保证**在持续调用中定期执行。
 *
 * 与防抖的区别：防抖在持续调用时**永远不执行**（一直被重置），
 * 节流会按固定节奏执行。适合"持续输入时也要定期落盘"的场景。
 */
export function throttle<T extends (...args: never[]) => unknown>(
  fn: T,
  wait: number,
): DebouncedFn<T> {
  let last = 0
  let timer: ReturnType<typeof setTimeout> | null = null
  let lastArgs: Parameters<T> | null = null

  const wrapped = ((...args: Parameters<T>): void => {
    lastArgs = args
    const now = Date.now()
    const remaining = wait - (now - last)

    if (remaining <= 0) {
      last = now
      const call = lastArgs
      lastArgs = null
      fn(...call)
      return
    }

    // 尾部补一次：保证"最后一次调用"不会被丢掉
    if (!timer) {
      timer = setTimeout(() => {
        timer = null
        last = Date.now()
        if (lastArgs) {
          const call = lastArgs
          lastArgs = null
          fn(...call)
        }
      }, remaining)
    }
  }) as DebouncedFn<T>

  wrapped.flush = (): void => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    if (lastArgs) {
      const call = lastArgs
      lastArgs = null
      last = Date.now()
      fn(...call)
    }
  }

  wrapped.cancel = (): void => {
    if (timer) clearTimeout(timer)
    timer = null
    lastArgs = null
  }

  wrapped.pending = (): boolean => timer !== null

  return wrapped
}
