/**
 * 站点引导数据（站点信息 / 顶部导航 / 主题槽位）
 *
 * 三者以前是三个独立的后端请求，现在由**一个 Nitro 内部接口**一次取回并做服务端缓存
 * （`server/routes/__site/bootstrap.get.ts`）。这里是唯一的客户端入口：
 * `useSiteInfo`、`useSiteNav`、`useThemeSlots` 都从它读同一份 `useState`，
 * 所以无论在布局还是页面里调用，整页只发一次请求。
 *
 * 约定与原来三个 composable 一致：
 *  - `useState` 承载结果，SSR 取好后随 payload 传给客户端，水合不再请求；
 *  - `loaded` 标记 + 在 `nuxtApp` 上做请求内单飞（**不用模块级变量**：
 *    SSR 下 `nuxtApp` 每请求一个实例，模块级变量会把某个请求的结果泄漏给其他请求）；
 *  - 失败也不重试（标记为已加载），各处回落到内置默认值，绝不让首屏因它整页 500。
 */
import type {SiteSettings} from '@/types/content'
import type {NavNode} from '@/composables/useSiteNav'
import type {ThemeSlots} from '@/composables/useThemeSlots'

/** 内部聚合接口路径。**不能放在 `/api/`**：nginx 与 devProxy 会把 `/api/**` 直接打给后端 */
export const SITE_BOOTSTRAP_URL = '/__site/bootstrap'

/** `useState` 键（三个 composable 共用，集中在这里避免键名漂移） */
export const SITE_SETTINGS_KEY = 'site-settings'
export const SITE_NAV_KEY = 'site-main-nav-items'
export const THEME_SLOTS_KEY = 'theme-slots'

/** 聚合接口的响应体（与 server/routes/__site/bootstrap.get.ts 的返回一一对应） */
export interface SiteBootstrapPayload {
  settings: SiteSettings | null
  nav: NavNode[]
  themeSlots: ThemeSlots
}

/** 单飞挂载点（挂在 NuxtApp 实例上，随请求生命周期存亡） */
interface SiteBootstrapFlight {
  _fbSiteBootstrap?: Promise<void>
}

/**
 * 取回引导数据（整页只发一次请求）。
 *
 * ⚠️ 所有 `useState` / `useNuxtApp` 调用都在**第一个 await 之前**完成：
 * 这些 composable 依赖当前 Vue 实例，await 之后再取会拿不到（服务端尤其如此）。
 */
export function loadSiteBootstrap(): Promise<void> {
  const loaded = useState<boolean>('site-bootstrap-loaded', () => false)
  const settings = useState<SiteSettings>(SITE_SETTINGS_KEY, () => ({}))
  const nav = useState<NavNode[]>(SITE_NAV_KEY, () => [])
  const slots = useState<ThemeSlots>(THEME_SLOTS_KEY, () => ({}))

  if (loaded.value) return Promise.resolve()

  const nuxtApp = useNuxtApp() as unknown as SiteBootstrapFlight
  nuxtApp._fbSiteBootstrap ??= (async () => {
    let payload: SiteBootstrapPayload | null = null
    try {
      payload = await $fetch<SiteBootstrapPayload>(SITE_BOOTSTRAP_URL)
    } catch {
      // 后端不可用：保持默认值，不让整页失败
      payload = null
    }

    if (payload) {
      if (payload.settings) settings.value = {...settings.value, ...payload.settings}
      nav.value = payload.nav ?? []
      slots.value = payload.themeSlots ?? {}
    }
    loaded.value = true
  })()

  return nuxtApp._fbSiteBootstrap
}
