/**
 * 编辑器状态的只读探针
 *
 * ## 为什么判定只写在这一份里
 *
 * 命令（`commands.ts`）要问「这片选区是不是已经加粗了」来决定是加还是摘，
 * 浮层菜单（`blocks.ts` + 两个菜单组件）要问同一个问题来决定按钮亮不亮。
 * 两边各写一遍迟早漂 —— 表现出来是「按钮亮着，按下去却又套了一层 `**`」，
 * 或者反过来「看着没加粗，按下去把标记摘了」。所以这里只判定一次，两边都读它。
 *
 * ## 为什么全是纯函数、只吃 `EditorState`
 *
 * 不碰 DOM、不碰 `EditorView`：这样组件里可以在任意时刻（渲染前、菜单打开前）
 * 问状态，而不必把 CodeMirror 的视图对象递来递去。位置测量那种要读屏幕坐标的事
 * 留在组件里，因为只有那儿才知道宿主元素的矩形。
 */
import type {EditorState, SelectionRange} from '@codemirror/state'

/** 一对标记相对选区的状态：`outside` = 选区外面正包着它，`inside` = 选区自己就是它 */
export type WrapState = 'outside' | 'inside' | 'none'

export interface Span {
  from: number
  to: number
}

/**
 * 一个选区里要分别处理标记的片段：单行就是选区本身，跨行则逐行切开（空行跳过）。
 *
 * 行内标记必须**按行**加：`~~第一段\n\n第二段~~` 在 Markdown 里不是删除线，块级边界
 * 会把这对符号留在原地变成字面残渣。
 */
export function wrapSpans(state: EditorState, range: SelectionRange): Span[] {
  const first = state.doc.lineAt(range.from).number
  const last = state.doc.lineAt(range.to).number
  if (first === last) return [{from: range.from, to: range.to}]

  const spans: Span[] = []
  for (let number = first; number <= last; number++) {
    const line = state.doc.line(number)
    const from = number === first ? range.from : line.from
    const to = number === last ? range.to : line.to
    if (to > from) spans.push({from, to})
  }
  return spans
}

/** 所有选区展开成的片段（多光标 + 跨行都在这儿摊平） */
export function selectedSpans(state: EditorState): Span[] {
  return state.selection.ranges.flatMap((range) => wrapSpans(state, range))
}

