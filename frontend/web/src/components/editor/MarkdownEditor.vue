<script lang="ts" setup>
/**
 * Markdown 正文编辑器（CodeMirror 6）
 *
 * ## 为什么整个底座只支持 Markdown 源码
 *
 * 项目正文**存的就是 Markdown**（`useArticleForm.form.content`、后台落库字段、
 * `renderMarkdown` 的入参三处同一份）。上一版为了"所见即所得"在中间架了一层
 * 富文本（ProseMirror 文档树 ↔ Markdown 序列化），于是每一次编辑都要过一遍
 * 有损往返：表格对齐、高亮、嵌套列表这些没有对应规范的地方就会留下残渣。
 * 直接把 Markdown 本身当作编辑对象，往返这一步就消失了 —— 顺带把「富文本/源码」
 * 这个切换按钮也消掉了：只有一种正文，就不需要两种视图。
 *
 * 排版效果由工作台的**分栏预览**负责（`renderMarkdown` 同一个出口），
 * 写作手感由 CodeMirror 的语法着色补回来：`#`、`**`、``` 这些标记符号淡显，
 * 标题按级放大，看起来仍然是这篇文档，而不是一串符号。
 *
 * ## 三个浮层，没有工具栏
 *
 * 版式照文档类产品：**选中文本**冒出一条横气泡（行内标记 + 链接），
 * **鼠标停在某一行**（或光标落在某一行）时行左边的槽里出现「+」，点开是块类型菜单，
 * **打字时**在行首或空格后敲 `/` 弹出同一张块菜单并跟着输入筛选。
 * 三者共用 `blocks.ts` 那一张表与 `commands.ts` 那一层动作，所以不存在
 * 「气泡里有、斜杠里没有」这种两份实现之间必然会有的缺口。
 *
 * 斜杠菜单的开关状态**不另外记一份**，每次视图更新都从文档本身重推
 * （`state.ts` 的 `slashTrigger`）：关键词被删空、光标移开、选区展开，菜单自己就没了。
 * 只有一处例外 —— Esc 关掉之后要给那段 `/关键词` 留个「已经关过」的记号，
 * 否则下一次视图更新又会把它弹回来，按 Esc 看起来像失灵。
 *
 * ## 为什么懒加载
 *
 * `markdown/setup` 那一边才 import CodeMirror 与 y-codemirror.next。
 * 这里只留一个空容器和 `await import()` —— 详情页、列表页这些不编辑正文的页面
 * 因此完全不会把这几百 KB 拉进首屏。
 *
 * 但浮层要的**命令与判定**（`commands.ts` / `blocks.ts` / `state.ts`）是静态引入的：
 * 它们只碰 `@codemirror/state` 的数据接口，不含视图与语言包，量级差着几十倍。
 * 若把它们也做成动态引入，菜单就得等一次网络往返才点得动，或者再写一份命令 ——
 * 两份命令早晚一处加粗用 `**`、另一处用 `__`。
 *
 * ## 协作绑定为什么不能走普通 prop
 *
 * `collab` 里装的是 `Y.Text` 与 `Awareness`。这两个对象内部靠自身引用与事件表工作，
 * 一旦被 Vue 的深响应代理包起来，`Y.observe` 收到的就是代理而不是原对象，
 * CRDT 的合并与撤销会静默错乱。所以：来源侧 `useCollabSession` 用 `shallowRef` 存，
 * 这里取用时再 `toRaw()` 一次 —— 两处各守一半，任何一处漏了都会变成"看着能协同，
 * 实际偶尔丢字"那种最难复现的 bug。
 */
import type {EditorState} from '@codemirror/state'

import type {IconName} from '@/lib/icons'
import type {BlockMenuItem} from './markdown/BlockMenu.vue'
import type {MarkItem} from './markdown/SelectionBubble.vue'
import type {
  MarkdownCollab,
  MarkdownMount,
  MarkdownUiBridge,
  MarkdownUiKey,
} from './markdown/setup'

