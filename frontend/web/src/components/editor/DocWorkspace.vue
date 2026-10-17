<script lang="ts" setup>
/**
 * 文档工作台 —— 文章编辑页的统一外壳
 *
 * 版面照的是「文档类产品」那一套：顶部一条文档栏（面包屑 + 状态 + 视图切换 + 动作），
 * 左侧一条可折叠的大纲栏，中间一栏**阅读宽度**的正文，设置收进按需滑出的抽屉。
 * 正文两侧是干净的留白 —— 写作时眼睛只需要跟着一条窄栏走。
 *
 * ## 为什么它必须不依赖 Element Plus
 *
 * 后台编辑页在 `layouts/admin.vue` 下（EP 是**动态 import** 进来的，约 1.1 MB，
 * 刻意不进前台初始包），投稿编辑页在 `layouts/default.vue` 下（**根本没有注册 EP**）。
 * 这个外壳要被两边共用，所以内部一律用原生控件 + `--color-*` 令牌。
 *
 * 页面通过**具名插槽**往里塞自己的东西：插槽内容编译在页面的作用域里，
 * 因此后台可以在 `#actions` / `#settings` 里照常写 `el-button`、`el-form` ——
 * 组件解析走的是全局注册表，与外壳无关。这条分工是整个共用方案能成立的关键。
 *
 * ## 滚动归属
 *
 * 外壳**不自建滚动容器**，滚动交给页面（后台是 `el-main`，前台是 window）。
 * 原因：`height: 100%` 在两种布局里都拿不到确定高度（前台布局的容器是
 * `min-h-dvh` 的弹性列，其高度由内容决定），硬撑出来的滚动容器会塌成一屏高
 * 或者根本不动。改为「文档栏 + 大纲栏 sticky」，两种布局都能得到同样的观感，
 * 滚动跟随的基准线直接取文档栏的实时 `getBoundingClientRect()`，不需要猜高度。
 */
import type {DocViewMode} from '@/composables/useDocViewMode'
import type {OutlineItem} from '@/utils/content'

import DocOutline from './DocOutline.vue'

const props = withDefaults(
  defineProps<{
    /** 文章标题（v-model:title）。大标题输入框由外壳统一渲染 */
    title: string
    /** 视图模式（v-model:mode）。状态由页面持有，外壳只负责呈现与切换 */
    mode: DocViewMode
    /** 大纲条目 */
    items?: OutlineItem[]
    /** 载入中 / 未找到时传 false：标题不该还能改，否则会被随后的加载结果覆盖 */
    editable?: boolean
    saving?: boolean
    dirty?: boolean
    savedAt?: string | null
    /** 字数与预计阅读分钟数 */
    units?: number
    minutes?: number
    titlePlaceholder?: string
    titleMaxlength?: number
    /**
     * 源码正文的目录定位能力（`MarkdownEditor` 暴露的 `lineElAt`）。
     *
     * 外壳只认这一个方法，不认 CodeMirror：源码态的正文里**没有 `<h2>` 元素**，
     * 只有第 N 行以 `##` 开头，所以「第几个标题元素」这条定位方式在那儿不成立。
     * 由页面把编辑器的 ref 递进来，外壳不必知道编辑器是谁 ——
     * 阅读态仍然走渲染结果的 DOM，两条路共用同一份目录。
     */
    sourceAnchor?: {lineElAt: (offset: number) => HTMLElement | null} | null
    /**
     * 文档栏吸顶时距视口顶部的距离。
     *
     * 前台布局顶部那条 `SiteHeader` 自己也是 sticky 的（`h-14` + 1px 边框），
     * 投稿页要传它的宽度让文档栏停在它下面。后台布局的滚动容器是 `el-main`，
     * 头部不在容器内，保持默认 0 即可。
     */
    stickyOffset?: string
  }>(),
  {
    items: () => [],
    editable: true,
    saving: false,
    dirty: false,
    savedAt: null,
    units: 0,
    minutes: 0,
    titlePlaceholder: '',
    titleMaxlength: 255,
    sourceAnchor: null,
    stickyOffset: '0px',
  },
)

