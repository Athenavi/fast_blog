/**
 * 主题槽位
 *
 * 对应原 astro 的 `lib/theme-components.ts`（`useThemeSlots`）。
 * 主题可以在后台「主题配置」里声明组件槽位映射（`component_slots`），
 * 例如把 `articleCard` 设为 `compact`。前端读一次、全局缓存，卡片组件据此选择变体。
 *
 * 后端契约：`GET /extension/theme/public/config` → `{slug, settings, component_slots}`
 * （公开接口，无需登录）。实际取数由聚合引导接口完成，见 `useSiteBootstrap`。
 *
 * ## 为什么不能再直接 `import {themeApi} from '@/api'`
 *
 * 两个原因，都不是风格问题：
 *
 *  1. **主题槽位是布局的依赖，会把后台接口层拖进前台首屏**。此前这里是
 *     `import {themeApi} from '@/api'`，而 `api/index.ts` 是一个 178 项的全量聚合出口
 *     （其中含 `export {default as http} from './request'`）。于是 **axios（约 20 KB gzip）
 *     与整套后台 API 模块（约 11 KB gzip）被钉在前台首屏关键路径上** ——
 *     实测它们确实出现在首页的 38 个 `<script>` 里。前台请用 `@/api/public`。
 *  2. **`themeApi` 走 axios，而 axios 的 `baseURL` 是相对路径 `/api/v3`**：在 Node 里
 *     会拼出相对 URL 直接抛 `Invalid URL`。SSR 阶段异常被吞掉并置 `loaded = true`，
 *     随 payload 传给客户端，客户端因此不会再重试 —— **主题槽位在服务端渲染的页面上
 *     永远是空的**。改走聚合接口（内部用 `$fetch`，服务端自动用绝对地址）之后，
 *     槽位在 SSR 阶段才真正生效。
 */
import {loadSiteBootstrap, THEME_SLOTS_KEY} from '@/composables/useSiteBootstrap'

export interface ThemeSlots {
  /** 文章卡片变体：default 标准 / compact 紧凑 */
  articleCard?: 'default' | 'compact' | string

  /** 其它槽位按主题自定义，未声明时使用默认实现 */
  [key: string]: unknown
}

export function useThemeSlots() {
  const slots = useState<ThemeSlots>(THEME_SLOTS_KEY, () => ({}))
  const loaded = useState<boolean>('theme-slots-loaded', () => false)

  async function load(): Promise<void> {
    if (loaded.value) return
    await loadSiteBootstrap()
    // 失败也标记为已加载，避免每次渲染都重试
    loaded.value = true
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
