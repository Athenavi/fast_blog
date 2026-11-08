/**
 * 文章正文的渲染前处理（纯字符串，SSR 与客户端跑同一段代码）
 *
 * 为什么单独成文件：这三件事都是**版式**决定的，却又必须在 `v-html` 之前做完 ——
 * 标题锚点要出现在 SSR 首屏（否则分享出去的 `#小节` 链接落不了地），
 * 首段的 `.fb-lead` 要写在标签上（CSS 的 `:first-child` 分不清"打头的段落"和
 * "打头的提示块里的段落"）。放在 `.vue` 里就没法脱离页面单独验证，
 * 抽出来之后浏览器与 Node 都能直接调用同一份实现。
 */
import {renderMarkdown} from '@/utils/markdown'

export interface TocHeading {
  id: string
  text: string
  level: number
}

/** 汉字/假名区间（用于 slug 与阅读时长）；用 codePointAt 判区间，不写转义区间 */
export function isCjk(code: number): boolean {
  return (
    (code >= 0x3400 && code <= 0x4dbf) ||
    (code >= 0x4e00 && code <= 0x9fff) ||
    (code >= 0xf900 && code <= 0xfaff) ||
    (code >= 0x3040 && code <= 0x30ff)
  )
}

/** 标题文本 → 锚点 id：中文留在 id 里（可读性优先），其余非字矩阵号折成连字符 */
export function slugify(text: string): string {
  let out = ''
  for (const ch of text.toLowerCase()) {
    const code = ch.codePointAt(0) ?? 0
    out += (/[a-z0-9_-]/.test(ch) || isCjk(code)) ? ch : '-'
  }
  const slug = out.replace(/-+/g, '-').replace(/^-|-$/g, '').slice(0, 40)
  return slug || 'section'
}

/**
 * 给 h2/h3 补 id 并把目录抽出来（按出现顺序）。
 * 已有 id 的标题保持原样 —— 作者手写过的锚点别人可能已经链接过。
 */
function injectHeadingIds(html: string, headings: TocHeading[]): string {
  return html.replace(/<h([23])\b([^>]*)>([\s\S]*?)<\/h\1>/gi, (match, level: string, attrs: string, inner: string) => {
    const text = String(inner)
      .replace(/<[^>]*>/g, '')
      .trim()
    if (!text) return match
    const existing = /\sid="([^"]+)"/.exec(String(attrs))?.[1]
    const id = existing ?? `sec-${headings.length + 1}-${slugify(text)}`
    headings.push({id, text, level: Number(level)})
    return existing ? match : `<h${level}${attrs} id="${id}">${inner}</h${level}>`
  })
}

/**
 * 首段标记：只有**开头第一个元素确实是普通段落、不含图片、够一屏读**时才下沉首字。
 * 封面图或提示块打头时硬套首字，出来的是"半个字符飘在图旁边"。
 */
function markLeadParagraph(html: string): string {
  const first = /^\s*<p\b[^>]*>([\s\S]*?)<\/p>/i.exec(html)
  if (!first) return html
  const inner = String(first[1])
  const text = inner.replace(/<[^>]*>/g, '').replace(/&[^\s;]+;/g, ' ').trim()
  if (/<img\b/i.test(inner) || text.replace(/\s+/g, '').length < 40) return html

  return html.replace(/^(\s*)<p\b([^>]*)>/i, (_all, space: string, attrs: string) => {
    const withClass = /\bclass="([^"]*)"/i.test(attrs)
      ? attrs.replace(/\bclass="([^"]*)"/i, (_m, existing: string) => `class="${`${existing} fb-lead`.trim()}"`)
      : `${attrs} class="fb-lead"`
    return `${space}<p${withClass}>`
  })
}

/** Markdown → 带锚点的正文 HTML + 目录数据 */
export function renderArticleBody(source: string | null | undefined): {html: string; headings: TocHeading[]} {
  const headings: TocHeading[] = []
  const html = markLeadParagraph(injectHeadingIds(renderMarkdown(source), headings))
  return {html, headings}
}

/**
 * 阅读时长（分钟）：汉字按字、西文按词估。
 *
 * 为什么不用后端字段：库里没有 `reading_time`，为一个估算值加一次往返或一列数据不值当；
 * 按"字数 ÷ 速度"估（约 400 字/分、230 词/分）是这类指标的通行做法。
 */
export function estimateReadingMinutes(source: string | null | undefined): number {
  const text = String(source ?? '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/[#*_>~|[\]()`]/g, ' ')
  let cjk = 0
  let words = 0
  let inWord = false
  for (const ch of text) {
    const code = ch.codePointAt(0) ?? 0
    if (isCjk(code)) {
      cjk += 1
      inWord = false
    } else if (/[a-z0-9]/i.test(ch)) {
      if (!inWord) words += 1
      inWord = true
    } else {
      inWord = false
    }
  }
  return Math.max(1, Math.round(cjk / 400 + words / 230))
}
