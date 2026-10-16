<script lang="ts" setup>
/**
 * 编辑文章（账号中心）
 *
 * 对应原 astro 的 `my/posts/edit.astro`。
 *
 * ## 两种状态，同一个页面
 *
 * - **普通编辑**：交给 `ArticleEditor`（富文本、标题、分类、标签、发布设置…）
 * - **协作编辑**：正文区换成 `CollabEditor`（Markdown 源码 + 实时预览，
 *   由 Yjs 驱动多人同步），其余管理字段仍由作者在退出协作后维护
 *
 * 协作是**同一页内的一个状态**，不是独立页面 —— 协作者从邀请链接进来时
 * 直接落在这一页上（URL 带 `?invite=<code>`），不需要跳转。
 *
 * ## 权限边界
 *
 * 谁能进、能进多久、最多几个人，**全部由后端强制**（`collaboration_invites`
 * 真表 + `invite_service`）。前端只负责展示与调用，**不做任何准入判断** ——
 * 前端判断等于没有边界。
 */
definePageMeta({layout: 'default', middleware: 'auth', title: 'myPosts.editTitle', applyTheme: false})

import {renderMarkdown} from '@/utils/markdown'

const route = useRoute()
const articleId = computed(() => Number(route.params.id))

const {t} = useI18n()

const message = ref('')

// ---------------------------------------------------------------- 协作会话

const collab = useCollabSession(articleId)

/** 邀请参数（所有者在开启协作时可配） */
const inviteHours = ref(24)
const inviteMaxUses = ref(5)

/** 是否是从邀请链接进来的协作者（决定显示"邀请设置"还是"协作中"） */
const fromInvite = computed(() => {
  if (typeof window === 'undefined') return false
  return new URLSearchParams(window.location.search).has('invite')
})

async function onStartCollab(): Promise<void> {
  await collab.start({expiresInHours: inviteHours.value, maxUses: inviteMaxUses.value})
}

async function onCopyInvite(): Promise<void> {
  if (!collab.inviteUrl.value) return
  try {
    await navigator.clipboard.writeText(collab.inviteUrl.value)
    pushToast(t('myPosts.collab.copied'), 'success')
  } catch {
    pushToast(t('myPosts.collab.copyFailed'), 'error')
  }
}

/**
 * 协作者从邀请链接进来时**自动加入房间**。
 *
 * 不自动加入的话，页面会完全空白：`ArticleEditor` 因 `fromInvite` 不渲染，
 * 而 `CollabEditor` 又因 `active` 仍为 false 也不渲染 —— 两个分支都不命中。
 *
 * 这里**必须用 `join()` 而不是 `start()`**：`start()` 会尝试签发邀请，
 * 而签发只允许文章所有者（后端 `_assert_target_owner` 会拒绝）。
 */
onMounted(() => {
  if (fromInvite.value && !collab.active.value) collab.join()
})

/** 从历史版本恢复过来的正文（供填回编辑器） */
const restoredContent = ref('')

/**
 * 历史里点「恢复」时：后端已经把该版本作为**新修订**写回（历史不丢），
 * 这里把正文交给编辑器。用 `:key` 重建编辑器是刻意的 ——
 * `ArticleEditor` 内部持有自己的表单状态，仅改 prop 不会重载正文。
 */
const editorKey = ref(0)

function onRestore(content: string): void {
  restoredContent.value = content
  editorKey.value += 1
  pushToast(t('myPosts.collab.history.restoreToEditor'), 'success')
}

// ---------------------------------------------------------------- 布局

/**
 * 三种布局：经典 / 专注 / 分栏预览。
 *
 * - `classic` 全宽，协作与历史都在手边
 * - `focus` 收窄居中，并隐藏协作条与历史按钮 —— 长文写作时去掉干扰
 * - `split` 正文区收窄，右侧留出预览栏
 */
const {layout, setLayout, isFocus, isSplit} = useEditorLayout()

const LAYOUT_LABELS: Record<string, string> = {
  classic: 'myPosts.layout.classic',
  focus: 'myPosts.layout.focus',
  split: 'myPosts.layout.split',
}