const emit = defineEmits<{
  (e: 'update:title', value: string): void
  (e: 'update:mode', value: DocViewMode): void
}>()

const {t} = useI18n()
const slots = useSlots()

/** 有设置内容才渲染「设置」入口 —— 从邀请链接进来的协作者没有设置可改 */
const hasSettings = computed(() => Boolean(slots.settings))

// ---------------------------------------------------------------- 视图模式

const MODES: readonly DocViewMode[] = ['edit', 'split', 'read']
const MODE_LABEL: Record<DocViewMode, string> = {
  edit: 'editor.doc.modeEdit',
  split: 'editor.doc.modeSplit',
  read: 'editor.doc.modeRead',
}

// ---------------------------------------------------------------- 大纲栏折叠

/**
 * 折叠状态是个人偏好，和视图模式一样存 localStorage。
 * 单独一个键而不是合并成一个对象：两处读写分属不同组件，合并反而互相覆盖。
 */
const RAIL_KEY = 'fb-doc-outline-collapsed'
const railCollapsed = ref(false)

function readRailCollapsed(): boolean {
  try {
    return window.localStorage.getItem(RAIL_KEY) === '1'
  } catch {
    return false
  }
}

function toggleRail(): void {
  railCollapsed.value = !railCollapsed.value
  try {
    window.localStorage.setItem(RAIL_KEY, railCollapsed.value ? '1' : '0')
  } catch {
    // 存不进就算了，本次会话内仍然生效
  }
}

// ---------------------------------------------------------------- 滚动跟随

const root = ref<HTMLElement | null>(null)
const bar = ref<HTMLElement | null>(null)
const docCol = ref<HTMLElement | null>(null)
const previewCol = ref<HTMLElement | null>(null)
const activeIndex = ref(-1)

/**
 * 承担滚动跟随的那一栏。
 *
 * 阅读态整屏都是渲染结果，目录自然该跟着预览走；其余两档跟正文。
 */
const trackedColumn = computed(() => (props.mode === 'read' ? previewCol.value : docCol.value))

/**
 * 渲染结果里的标题元素。
 *
 * 用「第 N 个标题元素」对上「第 N 条目录项」：外壳不认识编辑器的文档模型，也不要求
 * 谁去给标题加 id，两边只要出自同一份文档，顺序天然一致。
 *
 * **空标题要跳过**：`utils/content.ts` 建目录时不收没有文字的标题（点不动、也没
 * 信息量），而 `## ` 这种空标题在渲染结果里确实是一个 `<h2>`。两边口径必须一致，
 * 否则少筛一个，整条目录的跳转就全体错位一格 —— 而且错得很隐蔽，看着像"高亮不准"。
 */
function domHeadings(): HTMLElement[] {
  const column = trackedColumn.value
  if (!column) return []
  return Array.from(column.querySelectorAll<HTMLElement>('h1, h2, h3, h4, h5, h6')).filter(
    (el) => el.textContent?.trim(),
  )
}

/**
 * 目录第 `index` 项在屏幕上对应的那个元素；还没渲染出来时返回 null。
 *
 * 源码态和渲染态是两种定位方式：前者问编辑器「这个偏移落在哪一行」，
 * 后者数「第几个标题元素」。两者都按目录项的下标取，所以高亮与跳转始终对得上。
 */
function headingEl(index: number): HTMLElement | null {
  const item = props.items[index]
  if (!item) return null
  if (props.mode !== 'read') {
    const line = props.sourceAnchor?.lineElAt(item.offset) ?? null
    if (line) return line
  }
  return domHeadings()[index] ?? null
}

/**
 * 基准线：越过这条线的标题就算「已经进入视野」。
 *
 * 取吸顶元素的**实时下沿**而不是算出来的常量 —— 文档栏会因文案换行而变高，
 * 写死数字必然在某些语言下偏几像素。
 */
function stickyLine(): number {
  return bar.value?.getBoundingClientRect().bottom ?? 0
}