/** 行首已有的 ATX 标题标记（`### `） */
export const ATX_MARK = /^ {0,3}#{1,6} /
/** 行首已有的列表标记（无序、有序、任务） */
export const LIST_MARK = /^ {0,3}(?:[-*+] \[[ xX]\] |[-*+] |\d{1,9}[.)] )/
/** 行首已有的引用标记（`> `） */
export const QUOTE_MARK = /^ {0,3}> ?/
/** 任何一种行首标记 —— 「还原成正文」要剥掉的就是它 */
export const ANY_MARK = /^ {0,3}(?:#{1,6} |[-*+] \[[ xX]\] |[-*+] |\d{1,9}[.)] |> ?)/
/** 围栏那一行 */
export const FENCE_MARK = /^ {0,3}```/

/**
 * 选区与这对标记的关系。
 *
 * 单字符标记要额外确认它是「单独一个」：`**粗**` 里切斜体时，外侧那一个 `*` 属于 `**`
 * 的一部分，把它当斜体标记摘掉会得到 `*粗*` —— 等于把粗体悄悄改了。
 * **内外两侧都要查**：选区正好包住整条 `**粗**` 时命中的是 `inside` 分支，
 * 只看邻居字符拦不住，斜体那颗按钮会在粗体上误亮。
 */
export function wrapState(
  state: EditorState,
  from: number,
  to: number,
  open: string,
  close: string = open,
): WrapState {
  if (from === to) return 'none'
  const inner = state.sliceDoc(from, to)
  const outerOpen = state.sliceDoc(Math.max(0, from - open.length), from)
  const outerClose = state.sliceDoc(to, Math.min(state.doc.length, to + close.length))

  const adjacent =
    open.length === 1 &&
    (state.sliceDoc(Math.max(0, from - 2), from - 1) === open ||
      state.sliceDoc(to + close.length, to + close.length + 1) === open ||
      inner.startsWith(open + open) ||
      inner.endsWith(open + open))

  if (outerOpen === open && outerClose === close && !adjacent) return 'outside'
  if (
    !adjacent &&
    inner.length >= open.length + close.length &&
    inner.startsWith(open) &&
    inner.endsWith(close)
  )
    return 'inside'
  return 'none'
}

/** 当前选（几）区是不是都已经带着这对标记 —— 气泡菜单用它决定按钮亮不亮 */
export function isMarkActive(state: EditorState, open: string, close: string = open): boolean {
  const spans = selectedSpans(state)
  if (!spans.length) return false
  return spans.every(
    (span) => span.from < span.to && wrapState(state, span.from, span.to, open, close) !== 'none',
  )
}

/** 选区覆盖到的行号，去重升序（多光标重叠时同一行只处理一次） */
export function selectedLines(state: EditorState): number[] {
  const numbers = new Set<number>()
  for (const range of state.selection.ranges) {
    const first = state.doc.lineAt(range.from).number
    const last = state.doc.lineAt(range.to).number
    for (let n = first; n <= last; n++) numbers.add(n)
  }
  return [...numbers].sort((a, b) => a - b)
}

/** 选中行**全部**满足这个行首形状，才算「已经是这种块」 */
export function linesMatch(state: EditorState, test: RegExp): boolean {
  const numbers = selectedLines(state)
  if (!numbers.length) return false
  return numbers.every((number) => test.test(state.doc.line(number).text))
}

/** 选中行有没有任何一种行首标记 —— 决定「正文」这一项亮不亮 */
export function linesArePlain(state: EditorState): boolean {
  const numbers = selectedLines(state)
  if (!numbers.length) return false
  return numbers.every((number) => !ANY_MARK.test(state.doc.line(number).text))
}

/** 光标/选区是不是正好被一对围栏包着（与 `toggleCodeFence` 同一判据） */
export function isInCodeFence(state: EditorState): boolean {
  const {from, to} = state.selection.main
  const first = state.doc.lineAt(from)
  const last = state.doc.lineAt(to)
  const prev = first.number > 1 ? state.doc.line(first.number - 1) : null
  const next = last.number < state.doc.lines ? state.doc.line(last.number + 1) : null
  return Boolean(prev && next && FENCE_MARK.test(prev.text) && FENCE_MARK.test(next.text))
}

/** 一条已写好的链接 / 图片 */
export interface LinkSpan extends Span {
  /** 锚文本（图片则是 alt） */
  label: string
  url: string
  /** `url` 这一段在文档里的区间 —— 改地址时只替换它，不动锚文本 */
  urlFrom: number
  urlTo: number
  image: boolean
}

const LINK_RE = /(!?)\[([^\]]*)\]\(([^)]*)\)/g

/**
 * 选区落在一整条 `[文字](地址)` 里时把它找出来，否则 null。
 *
 * 只看**起点所在那一行**：跨行的链接不是合法 Markdown（空行会截断），为它写状态机没有意义。
 * 链接条（气泡菜单里那个输入框）靠它决定要不要把现有地址回填进去。
 */
export function linkAt(state: EditorState, from: number, to: number): LinkSpan | null {
  const line = state.doc.lineAt(from)
  for (const match of line.text.matchAll(LINK_RE)) {
    const mark = match[1] ?? ''
    const label = match[2] ?? ''
    const url = match[3] ?? ''
    const whole = match[0]
    const start = line.from + match.index
    const end = start + whole.length
    if (end < from || start > to) continue
    const urlFrom = start + mark.length + label.length + 3
    return {
      from: start,
      to: end,
      label,
      url,
      urlFrom,
      urlTo: urlFrom + url.length,
      image: mark === '!',
    }
  }
  return null
}

/** 斜杠菜单的触发点：`from..to` 就是待删除的 `/关键词` */
export interface SlashTrigger {
  from: number
  to: number
  query: string
}

/**
 * 光标前是不是正写着 `/关键词`。
 *
 * 要求 `/` 前面是行首或空白，这样「男/女」「50%/年」这些正文里的斜杠不会被当成命令 ——
 * 中文正文里斜杠紧贴在字后头，很常见。关键词最长 24 个非空白字符，超了就不该再弹菜单。
 */
export function slashTrigger(state: EditorState, pos: number): SlashTrigger | null {
  const line = state.doc.lineAt(pos)
  const upto = line.text.slice(0, pos - line.from)
  const match = /(?:^|\s)\/(\S{0,24})$/.exec(upto)
  if (!match) return null
  const query = match[1] ?? ''
  return {from: pos - query.length - 1, to: pos, query}
}
