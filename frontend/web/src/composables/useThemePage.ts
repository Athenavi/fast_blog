/**
 * 主题页面接管（页面级）
 *
 * 主题可在自己的 frontend/site/ 下提供整页组件（如 ArticlePage.vue），
 * scripts/scan-plugin-frontend.mjs 会把 frontend/** 整体复制到
 * src/.plugin-pages/<slug>/，并自动进入 .plugin-pages/_loader.ts 的
 * import.meta.glob 加载表。所以扫描器无需改动。
 *
 * 这里按当前激活主题（themeSlug，由 bootstrap.get.ts 下发）取对应组件；
 * 取不到返回 null，由调用方回退到内置默认页。
 *
 * 本轮只做页面级接管（用户拍板）：主题能整页接管就已能改前台结构，
 * 这是与 WordPress / Halo 主题能力差距里最关键的一层。区块级留作后续。
 */
import type {Component} from 'vue'

// 与 pages/admin/plugin-pages/[slug].vue 同一来源：~ 指向项目根（src/）。
// 该文件由 scripts/scan-plugin-frontend.mjs 生成（prescan / postinstall 时产出）。
import {pluginPageModules} from '~/.plugin-pages/_loader'
import {THEME_SLUG_KEY} from '@/composables/useSiteBootstrap'

/** 主题页面组件的存放目录（相对 .plugin-pages/<slug>/） */
const THEME_PAGE_DIR = 'site'

/**
 * 解析当前主题提供的页面组件
 *
 * @param pageName 页面名（不带扩展名），如 ArticlePage
 * @returns 组件加载器；当前主题未提供该页面时为 null
 */
export function useThemePage(pageName: string) {
  const themeSlug = useState<string | null>(THEME_SLUG_KEY, () => null)

  return computed<(() => Promise<Component>) | null>(() => {
    const slug = themeSlug.value
    if (!slug) return null
    // key 形如 ./<slug>/site/ArticlePage.vue（相对 _loader.ts 所在目录）
    const key = `./${slug}/${THEME_PAGE_DIR}/${pageName}.vue`
    return pluginPageModules[key] ?? null
  })
}
