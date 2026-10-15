/**
 * 站点公开信息（站点名、描述、页脚）
 *
 * 数据来源：**聚合引导接口**（`/__site/bootstrap`，见 `useSiteBootstrap`）。
 * 之前这里自己打一次 `/system/setting/public`，与导航、主题槽位各占一次后端往返；
 * 现在三者合并成一个请求并做服务端缓存，所以本文件只负责"读 `useState` + 兜默认值"。
 *
 * 后端不可用或尚未配置时使用内置默认值，保证标题等位置不出现 `undefined`。
 */
import type {SiteSettings} from '@/types/content'
import {loadSiteBootstrap, SITE_SETTINGS_KEY} from '@/composables/useSiteBootstrap'

const DEFAULTS: Required<Pick<SiteSettings, 'site_name' | 'site_description'>> = {
  site_name: 'FastBlog',
  site_description: '',
}

export async function useSiteInfo() {
  const site = useState<SiteSettings>(SITE_SETTINGS_KEY, () => ({...DEFAULTS}))

  // 先兜一次默认值：首屏（尚未取数）时标题等位置不能是 undefined
  if (!site.value.site_name) {
    site.value = {...DEFAULTS, ...site.value}
  }

  // 整页只发一次请求；已取过（含 SSR 随 payload 下发的那一次）时直接返回
  await loadSiteBootstrap()

  // 取到之后再兜一次：后端没配 site_name 时仍要有可见标题
  if (!site.value.site_name) {
    site.value = {...DEFAULTS, ...site.value}
  }

  return site
}
