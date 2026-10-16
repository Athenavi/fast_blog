/**
 * 后台"最近访问"页面（命令面板的加速入口）
 *
 * 命令面板里"最近访问"比"全部菜单"命中率更高：多数管理员每天只在少数几个页面之间来回。
 * 用 `useState` 共享，后台布局负责记录、命令面板负责读取。
 */

const STORAGE_KEY = 'fb-admin-recent-pages'
/** 最多记这么多条：再多就失去"最近"的意义 */
const MAX_ITEMS = 6

export function useRecentPages() {
  const pages = useState<string[]>('admin-recent-pages', () => [])

  /** 从 localStorage 灌入（只在客户端调用，避免 SSR 读到不一致内容） */
  function hydrate(): void {
    if (!import.meta.client) return
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const parsed = JSON.parse(raw) as unknown
      if (Array.isArray(parsed)) {
        pages.value = parsed.filter((item): item is string => typeof item === 'string')
      }
    } catch {
      // 结构损坏：当作没有记录
      pages.value = []
    }
  }

  function remember(path: string): void {
    if (!import.meta.client || !path) return
    const next = [path, ...pages.value.filter((item) => item !== path)].slice(0, MAX_ITEMS)
    pages.value = next
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    } catch {
      /* 隐私模式下写不进去：只是少了加速入口，不影响功能 */
    }
  }

  return {pages, hydrate, remember}
}
