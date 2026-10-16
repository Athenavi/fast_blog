import type {Editor} from '@tiptap/vue-3'

import type {IconName} from '@/lib/icons'

/**
 * 编辑器工具栏定义（UI/UX 路线图 Batch 1.1）
 *
 * 与 `extensions.ts` 一样，从 `components/site/RichEditor.vue` 里抽出来的**纯数据 + 命令**，
 * 好处：
 *   - 增减按钮不必再动编辑器组件；
 *   - 后续"块工具"（Batch 1.2 的 Slash 菜单里那批）可以直接复用同一份工具表生成菜单项，
 *     避免"工具栏有、slash 菜单没有"的两套命令。
 *
 * 为什么工具栏**仍渲染在 RichEditor 内部**：`isActive()` 的实时高亮依赖 tiptap 在同一组件
 * 内的渲染时机（`useEditor` 的实例 ref 变化才会触发重渲染）。等 Batch 1.2 引入菜单/浮层
 * 时再评估拆分，现在拆只会引入"按钮不亮"这类隐性回归。
 */

export interface EditorTool {
  id: string
  title: string
  /** 图标名（`@/lib/icons` 的 ICON_PATHS 键）；与 `label` 二选一 */
  icon?: IconName
  /** 文字按钮（如 H1/H2/H3，图标表里没有对应图形） */
  label?: string
  run: () => void
  isActive?: () => boolean
}

export type EditorToolGroup = EditorTool[]

/**
 * 工具栏快捷键提示（工具 id → 平台无关写法）
 *
 * 与 Tiptap 的内置绑定保持一致；这里只声明"提示文案"，按键本身由各扩展注册。
 * 没有默认绑定的工具（链接/图片/表格/任务列表）不列，避免提示用户去按一个不存在的键。
 * 展示时由 RichEditor 把 `Ctrl` 换成本平台的 Mod 键（macOS 上是 ⌘）。
 */
export const EDITOR_SHORTCUTS: Record<string, string> = {
  h1: 'Ctrl+Alt+1',
  h2: 'Ctrl+Alt+2',
  h3: 'Ctrl+Alt+3',
  bold: 'Ctrl+B',
  italic: 'Ctrl+I',
  underline: 'Ctrl+U',
  strike: 'Ctrl+Shift+S',
  highlight: 'Ctrl+Shift+H',
  bullet: 'Ctrl+Shift+8',
  ordered: 'Ctrl+Shift+7',
  quote: 'Ctrl+Shift+B',
  code: 'Ctrl+Alt+C',
  'align-left': 'Ctrl+Shift+L',
  'align-center': 'Ctrl+Shift+E',
  'align-right': 'Ctrl+Shift+R',
  undo: 'Ctrl+Z',
  redo: 'Ctrl+Shift+Z',
}

/** 需要调用方介入的动作（弹窗、DOM 交互），避免工具表里直接碰 UI */
export interface ToolbarActions {
  /** 打开媒体选择弹窗（图片按钮） */
  pickImage: () => void
  /** 设置/取消链接 */
  applyLink: () => void
}