function updateActive(): void {
  if (!props.items.length) {
    activeIndex.value = -1
    return
  }
  const line = stickyLine()
  let current = 0
  // 目录项按文档顺序排列：第一个还没越线的，就是当前小节的前一节
  for (const [index] of props.items.entries()) {
    const el = headingEl(index)
    if (!el) continue
    if (el.getBoundingClientRect().top - line <= 8) current = index
    else break
  }
  activeIndex.value = current
}

/**
 * 把量出来的吸顶高度写成 CSS 变量。
 *
 * 两处要用同一个数：大纲栏的 `top`、以及跳转时标题的 `scroll-margin-top`
 * （别让标题停在文档栏底下）。后者在样式表里，只能通过变量传过去。
 */
function measure(): void {
  const el = root.value
  if (!el) return
  const barH = bar.value?.offsetHeight ?? 0
  el.style.setProperty('--doc-bar-h', `${barH}px`)
  el.style.setProperty('--doc-sticky-h', `${barH + 12}px`)
}

let ticking = false

function onScroll(): void {
  if (ticking) return
  ticking = true
  window.requestAnimationFrame(() => {
    ticking = false
    updateActive()
  })
}

/**
 * 找到真正的滚动祖先。
 *
 * 后台在 `el-main`（`overflow-y: auto`）里滚动，前台滚的是 window。绑错对象
 * 不会报错，只会让目录高亮**永远停在第一条** —— 这类静默失效最难查，所以按
 * 计算样式判定，而不是假定其中一个。
 */
let scroller: HTMLElement | Window | null = null

function resolveScroller(): HTMLElement | Window {
  let node = root.value?.parentElement ?? null
  while (node && node !== document.body) {
    const {overflowY} = window.getComputedStyle(node)
    if (overflowY === 'auto' || overflowY === 'scroll' || overflowY === 'overlay') return node
    node = node.parentElement
  }
  return window
}

function bindScroller(): void {
  unbindScroller()
  scroller = resolveScroller()
  scroller.addEventListener('scroll', onScroll, {passive: true})
}

function unbindScroller(): void {
  scroller?.removeEventListener('scroll', onScroll)
  scroller = null
}

function onSelectHeading(index: number): void {
  // 源码态：问编辑器这一行在哪；阅读态：数渲染结果里的第 N 个标题
  headingEl(index)?.scrollIntoView({behavior: 'smooth', block: 'start'})
  activeIndex.value = index
}

/** 正文一有变化，标题数量与位置就变了：高亮与吸顶高度都要重算 */
watch(
  () => [props.items, props.mode],
  () => void nextTick(() => {
    measure()
    updateActive()
  }),
  {deep: true},
)

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  railCollapsed.value = readRailCollapsed()
  bindScroller()
  measure()
  updateActive()
  // 文档栏换行、工具栏出现/消失都会改变吸顶高度
  resizeObserver = new ResizeObserver(() => {
    measure()
    updateActive()
  })
  if (bar.value) resizeObserver.observe(bar.value)
  window.addEventListener('resize', onScroll, {passive: true})
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  unbindScroller()
  window.removeEventListener('resize', onScroll)
})

// ---------------------------------------------------------------- 设置抽屉

const settingsOpen = ref(false)
const drawer = ref<HTMLElement | null>(null)
/** 关闭后把焦点还给唤起抽屉的那个按钮，否则键盘用户会被丢回页面顶部 */
let opener: HTMLElement | null = null

function openSettings(event: MouseEvent): void {
  opener = event.currentTarget as HTMLElement | null
  settingsOpen.value = true
  void nextTick(() => drawer.value?.focus())
}

function closeSettings(): void {
  settingsOpen.value = false
  void nextTick(() => opener?.focus())
}
</script>

