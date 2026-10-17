/**
 * CodeMirror 6 的 Markdown 编辑器装配
 *
 * 这个文件是**唯一**一处把 CodeMirror、yjs、Markdown 语法绑到一起的地方。
 * `MarkdownEditor.vue` 用 `await import()` 引它，所以整包（含 y-codemirror.next）
 * 只在正文真的要编辑时才下载 —— 文章列表、详情页这些只读页面不该为此多背几百 KB。
 *
 * ## 为什么不套 `codemirror` 那个元包
 *
 * 元包的 `basicSetup` 带行号栏、折叠槽、搜索面板。文档写作不需要这些：
 * 行号是给代码看的，正文里它只会把左侧留白挤歪。所以这里逐项列扩展，
 * 每一项都说得出为什么在。
 */
import {Compartment, EditorState, type Extension} from '@codemirror/state'
import {
  EditorView,
  drawSelection,
  keymap,
  placeholder as placeholderExtension,
  rectangularSelection,
} from '@codemirror/view'
import {defaultKeymap, history, historyKeymap, indentWithTab} from '@codemirror/commands'
import {HighlightStyle, syntaxHighlighting} from '@codemirror/language'
import {markdown} from '@codemirror/lang-markdown'
import {tags as tag} from '@lezer/highlight'
import {yCollab, yUndoManagerKeymap} from 'y-codemirror.next'
import type {Awareness} from 'y-protocols/awareness'
import type * as Y from 'yjs'

import {MARKDOWN_KEYMAP} from './commands'

/** 协作绑定：必须是**原始**对象，不能经过 Vue 的响应式代理（见 MarkdownEditor.vue 文件头） */
export interface MarkdownCollab {
  ytext: Y.Text
  awareness: Awareness
}

/** 浮层菜单要接管的键：上下、选中、关掉，以及「弹链接输入条」 */
export type MarkdownUiKey = 'up' | 'down' | 'enter' | 'tab' | 'escape' | 'link'

/**
 * 装配时交给编辑器的**回调桥**。
 *
 * 为什么菜单的键盘路由要伸回 CodeMirror 里面：焦点一直在编辑器里，
 * 方向键和回车首先会被 `defaultKeymap` 拿去移光标、换行。浮层打开时这两个动作
 * 必须**替换**成「选下一项 / 插入这一项」，而这只能在键位表的最前面拦，
 * 事后 `preventDefault` 已经来不及。
 */
export interface MarkdownUiBridge {
  /** 返回 true = 这一键被浮层消费，CodeMirror 不再走默认行为 */
  onKey(key: MarkdownUiKey): boolean
}

export interface MarkdownUpdateInfo {
  docChanged: boolean
}

export interface MarkdownEditorOptions {
  placeholder?: string
  editable?: boolean
  /** 读屏与表单标签用的名字（编辑器本体是个 div，没有 `<label>` 可以挂） */
  label?: string
  /** 协作态：正文由 Y.Text 驱动，此时不注册本地 history（撤销交给共享的 UndoManager） */
  collab?: MarkdownCollab | null
  /** 文档变化回调（本地输入与远端同步都会走到） */
  onInput?: (text: string) => void
  /** 每次视图更新（选区、文档、可见范围）都回调，浮层靠它重新定位与显隐 */
  onUpdate?: (info: MarkdownUpdateInfo) => void
  /** 浮层菜单的键盘桥 */
  ui?: MarkdownUiBridge | null
}

/**
 * 浮层的键位表。
 *
 * 它排在所有键位**最前面**（CodeMirror 的 keymap 顺序即优先级），但每一项都只在
 * 浮层真的接着的时候返回 true；返回 false 就继续往下落到 `MARKDOWN_KEYMAP`
 * 和默认键 —— 菜单没开时，上下键仍然是移光标，回车仍然是换行。
 */
function uiKeymap(ui: MarkdownUiBridge): Extension {
  const bind = (key: string, name: MarkdownUiKey) => ({
    key,
    run: () => ui.onKey(name),
  })
  return keymap.of([
    bind('ArrowUp', 'up'),
    bind('ArrowDown', 'down'),
    bind('Enter', 'enter'),
    bind('Tab', 'tab'),
    bind('Escape', 'escape'),
    // Ctrl+K 归浮层：有选区时弹输入条，没选区时桥那边会退化成插入 `[ ]()` 骨架
    bind('Mod-k', 'link'),
  ])
}

/**
 * 语法高亮：只用 class，不写颜色。
 *
 * 颜色交给组件样式表里的 `--color-*` 令牌 —— 深浅色切换由 `<html class="dark">` 换变量值，
 * 若把颜色写进 `HighlightStyle` 就得自己监听主题再重装配一次编辑器。
 * `@lezer/markdown` 把 `#`、`**`、``` 这类**标记符号**归到 `processingInstruction`，
 * 正文归到各自节点，所以「标记淡、正文重」这条正好能按标签分开发，不用自己数哪几个字符是符号。
 */