import {applyLink, toggleWrap, wrapLink} from './markdown/commands'
import {BLOCK_ITEMS, matchBlock} from './markdown/blocks'
import {isMarkActive, linkAt, slashTrigger} from './markdown/state'
import BlockMenu from './markdown/BlockMenu.vue'
import SelectionBubble from './markdown/SelectionBubble.vue'

const props = withDefaults(
  defineProps<{
    /** 正文（Markdown 源码）。协作态下由 Y.Text 供给，这个 prop 不参与绑定 */
    modelValue?: string
    placeholder?: string
    editable?: boolean
    /** 读屏用的区域名字（编辑器本体是 div，没有原生 label 可挂） */
    label?: string
    /** 协作绑定；null = 本地编辑 */
    collab?: MarkdownCollab | null
  }>(),
  {modelValue: '', placeholder: '', editable: true, label: '', collab: null},
)

const emit = defineEmits<{(e: 'update:modelValue', value: string): void}>()

const {t} = useI18n()

/** 外层卡片：`position: relative`，三个浮层都按它的矩形定位 */
const root = ref<HTMLElement | null>(null)
/** CodeMirror 挂载点 */
const host = ref<HTMLElement | null>(null)

/** 装配结果与模块都留在**普通变量**里：EditorView 同样不能被响应式代理 */
let mount: MarkdownMount | null = null
let mod: typeof import('./markdown/setup') | null = null

// ------------------------------------------------------------------ 尺寸常量
// 浮层的定位靠这些数**预估**高度，而不是渲染完再量一次：
// 量一次就要多一轮「渲染 → 读矩形 → 再定位」，长列表里这会看见菜单先跳一下再落位。
const GUTTER = 6 // 「+」距卡片左沿
const MENU_W = 260 // 与 BlockMenu 的 CSS 宽度一致
const ITEM_H = 34
const MENU_PAD = 8
const MENU_HINT_H = 26
const MENU_MAX_H = 340
const GAP = 6
const BUBBLE_H = 34
/** 气泡按选区中心定位，左右各留这么多，免得半条气泡出卡片 */
const BUBBLE_HALF = 104

interface MarkDef {
  id: string
  open: string
  close?: string
  titleKey: string
  icon: IconName
}

/** 气泡里的行内标记：`close` 不给就是同一对符号 */
const MARKS: readonly MarkDef[] = [
  {id: 'bold', open: '**', titleKey: 'editor.bold', icon: 'bold'},
  {id: 'italic', open: '*', titleKey: 'editor.italic', icon: 'italic'},
  {id: 'strike', open: '~~', titleKey: 'editor.strike', icon: 'strikethrough'},
  {id: 'code', open: '`', titleKey: 'editor.md.inlineCode', icon: 'code-2'},
]

// ------------------------------------------------------------------ 浮层状态

interface Box {
  left: number
  top: number
}

/** 选区气泡（null = 不显示） */
const bubble = ref<(Box & {marks: MarkItem[]}) | null>(null)
const linkOpen = ref(false)
const linkValue = ref('')
/** 选区落在一条真链接里 —— 决定那颗按钮写「链接」还是「修改链接」，以及要不要清空地址 */
const linkEditing = ref(false)
/** 打开链接条时的选区，选区一变就收掉这条输入 */
let linkRange: {from: number; to: number} | null = null

/** 块类型菜单 */
const menu = ref<
  | (Box & {
      maxHeight: number
      source: 'plus' | 'slash'
      hint: string
    })
  | null
>(null)
const menuItems = ref<BlockMenuItem[]>([])
const menuHighlight = ref<string | null>(null)
/** 「+」锚定的行号：菜单要跟着那一行走，不能停在你上次打开它时的位置 */
let menuLine: number | null = null
/** 待删除的 `/关键词` */
let slashRange: {from: number; to: number} | null = null
/** Esc 关掉过的那一段 —— 内容没变之前不重开 */
let dismissed: {from: number; to: number} | null = null

/** 行左边槽里的「+」（left 由 GUTTER 定，这里只记行号与纵向位置） */
const plus = ref<{number: number; top: number} | null>(null)
/** 鼠标当前停在第几行（null = 不在正文上，交给光标那一行） */
let hoverLine: number | null = null

// ------------------------------------------------------------------ 装配