<template>
  <div
    ref="root"
    :data-mode="mode"
    :style="{'--doc-ws-offset': stickyOffset}"
    class="doc-ws"
  >
    <!-- 文档栏吸顶在 stickyOffset 处（前台要让开 SiteHeader，后台为 0）；
         大纲栏与标题的 scroll-margin 都按这条 --doc-ws-offset 推算，所以只在这一处声明 -->
    <header ref="bar" class="doc-ws__bar">
      <button
        :aria-expanded="!railCollapsed"
        :class="{'is-active': !railCollapsed}"
        :title="railCollapsed ? $t('editor.doc.expandOutline') : $t('editor.doc.collapseOutline')"
        class="doc-ws__icon-btn"
        type="button"
        @click="toggleRail"
      >
        <Icon class="h-4 w-4" name="list"/>
      </button>

      <div class="doc-ws__bar-info">
        <div class="doc-ws__crumbs">
          <slot name="breadcrumb"/>
        </div>
        <div class="doc-ws__sub">
          <slot name="status"/>
          <span v-if="dirty" class="doc-ws__state is-dirty">{{ $t('editor.doc.dirty') }}</span>
          <span v-else-if="savedAt" class="doc-ws__state">
            {{ $t('editor.doc.savedAt', {time: savedAt}) }}
          </span>
        </div>
      </div>

      <div class="doc-ws__bar-tools">
        <div :aria-label="$t('editor.doc.modeLabel')" class="doc-ws__modes" role="group">
          <button
            v-for="item in MODES"
            :key="item"
            :aria-pressed="mode === item"
            :class="{'is-active': mode === item}"
            class="doc-ws__mode"
            type="button"
            @click="emit('update:mode', item)"
          >
            {{ $t(MODE_LABEL[item]) }}
          </button>
        </div>
        <slot name="actions"/>
      </div>
    </header>

    <div class="doc-ws__body">
      <aside v-if="!railCollapsed" class="doc-ws__rail">
        <DocOutline
          :active-index="activeIndex"
          :items="items"
          @select="onSelectHeading"
        />
        <slot name="rail-foot"/>
      </aside>

      <!-- 编辑 / 分栏：正文栏。
           **用 v-show 而不是 v-if**：切到阅读态时编辑器不能卸载 —— 编辑器一销毁，
           撤销栈和光标位置就没了，光标还会掉回页面顶部，用户「看一眼再切回来」
           等于白白丢了半小时的回退能力。正文本身在 v-model 里，所以隐藏不会丢内容。 -->
      <main
        v-show="mode !== 'read'"
        ref="docCol"
        class="doc-ws__col doc-ws__col--doc"
      >
        <div class="doc-ws__paper">
          <div v-if="$slots.banner" class="doc-ws__banner">
            <slot name="banner"/>
          </div>

          <input
            :aria-label="$t('editor.doc.titleAria')"
            :disabled="!editable"
            :maxlength="titleMaxlength"
            :placeholder="titlePlaceholder || $t('editor.doc.titlePlaceholder')"
            :value="title"
            class="doc-ws__title"
            type="text"
            @input="emit('update:title', ($event.target as HTMLInputElement).value)"
          >

          <div class="doc-ws__meta">
            <slot name="meta"/>
            <span class="doc-ws__meta-item">{{ $t('editor.doc.units', {n: units}) }}</span>
            <span aria-hidden="true" class="doc-ws__meta-sep">·</span>
            <span class="doc-ws__meta-item">{{ $t('editor.doc.minutes', {n: minutes}) }}</span>
          </div>

          <slot name="document"/>
        </div>
      </main>

      <!-- 分栏 / 阅读：渲染结果。读的是**当前缓冲区**，不是上次保存的版本 -->
      <aside
        v-if="mode !== 'edit'"
        ref="previewCol"
        class="doc-ws__col doc-ws__col--preview"
        :aria-label="$t('editor.doc.modeRead')"
      >
        <div class="doc-ws__paper">
          <slot name="preview"/>
        </div>
      </aside>
    </div>

    <!-- 右下浮动作：目录展开 + 设置。窄屏时大纲栏会自动隐藏，这里兜住入口 -->
    <div class="doc-ws__fab">
      <button
        v-if="railCollapsed"
        :aria-label="$t('editor.doc.expandOutline')"
        class="doc-ws__fab-btn"
        type="button"
        @click="toggleRail"
      >
        <Icon class="h-4 w-4" name="list"/>
      </button>
      <button
        v-if="hasSettings"
        :aria-label="$t('editor.doc.settings')"
        class="doc-ws__fab-btn"
        type="button"
        @click="openSettings"
      >
        <Icon class="h-4 w-4" name="settings"/>
      </button>
    </div>

    <Teleport to="body">
      <div v-if="settingsOpen" class="doc-ws__scrim" @click="closeSettings"/>
      <section
        v-if="settingsOpen"
        ref="drawer"
        :aria-label="$t('editor.doc.settings')"
        class="doc-ws__drawer"
        role="dialog"
        tabindex="-1"
        @keydown.esc="closeSettings"
      >
        <header class="doc-ws__drawer-head">
          <h2 class="doc-ws__drawer-title">{{ $t('editor.doc.settings') }}</h2>
          <button
            :aria-label="$t('editor.doc.closeSettings')"
            class="doc-ws__icon-btn"
            type="button"
            @click="closeSettings"
          >
            <Icon class="h-4 w-4" name="x"/>
          </button>
        </header>
        <div class="doc-ws__drawer-body">
          <slot name="settings"/>
        </div>
      </section>
    </Teleport>
  </div>
