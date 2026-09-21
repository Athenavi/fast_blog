<script lang="ts" setup>
const {t} = useI18n()
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
import {EditorContent, useEditor} from '@tiptap/vue-3'
import {onBeforeUnmount, ref, watch} from 'vue'

import type {IconName} from '@/lib/icons'

/**
 * 富文本编辑器（Tiptap）
 *
 * 对应 astro 版 `editor/RichEditor.tsx`。技术栈与原来同源（Tiptap + StarterKit），
 * 所以扩展配置可以近乎平移：标题 1~3 级、加粗/斜体/下划线/删除线/高亮、
 * 有序/无序/任务列表、引用、代码块、链接、图片、表格、对齐、撤销重做。
 *
 * **两处刻意的差异**：
 *  1. astro 版的工具栏由父组件渲染（`RichEditor` 本身"no toolbar"），Nuxt 侧没有
 *     现成的工具栏组件，所以这里自带一条（功能更完整，调用方不需要再实现一遍）。
 *  2. astro 版的 AI 工具（润色/续写）调 `/api/v2/ai-*`，v3 没有 AI 域 ——
 *     按约定**不迁移**（见 docs/refactor/HANDOVER.md 的迁移结论）。
 *
 * 图片支持三种来源（`MediaPickerDialog`）：我的媒体库点选、本地上传
 * （v3 `mobile/media` 的 `/upload/image`，登录即可）、外链地址兜底。
 */
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
  extensions: [
    StarterKit.configure({heading: {levels: [1, 2, 3]}}),
    Placeholder.configure({placeholder: () => props.placeholder || t('editor.placeholder')}),
    Underline,
    LinkExt.configure({openOnClick: false, autolink: true}),
    ImageExt,
    TextAlign.configure({types: ['heading', 'paragraph']}),
    Highlight,
    Typography,
    TaskList,
    TaskItem.configure({nested: true}),
    Table.configure({resizable: true}),
    TableRow,
    TableHeader,
    TableCell,
  ],
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

interface Tool {
  id: string
  title: string
  icon?: IconName
  label?: string
  run: () => void
  isActive?: () => boolean
}

const pickerOpen = ref(false)

function insertImage(url: string): void {
  editor.value?.chain().focus().setImage({src: url}).run()
}

function applyLink(): void {
  const previous = editor.value?.getAttributes('link')?.href as string | undefined
  const url = window.prompt(t('editor.linkPrompt'), previous ?? '')
  if (url === null) return
  if (!url) {
    editor.value?.chain().focus().extendMarkRange('link').unsetLink().run()
    return
  }
  editor.value?.chain().focus().extendMarkRange('link').setLink({href: url}).run()
}