function build(): void {
  const parent = host.value
  if (!mod || !parent || mount) return

  const collab = toRaw(props.collab)
  const ui: MarkdownUiBridge = {onKey: handleKey}
  mount = mod.createMarkdownEditor(
    parent,
    collab ? collab.ytext.toString() : props.modelValue,
    {
      placeholder: props.placeholder,
      editable: props.editable,
      label: props.label,
      collab,
      ui,
      onInput: (text) => emit('update:modelValue', text),
      // 每一次视图更新都重新推导一遍浮层：选区、正文、可见范围都在里面
      onUpdate: (info) => {
        // 「+」菜单是给某一行用的，正文一动它就过期了（继续留着只会指错行）
        if (info.docChanged && menu.value?.source === 'plus') closeMenu()
        sync()
      },
    },
  )
}

function destroy(): void {
  closeOverlays()
  mount?.destroy()
  mount = null
}

onMounted(async () => {
  document.addEventListener('pointerdown', onDocPointerDown, true)
  mod = await import('./markdown/setup')
  // import 期间页面可能已经跳走（v-if 掉了编辑器）
  if (host.value) {
    build()
    sync()
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocPointerDown, true)
  destroy()
})

/**
 * 协作状态一变就重建视图。
 *
 * 两种模式的**内容供给方式**不同（本地缓冲区 ↔ Y.Text），撤销栈也不同
 * （本地 history ↔ 共享 UndoManager），这些都在装配期定死，热切换要动 5 个槽位
 * 还不一定干净。重建的代价是丢一次撤销历史，而这本来就该丢：
 * 「开启协作」是一次明确的换稿动作，把之前本地打的半个段落撤回到房间里没有意义。
 */
watch(
  () => props.collab,
  () => {
    destroy()
    build()
    void nextTick(sync)
  },
)

/** 外部改动（载入文章、恢复草稿、恢复历史版本）灌进来；自己发出的那一圈不回灌 */
watch(
  () => props.modelValue,
  (value) => {
    const view = mount?.view
    if (!view || props.collab) return
    if (value === view.state.doc.toString()) return
    view.dispatch({changes: {from: 0, to: view.state.doc.length, insert: value}})
  },
)

watch(
  () => props.editable,
  (value) => {
    mount?.setEditable(value)
    if (!value) closeOverlays()
  },
)

watch(
  () => props.placeholder,
  (value) => mount?.setPlaceholder(value),
)

// ------------------------------------------------------------------ 定位工具

/** 视口坐标换算到卡片内坐标 */
function relativeTop(viewportTop: number, hostRect: DOMRect): number {
  return viewportTop - hostRect.top
}

function clamp(value: number, min: number, max: number): number {
  // max < min（卡片比菜单还窄）时退回左边，宁可贴边也不要算出负宽度的居中
  return Math.min(Math.max(value, min), Math.max(min, max))
}

/**
 * 第 `number` 行在屏幕上的那个元素。
 *
 * 长正文被 CodeMirror **虚拟化了**：滚出视野的行只剩一个占位块，没有 `.cm-line` 元素。
 * 所以这里返回 null 是常态而不是错误 —— 浮层随之收起，等它滚回来再出现。
 */
function lineEl(number: number): HTMLElement | null {
  const view = mount?.view
  if (!view) return null
  const {state} = view
  if (number < 1 || number > state.doc.lines) return null
  try {
    const {node} = view.domAtPos(state.doc.line(number).from)
    const el = (node.nodeType === Node.TEXT_NODE ? node.parentElement : node) as HTMLElement | null
    return el?.closest<HTMLElement>('.cm-line') ?? null
  } catch {
    return null
  }
}

/** 光标/选区还在这块屏上吗：不在就别把浮层钉到一个不存在的位置 */
function isAlive(): boolean {
  const view = mount?.view
  const el = root.value
  if (!view || !el) return false
  return view.hasFocus || el.contains(document.activeElement)
}

/**
 * 菜单落点。
 *
 * 默认贴着锚点**下沿**、左边缘对齐；下面放不下（快到底了）就翻到锚点上方。
 * 横向永远不许出卡片：窄屏时分栏只有三四百 px 宽。
 */
