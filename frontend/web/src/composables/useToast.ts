/**
 * 前台统一提示（toast）
 *
 * 为什么自建：前台此前每个页面各自维护一个 `message` ref，提示出现的位置、时长、
 * 是否读屏友好都不一致。这里用一份轻量实现统一，不引入第三方依赖。
 *
 * - 队列用 `useState` 共享（SSR 安全，客户端接管后状态一致）
 * - 默认 3.6s 自动消失，点击可立即关闭
 * - 渲染交给 `components/site/ToastHost.vue`（含 `aria-live`）
 */
export type ToastKind = 'success' | 'error' | 'info'

export interface ToastItem {
  id: number
  kind: ToastKind
  text: string
}

/** 自动消失时长（毫秒） */
const DURATION = 3600

/** 自增 id：模块级计数器，避免多个组件实例产生重复 key */
let seq = 0

export function useToast() {
  const items = useState<ToastItem[]>('site-toasts', () => [])

  function dismiss(id: number): void {
    items.value = items.value.filter((item) => item.id !== id)
  }

  function push(text: string, kind: ToastKind = 'info'): number {
    seq += 1
    const id = seq
    items.value = [...items.value, {id, kind, text}]
    if (import.meta.client) {
      window.setTimeout(() => dismiss(id), DURATION)
    }
    return id
  }

  return {
    items,
    push,
    dismiss,
    success: (text: string) => push(text, 'success'),
    error: (text: string) => push(text, 'error'),
    info: (text: string) => push(text, 'info'),
  }
}