const markdownHighlight = HighlightStyle.define([
  {tag: tag.heading1, class: 'md-h1'},
  {tag: tag.heading2, class: 'md-h2'},
  {tag: tag.heading3, class: 'md-h3'},
  {tag: tag.heading4, class: 'md-h4'},
  {tag: tag.heading5, class: 'md-h5'},
  {tag: tag.heading6, class: 'md-h6'},
  {tag: tag.strong, class: 'md-strong'},
  {tag: tag.emphasis, class: 'md-em'},
  {tag: tag.strikethrough, class: 'md-strike'},
  {tag: tag.monospace, class: 'md-code'},
  {tag: [tag.link, tag.url], class: 'md-link'},
  {tag: tag.quote, class: 'md-quote'},
  {tag: tag.list, class: 'md-list'},
  {tag: tag.contentSeparator, class: 'md-rule'},
  {tag: tag.bool, class: 'md-task'},
  {tag: [tag.labelName, tag.string], class: 'md-meta'},
  {tag: [tag.processingInstruction, tag.meta, tag.escape, tag.character], class: 'md-mark'},
])

export interface MarkdownMount {
  view: EditorView
  setEditable(editable: boolean): void
  setPlaceholder(text: string): void
  destroy(): void
}

/**
 * 装配并挂载编辑器。
 *
 * `Compartment` 必须是**每个实例自己的一份**（所以放在函数里而不是模块顶层）：
 * 它是配置的槽位标识，两个编辑器共用一个槽时，改一个会把另一个也改掉。
 */
export function createMarkdownEditor(
  parent: HTMLElement,
  doc: string,
  options: MarkdownEditorOptions = {},
): MarkdownMount {
  const editableSlot = new Compartment()
  const placeholderSlot = new Compartment()
  const collab = options.collab
  const ui = options.ui

  const extensions: Extension[] = [
    // 正文是散文，一行可能长过一屏：必须软换行，否则横向滚动条把阅读节奏打断。
    EditorView.lineWrapping,
    drawSelection(),
    rectangularSelection(),
    syntaxHighlighting(markdownHighlight),
    // 默认就是 CommonMark + GFM：表格、删除线、任务列表都在，与 `renderMarkdown`
    // 那一侧（marked 的 GFM）口径一致 —— 两边语法不一致时，作者会在预览里看到另一种东西。
    markdown(),
    EditorState.tabSize.of(2),
    editableSlot.of(EditorView.editable.of(options.editable ?? true)),
    placeholderSlot.of(placeholderExtension(options.placeholder ?? '')),
    // 拼写检查的红波浪是给英文代码标识符用的，写在中文正文里只会一路画到底。
    EditorView.contentAttributes.of({
      spellcheck: 'false',
      ...(options.label ? {'aria-label': options.label} : {}),
    }),
    // 顺序即优先级：浮层先接键（菜单开着的时候方向键属于菜单），
    // 再轮到本项目的 Markdown 键位，最后才是 CodeMirror 默认键。
    ...(ui ? [uiKeymap(ui)] : []),
    keymap.of(MARKDOWN_KEYMAP),
    ...(collab
      ? // 协作：内容供给交给 Y.Text，撤销走 yjs 的共享 UndoManager —— 它只回退**自己**的改动，
        // 不会把别人刚打的字一起撤掉。这里绝不能再挂 `history()`：两套撤销栈并存时，
        // 一次 Ctrl+Z 撤回哪一层取决于谁先注册，表现出来就是「有时撤不动」。
        // `yCollab` 返回的是一组扩展（类型上写作 `Extension`，运行时是数组），
        // 所以整条放进数组、不要展开 —— `Extension` 本身就允许嵌套数组。
        [yCollab(collab.ytext, collab.awareness), keymap.of(yUndoManagerKeymap)]
      : [history(), keymap.of([...historyKeymap, indentWithTab])]),
    keymap.of(defaultKeymap),
    // 一个监听器干两件事：把正文交给页面（只在真的改了文档时），把「有更新」交给浮层。
    // 浮层要的是**每一次**更新 —— 只改了选区（拖动选中、点了一下）也得重新定位气泡。
    EditorView.updateListener.of((update) => {
      if (update.docChanged) options.onInput?.(update.state.doc.toString())
      options.onUpdate?.({docChanged: update.docChanged})
    }),
  ]

  const view = new EditorView({parent, doc, extensions})

  return {
    view,
    setEditable(editable) {
      view.dispatch({effects: editableSlot.reconfigure(EditorView.editable.of(editable))})
    },
    setPlaceholder(text) {
      view.dispatch({effects: placeholderSlot.reconfigure(placeholderExtension(text))})
    },
    destroy() {
      view.destroy()
    },
  }
}