function placeMenu(
  anchor: {top: number; bottom: number; left: number},
  count: number,
  withHint: boolean,
  hostRect: DOMRect,
): Box & {maxHeight: number} {
  const maxHeight = Math.min(
    MENU_MAX_H,
    Math.max(ITEM_H, count * ITEM_H) + MENU_PAD + (withHint ? MENU_HINT_H : 0),
  )
  const below = anchor.bottom + GAP
  const top = below + maxHeight <= window.innerHeight - 8 ? below : anchor.top - GAP - maxHeight
  return {
    left: clamp(anchor.left - hostRect.left, 8, hostRect.width - MENU_W - 8),
    top: relativeTop(top, hostRect),
    maxHeight,
  }
}

// ------------------------------------------------------------------ 每帧重推

function sync(): void {
  const view = mount?.view
  const el = root.value
  if (!view || !el || !props.editable || el.clientWidth === 0) return closeOverlays()

  syncMenu(view.state, el)
  syncPlus(view.state, el)
  syncBubble(el)
}

/** 块菜单：斜杠那一路每次重推，「+」那一路只在锚定的行还在的时候跟着行走 */
function syncMenu(state: EditorState, el: HTMLElement): void {
  const view = mount?.view
  if (!view) return
  const main = state.selection.main
  const trigger = main.empty && isAlive() ? slashTrigger(state, main.head) : null

  if (!trigger) {
    slashRange = null
    if (menu.value?.source === 'slash') closeMenu()
    return
  }

  slashRange = {from: trigger.from, to: trigger.to}
  if (dismissed && dismissed.from === trigger.from && dismissed.to === trigger.to) return

  const hostRect = el.getBoundingClientRect()
  const coords = view.coordsAtPos(trigger.from)
  if (!coords) return closeMenu()

  const items = toMenuItems(trigger.query, state)
  menuItems.value = items
  menu.value = {
    ...placeMenu({top: coords.top, bottom: coords.bottom, left: coords.left}, items.length, true, hostRect),
    source: 'slash',
    hint: t('editor.md.slashHint'),
  }
  // 筛选词一变，原来停着的那一项可能整条没了：回到第一条，回车永远有东西可插
  if (!items.some((item) => item.id === menuHighlight.value))
    menuHighlight.value = items[0]?.id ?? null
}

function syncPlus(state: EditorState, el: HTMLElement): void {
  const number = anchorLine(state)
  const line = number === null ? null : lineEl(number)
  if (number === null || !line) {
    plus.value = null
    if (menu.value?.source === 'plus') closeMenu()
    return
  }

  const view = mount?.view
  if (!view) return
  const hostRect = el.getBoundingClientRect()
  const rect = line.getBoundingClientRect()
  plus.value = {number, top: relativeTop(rect.top, hostRect)}

  // 「+」那一路菜单：锚在**打开它的那一行**上，鼠标随后移到别处也不能跟着跑
  if (menu.value?.source === 'plus') {
    const items = toMenuItems('', state)
    menuItems.value = items
    menu.value = {
      ...placeMenu(
        {top: rect.top, bottom: rect.bottom, left: hostRect.left + GUTTER},
        items.length,
        false,
        hostRect,
      ),
      source: 'plus',
      hint: '',
    }
    if (!items.some((item) => item.id === menuHighlight.value))
      menuHighlight.value = items[0]?.id ?? null
  }
}

/**
 * 「+」该停在哪一行。
 *
 * 菜单开着的时候钉在 `menuLine`（它是对着那一行开出来的，跟着鼠标走会指错行），
 * 否则跟着鼠标；鼠标不在正文上时跟着光标 —— 这样键盘用户按完回车也能看见它。
 */
function anchorLine(state: EditorState): number | null {
  if (menu.value?.source === 'plus' && menuLine !== null) return menuLine
  if (hoverLine !== null) return hoverLine
  return isAlive() ? state.doc.lineAt(state.selection.main.head).number : null
}

