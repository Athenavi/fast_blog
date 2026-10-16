/**
 * 顶部导航数据
 *
 * 数据源：后台「菜单管理」里 slug=main-nav 的菜单项（未配置时为空的数组，调用方回退内置导航）。
 *
 * 与 `useSiteInfo` / `useThemeSlots` 共用同一个聚合引导接口（见 `useSiteBootstrap`）：
 * 此前这里单独打一次 `/system/menu/public/main-nav`，现在整页只有一次请求。
 *
 * 仍抽成 composable 而不是留在 `SiteHeader` 里：布局与组件都读同一份 `useState`，
 * 谁先调用都只发一次请求，也不会因为组件渲染时机不同而重复取数。
 */
import {loadSiteBootstrap, SITE_NAV_KEY} from '@/composables/useSiteBootstrap'

export interface NavNode {
  id: number
  title: string
  url: string
}

export async function useSiteNav() {
  const nav = useState<NavNode[]>(SITE_NAV_KEY, () => [])

  await loadSiteBootstrap()

  return nav
}