/**
 * 分栏预览：读编辑器里**当前（可能未保存）**的正文渲染成 HTML。
 *
 * 用 `ArticleEditor` 暴露出来的 `content` 而不是另发一次请求 —— 预览要反映
 * "我正在写的东西"，而不是"上次保存的东西"，后者会让人以为改动丢了。
 */
const editorRef = ref<{
  content?: string
  title?: string
  dirty?: boolean
  savedAt?: string | null
  save?: () => unknown
} | null>(null)
const previewHtml = computed(() => renderMarkdown(editorRef.value?.content ?? ''))

/**
 * 底部状态带的数据。
 *
 * 字数按**去掉 HTML 标签后的字符数**算 —— 正文可能是 Tiptap 的 HTML，
 * 直接 `content.length` 会把标签也算进去，数字会大得离谱且随格式变化。
 */
const charCount = computed(() => {
  const raw = editorRef.value?.content ?? ''
  return raw.replace(/<[^>]*>/g, '').replace(/\s+/g, '').length
})

/** 中文阅读速度约 300 字/分钟，取整且至少 1 分钟 */
const readMinutes = computed(() => Math.max(1, Math.round(charCount.value / 300)))

const savedLabel = computed(() => {
  const at = editorRef.value?.savedAt
  if (!at) return ''
  const d = new Date(at)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString()
})

function onSaved(): void {
  message.value = t('myPosts.saved')
}
</script>