function syncBubble(el: HTMLElement): void {
  const view = mount?.view
  if (!view) return
  // 块菜单开着的时候不叠两层浮窗：那时候用户正在挑块类型
  if (menu.value || !isAlive()) {
    bubble.value = null
    linkOpen.value = false
    return
  }
  const state = view.state
  const main = state.selection.main
  linkEditing.value = false
  if (main.empty) {
    bubble.value = null
    linkOpen.value = false
    linkRange = null
    return
  }
  if (linkRange && (linkRange.from !== main.from || linkRange.to !== main.to)) linkOpen.value = false

  const start = view.coordsAtPos(main.from) ?? view.coordsAtPos(main.from, 1)
  const end = view.coordsAtPos(main.to) ?? view.coordsAtPos(main.to, -1)
  if (!start || !end) {
    bubble.value = null
    return
  }
  const hostRect = el.getBoundingClientRect()
  const center = (Math.min(start.left, end.left) + Math.max(start.right, end.right)) / 2
  const selTop = Math.min(start.top, end.top)
  const selBottom = Math.max(start.bottom, end.bottom)
  // 上面顶到视口边了就翻到选区下面
  const viewportTop = selTop - GAP - BUBBLE_H
  const top = viewportTop < 8 ? selBottom + GAP : viewportTop

  const link = linkAt(state, main.from, main.to)
  linkEditing.value = Boolean(link && !link.image)
  linkValue.value = link?.url ?? ''

  bubble.value = {
    left: clamp(center - hostRect.left, BUBBLE_HALF, Math.max(BUBBLE_HALF, hostRect.width - BUBBLE_HALF)),
    top: relativeTop(top, hostRect),
    marks: MARKS.map((mark) => ({
      id: mark.id,
      title: t(mark.titleKey),
      icon: mark.icon,
      active: isMarkActive(state, mark.open, mark.close ?? mark.open),
    })),
  }
}

function toMenuItems(query: string, state: EditorState): BlockMenuItem[] {
  return BLOCK_ITEMS.filter((item) => matchBlock(item, query, t(item.titleKey))).map((item) => ({
    id: item.id,
    title: t(item.titleKey),
    icon: item.icon,
    text: item.text,
    active: item.isActive?.(state) ?? false,
  }))
}

function closeMenu(): void {
  menu.value = null
  menuItems.value = []
  menuHighlight.value = null
  menuLine = null
}

function closeOverlays(): void {
  closeMenu()
  bubble.value = null
  plus.value = null
  linkOpen.value = false
  linkRange = null
  slashRange = null
  dismissed = null
  hoverLine = null
}

// ------------------------------------------------------------------ 动作

/** 从「+」打开块菜单：先把光标交给那一行，命令才知道要改哪一行 */
function openPlusMenu(number: number): void {
  const view = mount?.view
  const el = root.value
  if (!view || !el || !props.editable) return
  // 菜单开着的时候加号仍钉在这一行，再点它 = 关掉（不然只能选一项才能走）
  if (menu.value?.source === 'plus' && menuLine === number) return closeMenu()
  const {state} = view
  const line = state.doc.line(Math.min(number, state.doc.lines))
  // 整行选中会让气泡也跟着冒出来，所以只把光标放到行尾：行级命令按「哪几行」干活
  view.dispatch({selection: {anchor: line.to}})
  menuLine = number
  linkOpen.value = false
  dismissed = null

  const items = toMenuItems('', view.state)
  const hostRect = el.getBoundingClientRect()
  const rect = lineEl(number)?.getBoundingClientRect()
  if (!rect) return closeMenu()
  menuItems.value = items
  menu.value = {
    ...placeMenu({top: rect.top, bottom: rect.bottom, left: hostRect.left + GUTTER}, items.length, false, hostRect),
    source: 'plus',
    hint: '',
  }
  menuHighlight.value = items[0]?.id ?? null
}

function pick(id: string): void {
  const view = mount?.view
  const item = BLOCK_ITEMS.find((candidate) => candidate.id === id)
  const source = menu.value?.source
  const range = slashRange
  closeMenu()
  if (!view || !item) return
  if (source === 'slash' && range) {
    // 先抹掉 `/关键词`，再让命令落在同一个位置上 —— 顺序反了就把关键词留进正文了
    view.dispatch({changes: {from: range.from, to: range.to}, selection: {anchor: range.from}})
  }
  item.run(view)
  view.focus()
}

