<script lang="ts" setup>
import {EditorContent, useEditor} from '@tiptap/vue-3'
import {marked} from 'marked'
import {computed, onBeforeUnmount, onMounted, ref, watch} from 'vue'
import {serializeMarkdown} from '@/utils/tiptap-markdown'
import {renderMarkdown} from '@/utils/markdown'

import {createEditorExtensions} from '@/components/editor/extensions'
import {buildToolbarGroups, EDITOR_SHORTCUTS} from '@/components/editor/tools'

/**
 * 富文本编辑器（Tiptap）
 *
 * 对应 astro 版 `editor/RichEditor.tsx`。技术栈与原来同源（Tiptap + StarterKit），
 * 所以扩展配置可以近乎平移：标题 1~3 级、加粗/斜体/下划线/删除线/高亮、
 * 有序/无序/任务列表、引用、代码块、链接、图片、表格、对齐、撤销重做。
 *
 * **Batch 1.1 起，本组件只负责"组装"**：扩展集在 `components/editor/extensions.ts`、
 * 工具栏定义在 `components/editor/tools.ts`。调用方签名（`v-model` + `placeholder` +
 * `editable`）保持不变，因此既有调用点无需改动。
 *
 * **文档工作台（`components/editor/DocWorkspace.vue`）接入后的改动**：
 *  - 工具栏改为**吸顶**、滚动交还给页面：长文里工具栏要一直够得着，而滚动容器
 *    在后台布局是 `el-main`、在前台是 window，编辑器自己算不出该多高。
 *    因此 `.rich-editor` 不再有 `overflow: hidden` —— 它会静默地把 sticky 变成 relative。
 *  - 底部那条字数/阅读时长状态栏删掉了：工作台元信息行已经显示同一组数字
 *    （口径也换成了 `utils/content.ts` 的正确算法），两处各报一个数只会让人怀疑哪个准。
 *
 * 目录与字数**不在这里算** —— 由页面直接从 `v-model` 的 Markdown 取，见 `utils/content.ts`。
 *
 * 两处刻意的差异（保留自 astro 迁移）：
 *  1. astro 版的工具栏由父组件渲染（`RichEditor` 本身"no toolbar"），Nuxt 侧没有
 *     现成的工具栏组件，所以这里自带一条（功能更完整，调用方不需要再实现一遍）。
 *  2. astro 版的 AI 工具（润色/续写）调 `/api/v2/ai-*`，v3 有 `modules/ai` ——
 *     按 Batch 1.5 的计划另行接入，不在这里半途实现。
 *
 * 图片支持三种来源（`MediaPickerDialog`）：我的媒体库点选、本地上传
 * （v3 `mobile/media` 的 `/upload/image`，登录即可）、外链地址兜底。
 */
const {t} = useI18n()

const props = withDefaults(
  defineProps<{
    modelValue?: string
    placeholder?: string
    editable?: boolean
  }>(),
  {modelValue: '', placeholder: '', editable: true},
)

const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

/**
 * 粗略判断一段纯文本是否是 **Markdown 源码**。
 *
 * 用途：剪贴板**同时带 `text/html`** 时（从网页、富文本编辑器复制必然如此），
 * 需要决定是"保留原有富文本"还是"按 Markdown 解析"。
 * 判据只挑**渲染后不会原样保留**的标记，避免把普通中文正文误判成 Markdown。
 */
