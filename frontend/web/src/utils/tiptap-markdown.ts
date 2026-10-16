/**
 * Tiptap / ProseMirror 文档树 → Markdown
 *
 * ## 为什么是手写而不是装 `@tiptap/markdown`
 *
 * 本项目的编辑器工具栏只暴露固定的那几种能力（标题、粗斜删高亮、列表、任务列表、
 * 引用、提示块、代码块、链接、图片、表格、对齐、撤销重做）。手写一个覆盖这些节点的
 * 序列化器约两百行，**可读、可测、无新依赖**；而引入官方 markdown 扩展会连带
 * 一套自己的解析/序列化约定，出问题时排查面更大。
 *
 * ## 为什么不需要反向解析器
 *
 * 载入方向（Markdown → 文档树）走 **`marked` 转 HTML → `setContent(html)`** ——
 * `marked` 已经是本项目的依赖（`utils/markdown.ts` 在用），Tiptap 本来就吃 HTML。
 * 只需要写"出去"这一个方向。
 *
 * ## 空白处理
 *
 * Markdown 对空行敏感（多一个空行会变成代码块、少一个空行两段会粘起来）。
 * 这里用 `blocks` 数组按块收集、最后用**恰好一个空行**连接，
 * 而不是在遍历时手拼 `\n\n` —— 后者在嵌套结构里极易多出或少掉换行。
 */

/** ProseMirror 节点的最小形状（避免依赖 @tiptap/core 的具体类型） */
interface PMNode {
  type: { name: string }
  content?: PMNode[]
  text?: string
  marks?: Array<{ type: { name: string }; attrs?: Record<string, unknown> }>
  attrs?: Record<string, unknown>
}

/** 行内标记的包装：顺序固定，保证同样的内容每次输出一致 */
const MARK_ORDER = ['bold', 'italic', 'underline', 'strike', 'highlight', 'code', 'link'] as const

function escapeText(text: string): string {
  // 只转义会在行内造成结构歧义、或位于行首会被误认成块的字符
  return text
    .replace(/([\\`*_{}[\]()#+.!|-])/g, '\\$1')
    .replace(/^(\s*)(\d+)\.\s/gm, '$1$2\\. ')
}

/** 行内内容 → Markdown 文本 */
function inline(nodes: PMNode[] | undefined): string {
  if (!nodes?.length) return ''

  return nodes
    .map(node => {
      if (node.type.name === 'hardBreak') return '  \n'
      if (node.type.name !== 'text') {
        // 行内出现的其他节点（如 mention）退化为其文本内容，不丢字
        return inline(node.content)
      }

      let out = escapeText(node.text ?? '')
      const marks = node.marks ?? []

      // 按固定顺序包装，避免 mark 的遍历顺序影响输出
      for (const name of [...MARK_ORDER].reverse()) {
        const mark = marks.find(m => m.type.name === name)
        if (!mark) continue
        switch (name) {
          case 'bold':
            out = `**${out}**`
            break
          case 'italic':
            out = `*${out}*`
            break
          case 'underline':
            // Markdown 本身没有下划线；用 HTML 保留语义（预览端会渲染）
            out = `<u>${out}</u>`
            break
          case 'strike':
            out = `~~${out}~~`
            break
          case 'highlight':
            out = `==${out}==`
            break
          case 'code':
            out = `\`${out}\``
            break
          case 'link': {
            const href = String(mark.attrs?.href ?? '')
            out = href ? `[${out}](${href})` : out
            break
          }
        }
      }
      return out
    })
    .join('')
}

/** 列表项内容（去掉最外层 p 的多余换行） */
function listItemContent(node: PMNode, indent: string, marker: string): string {
  const body = (node.content ?? [])
    .map(child => block(child, indent + '  '))
    .join('\n')
    .trimEnd()
  return `${indent}${marker} ${body}`
}

function tableToMarkdown(node: PMNode, indent: string): string {
  const rows = (node.content ?? []).filter(r => r.type.name === 'tableRow')
  if (!rows.length) return ''

  const cells = rows.map(row =>
    (row.content ?? []).map(cell => inline(cell.content?.[0]?.content ?? cell.content).replace(/\|/g, '\\|')),
  )

  const header = cells[0] ?? []
  const lines = [
    `${indent}| ${header.join(' | ')} |`,
    `${indent}| ${header.map(() => '---').join(' | ')} |`,
    ...cells.slice(1).map(row => `${indent}| ${row.join(' | ')} |`),
  ]
  return lines.join('\n')
}

/** 块级节点 → Markdown（`indent` 用于列表嵌套） */
function block(node: PMNode, indent = ''): string {
  const text = inline(node.content)
  const alignOf = (n: PMNode): string => String(n.attrs?.textAlign ?? '')

  switch (node.type.name) {
    case 'paragraph': {
      const align = alignOf(node)
      const body = text.trim() ? text : ''
      // 只有非左对齐时才写 HTML —— 纯 Markdown 无法表达对齐
      return body && align && align !== 'left'
        ? `${indent}<p align="${align}">${body}</p>`
        : `${indent}${body}`
    }

    case 'heading': {
      const level = Number(node.attrs?.level ?? 1)
      return `${indent}${'#'.repeat(Math.min(Math.max(level, 1), 6))} ${text}`
    }

    case 'bulletList':
      return (node.content ?? [])
        .map(li => listItemContent(li, indent, '-'))
        .join('\n')

    case 'orderedList': {
      const start = Number(node.attrs?.start ?? 1)
      return (node.content ?? [])
        .map((li, i) => listItemContent(li, indent, `${start + i}.`))
        .join('\n')
    }

    case 'taskList':
      return (node.content ?? [])
        .map(li => {
          const checked = Boolean(li.attrs?.checked)
          return listItemContent(li, indent, `- [${checked ? 'x' : ' '}]`)
        })
        .join('\n')

    case 'blockquote': {
      const inner = (node.content ?? []).map(child => block(child, '')).join('\n\n')
      return inner
        .split('\n')
        .map(line => `${indent}> ${line}`.trimEnd())
        .join('\n')
    }

    case 'codeBlock': {
      const lang = String(node.attrs?.language ?? '')
      const code = (node.content ?? []).map(c => c.text ?? '').join('')
      return `${indent}\`\`\`${lang}\n${code}\n${indent}\`\`\``
    }

    case 'image': {
      const src = String(node.attrs?.src ?? '')
      const alt = String(node.attrs?.alt ?? '')
      const title = node.attrs?.title ? ` "${String(node.attrs.title)}"` : ''
      return src ? `${indent}![${alt}](${src}${title})` : ''
    }

    case 'horizontalRule':
      return `${indent}---`

    case 'table':
      return tableToMarkdown(node, indent)

    case 'details':
      // 提示块用 HTML 保留结构（Markdown 扩展语法各家不一，HTML 更稳）
      return `${indent}<details>\n${(node.content ?? []).map(c => block(c, indent)).join('\n')}\n${indent}</details>`

    case 'hardBreak':
      return `${indent}`

    default:
      // 未知块：保留其文本，宁可降级也不丢内容
      return text ? `${indent}${text}` : ''
  }
}

/**
 * 文档树 → Markdown 文本。
 *
 * 空文档返回空串（调用方据此显示占位），而不是一层层空块拼出来的空白。
 */
export function serializeMarkdown(doc: PMNode | null | undefined): string {
  if (!doc?.content?.length) return ''

  const blocks = doc.content
    .map(node => block(node))
    .map(chunk => chunk.trimEnd())
    .filter(chunk => chunk.length > 0)

  return blocks.join('\n\n')
}
