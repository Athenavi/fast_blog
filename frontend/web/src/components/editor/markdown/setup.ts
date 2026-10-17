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

export interface MarkdownEditorOptions {
  placeholder?: string
  editable?: boolean
  /** 读屏与表单标签用的名字（编辑器本体是个 div，没有 `<label>` 可以挂） */
  label?: string
  /** 协作态：正文由 Y.Text 驱动，此时不注册本地 history（撤销交给共享的 UndoManager） */
  collab?: MarkdownCollab | null
  /** 文档变化回调（本地输入与远端同步都会走到） */
  onInput?: (text: string) => void
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
    // 顺序即优先级：本项目的键位先匹配，再轮到 CodeMirror 默认键。
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
    ...(options.onInput
      ? [
          EditorView.updateListener.of((update) => {
            if (update.docChanged) options.onInput?.(update.state.doc.toString())
          }),
        ]
      : []),
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