</template>

<style scoped>
/* ---------------------------------------------------------------- 版面骨架 */
.doc-ws {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  background: var(--color-canvas);
  color: var(--color-fg);
}

.doc-ws__bar {
  position: sticky;
  top: var(--doc-ws-offset, 0px);
  z-index: 30;
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid var(--color-line);
  background: var(--color-surface);
}

.doc-ws__bar-info {
  display: flex;
  flex: 1 1 auto;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.doc-ws__crumbs {
  display: flex;
  gap: 6px;
  align-items: center;
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  color: var(--color-fg-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-ws__sub {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: var(--color-fg-subtle);
}

.doc-ws__state.is-dirty {
  font-weight: 500;
  color: var(--color-warning);
}

.doc-ws__bar-tools {
  display: flex;
  flex: none;
  gap: 8px;
  align-items: center;
}

/* ---------------------------------------------------------------- 控件 */
.doc-ws__icon-btn {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-fg-muted);
  cursor: pointer;
  transition: background-color 0.12s ease, color 0.12s ease;
}

.doc-ws__icon-btn:hover {
  background: var(--color-surface-soft);
  color: var(--color-fg);
}

.doc-ws__icon-btn.is-active {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.doc-ws__icon-btn:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 1px;
}

.doc-ws__modes {
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-control);
  background: var(--color-surface-soft);
}

.doc-ws__mode {
  padding: 3px 10px;
  border: none;
  border-radius: calc(var(--radius-control) - 3px);
  background: transparent;
  font-size: 12px;
  color: var(--color-fg-muted);
  cursor: pointer;
  transition: background-color 0.12s ease, color 0.12s ease;
}

.doc-ws__mode.is-active {
  background: var(--color-surface);
  color: var(--color-primary);
  box-shadow: 0 1px 2px rgb(15 23 42 / 8%);
}

.doc-ws__mode:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 1px;
}

/* ---------------------------------------------------------------- 三栏 */
.doc-ws__body {
  display: flex;
  flex: 1 1 auto;
  gap: 0;
  align-items: flex-start;
  min-width: 0;
}

/*
 * 大纲栏自己滚：正文很长时目录也跟着滚出视野就没有导航意义了。
 * `align-items: flex-start`（见 .doc-ws__body）是 sticky 生效的前提 ——
 * 否则弹性项会被拉伸到整行高度，粘附就没有可移动的空间。
 */
.doc-ws__rail {
  position: sticky;
  top: calc(var(--doc-ws-offset, 0px) + var(--doc-bar-h, 0px) + 12px);
  flex: 0 0 264px;
  box-sizing: border-box;
  max-height: calc(100dvh - var(--doc-ws-offset, 0px) - var(--doc-bar-h, 0px) - 24px);
  overflow-y: auto;
  padding: 16px 12px 24px 20px;
  border-right: 1px solid var(--color-line);
  overscroll-behavior: contain;
}

