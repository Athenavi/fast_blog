/**
 * 多语言 hreflang 声明
 *
 * 原 astro 侧是 `seo/HreflangMeta.tsx`。Nuxt 里用 `useHead` 的 `link` 即可，
 * 不需要组件；SSR 时会写进 `<head>`。
 *
 * 用法：
 * ```ts
 * useHreflang([
 *   {lang: 'zh-CN', href: 'https://example.com/articles/foo'},
 *   {lang: 'en', href: 'https://example.com/en/articles/foo'},
 * ])
 * ```
 * 单语言站点可以不调用它——但要保留这个能力，将来做多语言时直接可用。
 */

export interface HreflangEntry {
  /** BCP-47，如 zh-CN / en / x-default */
  lang: string
  href: string
}

export function useHreflang(entries: HreflangEntry[] | (() => HreflangEntry[])) {
  useHead(() => {
    const list = typeof entries === 'function' ? entries() : entries
    return {
      link: list
        .filter((item) => Boolean(item?.lang && item?.href))
        .map((item) => ({
          rel: 'alternate',
          hreflang: item.lang,
          href: item.href,
        })),
    }
  })
}

/**
 * 按当前路径推导多语言地址。
 *
 * 约定：默认语言不带前缀（`/articles/foo`），其它语言带前缀（`/en/articles/foo`）。
 * 后端文章支持 `language_code`，这里只负责生成网址声明。
 */
export function useHreflangByPath(options: {
  languages: string[]
  defaultLang: string
  origin: string
  /** 当前路径，默认取路由 path */
  path?: string
}) {
  const route = useRoute()
  const origin = options.origin.replace(/\/$/, '')

  useHreflang(() => {
    const path = options.path ?? route.path
    const stripped = path.replace(/^\/[a-z]{2}(-[A-Z]{2})?(?=\/|$)/, '') || '/'

    return options.languages.map((lang) => ({
      lang,
      href:
        lang === options.defaultLang
          ? `${origin}${stripped}`
          : `${origin}/${lang}${stripped === '/' ? '' : stripped}`,
    }))
  })
}