const TOOLBAR: Tool[][] = [
  [
    {
      id: 'h1',
      title: t('editor.h1'),
      label: 'H1',
      run: () => editor.value?.chain().focus().toggleHeading({level: 1}).run(),
      isActive: () => Boolean(editor.value?.isActive('heading', {level: 1})),
    },
    {
      id: 'h2',
      title: t('editor.h2'),
      label: 'H2',
      run: () => editor.value?.chain().focus().toggleHeading({level: 2}).run(),
      isActive: () => Boolean(editor.value?.isActive('heading', {level: 2})),
    },
    {
      id: 'h3',
      title: t('editor.h3'),
      label: 'H3',
      run: () => editor.value?.chain().focus().toggleHeading({level: 3}).run(),
      isActive: () => Boolean(editor.value?.isActive('heading', {level: 3})),
    },
    {
      id: 'bold',
      title: t('editor.bold'),
      icon: 'bold',
      run: () => editor.value?.chain().focus().toggleBold().run(),
      isActive: () => Boolean(editor.value?.isActive('bold')),
    },
    {
      id: 'italic',
      title: t('editor.italic'),
      icon: 'italic',
      run: () => editor.value?.chain().focus().toggleItalic().run(),
      isActive: () => Boolean(editor.value?.isActive('italic')),
    },
    {
      id: 'underline',
      title: t('editor.underline'),
      icon: 'underline',
      run: () => editor.value?.chain().focus().toggleUnderline().run(),
      isActive: () => Boolean(editor.value?.isActive('underline')),
    },
    {
      id: 'strike',
      title: t('editor.strike'),
      icon: 'strikethrough',
      run: () => editor.value?.chain().focus().toggleStrike().run(),
      isActive: () => Boolean(editor.value?.isActive('strike')),
    },
    {
      id: 'highlight',
      title: t('editor.highlight'),
      icon: 'highlighter',
      run: () => editor.value?.chain().focus().toggleHighlight().run(),
      isActive: () => Boolean(editor.value?.isActive('highlight')),
    },
  ],
  [
    {
      id: 'bullet',
      title: t('editor.bulletList'),
      icon: 'list',
      run: () => editor.value?.chain().focus().toggleBulletList().run(),
      isActive: () => Boolean(editor.value?.isActive('bulletList')),
    },
    {
      id: 'ordered',
      title: t('editor.orderedList'),
      icon: 'list-ordered',
      run: () => editor.value?.chain().focus().toggleOrderedList().run(),
      isActive: () => Boolean(editor.value?.isActive('orderedList')),
    },
    {
      id: 'task',
      title: t('editor.taskList'),
      icon: 'list-todo',
      run: () => editor.value?.chain().focus().toggleTaskList().run(),
      isActive: () => Boolean(editor.value?.isActive('taskList')),
    },
    {
      id: 'quote',
      title: t('editor.quote'),
      icon: 'quote',
      run: () => editor.value?.chain().focus().toggleBlockquote().run(),
      isActive: () => Boolean(editor.value?.isActive('blockquote')),
    },
    {
      id: 'code',
      title: t('editor.code'),
      icon: 'code',
      run: () => editor.value?.chain().focus().toggleCodeBlock().run(),
      isActive: () => Boolean(editor.value?.isActive('codeBlock')),
    },
  ],
  [
    {
      id: 'link',
      title: t('editor.link'),
      icon: 'link',
      run: applyLink,
      isActive: () => Boolean(editor.value?.isActive('link')),
    },
    {
      id: 'image',
      title: t('editor.image'),
      icon: 'image',
      run: () => {
        pickerOpen.value = true
      },
    },
    {
      id: 'table',
      title: t('editor.table'),
      icon: 'table',
      run: () =>
        editor.value
          ?.chain()
          .focus()
          .insertTable({rows: 3, cols: 3, withHeaderRow: true})
          .run(),
    },
  ],
  [
    {
      id: 'align-left',
      title: t('editor.alignLeft'),
      icon: 'align-left',
      run: () => editor.value?.chain().focus().setTextAlign('left').run(),
      isActive: () => Boolean(editor.value?.isActive({textAlign: 'left'})),
    },
    {
      id: 'align-center',
      title: t('editor.alignCenter'),
      icon: 'align-center',
      run: () => editor.value?.chain().focus().setTextAlign('center').run(),
      isActive: () => Boolean(editor.value?.isActive({textAlign: 'center'})),
    },
    {
      id: 'align-right',
      title: t('editor.alignRight'),
      icon: 'align-right',
      run: () => editor.value?.chain().focus().setTextAlign('right').run(),
      isActive: () => Boolean(editor.value?.isActive({textAlign: 'right'})),
    },
  ],
  [
    {
      id: 'undo',
      title: t('editor.undo'),
      icon: 'undo',
      run: () => editor.value?.chain().focus().undo().run(),
    },
    {
      id: 'redo',
      title: t('editor.redo'),
      icon: 'redo',
      run: () => editor.value?.chain().focus().redo().run(),
    },
  ],
]
</script>

<template>
  <div class="rich-editor">
    <!-- 工具栏 -->
    <div class="rich-editor__toolbar">
      <template v-for="(group, groupIndex) in TOOLBAR" :key="groupIndex">
        <span v-if="groupIndex > 0" class="rich-editor__divider"/>
        <button
          v-for="tool in group"
          :key="tool.id"
          :class="{ 'is-active': tool.isActive?.() }"
          :disabled="!editable"
          :title="tool.title"
          class="rich-editor__tool"
          type="button"
          @click="tool.run()"
        >
          <Icon v-if="tool.icon" :name="tool.icon" class="h-4 w-4"/>
          <span v-else class="text-[11px] font-semibold">{{ tool.label }}</span>
        </button>
      </template>
    </div>

    <!-- 编辑区 -->
    <EditorContent :editor="editor" class="rich-editor__body"/>

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
