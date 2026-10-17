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
 * ## 命令与 UI 的分工
 *
 * 键盘、选区气泡菜单、「+」与「/」块菜单要调同一批动作，所以动作全在这里；
 * 「现在是不是已经是加粗 / 已经是列表」这类**判定**在 `state.ts`，菜单和命令共读一份。
 * 分两处各写一遍插入字符串，早晚一处加粗用 `**`、另一处用 `__`。
 */
import {EditorSelection} from '@codemirror/state'
import type {ChangeSpec, EditorState, SelectionRange} from '@codemirror/state'
import type {Command, EditorView, KeyBinding} from '@codemirror/view'

import {
  ANY_MARK,
  ATX_MARK,
  FENCE_MARK,
  LIST_MARK,
  QUOTE_MARK,
  linkAt,
  selectedLines,
  wrapSpans,
  wrapState,
} from './state'

/**
 * 成对标记：`**粗**`、`*斜*`、`~~删~~`、`` `码` ``。
 *
 * 三种情形都要覆盖，缺一种就会出现「按了没反应」或「越按越多」：
 *  1. 选区**外侧**已经是这对标记 → 摘掉；
 *  2. 选区**自身**带着这对标记（双击选中词时常见）→ 摘掉；
 *  3. 其余（含空选区）→ 加上，空选区时把光标停在两个标记之间。
 *
 * 跨行的选区**按行**分别处理（`state.ts` 的 `wrapSpans`），空行跳过。
 */