.doc-ws__col {
  flex: 1 1 0;
  min-width: 0;
}

.doc-ws__col--preview {
  border-left: 1px solid var(--color-line);
  background: var(--color-surface);
}

.doc-ws__paper {
  max-width: 46rem;
  padding: 28px 32px 140px;
  margin-inline: auto;
}

/* 点目录跳转时，标题要停在吸顶的文档栏下面而不是被它盖住 */
.doc-ws :deep(h1),
.doc-ws :deep(h2),
.doc-ws :deep(h3),
.doc-ws :deep(h4),
.doc-ws :deep(h5),
.doc-ws :deep(h6) {
  scroll-margin-top: calc(var(--doc-ws-offset, 0px) + var(--doc-sticky-h, 96px));
}

/* ---------------------------------------------------------------- 标题与元信息 */
.doc-ws__banner {
  margin-bottom: 16px;
}

.doc-ws__title {
  width: 100%;
  padding: 0 0 6px;
  border: none;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  background: transparent;
  font: inherit;
  font-size: 30px;
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: -0.01em;
  color: var(--color-fg);
  transition: border-color 0.15s ease;
}

/*
 * 刻意不画四边描边：30px 的大标题套一个表单框很像后台表格，而这里要的是一篇文档。
 * 但**必须留下焦点指示** —— 只靠下划线，键盘用户点进来看不出这是可编辑的。
 */
.doc-ws__title:hover:not(:disabled) {
  border-bottom-color: var(--color-line-strong);
}

.doc-ws__title:focus-visible {
  border-bottom-color: var(--color-primary);
  outline: none;
}

.doc-ws__title:disabled {
  color: var(--color-fg-muted);
}

.doc-ws__title::placeholder {
  color: var(--color-fg-subtle);
}

.doc-ws__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin: 8px 0 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-line);
  font-size: 12px;
  color: var(--color-fg-subtle);
}

.doc-ws__meta-item {
  white-space: nowrap;
}

/* ---------------------------------------------------------------- 浮动作 */
.doc-ws__fab {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 20;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.doc-ws__fab-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-line);
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-fg-muted);
  box-shadow: 0 4px 14px rgb(15 23 42 / 12%);
  cursor: pointer;
}

.doc-ws__fab-btn:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.doc-ws__fab-btn:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* ---------------------------------------------------------------- 设置抽屉 */
.doc-ws__scrim {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgb(15 23 42 / 32%);
}

.doc-ws__drawer {
  position: fixed;
  top: 0;
  right: 0;
  z-index: 1001;
  display: flex;
  flex-direction: column;
  width: min(420px, 92vw);
  height: 100dvh;
  border-left: 1px solid var(--color-line);
  background: var(--color-surface);
  box-shadow: -12px 0 32px rgb(15 23 42 / 14%);
}

.doc-ws__drawer:focus-visible {
  outline: none;
}

.doc-ws__drawer-head {
  display: flex;
  flex: none;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-line);
}

.doc-ws__drawer-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-fg);
}

.doc-ws__drawer-body {
  flex: 1 1 auto;
  padding: 16px;
  overflow-y: auto;
  overscroll-behavior: contain;
}

/* ---------------------------------------------------------------- 窄屏 */
/* 分栏在窄屏改成上下堆叠：左右各 300px 时两边都读不出排版效果 */
@media (max-width: 1279px) {
  .doc-ws__body {
    flex-direction: column;
    align-items: stretch;
  }

  .doc-ws__rail {
    position: static;
    flex: none;
    width: auto;
    max-height: none;
    padding: 12px 16px;
    border-right: none;
    border-bottom: 1px solid var(--color-line);
  }

  .doc-ws__col {
    flex: none;
    width: 100%;
  }

  .doc-ws__col--preview {
    border-top: 1px solid var(--color-line);
    border-left: none;
  }

  .doc-ws__paper {
    padding: 20px 16px 120px;
  }
}

/* 手机宽度下没有版面放常驻目录栏，交给右下那颗浮动按钮 */
@media (max-width: 1023px) {
  .doc-ws__rail {
    display: none;
  }
}
</style>