<template>
  <div :data-editor-layout="layout" class="space-y-4">
    <!--
      吸顶操作条：长文滚动时"返回 / 标题 / 保存"始终可达。
      背景用不透明色 + z-index，避免正文从下面透出来。
    -->
    <header v-if="!fromInvite" class="editor-topbar">
      <NuxtLink class="editor-topbar__back" to="/my/posts">
        ← {{ t('myPosts.layout.back') }}
      </NuxtLink>
      <span class="editor-topbar__title">{{ editorRef?.title || t('myPosts.layout.untitled') }}</span>
      <span v-if="editorRef?.dirty" :title="t('myPosts.layout.statusDirty')" class="editor-topbar__dot">●</span>
      <button class="editor-topbar__save" type="button" @click="editorRef?.save?.()">
        {{ t('myPosts.layout.save') }}
      </button>
    </header>

    <!-- 布局切换：按钮组，选择写入 localStorage（个人偏好，不做成 URL 参数） -->
    <div :aria-label="t('myPosts.layout.label')" class="layout-switch" role="group">
      <button
        v-for="(key, name) in LAYOUT_LABELS"
        :key="name"
        :aria-pressed="layout === name"
        :class="{'is-active': layout === name}"
        class="layout-switch__btn"
        type="button"
        @click="setLayout(name as never)"
      >
        {{ t(key) }}
      </button>
    </div>
    <!-- 注意：本页在 `layout: 'default'`（前台布局）下，**没有注册 Element Plus**，
         所以这里一律用原生控件。用 el-* 会静默解析失败（控制台只有一条 warn，
         界面上则什么都不渲染）。 -->
    <div v-if="message" class="collab-alert">{{ message }}</div>

    <!-- 协作工具条：普通态显示"开启协作"，协作态显示状态与邀请 -->
    <section class="collab-bar">
      <template v-if="!collab.active.value">
        <div class="collab-bar__lead">
          <strong>{{ t('myPosts.collab.title') }}</strong>
          <span class="collab-bar__hint">{{ t('myPosts.collab.hint') }}</span>
        </div>

        <label class="collab-bar__field">
          <span>{{ t('myPosts.collab.hours') }}</span>
          <input v-model.number="inviteHours" class="collab-bar__num" max="720" min="1" type="number">
        </label>

        <label class="collab-bar__field">
          <span>{{ t('myPosts.collab.maxUses') }}</span>
          <input v-model.number="inviteMaxUses" class="collab-bar__num" max="50" min="1" type="number">
        </label>

        <button :disabled="collab.inviting.value" class="collab-btn collab-btn--primary"
                type="button" @click="onStartCollab">
          {{ t('myPosts.collab.start') }}
        </button>
      </template>

      <template v-else>
        <div class="collab-bar__lead">
          <span :data-status="collab.status.value" class="collab-bar__badge">
            {{ collab.statusLabel.value }}
          </span>
          <span class="collab-bar__hint">
            {{ t('myPosts.collab.online', {count: collab.online.value}) }}
          </span>
        </div>

        <!-- 邀请链接只对所有者显示；协作者没有签发权 -->
        <template v-if="collab.isOwner.value && collab.inviteUrl.value">
          <input :value="collab.inviteUrl.value" class="collab-bar__url" readonly>
          <button class="collab-btn" type="button" @click="onCopyInvite">
            {{ t('myPosts.collab.copy') }}
          </button>
        </template>
        <span v-else-if="!collab.isOwner.value" class="collab-bar__hint">
          {{ t('myPosts.collab.joinedAsGuest') }}
        </span>

        <div class="collab-bar__spacer"/>

        <button :disabled="collab.saving.value" class="collab-btn" type="button" @click="collab.saveToArticle">
          {{ t('myPosts.collab.saveToArticle') }}
        </button>
        <button class="collab-btn collab-btn--danger" type="button" @click="collab.stop">
          {{ t('myPosts.collab.stop') }}
        </button>
      </template>
    </section>

    <!--
      字段区**只给所有者**。

      `ArticleEditor` 走后台接口 `/content/article/{id}` 取数，而那个接口按**归属**
      校验（非本人 404）。协作者是从邀请链接进来的，没有归属权 —— 渲染它就会
      报「加载文章失败，可能不存在或不属于你」。协作者本来就只能编辑正文。
    -->
    <!--
      历史是**抽屉**（默认关闭），不常驻占版面 ——
      看历史是低频动作，不该跟正文抢横向空间。
      触发按钮与历史面板都**仅作者可见**：协作者没有归属权，读版本会被后端拒。
    -->
    <ArticleHistoryPanel
      v-if="!fromInvite"
      :article-id="articleId"
      :current-content="editorRef?.content ?? ''"
      @restore="onRestore"
    />

    <!--
      分栏预览：右侧实时渲染当前正文（未保存的改动也会显示）。
      编辑器与预览各占一列 —— 用**明确的容器类**定位，不用 `:not()` 通配：
      通配会把编辑器也框进"跨两列"，与预览栏重叠（这是实际发生过的 bug）。
    -->
    <div v-if="!fromInvite" class="editor-slot">
      <ArticleEditor
        :key="editorKey"
        ref="editorRef"
        :article-id="articleId"
        :hide-body="collab.active.value"
        :initial-content="restoredContent || undefined"
        :layout="layout === 'classic' ? 'two-column' : 'stacked'"
        @saved="onSaved"
      />
    </div>

    <aside v-if="isSplit && !collab.active.value" class="split-preview">
      <header class="split-preview__head">{{ t('myPosts.layout.previewTitle') }}</header>
      <!-- eslint-disable-next-line vue/no-v-html -- 内容来自本站用户自己的 Markdown，经 renderMarkdown 净化 -->
      <div class="prose split-preview__body" v-html="previewHtml"/>
    </aside>

    <!-- 底部状态带：写完一段最想确认的就是"多少字、存没存" -->
    <footer v-if="!fromInvite && !collab.active.value" class="editor-status">
      <span>{{ t('myPosts.layout.statusChars', {n: charCount}) }}</span>
      <span class="editor-status__sep">·</span>
      <span>{{ t('myPosts.layout.statusMinutes', {n: readMinutes}) }}</span>
      <template v-if="savedLabel">
        <span class="editor-status__sep">·</span>
        <span>{{ t('myPosts.layout.statusSavedAt', {time: savedLabel}) }}</span>
      </template>
      <span v-if="editorRef?.dirty" class="editor-status__dirty">
        ● {{ t('myPosts.layout.statusDirty') }}
      </span>
    </footer>
    <CollabEditor
      v-if="collab.active.value"
      :model-value="collab.text.value"
      :online="collab.online.value + 1"
      :status="collab.status.value"
      @update:model-value="collab.applyLocal"
    />
  </div>