/**
 * 行内标记按钮。
 *
 * 点完不关气泡：连着按「加粗 → 斜体」是常态，关掉再选一次才加得上反而更累。
 */
function runMark(id: string): void {
  const view = mount?.view
  const mark = MARKS.find((candidate) => candidate.id === id)
  if (!view || !mark) return
  toggleWrap(mark.open, mark.close ?? mark.open)(view)
  view.focus()
}

/** `Ctrl+K` 与气泡里那颗链接按钮 */
function openLinkBar(): boolean {
  const view = mount?.view
  if (!view || !props.editable) return false
  const main = view.state.selection.main
  if (main.empty) {
    // 没选中字没什么可「加链接」的，直接留骨架，光标停在待填的那一段
    wrapLink()(view)
    return true
  }
  const link = linkAt(view.state, main.from, main.to)
  linkValue.value = link?.url ?? ''
  linkRange = {from: main.from, to: main.to}
  linkOpen.value = true
  return true
}

function submitLink(url: string): void {
  const view = mount?.view
  linkOpen.value = false
  linkRange = null
  if (view) applyLink(url)(view)
  view?.focus()
}

/** 编辑器那条键位表打进来的键（见 `setup.ts` 的 `uiKeymap`） */
function handleKey(key: MarkdownUiKey): boolean {
  if (key === 'link') return openLinkBar()
  if (!menu.value) return false
  const items = menuItems.value
  if (!items.length) {
    if (key !== 'escape') return false
    dismissMenu()
    return true
  }
  if (key === 'escape') {
    dismissMenu()
    return true
  }
  if (key === 'up' || key === 'down') {
    const at = items.findIndex((item) => item.id === menuHighlight.value)
    const next = at < 0 ? 0 : (at + (key === 'up' ? -1 : 1) + items.length) % items.length
    menuHighlight.value = items[next]?.id ?? null
    return true
  }
  if (key === 'enter' || key === 'tab') {
    const id = menuHighlight.value ?? items[0]?.id
    if (!id) return false
    pick(id)
    return true
  }
  return false
}

function dismissMenu(): void {
  // 斜杠那条要给这段 `/关键词` 记一笔，否则下一次视图更新又把它弹回来
  if (menu.value?.source === 'slash' && slashRange) dismissed = {...slashRange}
  closeMenu()
}

// ------------------------------------------------------------------ 鼠标

function onPointerMove(event: PointerEvent): void {
  const target = event.target as HTMLElement | null
  if (!target || target.closest('[data-overlay]')) return
  if (!target.closest('.cm-line')) {
    // 停在正文两侧留白上时维持原状，别让它一会儿跟鼠标、一会儿跟光标
    if (target.closest('.cm-content')) return
    hoverLine = null
    sync()
    return
  }
  const view = mount?.view
  if (!view) return
  let pos: number
  try {
    pos = view.posAtDOM(target, 0)
  } catch {
    return
  }
  const number = view.state.doc.lineAt(pos).number
  if (number === hoverLine) return
  hoverLine = number
  sync()
}

function onPointerLeave(): void {
  if (hoverLine === null) return
  hoverLine = null
  sync()
}

/**
 * 点浮层外面就收 —— 「打开了但不选」也是一种回答。
 *
 * 挂在 `document` 的 capture 阶段，而不是压一层全屏遮罩：遮罩会把那一次点击吃掉，
 * 用户关掉菜单还得再点一次才能接着打字。用 `pointerdown` 而不是 `click`：它比
 * CodeMirror 处理点选更早，触屏也一样管用；浮层自己带 `data-overlay`，点其中的
 * 按钮与输入框都在早退分支里，不会把正在做的事打断。
 */
function onDocPointerDown(event: PointerEvent): void {
  const target = event.target as HTMLElement | null
  if (target?.closest('[data-overlay]')) return
  if (menu.value?.source === 'plus') closeMenu()
  if (linkOpen.value && target && !root.value?.contains(target)) {
    linkOpen.value = false
    linkRange = null
  }
}

