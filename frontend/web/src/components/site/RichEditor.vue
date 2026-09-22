<script lang="ts" setup>
import {EditorContent, useEditor} from '@tiptap/vue-3'
import {computed, onBeforeUnmount, onMounted, ref, watch} from 'vue'

import {createEditorExtensions} from '@/components/editor/extensions'
import {EDITOR_SHORTCUTS, buildToolbarGroups} from '@/components/editor/tools'

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

const editor = useEditor({
  content: props.modelValue,
  editable: props.editable,
  extensions: createEditorExtensions({
    placeholder: () => props.placeholder || t('editor.placeholder'),
  }),
  onUpdate: ({editor: instance}) => emit('update:modelValue', instance.getHTML()),
})

/** 外部改动（如切换文章/重置表单）时同步进编辑器，且不回灌 update 事件 */
watch(
  () => props.modelValue,
  (value) => {
    const instance = editor.value
    if (!instance) return
    if (value !== instance.getHTML()) instance.commands.setContent(value, {emitUpdate: false})
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

/** 字数与阅读时长：中文按字、西文按词（去标签后统计） */
const stats = computed(() => {
  const plain = plainText(props.modelValue || '').trim()
  const cjk = (plain.match(/[\u4e00-\u9fff]/g) ?? []).length
  const words = plain.replace(/[\u4e00-\u9fff]/g, ' ').split(/\s+/).filter(Boolean).length
  const units = cjk + words
  return {units, minutes: Math.max(1, Math.round(units / 400))}
})

function plainText(html: string): string {
  if (!import.meta.client) return html.replace(/<[^>]*>/g, ' ')
  const holder = document.createElement('div')
  holder.innerHTML = html
  return holder.textContent ?? ''
}

/**
 * 插入/编辑链接
 *
 * 用编辑器内的输入条替代 `window.prompt`：原生 prompt 的按钮文案跟随操作系统语言、
 * 无法样式化、移动端体验差（与后台用 ElMessageBox 的做法也不一致）。
 */
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

/** 工具表跟随编辑器实例与语言变化重建（`isActive` 高亮依赖 `editor` 就绪） */const toolbarGroups = computed(() =>
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
    <!-- 工具栏 -->
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

    <!-- 字数与阅读时长（此前创作者只能自己在别处统计） -->
    <div class="rich-editor__status">
      <span>{{ $t('editor.words', {n: stats.units}) }}</span>
      <span aria-hidden="true">·</span>
      <span>{{ $t('editor.readingTime', {n: stats.minutes}) }}</span>
    </div>

    <!-- 媒体选择弹窗（我的媒体库 / 本地上传 / 外链） -->
    <MediaPickerDialog v-model="pickerOpen" @select="insertImage"/>
  </div>
</template>

<style scoped>
.rich-editor {
  overflow: hidden;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-card);
  background-color: var(--color-surface);
}

.rich-editor__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  align-items: center;
  padding: 6px 8px;
  border-bottom: 1px solid var(--color-line);
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

/* 底部状态栏：字数与阅读时长 */
.rich-editor__status {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--color-fg-subtle);
  border-top: 1px solid var(--color-line);
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
