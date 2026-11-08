/**
 * 阅读偏好（正文字号 / 行宽）
 *
 * 为什么值得做：正文宽度与字号此前是写死的（`max-w-read` + 固定字号），
 * 读者没有任何调节余地——长文阅读里这是最常被抱怨的一点。
 *
 * ## 存储：localStorage + `<head>` 内联脚本，**不用 cookie**
 *
 * 这和主题/配色走同一条路（见 `useTheme.ts` 与 `app.vue` 的说明），理由在这里同样成立：
 * 公开页 `/articles/**` 开了 `swr` 边缘缓存，要求「同一份响应可以发给任何访问者」。
 * 用 `useCookie` 参与 SSR 会两头出问题——缓存里某个人选的宽度被发给所有人，
 * 而带 `default` 的 `useCookie` 还会在响应头写回 `Set-Cookie`，把别人已选的字号覆盖掉。
 *
 * 所以：
 *  - 首屏属性由 `app.vue` 的内联脚本在 CSS 生效前写进 `<html data-read-*>`（不闪）；
 *  - 本文件只负责切换与持久化，SSR 阶段一个响应头都不写；
 *  - 旧版存在 cookie 里的值仍兜一次，老读者不用重设。
 *
 * 落到样式上的方式是 **`<html>` 上的 data 属性 + CSS 变量**（见 styles/index.css 的
 * `[data-read-size=...]` / `[data-read-width=...]`），而不是拼一串 Tailwind 类名：
 * 类名字符串只能作用在一个元素上，而正文里的标题、图注、代码块，乃至正文之外的
 * 面包屑都要跟着同一条宽度走，变量能被整棵树继承。
 *
 * ⚠️ 两个 localStorage 键与 `app.vue` 内联脚本里的字面量**必须保持一致**。
 */
export type ReadingFontSize = 'sm' | 'md' | 'lg'
export type ReadingWidth = 'narrow' | 'wide'

/** 字号的 localStorage 键（与旧 cookie 同名，脚本读同一个键） */
export const READ_SIZE_STORAGE_KEY = 'fb-read-size'
/** 行宽的 localStorage 键（同上） */
export const READ_WIDTH_STORAGE_KEY = 'fb-read-width'

export const FONT_SIZES: Array<{ label: string; value: ReadingFontSize }> = [
  {label: 'fontSmall', value: 'sm'},
  {label: 'fontMedium', value: 'md'},
  {label: 'fontLarge', value: 'lg'},
]

export const WIDTHS: Array<{ label: string; value: ReadingWidth }> = [
  {label: 'widthNarrow', value: 'narrow'},
  {label: 'widthWide', value: 'wide'},
]

/** 从 localStorage 读，读不到（隐私模式）或没有时回落到旧 cookie */
function readStored(key: string): string {
  try {
    const stored = localStorage.getItem(key)
    if (stored) return stored
    const matched = document.cookie.match(new RegExp(`(?:^|;\\s*)${key}=([^;]+)`))
    return matched?.[1] ? decodeURIComponent(matched[1]) : ''
  } catch {
    return ''
  }
}

export function useReadingPrefs() {
  // 初始值取中性默认：真实值由内联脚本写在 `<html>` 上，客户端挂载后再对齐到这里
  const fontSize = useState<ReadingFontSize>('read-size', () => 'md')
  const width = useState<ReadingWidth>('read-width', () => 'narrow')

  function applyDom(): void {
    if (!import.meta.client) return
    const root = document.documentElement
    root.dataset.readSize = fontSize.value
    root.dataset.readWidth = width.value
    try {
      localStorage.setItem(READ_SIZE_STORAGE_KEY, fontSize.value)
      localStorage.setItem(READ_WIDTH_STORAGE_KEY, width.value)
    } catch {
      // 写不进去（隐私模式）不影响本次会话的阅读体验
    }
  }

  function setSize(value: ReadingFontSize): void {
    fontSize.value = value
    applyDom()
  }

  function setWidth(value: ReadingWidth): void {
    width.value = value
    applyDom()
  }

  onMounted(() => {
    const size = readStored(READ_SIZE_STORAGE_KEY)
    const wide = readStored(READ_WIDTH_STORAGE_KEY)
    fontSize.value = size === 'sm' || size === 'lg' ? size : 'md'
    width.value = wide === 'wide' ? 'wide' : 'narrow'
    applyDom()
  })

  return {fontSize, width, setSize, setWidth}
}
