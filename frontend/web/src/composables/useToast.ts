/**
 * 前台统一提示（toast）
 *
 * 为什么自建：前台此前每个页面各自维护一个 `message` ref，提示出现的位置、时长、
 * 是否读屏友好都不一致。这里用一份轻量实现统一，不引入第三方依赖。
 *
 * - 队列用 `useState` 共享（SSR 安全，客户端接管后状态一致）
 * - 默认 3.6s 自动消失，点击可立即关闭，**鼠标悬停会暂停**（WCAG 2.2.1 时限可控）
 * - 同屏最多 3 条，超出挤掉最早的（连点错误不会糊满屏幕）
 * - 渲染交给 `components/site/ToastHost.vue`（polite / assertive 两个 live region）
 *
 * 另提供模块级 `pushToast()`：HTTP 拦截器等**没有组件上下文**的地方也能提示，
 * 由宿主组件注册一次"写入队列"的能力即可。
 */
export type ToastKind = 'success' | 'error' | 'info' | 'warning'

export interface ToastItem {
  id: number
  kind: ToastKind
  text: string
}

/** 自动消失时长（毫秒） */
const DURATION = 3600
/** 同屏最多堆几条 */
const MAX_VISIBLE = 3

/** 自增 id：模块级计数器，避免多个组件实例产生重复 key */
let seq = 0

type ToastSink = (text: string, kind: ToastKind) => void

let sink: ToastSink | null = null
/** 宿主尚未挂载时的暂存（首屏请求可能早于 ToastHost 渲染） */
const queued: Array<{ text: string; kind: ToastKind }> = []

function setToastSink(next: ToastSink): void {
  sink = next
  while (queued.length) {
    const item = queued.shift()
    if (item) next(item.text, item.kind)
  }
}

/** 从任意位置推一条提示（含非组件上下文） */
export function pushToast(text: string, kind: ToastKind = 'info'): void {
  if (sink) sink(text, kind)
  else queued.push({text, kind})
}

export function useToast() {
  const items = useState<ToastItem[]>('site-toasts', () => [])

  /** id → 计时器句柄 */
  const timers = new Map<number, number>()

  function clearTimer(id: number): void {
    const handle = timers.get(id)
    if (handle !== undefined) window.clearTimeout(handle)
    timers.delete(id)
  }

  function dismiss(id: number): void {
    if (import.meta.client) clearTimer(id)
    items.value = items.value.filter((item) => item.id !== id)
  }

  function startTimer(id: number): void {
    if (!import.meta.client) return
    timers.set(
      id,
      window.setTimeout(() => dismiss(id), DURATION),
    )
  }

  function push(text: string, kind: ToastKind = 'info'): number {
    seq += 1
    const id = seq
    const next = [...items.value, {id, kind, text}]
    if (next.length > MAX_VISIBLE) {
      const dropped = next.splice(0, next.length - MAX_VISIBLE)
      if (import.meta.client) dropped.forEach((item) => clearTimer(item.id))
    }
    items.value = next
    startTimer(id)
    return id
  }

  /**
   * 悬停暂停：先停掉计时器，移开后再给完整时长。
   * 对"时限"类要求（WCAG 2.2.1）来说，这等价于用户可延长提示的停留时间。
   */
  function pause(id: number): void {
    if (!import.meta.client) return
    const handle = timers.get(id)
    if (handle === undefined) return
    window.clearTimeout(handle)
    timers.delete(id)
  }

  function resume(id: number): void {
    if (!import.meta.client || timers.has(id)) return
    startTimer(id)
  }

  // 注册模块级出口（幂等：重复注册只是指向同一份队列）
  setToastSink((text, kind) => push(text, kind))

  return {
    items,
    push,
    dismiss,
    pause,
    resume,
    success: (text: string) => push(text, 'success'),
    error: (text: string) => push(text, 'error'),
    warning: (text: string) => push(text, 'warning'),
    info: (text: string) => push(text, 'info'),
  }
}
