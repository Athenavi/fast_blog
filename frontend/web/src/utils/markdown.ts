/**
 * Markdown 渲染出口（前端唯一）
 *
 * ## 为什么需要这个文件
 *
 * 前端此前**没有任何 markdown 渲染能力**：`package.json` 里有 `marked` 依赖，
 * 却没有任何地方封装它。这导致两个真实问题：
 *   1. **文章详情页的 markdown 正文渲染不出来**（用户报过）；
 *   2. **协作编辑需要"边写边看"**，没有渲染器就只能退化成记事本。
 *
 * 所以这里建立**唯一出口**。所有要用 markdown 的地方都走它 —— 不是风格洁癖：
 * 渲染 + 净化是**安全边界**，分散成多份实现，其中一份出问题时其余几份还在跑。
 *
 * ## 净化为什么是必须的
 *
 * 协作场景里，输入可能来自**免登录的外部协作者**，而渲染结果要经过 `v-html`。
 * 没有净化，一个 `<img onerror=...>` 就能在所有者（已登录、有管理权限）的
 * 浏览器里执行脚本。这里做的是**白名单**过滤，不是黑名单——黑名单永远漏。
 */

import {marked} from 'marked'

/** 允许保留的标签：markdown 常用子集 + 常见排版标签 */
const ALLOWED_TAGS = new Set([
  'p', 'br', 'hr', 'strong', 'em', 'del', 'code', 'pre', 'blockquote',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'ul', 'ol', 'li', 'a', 'img',
  'table', 'thead', 'tbody', 'tr', 'th', 'td',
  'span', 'div', 'sup', 'sub', 'kbd',
])

/** 允许保留的属性 */
const ALLOWED_ATTRS = new Set([
  'href', 'title', 'alt', 'src', 'class', 'id',
  'colspan', 'rowspan', 'align',
])

/** 只允许这些协议 —— `javascript:` / `data:` 一律剥掉 */
const SAFE_URL = /^(https?:|mailto:|tel:|#|\/)/i

marked.setOptions({
  gfm: true,          // 表格、任务列表、删除线
  breaks: true,       // 单个换行即 <br>：与技术文档的书写习惯一致
})

/**
 * 把 HTML 字符串按白名单清洗。
 *
 * 用 `DOMParser` 解析（**不是**正则）——正则在 HTML 上的边界情况无穷无尽，
 * 而浏览器自己的解析器才是权威。解析后遍历元素树、剥掉不在白名单里的节点与属性。
 */
function sanitize(html: string): string {
  // SSR 阶段没有 DOMParser：此时不渲染富文本，返回转义后的纯文本更安全
  if (typeof window === 'undefined' || typeof DOMParser === 'undefined') {
    return html.replace(/[<>&]/g, ch => ({'<': '&lt;', '>': '&gt;', '&': '&amp;'}[ch] ?? ch))
  }

  const doc = new DOMParser().parseFromString(`<div>${html}</div>`, 'text/html')
  const root = doc.body.firstElementChild
  if (!root) return ''

  const walk = (node: Element): void => {
    // 先收集再处理：直接边遍历边删会让 children 实时变化
    for (const child of Array.from(node.children)) {
      const tag = child.tagName.toLowerCase()

      if (!ALLOWED_TAGS.has(tag)) {
        // 不在白名单：**保留文字、丢掉标签**（直接删元素会静默吞掉用户内容）
        child.replaceWith(...Array.from(child.childNodes))
        continue
      }

      for (const attr of Array.from(child.attributes)) {
        const name = attr.name.toLowerCase()
        const value = attr.value

        if (!ALLOWED_ATTRS.has(name)) {
          child.removeAttribute(attr.name)
          continue
        }

        // URL 类属性逐个校验协议
        if ((name === 'href' || name === 'src') && !SAFE_URL.test(value.trim())) {
          child.removeAttribute(attr.name)
        }
      }

      // 外链统一加 rel，避免反向标签劫持（`window.opener`）
      if (tag === 'a' && child.getAttribute('href')) {
        child.setAttribute('rel', 'noopener noreferrer nofollow')
      }

      walk(child)
    }
  }

  walk(root)
  return root.innerHTML
}

/**
 * Markdown → 安全 HTML。
 *
 * 空输入返回**空串**（调用方据此显示占位），而不是 `<p></p>` 这种空壳。
 */
export function renderMarkdown(source: string | null | undefined): string {
  const text = (source ?? '').trim()
  if (!text) return ''

  const raw = marked.parse(text, {async: false}) as string
  return sanitize(raw)
}