defineExpose({
  /**
   * 源码里某个偏移所在的那一行。
   *
   * 工作台的目录跳转与滚动跟随靠它：源码模式下正文里**没有 `<h2>` 这种元素**，
   * 只有第 N 行以 `##` 开头，所以外壳按「目录项的源码偏移」而不是「第几个标题元素」
   * 来找位置。两者对不上时目录会整体错位，见 `utils/content.ts` 的 `offset`。
   */
  lineElAt(offset: number): HTMLElement | null {
    const view = mount?.view
    if (!view) return null
    const pos = Math.max(0, Math.min(view.state.doc.length, offset))
    // 行首一定在文档里；用 lineAt 夹一次，避免远端刚删短了正文时下标越界
    return lineEl(view.state.doc.lineAt(pos).number)
  },
})
</script>

<template>
  <div
    ref="root"
    class="md-editor"
    @pointerleave="onPointerLeave"
    @pointermove="onPointerMove"
  >
    <div ref="host" class="md-editor__cm"/>

    <!-- 行左边的槽：鼠标停在哪一行、或者光标落在哪一行，「+」就在哪一行。
         不可编辑时 `sync()` 会把三个浮层一起收掉，这里不需要再各判一次 editable -->
    <button
      v-if="plus"
      :aria-label="$t('editor.md.addBlock')"
      :style="{top: `${plus.top}px`}"
      class="md-plus"
      data-overlay="true"
      type="button"
      @click="openPlusMenu(plus.number)"
    >
      <Icon class="h-4 w-4" name="plus"/>
    </button>

    <SelectionBubble
      v-if="bubble"
      :apply-text="$t('editor.md.linkApply')"
      :cancel-text="$t('editor.md.linkCancel')"
      :label="$t('editor.md.bubble')"
      :link-active="linkEditing"
      :link-open="linkOpen"
      :link-placeholder="$t('editor.md.linkInputPlaceholder')"
      :link-title="linkEditing ? $t('editor.md.linkEdit') : $t('editor.link')"
      :link-value="linkValue"
      :marks="bubble.marks"
      :style="{left: `${bubble.left}px`, top: `${bubble.top}px`}"
      class="md-editor__ov md-editor__ov--bubble"
      data-overlay="true"
      @close-link="linkOpen = false"
      @open-link="openLinkBar"
      @run="runMark"
      @submit-link="submitLink"
    />

    <BlockMenu
      v-if="menu"
      :empty-text="$t('editor.md.blockEmpty')"
      :hint="menu.hint"
      :highlight="menuHighlight"
      :items="menuItems"
      :label="$t('editor.md.blocks')"
      :max-height="menu.maxHeight"
      :style="{left: `${menu.left}px`, top: `${menu.top}px`}"
      class="md-editor__ov"
      data-overlay="true"
      @hover="(id: string) => (menuHighlight = id)"
      @pick="pick"
    />
  </div>
</template>

<style scoped>
/*
 * 高度交给内容：`.cm-editor { height: auto }` + 不设滚动容器，
 * 于是页面滚动（后台是 `el-main`、前台是 window）而不是编辑器内部滚一屏。
 * 这与工作台的 sticky 文档栏是同一套判断 —— 两处各自滚的话，
 * 长文里目录跟随、吸顶基准线都会算错。
 *
 * 浮层用 `position: absolute` 钉在这张卡片上，而**不是** fixed 钉在视口上：
 * 页面滚动时卡片和正文一起走，跟着正文算出来的偏移自然还对，
 * 不必监听 scroll 去补位置（漏一个滚动祖先，浮层就会飘在原地）。
 */
