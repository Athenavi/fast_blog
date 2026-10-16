/**
 * 前台引导数据聚合接口（站点信息 / 顶部导航 / 主题槽位）
 *
 * ## 为什么要聚合 + 缓存
 *
 * 这三个都是**每个前台页面都会用**的公开配置，此前由 `layouts/default.vue` 直接向后端
 * 发三个请求。虽然它们是并发的（只占一轮往返），但那一轮往返**串在页面自己取数的前面**
 * ——布局 setup 先于页面 setup 执行，页面只能等它完成才发请求。于是每次 SSR 都是
 * 「布局 1 RTT（3 个请求）→ 页面 1 RTT」，而这三个值几分钟才变一次。
 *
 * 现在：布局只等这一次**本地 Nitro 调用**（同进程，不再穿到 Python 后端），
 * 结果按 `maxAge` 缓存在 Nitro 里（`swr`：过期先给旧的、后台再刷），
 * 后端只在缓存未命中时才被问一次。实测省掉一整轮后端往返。
 *
 * ## 路径为什么是 `/__site/bootstrap` 而不是 `/api/...`
 *
 * nginx 的 `location /api/` 与 dev 的 `nitro.devProxy['/api']` 都会把 `/api/**`
 * **直接打到 Python 后端**，根本到不了 Nuxt。所以这个内部接口必须绕开 `/api` 前缀。
 * 名称用双下划线前缀表明它是内部约定接口，另外已在 `nuxt.config.ts` 的 PWA
 * `navigateFallbackDenylist` 里排除，避免 Service Worker 把导航请求回退成 HTML。
 *
 * ## 缓存键必须带域名
 *
 * 后端的多站点隔离是按**请求域名**解析的（`src/middleware/multisite_middleware.py`：
 * 先精确匹配 `Site.domain`，再匹配子域名，再匹配路径前缀，最后回落默认站点）。
 * `system_settings` 是全局表，但 `menus` 与 `themes` 是站点级数据 ——
 * 用常量做缓存键会把 A 站点的导航发给 B 站点。因此键取 `<域名> + <后端地址>`。
 */
import type {H3Event} from 'h3'

interface BackendEnvelope<T> {
  code: number
  msg?: string
  data: T
}

interface BootstrapPayload {
  settings: unknown
  nav: unknown[]
  themeSlots: Record<string, unknown>
  /**
   * 当前激活主题的 `styles.css`（服务端内联进 `<head>`，不额外发请求）
   *
   * 注意与**用户级**配色的区别：主题 CSS 是**服务器级**的（同一份发给所有访问者），
   * 所以可以安全参与 SSR 直出；而 `data-theme` / `data-accent` 是用户级的，
   * 参与直出会被公开页的 swr 边缘缓存串号（见 `app.vue` 的说明）。
   */
  themeCss: string
  /**
   * 主题设置渲染出的 CSS 变量块（`:root { --color-primary: …; }`）
   *
   * 与 `themeCss` 分开传：注入时它必须**在前**，主题 CSS 才能覆盖默认值。
   */
  themeVariables: string
  /** 当前激活主题的 slug（调试用；也便于判断是否换了主题） */
  themeSlug: string | null
  /**
   * L1 声明式页面（`theme.json` 的 `templates`）
   *
   * 形如 `{HomePage: [{block, props, children}, ...]}`，由后端做白名单校验后下发。
   * 前端区块渲染器解释执行 —— 这是"改 theme.json 刷新即生效"的载体，**无需重新构建**。
   */
  themeTemplates: Record<string, unknown[]>
}

/** 缓存新鲜期（秒）：公开配置改动极少，120s 足够且不至于让后台改完看不见 */
const CACHE_MAX_AGE = 120
/** 过期后仍可继续复用的时间（秒）：在此期间先返回旧值并后台刷新 */
const CACHE_STALE_MAX_AGE = 600

/** 取一个后端公开配置（统一解 `{code, msg, data}` 信封；失败返回 null 由调用方降级） */
async function fetchPublic<T>(
  base: string,
  path: string,
  headers: Record<string, string>,
): Promise<T | null> {
  try {
    const resp = await $fetch<BackendEnvelope<T>>(`${base}/api/v3${path}`, {headers})
    return resp?.code === 200 ? resp.data : null
  } catch {
    return null
  }
}

/**
 * 真正的取数逻辑（被缓存）
 *
 * `forwardedHost` 参与缓存键，也作为 `x-forwarded-host` 转发给后端：
 * Node 的 `fetch`（undici）**不允许覆盖 `Host`**（实测会忽略，仍旧用 URL 里的主机），
 * 所以只能走 `x-forwarded-host`。后端 uvicorn 默认 `proxy_headers=True`，
 * 在受信来源下会用它改写请求域名 —— 也就是说这个头一旦被后端采纳，
 * SSR 取到的就是**当前访问域名对应的站点**，而不是默认站点。
 */
const fetchBootstrap = defineCachedFunction(
  async (base: string, forwardedHost: string): Promise<BootstrapPayload> => {
    const headers: Record<string, string> = {
      accept: 'application/json',
      'x-forwarded-host': forwardedHost,
    }

    const [settings, nav, theme, themeCss] = await Promise.all([
      fetchPublic<unknown>(base, '/system/setting/public', headers),
      fetchPublic<{ items?: unknown[] }>(base, '/system/menu/public/main-nav', headers),
      fetchPublic<{
        component_slots?: Record<string, unknown>
        templates?: Record<string, unknown[]>
      }>(
        base,
        '/extension/theme/public/config',
        headers,
      ),
      // 主题 CSS：后端已有公开端点（`theme_ops_service.active_css()` 返回 {slug, css, length}）。
      // 放在这里一起取，就能复用同一个缓存条目 —— 不必为样式再开一条请求链路。
      fetchPublic<{ slug?: string | null; css?: string; variables?: string }>(
        base,
        '/extension/theme/public/css',
        headers,
      ),
    ])

    return {
      settings: settings ?? null,
      nav: nav?.items ?? [],
      themeSlots: theme?.component_slots ?? {},
      themeCss: themeCss?.css ?? '',
      // 主题设置渲染出的 CSS 变量块（后端 `theme/variables.py`），与主题 CSS 分开传
      themeVariables: themeCss?.variables ?? '',
      // L1 声明式页面（后端已按区块白名单校验过）
      themeTemplates: theme?.templates ?? {},
      themeSlug: themeCss?.slug ?? null,
    }
  },
  {
    name: 'site-bootstrap',
    maxAge: CACHE_MAX_AGE,
    staleMaxAge: CACHE_STALE_MAX_AGE,
    swr: true,
    getKey: (base: string, forwardedHost: string) => `${forwardedHost}|${base}`,
  },
)

export default defineEventHandler(async (event: H3Event): Promise<BootstrapPayload> => {
  const config = useRuntimeConfig(event)
  const base = String(config.public.apiBaseUrl || 'http://127.0.0.1:9421').replace(/\/+$/, '')

  // 取访问者看到的域名；`x-forwarded-host` 优先（有反向代理时它才是原始域名）
  const forwardedHost =
    getRequestHeader(event, 'x-forwarded-host') ||
    getRequestHeader(event, 'host') ||
    'default'

  return await fetchBootstrap(base, forwardedHost)
})
