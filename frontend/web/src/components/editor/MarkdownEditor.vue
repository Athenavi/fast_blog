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
 * ## 为什么懒加载
 *
 * `markdown/setup` 那一边才 import CodeMirror 与 y-codemirror.next。
 * 这里只留一个空容器和 `await import()` —— 详情页、列表页这些不编辑正文的页面
 * 因此完全不会把这几百 KB 拉进首屏。
 *
 * ## 协作绑定为什么不能走普通 prop
 *
 * `collab` 里装的是 `Y.Text` 与 `Awareness`。这两个对象内部靠自身引用与事件表工作，
 * 一旦被 Vue 的深响应代理包起来，`Y.observe` 收到的就是代理而不是原对象，
 * CRDT 的合并与撤销会静默错乱。所以：来源侧 `useCollabSession` 用 `shallowRef` 存，
 * 这里取用时再 `toRaw()` 一次 —— 两处各守一半，任何一处漏了都会变成"看着能协同，
 * 实际偶尔丢字"那种最难复现的 bug。
 */
import type {MarkdownCollab, MarkdownMount} from './markdown/setup'

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

const host = ref<HTMLElement | null>(null)

/** 装配结果与模块都留在**普通变量**里：EditorView 同样不能被响应式代理 */
let mount: MarkdownMount | null = null
let mod: typeof import('./markdown/setup') | null = null

function build(): void {
  const parent = host.value
  if (!mod || !parent || mount) return

  const collab = toRaw(props.collab)
  mount = mod.createMarkdownEditor(
    parent,
    collab ? collab.ytext.toString() : props.modelValue,
    {
      placeholder: props.placeholder,
      editable: props.editable,
      label: props.label,
      collab,
      onInput: (text) => emit('update:modelValue', text),
    },
  )
}

function destroy(): void {
  mount?.destroy()
  mount = null
}

onMounted(async () => {
  mod = await import('./markdown/setup')
  // import 期间页面可能已经跳走（v-if 掉了编辑器）
  if (host.value) build()
})

onBeforeUnmount(destroy)

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
  (value) => mount?.setEditable(value),
)

watch(
  () => props.placeholder,
  (value) => mount?.setPlaceholder(value),
)

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
    const line = view.state.doc.lineAt(pos).from
    let node: Node | undefined
    try {
      node = view.domAtPos(line).node
    } catch {
      return null
    }
    const el = (node?.nodeType === Node.TEXT_NODE ? node.parentElement : node) as HTMLElement | null
    return el?.closest<HTMLElement>('.cm-line') ?? null
  },
})
</script>

<template>
  <div class="md-editor">
    <div ref="host" class="md-editor__cm"/>
  </div>
</template>

<style scoped>
/*
 * 高度交给内容：`.cm-editor { height: auto }` + 不设滚动容器，
 * 于是页面滚动（后台是 `el-main`、前台是 window）而不是编辑器内部滚一屏。
 * 这与工作台的 sticky 文档栏是同一套判断 —— 两处各自滚的话，
 * 长文里目录跟随、吸顶基准线都会算错。
 */
.md-editor {
  border: 1px solid var(--color-line);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.md-editor__cm {
  min-height: 360px;
  padding: 4px 0 8px;
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

.md-editor__cm :deep(.cm-content) {
  padding: 10px 18px 24px;
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