function looksLikeMarkdown(text: string): boolean {
  return (
    /^#{1,6}\s/m.test(text) || // # 标题
    /^\s*[-*+]\s+\S/m.test(text) || // - 无序列表
    /^\s*\d+[.)]\s+\S/m.test(text) || // 1. 有序列表
    /^>\s*\S/m.test(text) || // > 引用
    /^\s*```/m.test(text) || // 围栏代码块
    /\*\*[^*\n]+\*\*/.test(text) || // **粗体**
    /^\|.+\|/m.test(text) // | 表格 |
  )
}

const editor = useEditor({
  content: props.modelValue,
  editable: props.editable,
  extensions: createEditorExtensions({
    placeholder: () => props.placeholder || t('editor.placeholder'),
  }),
  editorProps: {
    /**
     * 粘贴：**纯文本按 Markdown 解析**。
     *
     * 为什么需要：Tiptap 默认把纯文本按"每行一个段落"插入，于是 Markdown 标记
     * （`## 标题`、`1. 列表`、`- 列表`）会**原样留在正文里** —— 作者从源码模式或
     * 别处粘回自己写的 Markdown 时，看到的是一串字面符号（用户描述为"粘贴 md 会
     * 自动加行号"，实际是列表序号被当文本留下了）。手动输入之所以正常，是因为
     * 它走的是 input rule 那条路径，与粘贴不是同一个入口。
     *
     * **带 `text/html` 的粘贴仍走默认处理**：从网页或其它编辑器复制时保留原格式，
     * 不强行套 Markdown 解析。
     */
    handlePaste: (_view, event) => {
      const clipboard = event.clipboardData
      if (!clipboard) return false
      const text = clipboard.getData('text/plain')
      if (!text.trim()) return false
      // 剪贴板带 HTML 时（从网页或富文本编辑器复制，**真实粘贴通常如此**），
      // 只有纯文本明显是 Markdown 源码才按 Markdown 解析，否则保留原有富文本格式。
      //
      // 注意顺序：**不能**在这之前写 `if (getData('text/html')) return false`。
      // 那样带 HTML 的粘贴会一律退回 Tiptap 默认处理，正文里就会留下字面的
      // 列表序号（`1.` / `2.`）—— 用户报的"粘贴 md 自动加行号"正是它。
      if (clipboard.getData('text/html') && !looksLikeMarkdown(text)) return false
      // 解析成 HTML 再插入：Tiptap 用 `parseHTML` 处理，**不依赖**各扩展的
      // markdown 规范。曾试过 `@tiptap/markdown`，但当前版本里 orderedList /
      // bulletList 没有 markdown 规范，`#` 会落到强调的 fallback（变成斜体）、
      // 整篇还会被塞进一个大 `<ol>` —— 比不解析更糟，已弃用。
      const html = marked.parse(text, {async: false})
      editor.value?.chain().focus().insertContent(html).run()
      return true // 已处理，阻止默认的粘贴
    },
  },
  onUpdate: ({editor: instance}) => {
    emit('update:modelValue', serializeMarkdown(instance.getJSON() as never))
  },
})

/** 外部改动（如切换文章/重置表单）时同步进编辑器，且不回灌 update 事件 */
watch(
  () => props.modelValue,
  (value) => {
    const instance = editor.value
    if (!instance) return
    if (value !== serializeMarkdown(instance.getJSON() as never)) {
      instance.commands.setContent(renderMarkdown(value), {emitUpdate: false})
    }
  },
)

watch(
  () => props.editable,
  (value) => editor.value?.setEditable(value),
)

onBeforeUnmount(() => editor.value?.destroy())

const pickerOpen = ref(false)

/** 选图后先问"图片描述"，再插入（alt 供读屏与搜索引擎使用） */
const imagePendingSrc = ref('')
const imageAlt = ref('')

function insertImage(url: string): void {
  imagePendingSrc.value = url
  imageAlt.value = ''
}

function applyImage(): void {
  const src = imagePendingSrc.value
  if (!src) return
  const alt = imageAlt.value.trim()
  editor.value?.chain().focus().setImage(alt ? {src, alt} : {src}).run()
  imagePendingSrc.value = ''
  imageAlt.value = ''
}

function cancelImage(): void {
  imagePendingSrc.value = ''
  imageAlt.value = ''
}

/** 当前平台的 Mod 键写法：macOS 用 ⌘，其它平台用 Ctrl */
const modKey = ref('Ctrl')

onMounted(() => {
  if (/Mac|iPhone|iPad/i.test(navigator.userAgent)) modKey.value = '⌘'
})

