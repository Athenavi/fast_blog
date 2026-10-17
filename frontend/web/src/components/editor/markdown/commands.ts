/**
 * Markdown 源码编辑命令（CodeMirror 6）
 *
 * 全部写成 CodeMirror 的 `Command`：`(view) => boolean`，返回 false 表示「这个键我不管」，
 * CodeMirror 会继续往下找别的绑定。
 *
 * ## 为什么命令直接改文本，而不是改文档树再序列化
 *
 * 上一版编辑器（Tiptap）存的是 ProseMirror 文档树，落盘前要走一次
 * `serializeMarkdown(JSON)`。那条链上每一环都可能不忠实 —— 高亮、对齐、任务列表
 * 各自要有对应的 Markdown 规范，缺一个就把标记当普通文字留下，或者干脆丢掉。
 * 这里改的就是正文本身，**没有序列化这一步，所以没有这一类 bug**；
 * 粘贴同理：粘进来的是文本，文本就是正文，不再有「粘贴 Markdown 变成字面序号」那个问题。
 *
 * ## 为什么命令与 UI 分开
 *
 * 键盘（本切片）、选区气泡菜单与「+」块菜单（下一切片）要调同一批动作。
 * 分两处各写一遍插入字符串，早晚一处加粗用 `**`、另一处用 `__`。
 */
import {EditorSelection} from '@codemirror/state'
import type {ChangeSpec, EditorState, SelectionRange} from '@codemirror/state'
import type {Command, EditorView, KeyBinding} from '@codemirror/view'

/**
 * 成对标记：`**粗**`、`*斜*`、`~~删~~`、`` `码` ``。
 *
 * 三种情形都要覆盖，缺一种就会出现「按了没反应」或「越按越多」：
 *  1. 选区**外侧**已经是这对标记 → 摘掉；
 *  2. 选区**自身**带着这对标记（双击选中词时常见）→ 摘掉；
 *  3. 其余（含空选区）→ 加上，空选区时把光标停在两个标记之间。
 */
export function toggleWrap(open: string, close: string = open): Command {
  return (view) => {
    const {state} = view
    const specs: ChangeSpec[] = []
    const ranges: SelectionRange[] = []
    /** 已处理过的改动带来的净长度位移：选区坐标要换算到**新文档** */
    let shift = 0

    /**
     * 跨行的选区**按行**加标记，而不是整段包起来。
     *
     * `~~第一段\n\n第二段~~` 在 Markdown 里不是删除线：块级边界会把这对符号留在原地
     * 变成残渣，屏幕上就是两串字面的 `~~`。按行走与列表、引用这些行级命令同一口径，
     * 也顺便让「全选整篇再按加粗」不会毁掉文档结构。
     */
    for (const range of state.selection.ranges) {
      for (const span of wrapSpans(state, range)) {
        const {from, to} = span
        const inner = state.sliceDoc(from, to)
        const outerOpen = state.sliceDoc(Math.max(0, from - open.length), from)
        const outerClose = state.sliceDoc(to, Math.min(state.doc.length, to + close.length))

        // 单字符标记必须真是「单独一个」：`**粗**` 里切斜体时外侧那一个 `*` 属于 `**` 的一部分，
        // 把它当斜体标记摘掉会得到 `*粗*`，等于把粗体悄悄改了。
        const adjacent =
          open.length === 1 &&
          (state.sliceDoc(Math.max(0, from - 2), from - 1) === open ||
            state.sliceDoc(to + close.length, to + close.length + 1) === open)
        const wrappedOutside = outerOpen === open && outerClose === close && !adjacent

        if (wrappedOutside) {
          specs.push({from: from - open.length, to: from}, {from: to, to: to + close.length})
          ranges.push(EditorSelection.range(from - open.length + shift, to - open.length + shift))
          shift -= open.length + close.length
          continue
        }

        if (
          inner.length >= open.length + close.length &&
          inner.startsWith(open) &&
          inner.endsWith(close)
        ) {
          const body = inner.slice(open.length, inner.length - close.length)
          specs.push({from, to, insert: body})
          ranges.push(EditorSelection.range(from + shift, from + body.length + shift))
          shift -= open.length + close.length
          continue
        }

        if (from === to) {
          specs.push({from, insert: open + close})
          ranges.push(EditorSelection.cursor(from + open.length + shift))
          shift += open.length + close.length
          continue
        }

        specs.push({from, insert: open}, {from: to, insert: close})
        ranges.push(
          EditorSelection.range(from + open.length + shift, to + open.length + close.length + shift),
        )
        shift += open.length + close.length
      }
    }

    // `create` 会排序并合并重叠的选区：多光标落在同一处时，合并正是我们要的
    view.dispatch({changes: specs, selection: EditorSelection.create(ranges, 0), scrollIntoView: true})
    return true
  }
}