</template>

<style scoped>
/* ── 吸顶操作条 ──────────────────────────────────────────── */

.editor-topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  /* 必须不透明：否则正文会从下面透出来 */
  background: #fff;
  border-bottom: 1px solid var(--el-border-color-lighter, #ebeef5);
}

.editor-topbar__back {
  flex-shrink: 0;
  font-size: 13px;
  color: #606266;
  text-decoration: none;
}

.editor-topbar__back:hover {
  color: #2271b1;
}

.editor-topbar__title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.editor-topbar__dot {
  flex-shrink: 0;
  color: #e6a23c;
  font-size: 10px;
}

.editor-topbar__save {
  flex-shrink: 0;
  padding: 4px 14px;
  border: 1px solid #2271b1;
  border-radius: 4px;
  background: #2271b1;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}

.editor-topbar__save:hover {
  filter: brightness(0.95);
}

.editor-topbar__back:focus-visible,
.editor-topbar__save:focus-visible {
  outline: 2px solid #2271b1;
  outline-offset: 2px;
}

/* 分栏模式下吸顶条跨满两列 */
[data-editor-layout='split'] > .editor-topbar {
  grid-column: 1 / -1;
}

/* ── 布局切换 ──────────────────────────────────────────── */

.layout-switch {
  display: inline-flex;
  gap: 2px;
  align-self: flex-start;
  padding: 2px;
  border: 1px solid var(--el-border-color, #dcdfe6);
  border-radius: 6px;
  background: #f5f7fa;
}

.layout-switch__btn {
  padding: 4px 12px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #606266;
  font-size: 12px;
  cursor: pointer;
}

.layout-switch__btn.is-active {
  background: #fff;
  color: #2271b1;
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.08);
}

.layout-switch__btn:focus-visible {
  outline: 2px solid #2271b1;
  outline-offset: 1px;
}

/*
 * 专注模式：收窄居中，并把协作条、历史触发按钮、布局切换之外的非正文元素淡出。
 * 用 `max-width` 而不是 `display:none` —— 完全隐藏会让用户找不到怎么切回去。
 */
[data-editor-layout='focus'] .collab-bar,
[data-editor-layout='focus'] .hist-trigger {
  display: none;
}

[data-editor-layout='focus'] :deep(.max-w-read) {
  max-width: 42rem;
  margin-inline: auto;
}

/*
 * 分栏预览：编辑器占左列、预览占右列，横幅类元素（吸顶条/布局切换/协作条/状态带）
 * 跨满两列。
 *
 * 各元素列位**写死**，不用 `:not()` 通配 —— 早先版本写成
 * `> :not(.split-preview) { grid-column: 1 / -1 }`，结果把编辑器也框进"跨两列"，
 * 与右侧预览栏重叠（实际发生过的 bug）。通配看起来省事，但会把"没想到的元素"
 * 也一起改掉，而这种错只有在真渲染出来时才看得见。
 */
[data-editor-layout='split'] {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
  /* 刻意**不设** max-width：根容器已被 `lg:max-w-none` 放宽，
     这里再限宽会让整页贴在左边、右侧留出大片空白（实际发生过）。 */
}

[data-editor-layout='split'] > .editor-slot {
  grid-column: 1;
  min-width: 0; /* 允许内部长内容收缩，否则 grid 列会被撑破 */
}

[data-editor-layout='split'] > .split-preview {
  grid-column: 2;
}

[data-editor-layout='split'] > .editor-topbar,
[data-editor-layout='split'] > .layout-switch,
[data-editor-layout='split'] > .collab-alert,
[data-editor-layout='split'] > .collab-bar,
[data-editor-layout='split'] > .editor-status {
  grid-column: 1 / -1;
}

.split-preview__head {
  position: sticky;
  top: 0;
  padding-bottom: 8px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--color-line, var(--el-border-color-lighter, #ebeef5));
  /* 跟随深浅色，不写死白色 —— 否则深色模式下头部会是一块刺眼的亮条 */
  background: var(--color-surface, #fff);
  color: var(--color-fg-muted, #909399);
  font-size: 12px;
}

.split-preview__body {
  font-size: 14px;
  line-height: 1.7;
}

/* 预览栏的外框（列位在别处指定，这里只管外观）
 *
 * 颜色一律走**站点令牌**而不是写死 `#fff` —— 站点可能处于深色模式，
 * 写死白底会让正文变成"浅灰字压白底"，对比度跌到不可读（实际发生过）。
 * 与主题令牌（--color-*）的区别：那些由主题设置驱动、不随深浅色变化，
 * 这里要的恰恰是**跟随深浅色**，所以用 --color-surface / --color-fg。 */
.split-preview {
  align-self: start;
  max-height: calc(100vh - 32px);
  overflow: auto;
  padding: 16px;
  border: 1px solid var(--color-line, var(--el-border-color-lighter, #ebeef5));
  border-radius: 6px;
  background: var(--color-surface, #fff);
  color: var(--color-fg, #1d2327);
}

/* 底部状态带：常驻但不抢视觉，只在信息层面回答"多少字、存没存" */
.editor-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 2px;
  font-size: 12px;
  color: #909399;
  border-top: 1px solid var(--el-border-color-lighter, #ebeef5);
}

.editor-status__sep {
  color: #dcdfe6;
}

.editor-status__dirty {
  margin-left: auto;
  color: #e6a23c;
}

/* 历史触发按钮是"自身宽度"的元素 —— 网格里不加约束会被拉伸成整行（实际发生过）。
   必须用 `:deep()`：该按钮在子组件内，带的是子组件的 scoped 属性，
   父组件的 `> .hist-trigger` 匹配不到它。注意不能写成 `> :deep(...)`，那是无效语法。 */
[data-editor-layout='split'] :deep(.hist-trigger) {
  justify-self: start;
}

/* ── 协作工具条 ──────────────────────────────────────────── */

.collab-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--admin-radius, 6px);
  background: var(--el-bg-color);
}

.collab-bar__lead {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.collab-bar__hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.collab-bar__field {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--el-text-color-regular, #606266);
}

/* 原生控件的样式：本页没有 Element Plus，所以这些必须自己写 */
.collab-alert {
  padding: 8px 12px;
  border-radius: 6px;
  background: #f0f9eb;
  color: #67c23a;
  font-size: 13px;
}

.collab-bar__num {
  width: 72px;
  padding: 4px 6px;
  border: 1px solid var(--el-border-color, #dcdfe6);
  border-radius: 4px;
  font-size: 13px;
  color: inherit;
  background: var(--el-bg-color, #fff);
}

.collab-btn {
  padding: 6px 14px;
  border: 1px solid var(--el-border-color, #dcdfe6);
  border-radius: 4px;
  background: var(--el-bg-color, #fff);
  color: var(--el-text-color-regular, #606266);
  font-size: 13px;
  line-height: 1.4;
  cursor: pointer;
  transition: opacity 150ms ease;
}

.collab-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* 焦点可见：键盘用户必须看得见自己在哪（与主题侧同一口径） */
.collab-btn:focus-visible,
.collab-bar__num:focus-visible,
.collab-bar__url:focus-visible {
  outline: 2px solid var(--el-color-primary, #2271b1);
  outline-offset: 2px;
}

.collab-btn--primary {
  border-color: var(--el-color-primary, #2271b1);
  background: var(--el-color-primary, #2271b1);
  color: #fff;
}

.collab-btn--danger {
  border-color: var(--el-color-danger, #d63638);
  color: var(--el-color-danger, #d63638);
}

.collab-bar__url {
  flex: 1;
  min-width: 240px;
}

.collab-bar__spacer {
  flex: 1;
}

.collab-bar__badge {
  align-self: flex-start;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  background: var(--el-fill-color);
  color: var(--el-text-color-regular);
}

.collab-bar__badge[data-status='connected'],
.collab-bar__badge[data-status='synced'] {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}

.collab-bar__badge[data-status='connecting'] {
  background: var(--el-color-warning-light-9);
  color: var(--el-color-warning);
}

.collab-bar__badge[data-status='disconnected'],
.collab-bar__badge[data-status='rejected'] {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}
</style>