/** 按钮提示：有快捷键的工具把快捷键一起标出来（此前只有功能名，用户不知道能按键盘） */
function toolTitle(tool: { id: string; title: string }): string {
  const shortcut = EDITOR_SHORTCUTS[tool.id]
  if (!shortcut) return tool.title
  return `${tool.title} (${modKey.value === '⌘' ? shortcut.replace('Ctrl', '⌘') : shortcut})`
}

/** 插入/编辑链接：用一条内联输入条替代原生 `window.prompt`（留空即移除链接） */
const linkOpen = ref(false)
const linkUrl = ref('')

function openLinkPanel(): void {
  linkUrl.value = (editor.value?.getAttributes('link')?.href as string | undefined) ?? ''
  linkOpen.value = true
}

function applyLink(): void {
  const instance = editor.value
  if (!instance) return
  const url = linkUrl.value.trim()
  if (!url) {
    instance.chain().focus().extendMarkRange('link').unsetLink().run()
  } else {
    instance.chain().focus().extendMarkRange('link').setLink({href: url}).run()
  }
  linkOpen.value = false
}

/** 快捷键面板：把 EDITOR_SHORTCUTS 与工具栏标题对应起来，用户不必去翻文档 */
const shortcutOpen = ref(false)

const shortcutRows = computed(() => {
  const titles = new Map<string, string>()
  for (const group of toolbarGroups.value) {
    for (const tool of group) titles.set(tool.id, tool.title)
  }
  return Object.entries(EDITOR_SHORTCUTS)
    .filter(([id]) => titles.has(id))
    .map(([id, keys]) => ({
      id,
      title: titles.get(id) ?? id,
      keys: modKey.value === '⌘' ? keys.replace('Ctrl', '⌘') : keys,
    }))
})

/** 工具表跟随编辑器实例与语言变化重建（`isActive` 高亮依赖 `editor` 就绪） */
const toolbarGroups = computed(() =>
  buildToolbarGroups(editor.value, (key) => t(key), {
    pickImage: () => {
      pickerOpen.value = true
    },
    applyLink: openLinkPanel,
  }),
)
</script>