export function toggleWrap(open: string, close: string = open): Command {
  return (view) => {
    const {state} = view
    const specs: ChangeSpec[] = []
    const ranges: SelectionRange[] = []
    /** 已处理过的改动带来的净长度位移：选区坐标要换算到**新文档** */
    let shift = 0

    for (const range of state.selection.ranges) {
      for (const span of wrapSpans(state, range)) {
        const {from, to} = span
        const kind = wrapState(state, from, to, open, close)

        if (kind === 'outside') {
          specs.push({from: from - open.length, to: from}, {from: to, to: to + close.length})
          ranges.push(EditorSelection.range(from - open.length + shift, to - open.length + shift))
          shift -= open.length + close.length
          continue
        }

        if (kind === 'inside') {
          const inner = state.sliceDoc(from, to)
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
        // 结尾只加 `open.length`：闭合标记插在 `to` **之后**，不会把选区末端推过去。
        // 这里多算一次 close.length 会让选区停在 `**粗**` 的右半边之外，
        // `wrapState` 于是判成 'none'，气泡里那颗按钮永远不会亮。
        ranges.push(EditorSelection.range(from + open.length + shift, to + open.length + shift))
        shift += open.length + close.length
      }
    }

    // `create` 会排序并合并重叠的选区：多光标落在同一处时，合并正是我们要的
    view.dispatch({
      changes: specs,
      selection: EditorSelection.create(ranges, 0),
      scrollIntoView: true,
    })
    return true
  }
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
  state: EditorState,
  resolve: (lineText: string, index: number) => {prefix: string; strip: RegExp},
): boolean {
  const numbers = selectedLines(state)
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

export function setHeading(level: 1 | 2 | 3 | 4 | 5 | 6): Command {
  const prefix = `${'#'.repeat(level)} `
  return (view) => toggleLinePrefix(view, view.state, () => ({prefix, strip: ATX_MARK}))
}

export function toggleList(kind: 'bullet' | 'ordered' | 'task'): Command {
  return (view) =>
    toggleLinePrefix(view, view.state, (lineText, index) => {
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
  return (view) => toggleLinePrefix(view, view.state, () => ({prefix: '> ', strip: QUOTE_MARK}))
}

/** 把选中行的行首标记全剥掉，还原成普通段落 */
export function setParagraph(): Command {
  return (view) => {
    const {state} = view
    const specs: ChangeSpec[] = []
    for (const number of selectedLines(state)) {
      const line = state.doc.line(number)
      const mark = ANY_MARK.exec(line.text)?.[0]
      if (mark) specs.push({from: line.from, to: line.from + mark.length})
    }
    if (!specs.length) return false
    view.dispatch({changes: specs, scrollIntoView: true})
    return true
  }
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

    if (prev && next && FENCE_MARK.test(prev.text) && FENCE_MARK.test(next.text)) {
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
 * 在光标所在行下面放一个块级骨架。
 *
 * `select` 是**相对骨架起点**的选区，用来把光标停在该填的那一段上（表头单元、图片地址）；
 * 不传就停在骨架末尾。
 *
 * 「块与块之间要空一行」这条不是美观问题：`文字` 紧跟 `---` 会被读成 setext 二级标题，
 * 紧跟表格那行 `| | |` 会被读成上一段的续行。所以前一行有字时补两个换行，
 * 骨架后面固定补一个换行（让下一个块不会粘在骨架上）。当前行是空行时直接填满它，
 * 不额外造出空行 —— 「在新行的加号上点一块」是最常见的路径。
 */
function insertBlock(block: {text: string; select?: [number, number]}): Command {
  return (view) => {
    const {state} = view
    const line = state.doc.lineAt(state.selection.main.head)
    const lead = line.text.trim() ? '\n\n' : ''
    const start = line.to + lead.length
    const [from, to] = block.select ?? []
    view.dispatch({
      changes: {from: line.to, insert: `${lead}${block.text}`},
      selection:
        from === undefined || to === undefined
          ? EditorSelection.cursor(start + block.text.length)
          : EditorSelection.range(start + from, start + to),
      scrollIntoView: true,
    })
    return true
  }
}

/** 三列两行的表格骨架，光标停在第一个表头单元里（选中那两个空格，直接打字替换） */
export const insertTable: Command = insertBlock({
  text: '|  |  |  |\n| --- | --- | --- |\n|  |  |  |\n',
  select: [1, 3],
})

export const insertDivider: Command = insertBlock({text: '---\n'})

/** 图片骨架：`![](https://)`，地址段选中，粘上去就能替换 */
export const insertImage: Command = insertBlock({text: '![](https://)\n', select: [4, 12]})

/**
 * 链接骨架：`[文字](url)`。
 *
 * 不弹窗、不假定 URL 从哪来 —— 三种起点都把光标停在**待填的那一段**上：
 * 选中一个网址 → 光标停在方括号里补锚文本；选中文字 → 光标停在圆括号里补网址；
 * 空选区 → 光标停在方括号里。气泡菜单里那条链接输入条走 `applyLink`。
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

    view.dispatch({
      changes: specs,
      selection: EditorSelection.create(ranges, 0),
      scrollIntoView: true,
    })
    return true
  }
}

/**
 * 链接输入条提交的动作：设定 / 改写 / 删除当前选区上的链接。
 *
 * 与 `wrapLink` 分成两个命令是有原因的：气泡菜单里那个输入框要能**改**一条已有链接的地址，
 * 而 `wrapLink` 只会再套一层，套完变成 `[[文字](旧)](新)` 这种没法看的形状。
 * 传空地址 = 移除链接（保留锚文本），与旧版工具栏「留空则移除链接」的口径一致。
 */
export function applyLink(url: string): Command {
  return (view) => {
    const {state} = view
    const {from, to} = state.selection.main
    const link = linkAt(state, from, to)

    if (!url) {
      if (!link || link.image) return false
      view.dispatch({
        changes: {from: link.from, to: link.to, insert: link.label},
        selection: {anchor: link.from + link.label.length},
        scrollIntoView: true,
      })
      return true
    }

    if (link) {
      const changes =
        link.url === url ? [] : [{from: link.urlFrom, to: link.urlTo, insert: url}]
      view.dispatch({
        changes,
        selection: {anchor: link.to + (url.length - link.url.length)},
        scrollIntoView: true,
      })
      return true
    }

    // 选区要按行切开：连击选中整行时选区**带着行尾那个换行**，照原样包就变成
    // `[文字\n](url)`，`url` 那一截被甩到下一行去。行内标记不会有这种形状。
    const [span] = wrapSpans(state, state.selection.main)
    if (!span) return false
    const label = state.sliceDoc(span.from, span.to)
    const insert = `[${label}](${url})`
    view.dispatch({
      changes: {from: span.from, to: span.to, insert},
      selection: {anchor: span.from + insert.length},
      scrollIntoView: true,
    })
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
 *
 * `Ctrl+K` 不在这儿：它归浮层菜单那一层（`setup.ts` 的 `uiKeymap` 先接，
 * 有选区就弹链接输入条，没选区就插入 `[ ]()` 骨架）。
 */
export const MARKDOWN_KEYMAP: KeyBinding[] = [
  {key: 'Mod-b', run: toggleWrap('**')},
  {key: 'Mod-i', run: toggleWrap('*')},
  {key: 'Mod-Shift-s', run: toggleWrap('~~')},
  {key: 'Mod-Shift-c', run: toggleWrap('`')},
  {key: 'Mod-Alt-c', run: toggleCodeFence()},
  {key: 'Mod-Alt-1', run: setHeading(1)},
  {key: 'Mod-Alt-2', run: setHeading(2)},
  {key: 'Mod-Alt-3', run: setHeading(3)},
  {key: 'Mod-Shift-8', run: toggleList('bullet')},
  {key: 'Mod-Shift-7', run: toggleList('ordered')},
  {key: 'Mod-Shift-9', run: toggleList('task')},
  {key: 'Mod-Shift-b', run: toggleQuote()},
]
