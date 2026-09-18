/**
 * JSON-LD 结构化数据
 *
 * 原 astro 侧是 React 组件（`seo/SchemaJsonLd.tsx`，含 Article/Website/Organization 模板）。
 * 在 Nuxt 里不需要组件——`useHead` 直接注入 `<script type="application/ld+json">` 即可，
 * 服务端渲染时会写进 HTML，爬虫可直接读到。
 *
 * 用法：
 * ```ts
 * useJsonLd('Article', () => ({headline: article.value?.title, ...}))
 * ```
 * 传函数（或 ref/computed）可保持响应式。
 */

type JsonLdType =
  | 'Article'
  | 'AboutPage'
  | 'ContactPage'
  | 'Organization'
  | 'WebSite'
  | 'BreadcrumbList'
  | 'FAQPage'
  | 'Person'

type JsonLdData = Record<string, unknown>

const SCHEMA_CONTEXT = 'https://schema.org'

export function useJsonLd(type: JsonLdType, data: JsonLdData | (() => JsonLdData)) {
  useHead(() => {
    const payload = typeof data === 'function' ? data() : data
    return {
      script: [
        {
          type: 'application/ld+json',
          innerHTML: JSON.stringify({'@context': SCHEMA_CONTEXT, '@type': type, ...payload}),
        },
      ],
    }
  })
}

/** 站点级 WebSite（含站内搜索入口），适合放在首页 */
export function useWebsiteJsonLd(input: { name: string; description?: string; url: string }) {
  useJsonLd('WebSite', () => ({
    name: input.name,
    description: input.description || undefined,
    url: input.url,
    potentialAction: {
      '@type': 'SearchAction',
      target: `${input.url.replace(/\/$/, '')}/search?q={search_term_string}`,
      'query-input': 'required name=search_term_string',
    },
  }))
}

/** 文章级 Article，适合放在文章详情页 */
export function useArticleJsonLd(
  input: {
    headline?: string | null
    description?: string | null
    image?: string | null
    datePublished?: string | null
    dateModified?: string | null
    authorName?: string | null
    url: string
  },
  options?: { keywords?: string[]; section?: string | null },
) {
  useJsonLd('Article', () => ({
    headline: input.headline || undefined,
    description: input.description || undefined,
    image: input.image || undefined,
    datePublished: input.datePublished || undefined,
    dateModified: input.dateModified || input.datePublished || undefined,
    mainEntityOfPage: {'@type': 'WebPage', '@id': input.url},
    author: input.authorName ? {'@type': 'Person', name: input.authorName} : undefined,
    keywords: options?.keywords?.length ? options.keywords.join(', ') : undefined,
    articleSection: options?.section || undefined,
  }))
}

/** 面包屑（与 Breadcrumbs 组件配套） */
export function useBreadcrumbJsonLd(items: Array<{ label: string; to?: string }>, origin: string) {
  useJsonLd('BreadcrumbList', () => ({
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.label,
      item: item.to ? `${origin.replace(/\/$/, '')}${item.to}` : undefined,
    })),
  }))
}
