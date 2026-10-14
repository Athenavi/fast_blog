/**
 * 顶部导航数据
 *
 * 数据源：后台「菜单管理」里 slug=main-nav 的菜单项（未配置时接口 404 → 调用方回退内置导航）。
 *
 * **为什么抽成 composable 而不是留在 `SiteHeader` 里**：布局的 setup 先于 `SiteHeader`
 * 执行（`SiteHeader` 是布局模板里的子组件）。取数留在组件内时，这次后端往返只能排在
 * 布局自己的取数**之后**串行发生；抽出来之后，布局可以用一个 `Promise.all` 把
 * 「站点信息 + 主题槽位 + 导航」三次请求并发发出去，少一整轮往返。
 *
 * 与 `useSiteInfo` 同一套约定：`useState` 承载结果 + `loaded` 标记 + 在 `nuxtApp`
 * 上做请求内单飞（`nuxtApp` 每请求一个实例，不会跨请求泄漏）。
 */

export interface NavNode {
  id: number
  title: string
  url: string
}

/** 单飞挂载点 */
interface SiteNavFlight {
  _fbSiteNavFlight?: Promise<{ items: NavNode[] } | null>
}

export async function useSiteNav() {
  const nav = useState<NavNode[]>('site-main-nav-items', () => [])
  const loaded = useState<boolean>('site-main-nav-loaded', () => false)

  if (loaded.value) return nav

  const nuxtApp = useNuxtApp() as unknown as SiteNavFlight
  nuxtApp._fbSiteNavFlight ??= apiGet<{ items: NavNode[] }>('/system/menu/public/main-nav')

  const data = await nuxtApp._fbSiteNavFlight
  nav.value = data?.items ?? []
  // 失败也标记为已加载（接口 404 是"未配置菜单"的正常情况，不该每次重试）
  loaded.value = true
  return nav
}