.md-editor {
  position: relative;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.md-editor__cm {
  min-height: 360px;
  padding: 4px 0 8px;
}

.md-editor__ov {
  position: absolute;
  z-index: 5;
}

.md-editor__ov--bubble {
  transform: translateX(-50%);
}

.md-editor__cm :deep(.cm-editor) {
  height: auto;
  font-size: 16px;
  line-height: 1.8;
  color: var(--color-fg);
  background: transparent;
}

/* CodeMirror 自带的焦点描边是给表单用的；这里是整页正文，不要再套一层框 */
.md-editor__cm :deep(.cm-editor.cm-focused) {
  outline: none;
}

.md-editor__cm :deep(.cm-scroller) {
  font-family: inherit;
}

/*
 * 左侧留出 34px 的槽给「+」：Notion / 飞书都把加号放在正文外面，但这里的正文栏
 * 两边是页面留白，负偏移会撞上限宽或被子元素的 `overflow` 裁掉。放在卡片内，
 * 槽宽由这一条声明，`GUTTER` 只管按钮自己贴左多远。
 */
.md-editor__cm :deep(.cm-content) {
  padding: 10px 18px 24px 34px;
  caret-color: var(--color-fg);
}

/* 深色模式下基础主题的黑色光标与浅灰选中都不可用，一律换成令牌 */
.md-editor__cm :deep(.cm-cursor),
.md-editor__cm :deep(.cm-dropCursor) {
  border-left-color: var(--color-fg);
}

.md-editor__cm :deep(.cm-selectionBackground),
.md-editor__cm :deep(.cm-focused .cm-selectionBackground),
.md-editor__cm :deep(.cm-line ::selection) {
  background-color: color-mix(in srgb, var(--color-primary) 22%, transparent) !important;
}

/* 点目录跳转、或把光标敲到屏幕边缘时，别让吸顶的文档栏盖住这一行 */
.md-editor__cm :deep(.cm-line) {
  padding: 0;
  scroll-margin-top: calc(var(--doc-ws-offset, 0px) + var(--doc-sticky-h, 0px));
}

/* ---------------------------------------------------- 行左边的「+」 */
.md-plus {
  position: absolute;
  z-index: 5;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid var(--color-line);
  border-radius: 7px;
  background: var(--color-surface);
  color: var(--color-fg-subtle);
  box-shadow: 0 1px 3px rgb(15 23 42 / 8%);
  cursor: pointer;
  transition: color 0.12s ease, border-color 0.12s ease;
}

.md-plus:hover,
.md-plus:focus-visible {
  color: var(--color-primary);
  border-color: var(--color-primary);
  outline: none;
}

/* ---------------------------------------------------- Markdown 语法着色 */
.md-editor__cm :deep(.md-h1) {
  font-size: 1.5em;
  font-weight: 700;
  line-height: 1.45;
}

.md-editor__cm :deep(.md-h2) {
  font-size: 1.3em;
  font-weight: 700;
  line-height: 1.5;
}

.md-editor__cm :deep(.md-h3) {
  font-size: 1.15em;
  font-weight: 600;
}

.md-editor__cm :deep(.md-h4),
.md-editor__cm :deep(.md-h5),
.md-editor__cm :deep(.md-h6) {
  font-size: 1.05em;
  font-weight: 600;
}

.md-editor__cm :deep(.md-strong) {
  font-weight: 700;
}

.md-editor__cm :deep(.md-em) {
  font-style: italic;
}

.md-editor__cm :deep(.md-strike) {
  text-decoration: line-through;
}

.md-editor__cm :deep(.md-code) {
  padding: 1px 3px;
  font-family: var(--font-mono);
  font-size: 0.9em;
  background: var(--color-surface-soft);
  border-radius: 4px;
}

.md-editor__cm :deep(.md-link) {
  color: var(--color-primary);
}

.md-editor__cm :deep(.md-quote) {
  color: var(--color-fg-muted);
  font-style: italic;
}

.md-editor__cm :deep(.md-meta) {
  color: var(--color-fg-subtle);
}

/*
 * 标记符号（`#`、`**`、```、`>`、`-`）淡显，放在最后一条：
 * 它与标题、链接这些**同一批 span** 上（`## 标题` 里的 `##` 同时带着 `md-h2` 和 `md-mark`），
 * 字号该继承标题的、颜色该取淡的 —— 同特异度下后写的赢，所以颜色由这条定。
 */
.md-editor__cm :deep(.md-mark) {
  color: var(--color-fg-subtle);
}
</style>
