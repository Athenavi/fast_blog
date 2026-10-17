/**
 * 块类型表 ——「+」菜单与「/」菜单共用的同一张表
 *
 * 两个入口要的是同一批动作：分开维护迟早出现「加号里有表格、斜杠里没有」。
 * 所以这里只声明**数据 + 命令**，位置、跟随、筛选渲染都由浮层组件负责。
 *
 * 标题文字走 i18n key（`titleKey`），由调用方在渲染时翻译 —— 这张表是纯数据，
 * 在模块顶层调 `t()` 会拿到没初始化的 i18n 实例。
 *
 * `keywords` 只写英文与小号数字，给斜杠筛选当拼音之外的第二条路：
 * `/h1`、`/table`、`/code` 这类是写作者肌肉记忆里的东西，而 `/标题` 靠 `title` 匹配。
 */
import type {EditorState} from '@codemirror/state'
import type {Command} from '@codemirror/view'

import type {IconName} from '@/lib/icons'

import {
  insertDivider,
  insertImage,
  insertTable,
  setHeading,
  setParagraph,
  toggleCodeFence,
  toggleList,
  toggleQuote,
} from './commands'
import {isInCodeFence, linesArePlain, linesMatch} from './state'

/**
 * 各项的行首形状。
 *
 * 这些正则**一律不带 `g`**：`linesMatch` 用 `re.test()` 逐行判断，带 `g` 的同一个
 * 正则实例会在两次调用之间留下 `lastIndex`，表现为「第二行开始就判不准」。
 * 无序与任务互斥（任务那行也以 `- ` 开头），用先行否定把两者分开，否则菜单里两项同时亮。
 */
const RE_H1 = /^ {0,3}# /
const RE_H2 = /^ {0,3}## /
const RE_H3 = /^ {0,3}### /
const RE_BULLET = /^ {0,3}[-*+] (?!\[[ xX]\])/
const RE_ORDERED = /^ {0,3}\d{1,9}[.)] /
const RE_TASK = /^ {0,3}[-*+] \[[ xX]\]/
const RE_QUOTE = /^ {0,3}> ?/

export interface BlockItem {
  id: string
  /** i18n key */
  titleKey: string
  icon?: IconName
  /** 图标表里没有对应图形的项（H1–H3）用文字 */
  text?: string
  keywords: readonly string[]
  /** 菜单项的「已经是了，点它是取消」态；插入类动作没有这个状态 */
  isActive?: (state: EditorState) => boolean
  run: Command
}

export const BLOCK_ITEMS: readonly BlockItem[] = [
  {
    id: 'paragraph',
    titleKey: 'editor.md.paragraph',
    icon: 'type',
    keywords: ['text', 'p', 'plain', 'normal'],
    isActive: linesArePlain,
    run: setParagraph(),
  },
  {
    id: 'h1',
    titleKey: 'editor.h1',
    text: 'H1',
    keywords: ['h1', 'heading1', 'title'],
    isActive: (state) => linesMatch(state, RE_H1),
    run: setHeading(1),
  },
  {
    id: 'h2',
    titleKey: 'editor.h2',
    text: 'H2',
    keywords: ['h2', 'heading2'],
    isActive: (state) => linesMatch(state, RE_H2),
    run: setHeading(2),
  },
  {
    id: 'h3',
    titleKey: 'editor.h3',
    text: 'H3',
    keywords: ['h3', 'heading3'],
    isActive: (state) => linesMatch(state, RE_H3),
    run: setHeading(3),
  },
  {
    id: 'bullet',
    titleKey: 'editor.bulletList',
    icon: 'list',
    keywords: ['bullet', 'ul', 'list'],
    isActive: (state) => linesMatch(state, RE_BULLET),
    run: toggleList('bullet'),
  },
  {
    id: 'ordered',
    titleKey: 'editor.orderedList',
    icon: 'list-ordered',
    keywords: ['ordered', 'ol', 'number', 'list'],
    isActive: (state) => linesMatch(state, RE_ORDERED),
    run: toggleList('ordered'),
  },
  {
    id: 'task',
    titleKey: 'editor.taskList',
    icon: 'list-todo',
    keywords: ['task', 'todo', 'check'],
    isActive: (state) => linesMatch(state, RE_TASK),
    run: toggleList('task'),
  },
  {
    id: 'quote',
    titleKey: 'editor.quote',
    icon: 'quote',
    keywords: ['quote', 'blockquote'],
    isActive: (state) => linesMatch(state, RE_QUOTE),
    run: toggleQuote(),
  },
  {
    id: 'code',
    titleKey: 'editor.code',
    icon: 'code',
    keywords: ['code', 'fence', 'pre', 'block'],
    isActive: isInCodeFence,
    run: toggleCodeFence(),
  },
  {
    id: 'table',
    titleKey: 'editor.table',
    icon: 'table',
    keywords: ['table', 'grid'],
    run: insertTable,
  },
  {
    id: 'divider',
    titleKey: 'editor.md.divider',
    icon: 'minus',
    keywords: ['divider', 'rule', 'hr', 'line'],
    run: insertDivider,
  },
  {
    id: 'image',
    titleKey: 'editor.image',
    icon: 'image',
    keywords: ['image', 'picture', 'img'],
    run: insertImage,
  },
]

/**
 * 关键词匹配。
 *
 * 标题也参与匹配（`/表` 能筛出「插入表格」）—— 中文写作者只会打中文，
 * 只匹配英文关键词的菜单在他们眼里等于没有筛选。
 */
export function matchBlock(item: BlockItem, query: string, title: string): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return true
  if (title.toLowerCase().includes(q)) return true
  return item.keywords.some((k) => k.startsWith(q) || k.includes(q))
}