/** 一个选区里要分别加标记的片段：单行就是选区本身，跨行则逐行切开（空行跳过） */
function wrapSpans(state: EditorState, range: SelectionRange): Array<{from: number; to: number}> {
  const first = state.doc.lineAt(range.from).number
  const last = state.doc.lineAt(range.to).number
  if (first === last) return [{from: range.from, to: range.to}]

  const spans: Array<{from: number; to: number}> = []
  for (let number = first; number <= last; number++) {
    const line = state.doc.line(number)
    const from = number === first ? range.from : line.from
    const to = number === last ? range.to : line.to
    if (to > from) spans.push({from, to})
  }
  return spans
}

/** 选区覆盖到的行号，去重升序（多光标重叠时同一行只处理一次） */
function selectedLines(view: EditorView): number[] {
  const {state} = view
  const numbers = new Set<number>()
  for (const range of state.selection.ranges) {
    const first = state.doc.lineAt(range.from).number
    const last = state.doc.lineAt(range.to).number
    for (let n = first; n <= last; n++) numbers.add(n)
  }
  return [...numbers].sort((a, b) => a - b)
}

/**
 * 换行首标记。
 *
 * 语义是「设定」而不是「异或」：`## ` 上按 H1 得到 `# `，而不是把 `## ` 删掉。
 * 只有当前已经是目标标记时才清除 —— 这样列表、引用、标题的按钮才像按钮（按下去变、再按取消），
 * 而不是在三种状态之间循环（循环会让用户以为卡住了）。
 *
 * `resolve` 收到该行的文本与它在选区里的序号，序号是给有序列表编号用的。
 */
function toggleLinePrefix(
  view: EditorView,
  resolve: (lineText: string, index: number) => {prefix: string; strip: RegExp},
): boolean {
  const {state} = view
  const numbers = selectedLines(view)
  if (!numbers.length) return false

  const specs: ChangeSpec[] = []
  numbers.forEach((number, index) => {
    const line = state.doc.line(number)
    const {prefix, strip} = resolve(line.text, index)
    if (line.text.startsWith(prefix)) {
      specs.push({from: line.from, to: line.from + prefix.length})
      return
    }
    const existing = strip.exec(line.text)?.[0].length ?? 0
    specs.push({from: line.from, to: line.from + existing, insert: prefix})
  })

  view.dispatch({changes: specs, scrollIntoView: true})
  return true
}

/** 行首已有的 ATX 标题标记（`### `） */
const ATX_MARK = /^ {0,3}#{1,6} /
/** 行首已有的列表标记（无序、有序、任务） */
const LIST_MARK = /^ {0,3}(?:[-*+] \[[ xX]\] |[-*+] |\d{1,9}[.)] )/
/** 行首已有的引用标记（`> `） */
const QUOTE_MARK = /^ {0,3}> /

export function setHeading(level: 1 | 2 | 3 | 4 | 5 | 6): Command {
  const prefix = `${'#'.repeat(level)} `
  return (view) => toggleLinePrefix(view, () => ({prefix, strip: ATX_MARK}))
}

export function toggleList(kind: 'bullet' | 'ordered' | 'task'): Command {
  return (view) =>
    toggleLinePrefix(view, (lineText, index) => {
      if (kind === 'ordered') return {prefix: `${index + 1}. `, strip: LIST_MARK}
      if (kind === 'task')
        return {
          // 已经是任务项时只留 `- `，让「任务列表」按钮能退回到普通无序列表
          prefix: lineText.includes('[ ]') || lineText.includes('[x]') ? '- ' : '- [ ] ',
          strip: LIST_MARK,
        }
      return {prefix: '- ', strip: LIST_MARK}
    })
}

