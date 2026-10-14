/**
 * 站点公开信息（站点名、描述、页脚）
 *
 * **请求内单飞 + 一次取完**：
 *  - `useState` 承载结果，SSR 取好后随 payload 传给客户端，客户端水合不再请求；
 *  - `loaded` 标记"已经取过"，同一请求内第二次调用直接复用（原先每次都重新 `await`
 *    一次接口 —— 而 `layouts/default.vue` 与页面各自调用一次，等于每页白打一次
 *    `/system/setting/public`，且串在关键路径上）；
 *  - 进行中的 Promise 挂在 `nuxtApp` 上做单飞。**刻意不用模块级变量**：SSR 下
 *    `nuxtApp` 是每请求一个实例，模块级变量会把某个请求（乃至某个用户）的结果
 *    泄漏给其他请求。
 *
 * 后端不可用或尚未配置时使用内置默认值，保证标题等位置不出现 `undefined`。
 */
import type {SiteSettings} from '@/types/content'

const DEFAULTS: Required<Pick<SiteSettings, 'site_name' | 'site_description'>> = {
  site_name: 'FastBlog',
  site_description: '',
}

/** 单飞挂载点（挂在 NuxtApp 实例上，随请求生命周期存亡） */
interface SiteInfoFlight {
  _fbSiteInfoFlight?: Promise<SiteSettings | null>
}

export async function useSiteInfo() {
  const site = useState<SiteSettings>('site-settings', () => ({...DEFAULTS}))
  const loaded = useState<boolean>('site-settings-loaded', () => false)

  if (!site.value.site_name) {
    site.value = {...DEFAULTS, ...site.value}
  }

  // 已经取过（含 SSR 随 payload 下发的那一次）→ 直接复用，不再打接口
  if (loaded.value) return site

  const nuxtApp = useNuxtApp() as unknown as SiteInfoFlight
  nuxtApp._fbSiteInfoFlight ??= apiGet<SiteSettings>('/system/setting/public')

  const data = await nuxtApp._fbSiteInfoFlight
  if (data) {
    site.value = {...site.value, ...data}
  }
  // 失败也标记为已加载，避免每次调用都重试（与 useThemeSlots 的约定一致）
  loaded.value = true
  return site
}