<template>
  <div class="rich-editor">
    <!-- 工具栏（吸顶：见样式注释，偏移量由工作台写在 --doc-ws-offset / --doc-bar-h 上） -->
    <div :aria-label="$t('editor.toolbar')" class="rich-editor__toolbar" role="toolbar">
      <template v-for="(group, groupIndex) in toolbarGroups" :key="groupIndex">
        <span v-if="groupIndex > 0" class="rich-editor__divider"/>
        <button
          v-for="tool in group"
          :key="tool.id"
          :aria-label="tool.title"
          :aria-pressed="Boolean(tool.isActive?.())"
          :class="{ 'is-active': tool.isActive?.() }"
          :disabled="!editable"
          :title="toolTitle(tool)"
          class="rich-editor__tool"
          type="button"
          @click="tool.run()"
        >
          <Icon v-if="tool.icon" :name="tool.icon" class="h-4 w-4"/>
          <span v-else class="text-[11px] font-semibold">{{ tool.label }}</span>
        </button>
      </template>

      <span class="rich-editor__divider"/>
      <button
        :aria-expanded="shortcutOpen"
        :aria-label="$t('editor.shortcuts')"
        :class="{'is-active': shortcutOpen}"
        :title="$t('editor.shortcuts')"
        class="rich-editor__tool"
        type="button"
        @click="shortcutOpen = !shortcutOpen"
      >
        <span class="text-[11px] font-semibold">?</span>
      </button>
    </div>

    <!-- 快捷键面板 -->
    <div v-if="shortcutOpen" class="rich-editor__shortcuts">
      <p class="rich-editor__shortcuts-title">{{ $t('editor.shortcuts') }}</p>
      <ul class="rich-editor__shortcuts-list">
        <li v-for="row in shortcutRows" :key="row.id">
          <span>{{ row.title }}</span>
          <kbd>{{ row.keys }}</kbd>
        </li>
      </ul>
    </div>

    <!-- 链接输入条：替代原生 window.prompt（留空即移除链接） -->
    <div v-if="linkOpen" class="rich-editor__link-bar">
      <Icon class="h-4 w-4 shrink-0 text-fg-subtle" name="link"/>
      <Input
        v-model="linkUrl"
        :placeholder="$t('editor.linkPrompt')"
        autofocus
        class="flex-1"
        @keydown.enter="applyLink"
        @keydown.esc="linkOpen = false"
      />
      <Button size="sm" type="button" @click="applyLink">{{ $t('common.confirm') }}</Button>
      <Button size="sm" type="button" variant="ghost" @click="linkOpen = false">
        {{ $t('common.cancel') }}
      </Button>
    </div>

    <!-- 图片描述：插入前补 alt（读屏与搜索引擎都用它） -->
    <div v-if="imagePendingSrc" class="rich-editor__link-bar">
      <Icon class="h-4 w-4 shrink-0 text-fg-subtle" name="image"/>
      <Input
        v-model="imageAlt"
        :placeholder="$t('editor.imageAlt')"
        autofocus
        class="flex-1"
        @keydown.enter="applyImage"
        @keydown.esc="cancelImage"
      />
      <Button size="sm" type="button" @click="applyImage">{{ $t('common.confirm') }}</Button>
      <Button size="sm" type="button" variant="ghost" @click="cancelImage">
        {{ $t('common.cancel') }}
      </Button>
    </div>

    <!-- 编辑区 -->
    <EditorContent :editor="editor" class="rich-editor__body"/>

    <!-- 媒体选择弹窗（我的媒体库 / 本地上传 / 外链） -->
    <MediaPickerDialog v-model="pickerOpen" @select="insertImage"/>
  </div>
</template>

<style scoped>
/*
 * 没有 `overflow: hidden` —— 它会创建一个裁剪容器，把工具栏的 `position: sticky`
 * 静默降级成普通定位（不报错、看不出来，只是吸不住）。
 * 圆角改由工具栏自己承担（见下），所以这里不需要裁剪。
 */
.rich-editor {
  border: 1px solid var(--color-line);
  border-radius: var(--radius-card);
  background-color: var(--color-surface);
}

/*
 * 吸顶工具栏。
 *
 * `--doc-ws-offset` = 工作台距滚动容器顶部的距离（前台布局还有站点导航条，后台为 0），
 * `--doc-bar-h`     = 顶部文档栏实测高度。两者都由 `DocWorkspace` 测量后写变量，
 * 这里不猜常量 —— 猜了就会在导航高度变化时错位。
 * 独立使用（不在工作台里）时两个变量缺省为 0，等价于贴着视口顶部吸住。
 */
.rich-editor__toolbar {
  position: sticky;
  top: calc(var(--doc-ws-offset, 0px) + var(--doc-bar-h, 0px));
  z-index: 10;
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  align-items: center;
  padding: 6px 8px;
  border-bottom: 1px solid var(--color-line);
  border-radius: calc(var(--radius-card) - 1px) calc(var(--radius-card) - 1px) 0 0;
  background-color: var(--color-surface-soft);
}

.rich-editor__tool {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  color: var(--color-fg-muted);
  cursor: pointer;
  background: transparent;
  border: none;
  border-radius: var(--radius-control);
  transition: background-color 0.12s ease, color 0.12s ease;
}

.rich-editor__tool:hover:not(:disabled) {
  color: var(--color-fg);
  background-color: var(--color-surface);
}

.rich-editor__tool.is-active {
  color: var(--color-primary-fg);
  background-color: var(--color-primary);
}

.rich-editor__tool:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.rich-editor__divider {
  width: 1px;
  height: 18px;
  margin: 0 4px;
  background-color: var(--color-line);
}

