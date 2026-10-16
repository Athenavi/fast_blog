<script lang="ts" setup>
/**
 * 协作编辑器：Markdown 源码 + 实时预览
 *
 * ## 为什么是 textarea 而不是 Tiptap
 *
 * 协同编辑需要把正文表示成 CRDT 能合并的结构。富文本（ProseMirror 文档树）
 * 要做这件事得引入 `y-prosemirror` 并把整个编辑器绑定重写成 CRDT 感知的
 * （绑定、光标、undo 栈都要改），工程量与风险都远大于本轮目标。
 *
 * 所以协作态用 **纯文本（Markdown 源码）** —— Yjs 的 `Y.Text` 正是为纯文本设计的，
 * 合并语义清晰。**格式能力靠 Markdown 语法 + 实时预览补回来**：
 * 左边写源码、右边立刻渲染，所见即所得。
 *
 * ## 为什么预览不是"可选的"
 *
 * 用户明确要求「文本协作时仍然是 markdown 实时渲染的」。只给 textarea，
 * 协作期间就退化成记事本了 —— 所以预览是**必备的一半**，不是装饰。
 *
 * ## 渲染安全
 *
 * Markdown 渲染走 `renderMarkdown`（项目内唯一的渲染出口，已做 HTML 转义与
 * 危险协议过滤）。这里**不做第二套渲染实现** —— 两套渲染必然分叉，
 * 其中一套出安全问题时另一套还在用。
 */
import {computed} from 'vue'
import {renderMarkdown} from '@/utils/markdown'
import type {CollabStatus} from '@/lib/yjs/collab-provider'

const props = defineProps<{
  /** 正文（v-model）—— 协作态下由 Yjs 驱动 */
  modelValue: string
  /** 连接状态，用于顶部状态条 */
  status?: CollabStatus
  /** 在线人数 */
  online?: number
  /** 只读（协作者被撤销授权、或链接过期时降级为只读） */
  readonly?: boolean
  /** 占位文案 */
  placeholder?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const {t} = useI18n()

/** 右侧预览的 HTML —— 唯一渲染出口，见文件头注释 */
const html = computed(() => renderMarkdown(props.modelValue || ''))

/** 字数：按非空白字符计，中英文都适用 */
const charCount = computed(() => (props.modelValue || '').replace(/\s+/g, '').length)

function onInput(event: Event): void {
  emit('update:modelValue', (event.target as HTMLTextAreaElement).value)
}
</script>

<template>
  <div class="collab-editor">
    <div class="collab-editor__head">
      <span :data-status="status" class="collab-editor__badge">
        {{ t(`myPosts.collab.${status || 'connecting'}`) }}
      </span>
      <span v-if="online !== undefined" class="collab-editor__online">
        {{ t('myPosts.collab.online', {count: online}) }}
      </span>
      <span class="collab-editor__spacer"/>
      <span class="collab-editor__count">
        {{ t('myPosts.collab.charCount', {count: charCount}) }}
      </span>
    </div>

    <div class="collab-editor__split">
      <!-- 左：Markdown 源码 -->
      <label class="collab-editor__pane">
        <span class="collab-editor__pane-label">{{ t('myPosts.collab.source') }}</span>
        <textarea
          :placeholder="placeholder || t('myPosts.collab.placeholder')"
          :readonly="readonly"
          :value="modelValue"
          class="collab-editor__textarea"
          spellcheck="false"
          @input="onInput"
        />
      </label>

      <!-- 右：实时预览。渲染走同一个 renderMarkdown，与前台详情页口径一致 -->
      <div class="collab-editor__pane">
        <span class="collab-editor__pane-label">{{ t('myPosts.collab.preview') }}</span>
        <div class="collab-editor__preview prose-content" v-html="html"/>
      </div>
    </div>
  </div>
</template>

<style scoped>
.collab-editor {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--el-border-color);
  border-radius: var(--admin-radius, 6px);
  overflow: hidden;
  background: var(--el-bg-color);
}

.collab-editor__head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.collab-editor__spacer {
  flex: 1;
}

.collab-editor__badge {
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--el-fill-color);
  color: var(--el-text-color-regular);
}

/* 状态用颜色区分，但**不只靠颜色**——文案本身也说明了状态 */
.collab-editor__badge[data-status='connected'] {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}

.collab-editor__badge[data-status='connecting'] {
  background: var(--el-color-warning-light-9);
  color: var(--el-color-warning);
}

.collab-editor__badge[data-status='disconnected'],
.collab-editor__badge[data-status='error'] {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}

/*
 * 左右分栏：窄屏堆叠（上下），宽屏并排。
 * 用 `minmax(0, 1fr)` 而不是 `1fr`：否则长代码行会把栅格撑破。
 */
.collab-editor__split {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  min-height: 420px;
}

@media (min-width: 1024px) {
  .collab-editor__split {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
}

.collab-editor__pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.collab-editor__pane + .collab-editor__pane {
  border-top: 1px solid var(--el-border-color-lighter);
}

@media (min-width: 1024px) {
  .collab-editor__pane + .collab-editor__pane {
    border-top: none;
    border-left: 1px solid var(--el-border-color-lighter);
  }
}

.collab-editor__pane-label {
  padding: 6px 12px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  background: var(--el-fill-color-lighter);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.collab-editor__textarea {
  flex: 1;
  width: 100%;
  min-height: 360px;
  padding: 12px;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  color: var(--el-text-color-primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.7;
  tab-size: 2;
}

.collab-editor__textarea:read-only {
  color: var(--el-text-color-regular);
  background: var(--el-fill-color-lighter);
}

.collab-editor__preview {
  flex: 1;
  min-height: 360px;
  max-height: 70vh;
  padding: 12px 16px;
  overflow: auto;
}

/*
 * 预览区不重复写一套排版规则 —— 复用 `prose-content`（前台详情页在用的正文样式），
 * 只补两处它在编辑器场景下需要的约束。这样"预览看到的"与"发布后的"排版一致。
 */
.collab-editor__preview :deep(pre) {
  overflow-x: auto;
}

.collab-editor__preview :deep(img) {
  max-width: 100%;
  height: auto;
}
</style>
