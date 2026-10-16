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
definePageMeta({layout: 'default', middleware: 'auth', title: 'myPosts.editTitle'})

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

function onSaved(): void {
  message.value = t('myPosts.saved')
}
</script>

<template>
  <div :data-editor-layout="layout" class="space-y-4">
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
      @restore="onRestore"
    />

    <ArticleEditor
      v-if="!fromInvite"
      :key="editorKey"
      :article-id="articleId"
      :initial-content="restoredContent || undefined"
      :hide-body="collab.active.value"
      @saved="onSaved"
    />
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

/* 分栏预览：正文收窄，右侧留出预览栏的位置 */
[data-editor-layout='split'] :deep(.max-w-read) {
  max-width: 34rem;
  margin-inline: 0;
}

[data-editor-layout='split'] {
  max-width: 1100px;
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
