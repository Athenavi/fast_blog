/**
 * 主题槽位
 *
 * 对应原 astro 的 `lib/theme-components.ts`（`useThemeSlots`）。
 *
 * 主题可以在后台「主题配置」里声明组件槽位映射（`component_slots`），
 * 例如把 `articleCard` 设为 `compact`。前端读一次、全局缓存，卡片组件据此选择变体。
 *
 * 后端契约：`GET /extension/theme/public/config` → `{slug, settings, component_slots}`
 * （公开接口，无需登录）。
 */
import {themeApi} from '@/api'

export interface ThemeSlots {
  /** 文章卡片变体：default 标准 / compact 紧凑 */
  articleCard?: 'default' | 'compact' | string

  /** 其它槽位按主题自定义，未声明时使用默认实现 */
  [key: string]: unknown
}

export function useThemeSlots() {
  const slots = useState<ThemeSlots>('theme-slots', () => ({}))
  const loaded = useState<boolean>('theme-slots-loaded', () => false)

  async function load(): Promise<void> {
    if (loaded.value) return
    try {
      const config = await themeApi.publicConfig()
      slots.value = (config?.component_slots ?? {}) as ThemeSlots
    } catch {
      slots.value = {}
    } finally {
      // 失败也标记为已加载，避免每次渲染都重试
      loaded.value = true
    }
  }

  /** 取字符串型槽位值（带默认回退） */
  function slot(name: string, fallback = ''): string {
    const value = slots.value?.[name]
    return typeof value === 'string' && value ? value : fallback
  }

  return {slots, loaded, load, slot}
}

/** 页面级初始化（在需要的布局或页面里 await 一次即可） */
export async function initThemeSlots(): Promise<void> {
  const {load} = useThemeSlots()
  await load()
}
