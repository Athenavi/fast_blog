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

function onSaved(): void {
  message.value = t('myPosts.saved')
}
</script>

<template>
  <div class="space-y-4">
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
    <ArticleEditor
      v-if="!fromInvite"
      :article-id="articleId"
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
