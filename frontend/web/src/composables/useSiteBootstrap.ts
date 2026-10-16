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
export const THEME_CSS_KEY = 'theme-css'
export const THEME_VARIABLES_KEY = 'theme-variables'
export const THEME_TEMPLATES_KEY = 'theme-templates'
export const THEME_SLUG_KEY = 'theme-slug'

/** 聚合接口的响应体（与 server/routes/__site/bootstrap.get.ts 的返回一一对应） */
export interface SiteBootstrapPayload {
  settings: SiteSettings | null
  nav: NavNode[]
  themeSlots: ThemeSlots
  /** 当前激活主题的 styles.css（服务器级，可安全 SSR 直出） */
  themeCss: string
  /** 主题设置渲染出的 CSS 变量块（服务器级，可安全 SSR 直出） */
  themeVariables: string
  /**
   * L1 声明式页面（`theme.json` 的 `templates`）
   *
   * 形如 `{HomePage: [{block, props, children}, ...]}`，后端已按区块白名单校验。
   * 区块渲染器解释执行 —— "改 theme.json 刷新即生效"的载体，无需重新构建。
   */
  themeTemplates: Record<string, unknown[]>
  themeSlug: string | null
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
  const themeCss = useState<string>(THEME_CSS_KEY, () => '')
  const themeVariables = useState<string>(THEME_VARIABLES_KEY, () => '')
  const themeTemplates = useState<Record<string, unknown[]>>(THEME_TEMPLATES_KEY, () => ({}))
  const themeSlug = useState<string | null>(THEME_SLUG_KEY, () => null)

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
      themeCss.value = payload.themeCss ?? ''
      themeVariables.value = payload.themeVariables ?? ''
      themeTemplates.value = payload.themeTemplates ?? {}
      themeSlug.value = payload.themeSlug ?? null
    }
    loaded.value = true
  })()

  return nuxtApp._fbSiteBootstrap
}

/**
 * 当前主题 CSS（服务器级，可安全 SSR 直出）
 *
 * 由 `loadSiteBootstrap()` 一次取回；未取到时返回空串，布局据此不注入任何样式
 * （而不是注入一段占位 —— 空的 `<style>` 只会让 HTML 更难看懂）。
 */
export function useThemeCss() {
  return useState<string>(THEME_CSS_KEY, () => '')
}

/**
 * 当前主题设置渲染出的 CSS 变量块（服务器级）
 *
 * 与 `useThemeCss()` 分开：注入时必须**先变量、后主题 CSS** —— 主题 CSS 依赖
 * 这些变量（`var(--color-primary)`），且允许它覆盖默认值。
 */
export function useThemeVariables() {
  return useState<string>(THEME_VARIABLES_KEY, () => '')
}

/**
 * 当前主题声明的 L1 页面区块（`theme.json` 的 `templates`）
 *
 * 形如 `{HomePage: [{block, props, children}, ...]}`，后端已按白名单校验。
 * 与 `useThemePage()`（L2 编译期组件）互补：L2 优先，取不到才用 L1。
 */
export function useThemeTemplates() {
  return useState<Record<string, unknown[]>>(THEME_TEMPLATES_KEY, () => ({}))
}

/**
 * 当前激活主题的 slug
 *
 * 布局用它给根元素挂 `data-theme`，从而形成**布局契约**（Halo 的 `layout.html` 精神）：
 * 主题的 `styles.css` 可以定向 `.theme-<slug> .t-card { … }`，
 * 插件的前台页面也能复用同一套主题样式，不必各自重复实现。
 */
export function useThemeSlug() {
  return useState<string | null>(THEME_SLUG_KEY, () => null)
}
