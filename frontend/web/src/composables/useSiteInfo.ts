/**
 * 站点公开信息（站点名、描述、页脚）
 *
 * 用 `useState` 做请求内缓存：SSR 一次取好后随 payload 传给客户端，
 * 避免每个页面重复请求同一份设置。
 *
 * 后端不可用或尚未配置时使用内置默认值，保证标题等位置不出现 `undefined`。
 */
import type {SiteSettings} from '@/types/content'

const DEFAULTS: Required<Pick<SiteSettings, 'site_name' | 'site_description'>> = {
  site_name: 'FastBlog',
  site_description: '一个基于 FastAPI 与 Nuxt 的博客',
}

export async function useSiteInfo() {
  const site = useState<SiteSettings>('site-settings', () => ({...DEFAULTS}))
  if (!site.value.site_name) {
    site.value = {...DEFAULTS, ...site.value}
  }
  const data = await apiGet<SiteSettings>('/system/setting/public')
  if (data) {
    site.value = {...site.value, ...data}
  }
  return site
}
