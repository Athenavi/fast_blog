import type {Extensions} from '@tiptap/core'
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight'
import Highlight from '@tiptap/extension-highlight'
import ImageExt from '@tiptap/extension-image'
import LinkExt from '@tiptap/extension-link'
import {TaskItem, TaskList} from '@tiptap/extension-list'
import {Table, TableCell, TableHeader, TableRow} from '@tiptap/extension-table'
import TextAlign from '@tiptap/extension-text-align'
import Typography from '@tiptap/extension-typography'
import Underline from '@tiptap/extension-underline'
import {Placeholder} from '@tiptap/extensions'
import StarterKit from '@tiptap/starter-kit'

import {lowlight} from '@/lib/highlight'
import {Callout} from '@/components/editor/callout'

/**
 * 编辑器扩展集（UI/UX 路线图 Batch 1.1）
 *
 * 抽出来的原因：扩展配置原本硬编码在 `components/site/RichEditor.vue` 里，任何调用方
 * 想增减能力（例如文章编辑器要表格、评论编辑器不要）都得改那个组件。现在由参数决定，
 * 后续块化（Batch 1.2 的 SlashMenu / BlockHandle / callout 等块）也在这里注册。
 *
 * 约定：**扩展顺序有语义**（StarterKit 提供基础节点与 mark，其它扩展在其后补挂），
 * 不要为了好看重排。
 */
export interface EditorExtensionOptions {
  /** 占位文案；传函数可跟随 i18n 切换 */
  placeholder?: string | (() => string)
  /** 标题级别（默认 1~3）；`Level` 即 StarterKit 接受的 1~6 字面量 */
  headingLevels?: (1 | 2 | 3 | 4 | 5 | 6)[]
  /** 表格（文章/页面编辑器需要，短文本编辑器通常不要） */
  tables?: boolean
  /** 任务列表 */
  tasks?: boolean
  /** 图片节点 */
  images?: boolean
  /** 段落/标题/图片对齐 */
  textAlign?: boolean
  /** 智能排版（把 -- 转成 —、引号成对等） */
  typography?: boolean
  /** 代码块语法高亮（lowlight）；关掉可省掉 highlight.js 的按需加载 */
  codeHighlight?: boolean
  /** 提示块（callout）：注意/警告/成功/危险这类强调段落 */
  callouts?: boolean
}

export function createEditorExtensions(options: EditorExtensionOptions = {}): Extensions {
  const {
    placeholder = '',
    headingLevels = [1, 2, 3],
    tables = true,
    tasks = true,
    images = true,
    textAlign = true,
    typography = true,
    codeHighlight = true,
    callouts = true,
  } = options

  const resolvePlaceholder = () => (typeof placeholder === 'function' ? placeholder() : placeholder)

  const extensions: Extensions = [
    // 关掉 StarterKit 自带的 codeBlock，改用带语法高亮的 lowlight 版本
    StarterKit.configure({codeBlock: false, heading: {levels: headingLevels}}),
    Placeholder.configure({placeholder: resolvePlaceholder}),
    Underline,
    LinkExt.configure({openOnClick: false, autolink: true}),
  ]

  if (codeHighlight) extensions.push(CodeBlockLowlight.configure({lowlight}))
  if (callouts) extensions.push(Callout)
  if (images) extensions.push(ImageExt)
  // 图片也纳入对齐范围：长文里图片靠左/居中是很常见的排版需求
  if (textAlign) extensions.push(TextAlign.configure({types: ['heading', 'paragraph', 'image']}))
  extensions.push(Highlight)
  if (typography) extensions.push(Typography)
  if (tasks) extensions.push(TaskList, TaskItem.configure({nested: true}))
  if (tables) extensions.push(Table.configure({resizable: true}), TableRow, TableHeader, TableCell)

  return extensions
}