/* 链接输入条 / 图片描述条（替代 window.prompt） */
.rich-editor__link-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 8px 10px;
  border-bottom: 1px solid var(--color-line);
  background-color: var(--color-surface-soft);
}

/* 快捷键面板 */
.rich-editor__shortcuts {
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-line);
  background-color: var(--color-surface-soft);
}

.rich-editor__shortcuts-title {
  margin: 0 0 6px;
  font-size: 12px;
  color: var(--color-fg-subtle);
}

.rich-editor__shortcuts-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 4px 14px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.rich-editor__shortcuts-list li {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--color-fg-muted);
}

.rich-editor__shortcuts-list kbd {
  padding: 0 4px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-fg);
  border: 1px solid var(--color-line);
  border-radius: 4px;
}

.rich-editor__body :deep(.ProseMirror) {
  min-height: 320px;
  padding: 14px 16px;
  font-size: 15px;
  line-height: 1.75;
  color: var(--color-fg);
  outline: none;
}

.rich-editor__body :deep(.ProseMirror p) {
  margin: 0 0 0.75em;
}

.rich-editor__body :deep(.ProseMirror h1) {
  margin: 1em 0 0.5em;
  font-size: 1.6em;
  font-weight: 700;
}

.rich-editor__body :deep(.ProseMirror h2) {
  margin: 1em 0 0.5em;
  font-size: 1.35em;
  font-weight: 600;
}

.rich-editor__body :deep(.ProseMirror h3) {
  margin: 1em 0 0.4em;
  font-size: 1.15em;
  font-weight: 600;
}

.rich-editor__body :deep(.ProseMirror ul),
.rich-editor__body :deep(.ProseMirror ol) {
  margin: 0 0 0.75em;
  padding-left: 1.4em;
}

.rich-editor__body :deep(.ProseMirror ul) {
  list-style: disc;
}

.rich-editor__body :deep(.ProseMirror ol) {
  list-style: decimal;
}

.rich-editor__body :deep(.ProseMirror ul[data-type='taskList']) {
  padding-left: 0.2em;
  list-style: none;
}

.rich-editor__body :deep(.ProseMirror ul[data-type='taskList'] li) {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.rich-editor__body :deep(.ProseMirror blockquote) {
  padding-left: 12px;
  margin: 0 0 0.75em;
  color: var(--color-fg-muted);
  border-left: 3px solid var(--color-line-strong);
}

.rich-editor__body :deep(.ProseMirror pre) {
  padding: 12px 14px;
  margin: 0 0 0.75em;
  overflow-x: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
  background-color: var(--color-surface-soft);
  border-radius: var(--radius-control);
}

.rich-editor__body :deep(.ProseMirror code) {
  padding: 1px 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.9em;
  background-color: var(--color-surface-soft);
  border-radius: 4px;
}

.rich-editor__body :deep(.ProseMirror pre code) {
  padding: 0;
  background: none;
}

.rich-editor__body :deep(.ProseMirror a) {
  color: var(--color-primary);
  text-decoration: underline;
}

.rich-editor__body :deep(.ProseMirror mark) {
  padding: 0 2px;
  background-color: var(--color-warning-soft);
  border-radius: 3px;
}

.rich-editor__body :deep(.ProseMirror img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-card);
}

.rich-editor__body :deep(.ProseMirror table) {
  width: 100%;
  margin: 0 0 0.75em;
  border-collapse: collapse;
}

.rich-editor__body :deep(.ProseMirror th),
.rich-editor__body :deep(.ProseMirror td) {
  padding: 6px 8px;
  border: 1px solid var(--color-line);
}

.rich-editor__body :deep(.ProseMirror th) {
  font-weight: 600;
  background-color: var(--color-surface-soft);
}

.rich-editor__body :deep(.ProseMirror .is-editor-empty:first-child::before) {
  float: left;
  height: 0;
  color: var(--color-fg-subtle);
  pointer-events: none;
  content: attr(data-placeholder);
}
</style>