export function buildToolbarGroups(
  editor: Editor | undefined,
  t: (key: string) => string,
  actions: ToolbarActions,
): EditorToolGroup[] {
  const active = (check: () => boolean) => () => Boolean(editor && check())

  return [
    [
      {
        id: 'h1',
        title: t('editor.h1'),
        label: 'H1',
        run: () => editor?.chain().focus().toggleHeading({level: 1}).run(),
        isActive: active(() => Boolean(editor?.isActive('heading', {level: 1}))),
      },
      {
        id: 'h2',
        title: t('editor.h2'),
        label: 'H2',
        run: () => editor?.chain().focus().toggleHeading({level: 2}).run(),
        isActive: active(() => Boolean(editor?.isActive('heading', {level: 2}))),
      },
      {
        id: 'h3',
        title: t('editor.h3'),
        label: 'H3',
        run: () => editor?.chain().focus().toggleHeading({level: 3}).run(),
        isActive: active(() => Boolean(editor?.isActive('heading', {level: 3}))),
      },
      {
        id: 'bold',
        title: t('editor.bold'),
        icon: 'bold',
        run: () => editor?.chain().focus().toggleBold().run(),
        isActive: active(() => Boolean(editor?.isActive('bold'))),
      },
      {
        id: 'italic',
        title: t('editor.italic'),
        icon: 'italic',
        run: () => editor?.chain().focus().toggleItalic().run(),
        isActive: active(() => Boolean(editor?.isActive('italic'))),
      },
      {
        id: 'underline',
        title: t('editor.underline'),
        icon: 'underline',
        run: () => editor?.chain().focus().toggleUnderline().run(),
        isActive: active(() => Boolean(editor?.isActive('underline'))),
      },
      {
        id: 'strike',
        title: t('editor.strike'),
        icon: 'strikethrough',
        run: () => editor?.chain().focus().toggleStrike().run(),
        isActive: active(() => Boolean(editor?.isActive('strike'))),
      },
      {
        id: 'highlight',
        title: t('editor.highlight'),
        icon: 'highlighter',
        run: () => editor?.chain().focus().toggleHighlight().run(),
        isActive: active(() => Boolean(editor?.isActive('highlight'))),
      },
    ],
    [
      {
        id: 'bullet',
        title: t('editor.bulletList'),
        icon: 'list',
        run: () => editor?.chain().focus().toggleBulletList().run(),
        isActive: active(() => Boolean(editor?.isActive('bulletList'))),
      },
      {
        id: 'ordered',
        title: t('editor.orderedList'),
        icon: 'list-ordered',
        run: () => editor?.chain().focus().toggleOrderedList().run(),
        isActive: active(() => Boolean(editor?.isActive('orderedList'))),
      },
      {
        id: 'task',
        title: t('editor.taskList'),
        icon: 'list-todo',
        run: () => editor?.chain().focus().toggleTaskList().run(),
        isActive: active(() => Boolean(editor?.isActive('taskList'))),
      },
      {
        id: 'quote',
        title: t('editor.quote'),
        icon: 'quote',
        run: () => editor?.chain().focus().toggleBlockquote().run(),
        isActive: active(() => Boolean(editor?.isActive('blockquote'))),
      },
      {
        id: 'callout',
        title: t('editor.callout'),
        icon: 'info',
        run: () => editor?.chain().focus().toggleCallout().run(),
        isActive: active(() => Boolean(editor?.isActive('callout'))),
      },
      {
        id: 'code',
        title: t('editor.code'),
        icon: 'code',
        run: () => editor?.chain().focus().toggleCodeBlock().run(),
        isActive: active(() => Boolean(editor?.isActive('codeBlock'))),
      },
    ],
    [
      {
        id: 'link',
        title: t('editor.link'),
        icon: 'link',
        run: actions.applyLink,
        isActive: active(() => Boolean(editor?.isActive('link'))),
      },
      {
        id: 'image',
        title: t('editor.image'),
        icon: 'image',
        run: actions.pickImage,
      },
      {
        id: 'table',
        title: t('editor.table'),
        icon: 'table',
        run: () => editor?.chain().focus().insertTable({rows: 3, cols: 3, withHeaderRow: true}).run(),
      },
    ],
    [
      {
        id: 'align-left',
        title: t('editor.alignLeft'),
        icon: 'align-left',
        run: () => editor?.chain().focus().setTextAlign('left').run(),
        isActive: active(() => Boolean(editor?.isActive({textAlign: 'left'}))),
      },
      {
        id: 'align-center',
        title: t('editor.alignCenter'),
        icon: 'align-center',
        run: () => editor?.chain().focus().setTextAlign('center').run(),
        isActive: active(() => Boolean(editor?.isActive({textAlign: 'center'}))),
      },
      {
        id: 'align-right',
        title: t('editor.alignRight'),
        icon: 'align-right',
        run: () => editor?.chain().focus().setTextAlign('right').run(),
        isActive: active(() => Boolean(editor?.isActive({textAlign: 'right'}))),
      },
    ],
    [
      {
        id: 'undo',
        title: t('editor.undo'),
        icon: 'undo',
        run: () => editor?.chain().focus().undo().run(),
      },
      {
        id: 'redo',
        title: t('editor.redo'),
        icon: 'redo',
        run: () => editor?.chain().focus().redo().run(),
      },
    ],
  ]
}