export function toggleQuote(): Command {
  return (view) => toggleLinePrefix(view, () => ({prefix: '> ', strip: QUOTE_MARK}))
}

/**
 * 围栏代码块。
 *
 * 判断「已经在围栏里」用的是**选区上下相邻的两行**是不是 ``` —— 而不是全文扫一遍配对：
 * 后者要把整篇重算一次状态机（`utils/content.ts` 里那种），为一个开关动作不值得，
 * 而且嵌套围栏（围栏里演示围栏）本来就配不准。
 */
export function toggleCodeFence(): Command {
  return (view) => {
    const {state} = view
    const {from, to} = state.selection.main
    const first = state.doc.lineAt(from)
    const last = state.doc.lineAt(to)
    const prev = first.number > 1 ? state.doc.line(first.number - 1) : null
    const next = last.number < state.doc.lines ? state.doc.line(last.number + 1) : null
    const fenced = /^ {0,3}```/

    if (prev && next && fenced.test(prev.text) && fenced.test(next.text)) {
      view.dispatch({
        changes: [
          {from: prev.from, to: first.from},
          {from: last.to, to: Math.min(state.doc.length, next.to + 1)},
        ],
        scrollIntoView: true,
      })
      return true
    }

    const open = '```\n'
    view.dispatch({
      changes: [{from: first.from, insert: open}, {from: last.to, insert: '\n```'}],
      selection: EditorSelection.range(from + open.length, to + open.length),
      scrollIntoView: true,
    })
    return true
  }
}

/**
 * 链接骨架：`[文字](url)`。
 *
 * 不弹窗、不假定 URL 从哪来 —— 三种起点都把光标停在**待填的那一段**上：
 * 选中一个网址 → 光标停在方括号里补锚文本；选中文字 → 光标停在圆括号里补网址；
 * 空选区 → 光标停在方括号里。真正的链接输入条在下一切片的选区菜单里。
 */
export function wrapLink(): Command {
  return (view) => {
    const {state} = view
    const specs: ChangeSpec[] = []
    const ranges: SelectionRange[] = []
    let shift = 0

    for (const range of state.selection.ranges) {
      const text = state.sliceDoc(range.from, range.to)
      const asUrl = /^https?:\/\/\S+$/i.test(text)
      const insert = asUrl ? `[](${text})` : `[${text}]()`
      const caretAt = asUrl ? range.from + 1 : range.from + 1 + text.length + 2
      specs.push({from: range.from, to: range.to, insert})
      ranges.push(EditorSelection.cursor(caretAt + shift))
      shift += insert.length - (range.to - range.from)
    }

    view.dispatch({changes: specs, selection: EditorSelection.create(ranges, 0), scrollIntoView: true})
    return true
  }
}

/**
 * 快捷键表。
 *
 * 与上一版工具栏的键位**尽量对齐**（`Ctrl+Alt+1..3` 标题、`Ctrl+Shift+8/7` 列表、
 * `Ctrl+Shift+B` 引用、`Ctrl+Alt+C` 代码块），老用户的手感不用重学；
 * 上一版里 Markdown 没有对应物的「下划线 / 高亮 / 对齐」三组直接不保留 ——
 * 留一个按了没反应的键比删掉它更糟。
 */
export const MARKDOWN_KEYMAP: KeyBinding[] = [
  {key: 'Mod-b', run: toggleWrap('**')},
  {key: 'Mod-i', run: toggleWrap('*')},
  {key: 'Mod-Shift-s', run: toggleWrap('~~')},
  {key: 'Mod-Shift-c', run: toggleWrap('`')},
  {key: 'Mod-Alt-c', run: toggleCodeFence()},
  {key: 'Mod-k', run: wrapLink()},
  {key: 'Mod-Alt-1', run: setHeading(1)},
  {key: 'Mod-Alt-2', run: setHeading(2)},
  {key: 'Mod-Alt-3', run: setHeading(3)},
  {key: 'Mod-Shift-8', run: toggleList('bullet')},
  {key: 'Mod-Shift-7', run: toggleList('ordered')},
  {key: 'Mod-Shift-9', run: toggleList('task')},
  {key: 'Mod-Shift-b', run: toggleQuote()},
]
