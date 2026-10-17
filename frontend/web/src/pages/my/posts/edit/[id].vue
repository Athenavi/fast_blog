<script lang="ts" setup>
/**
 * 编辑文章（账号中心）—— 与后台编辑页共用 `DocWorkspace` 外壳
 *
 * 对应原 astro 的 `my/posts/edit.astro`。`/my/posts/edit/new` 新建、
 * `/my/posts/edit/{id}` 编辑，同一页两种状态（原来是另有一个 `/my/posts/create`，
 * 两个文件的字段与保存逻辑几乎逐行重复，分叉只早晚问题，已合并）。
 *
 * ## 同一个编辑器，两种内容来源
 *
 * 正文只有 **Markdown 源码**这一种（`MarkdownEditor`，CodeMirror 6）：
 * 项目存的就是 Markdown，中间再架一层富文本就要每次编辑都过一次有损的序列化往返。
 * 排版效果看工作台的**分栏预览**，不是看另一种编辑视图 ——
 * 所以原来那个「富文本 / 源码」切换按钮连同它背后的两套状态一起删了。
 *
 * 协作是**同一页内的一个状态**，不是独立页面 —— 协作者从邀请链接进来时直接落在
 * 这一页上（URL 带 `?invite=<code>`）。协作态只是把编辑器的内容来源从表单缓冲区
 * 换成房间里的 `Y.Text`，版面、目录、预览一概不变。
 *
 * ## 权限边界
 *
 * 谁能进、能进多久、最多几个人，**全部由后端强制**（`collaboration_invites` 真表 +
 * `invite_service`）。前端只负责展示与调用，**不做任何准入判断** —— 前端判断等于没有边界。
 *
 * 唯一一处例外是**渲染层面**的：从邀请链接进来的协作者没有归属权，
 * 所以不渲染设置字段与历史面板 —— 那些都走 `/content/article/{id}`，非本人会 404，
 * 报错信息还是「文章不存在」。这不是权限判断，只是不去发必然失败的请求。
 */
definePageMeta({layout: 'default', middleware: 'auth', title: 'myPosts.editTitle', applyTheme: false})

import ArticleHistoryPanel from '@/components/admin/ArticleHistoryPanel.vue'
import ArticleSettingsFields from '@/components/editor/ArticleSettingsFields.vue'
import DocWorkspace from '@/components/editor/DocWorkspace.vue'
import MarkdownEditor from '@/components/editor/MarkdownEditor.vue'
import {categoryApi, mobileApi, type CategoryItem} from '@/api/public'
import {useArticleForm} from '@/composables/useArticleForm'
import {useDocViewMode} from '@/composables/useDocViewMode'
import {useSaveShortcut} from '@/composables/useSaveShortcut'
import {countContentUnits, headingsFromMarkdown} from '@/utils/content'
import {formatDateTime} from '@/utils/format'
import {renderMarkdown} from '@/utils/markdown'

const route = useRoute()
const router = useRouter()
const {t} = useI18n()

const routeId = computed(() => String(route.params.id ?? 'new'))
const articleId = computed<number | null>(() => (routeId.value === 'new' ? null : Number(routeId.value)))
const isNew = computed(() => articleId.value === null)

/** 邀请参数（所有者在开启协作时可配） */
const inviteHours = ref(24)
const inviteMaxUses = ref(5)

/**
 * 是否从邀请链接进来。
 *
 * 用 `window.location.search` 而不是 `route.query`：本页在 `definePageMeta` 之外
 * 没有 SSR 数据依赖，而协作那套（`useCollabSession`）本来就只在客户端跑。
 */
const fromInvite = computed(() => {
  if (typeof window === 'undefined') return false
  return new URLSearchParams(window.location.search).has('invite')
})

const collab = useCollabSession(computed(() => articleId.value ?? 0))
const {mode, setMode} = useDocViewMode()

const {
  form,
  loading,
  saving,
  dirty,
  savedAt,
  notFound,
  error,
  markDirty,
  load,
  save,
  draftAvailable,
  restoreDraft,
  discardDraft,
} = useArticleForm({
  mode: 'contributor',
  articleId,
  messages: {
    titleRequired: t('myPosts.titleRequired'),
    saveFailed: t('myPosts.saveFailed'),
    loadFailed: t('myPosts.loadFailed'),
  },
})

const ready = computed(() => !loading.value && !notFound.value)

/** 普通编辑才归本页的表单管；协作态的正文在 Yjs 里，保存走协作条 */
const isCollab = computed(() => collab.active.value)

/**
 * 编辑器的实例引用。
 *
 * 外壳要点目录跳到「源码里第 N 个标题那一行」，而那一行只有编辑器自己找得到，
 * 所以把这个 ref 交给 `DocWorkspace` 的 `sourceAnchor`（它只认 `lineElAt` 一个方法）。
 */
const editor = ref<InstanceType<typeof MarkdownEditor> | null>(null)

/**
 * 编辑器改动写回表单。
 *
 * 协作态**直接返回**：那时正文归房间里的 `Y.Text`，写进 `form.content` 等于凭空造出
 * 第二份正文，两边会互相追（而且落库时谁赢看不出来）。
 * 结束协作时由 `stopCollab()` 把房间里的最终文本一次性交回表单。
 */
function onContentInput(value: string): void {
  if (isCollab.value) return
  form.content = value
  markDirty()
}

/**
 * 大纲、字数、预览同读**一份字符串**。
 *
 * 协作态读的是 Yjs 里的文本而不是 `form.content` —— 此时 `form.content` 还是
 * 开启协作之前的旧正文，拿它建目录会得到一份与屏幕上完全不符的大纲。
 */
const sourceText = computed(() => (isCollab.value ? collab.text.value : form.content))
const outline = computed(() => headingsFromMarkdown(sourceText.value))
const stats = computed(() => countContentUnits(sourceText.value))
const previewHtml = computed(() => renderMarkdown(sourceText.value))

// ---------------------------------------------------------------- 加载

const categories = ref<CategoryItem[]>([])

async function loadCategories(): Promise<void> {
  try {
    const tree = await categoryApi.publicTree()
    // 展平为一级 + 二级，用全角空格缩进表示层级，便于原生 select 显示
    const flat: CategoryItem[] = []
    const walk = (items: CategoryItem[], depth = 0) => {
      for (const item of items) {
        flat.push({...item, name: `${'　'.repeat(depth)}${item.name}`})
        if (item.children?.length) walk(item.children, depth + 1)
      }
    }
    walk(tree)
    categories.value = flat
  } catch {
    categories.value = []
  }
}

/**
 * 协作者从邀请链接进来时**自动加入房间**。
 *
 * 不自动加入的话，协作者对着的是一个**空正文**：设置字段因 `fromInvite` 不渲染，
 * 房间也没连上 —— 很容易让人以为文章本来就是空的，然后一保存就真的空了。
 *
 * 这里**必须用 `join()` 而不是 `start()`**：`start()` 会尝试签发邀请，
 * 而签发只允许文章所有者（后端 `_assert_target_owner` 会拒绝）。
 */
onMounted(async () => {
  if (fromInvite.value && !collab.active.value) collab.join()
  if (fromInvite.value) return
  await Promise.all([loadCategories(), load()])
})

// ---------------------------------------------------------------- 保存

const message = ref('')

async function submit(): Promise<void> {
  message.value = ''
  const result = await save()
  if (!result.ok) return
  message.value = isNew.value ? t('myPosts.draftCreated') : t('myPosts.saved')
  // 新建成功后进入编辑态：URL 里还是 `new` 的话，历史面板与协作都无从挂上
  if (result.id !== null && articleId.value === null) await router.replace(`/my/posts/edit/${result.id}`)
}

/** Ctrl/Cmd + S 与顶栏「保存」同义；协作态下让位给协作条的落库按钮 */
useSaveShortcut(() => submit(), {enabled: () => !saving.value && !loading.value && !isCollab.value})

function onTitleInput(value: string): void {
  form.title = value
  markDirty()
}

/** 上传封面：走移动端封面专用端点（`POST /mobile/media/upload/article-cover`） */
async function pickCover(): Promise<void> {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    saving.value = true
    try {
      const uploaded = await mobileApi.mediaUploadArticleCover(file)
      form.cover_image = uploaded.file_url ?? ''
      markDirty()
      message.value = t('myPosts.coverUploaded')
    } catch {
      error.value = t('myPosts.coverUploadFailed')
    } finally {
      saving.value = false
    }
  }
  input.click()
}

// ---------------------------------------------------------------- 协作

async function onStartCollab(): Promise<void> {
  await collab.start({expiresInHours: inviteHours.value, maxUses: inviteMaxUses.value})
}

/**
 * 结束协作：先把房间里的最终文本交回表单，再断线。
 *
 * 顺序不能反 —— `leave()` 会把正文快照清空。原来是断完就回到富文本编辑器，
 * 里面还躺着开启协作**之前**的那份正文：屏幕上看着没丢，按一次保存就把
 * 协作期间写的东西全覆盖了。
 */
function stopCollab(): void {
  const final = collab.text.value
  collab.stop()
  form.content = final
  markDirty()
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
 * 从历史版本恢复：直接把正文写回表单。
 *
 * 原来是给 `ArticleEditor` 换 `:key` 强制重建 —— 因为表单状态在那个组件**内部**，
 * 只改 prop 不会重载。现在表单归本页的 `useArticleForm` 持有，直接赋值就够了，
 * 而重建编辑器会连带丢掉撤销历史与光标位置，没有任何理由。
 */
function onRestore(content: string): void {
  form.content = content
  markDirty()
  pushToast(t('myPosts.collab.history.restoreToEditor'), 'success')
}
</script>

<template>
  <DocWorkspace
    :dirty="dirty"
    :editable="ready && !fromInvite"
    :items="outline"
    :minutes="stats.minutes"
    :mode="mode"
    :saved-at="savedAt"
    :saving="saving"
    :source-anchor="editor"
    sticky-offset="57px"
    :title="form.title"
    :title-maxlength="255"
    :title-placeholder="$t('myPosts.titlePlaceholder')"
    :units="stats.units"
    @update:mode="setMode"
    @update:title="onTitleInput"
  >
    <template #breadcrumb>
      <NuxtLink class="crumb crumb--link" to="/my/posts">{{ $t('myPosts.title') }}</NuxtLink>
      <Icon class="h-3 w-3" name="chevron-right"/>
      <span class="crumb crumb--current">
        {{ isNew ? $t('myPosts.createTitle') : $t('myPosts.editTitle') }}
      </span>
    </template>

    <template #status>
      <span class="notice">{{ $t('myPosts.draftNotice') }}</span>
    </template>

    <template v-if="!fromInvite" #actions>
      <ArticleHistoryPanel
        v-if="articleId !== null"
        :article-id="articleId"
        :current-content="sourceText"
        @restore="onRestore"
      />
      <Button
        v-if="!isCollab"
        :disabled="saving || loading"
        type="button"
        @click="submit"
      >
        <Icon v-if="saving" class="h-4 w-4 animate-spin" name="loader-circle"/>
        <Icon v-else class="h-4 w-4" name="save"/>
        {{ isNew ? $t('myPosts.saveDraft') : $t('myPosts.saveUpdate') }}
      </Button>
    </template>

    <!--
      横幅区：本地草稿 / 保存结果 / 协作工具条。
      放在正文之上、标题之下，因为这几件事都在回答「我这份内容现在安全吗」。
    -->
    <template v-if="!fromInvite || isCollab" #banner>
      <div class="banner-stack">
        <div
          v-if="draftAvailable"
          class="notice-row notice-row--warning"
          role="status"
        >
          <Icon class="h-4 w-4 shrink-0" name="alert-circle"/>
          <span class="flex-1">
            {{ $t('common.localDraftFound', {time: formatDateTime(draftAvailable.savedAt)}) }}
          </span>
          <Button size="sm" type="button" @click="restoreDraft">{{ $t('common.localDraftRestore') }}</Button>
          <Button size="sm" type="button" variant="outline" @click="discardDraft">
            {{ $t('common.localDraftDiscard') }}
          </Button>
        </div>

        <p v-if="error" class="notice-row notice-row--danger" role="alert">{{ error }}</p>
        <p v-else-if="message" class="notice-row notice-row--success" role="status">{{ message }}</p>

        <!--
          协作工具条：普通态显示「开启协作」，协作态显示连接状态与邀请链接。
          协作者（`fromInvite`）只看到状态与落库/退出按钮，没有签发权。
        -->
        <section class="collab-bar">
          <template v-if="!isCollab">
            <div class="collab-bar__lead">
              <strong>{{ $t('myPosts.collab.title') }}</strong>
              <span class="collab-bar__hint">{{ $t('myPosts.collab.hint') }}</span>
            </div>

            <label class="collab-bar__field">
              <span>{{ $t('myPosts.collab.hours') }}</span>
              <input v-model.number="inviteHours" class="collab-bar__num" max="720" min="1" type="number">
            </label>

            <label class="collab-bar__field">
              <span>{{ $t('myPosts.collab.maxUses') }}</span>
              <input v-model.number="inviteMaxUses" class="collab-bar__num" max="50" min="1" type="number">
            </label>

            <Button :disabled="collab.inviting.value" class="flex-none" type="button" @click="onStartCollab">
              {{ $t('myPosts.collab.start') }}
            </Button>
          </template>

          <template v-else>
            <div class="collab-bar__lead">
              <span :data-status="collab.status.value" class="collab-bar__badge">
                {{ collab.statusLabel.value }}
              </span>
              <span class="collab-bar__hint">
                {{ $t('myPosts.collab.online', {count: collab.online.value}) }}
              </span>
            </div>

            <!-- 邀请链接只对所有者显示；协作者没有签发权 -->
            <template v-if="collab.isOwner.value && collab.inviteUrl.value">
              <input :value="collab.inviteUrl.value" class="collab-bar__url" readonly>
              <Button size="sm" type="button" variant="outline" @click="onCopyInvite">
                {{ $t('myPosts.collab.copy') }}
              </Button>
            </template>
            <span v-else-if="!collab.isOwner.value" class="collab-bar__hint">
              {{ $t('myPosts.collab.joinedAsGuest') }}
            </span>

            <span class="collab-bar__spacer"/>

            <Button :disabled="collab.saving.value" size="sm" type="button" @click="collab.saveToArticle">
              {{ $t('myPosts.collab.saveToArticle') }}
            </Button>
            <Button size="sm" type="button" variant="ghost" @click="stopCollab">
              {{ $t('myPosts.collab.stop') }}
            </Button>
          </template>
        </section>
      </div>
    </template>

    <template #document>
      <div v-if="loading" class="space-y-3">
        <Skeleton class="h-10 w-full"/>
        <Skeleton class="h-64 w-full"/>
      </div>

      <AdminEmpty
        v-else-if="notFound"
        :desc="$t('myPosts.loadFailed')"
        variant="error"
      />

      <!--
        协作态只换内容来源（`collab` 从 null 变成房间里的 Y.Text），编辑器本体不换。
        同一篇正文不能同时被两个视图持有，否则保存时必然互相覆盖；
        而 `form.content` 在这一态**不参与绑定**，见 `onContentInput`。
      -->
      <MarkdownEditor
        v-else
        ref="editor"
        :collab="collab.binding.value"
        :editable="ready"
        :label="$t('editor.md.ariaLabel')"
        :model-value="form.content"
        :placeholder="$t('editor.md.placeholder')"
        @update:model-value="onContentInput"
      />
    </template>

    <template #preview>
      <!-- 标题用 <p> 而不是 <h1>：外壳按「第 N 个标题元素」定位目录项，多一个 h 标签会全体错位 -->
      <p class="preview-title">{{ form.title || $t('myPosts.titlePlaceholder') }}</p>
      <p class="preview-note">{{ $t('editor.doc.previewNote') }}</p>
      <!-- eslint-disable-next-line vue/no-v-html —— renderMarkdown 是项目内唯一的渲染+净化出口 -->
      <div class="prose-content" v-html="previewHtml"/>
    </template>

    <template v-if="!fromInvite" #settings>
      <ArticleSettingsFields
        :categories="categories"
        :form="form"
        @change="markDirty"
        @upload-cover="pickCover"
      />
    </template>
  </DocWorkspace>
</template>

<style scoped>
/*
 * 外壳负责文档栏、大纲栏、纸张留白与设置抽屉；这里只留它管不着的局部样式。
 * 颜色一律走 `--color-*` 令牌：本页会处于深色模式，写死 `#fff` 会让正文变成
 * "浅灰字压白底"，对比度跌到不可读（实际发生过）。
 */
.crumb {
  color: var(--color-fg-muted);
  white-space: nowrap;
}

.crumb--link {
  text-decoration: none;
}

.crumb--link:hover {
  color: var(--color-primary);
}

.crumb--current {
  font-weight: 500;
  color: var(--color-fg);
}

.notice {
  color: var(--color-fg-subtle);
}

/*
 * 手机上文档栏只有两行的额度，这句常驻说明先让路 —— 「草稿/未保存」那一项由外壳自己显示，
 * 不受这里影响。
 */
@media (max-width: 767px) {
  .notice {
    display: none;
  }
}

/* ---------------------------------------------------------------- 横幅区 */
.banner-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.notice-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin: 0;
  padding: 10px 12px;
  border-radius: var(--radius-card);
  font-size: 13px;
}

.notice-row--warning {
  color: var(--color-fg);
  background: var(--color-warning-soft);
}

.notice-row--danger {
  color: var(--color-danger);
  background: var(--color-surface-soft);
}

.notice-row--success {
  color: var(--color-success);
  background: var(--color-surface-soft);
}

/* ---------------------------------------------------------------- 协作工具条 */
.collab-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

.collab-bar__lead {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.collab-bar__hint {
  font-size: 12px;
  color: var(--color-fg-muted);
}

.collab-bar__field {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: var(--color-fg-muted);
}

/* 原生控件的样式：本页没有 Element Plus，所以这些必须自己写 */
.collab-bar__num {
  width: 72px;
  padding: 4px 6px;
  font-size: 13px;
  color: var(--color-fg);
  background: var(--color-surface);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-control);
}

.collab-bar__url {
  flex: 1;
  min-width: 240px;
  padding: 6px 8px;
  font-size: 12px;
  color: var(--color-fg-muted);
  background: var(--color-surface-soft);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-control);
}

.collab-bar__spacer {
  flex: 1;
}

.collab-bar__badge {
  align-self: flex-start;
  padding: 2px 8px;
  font-size: 12px;
  border-radius: var(--radius-pill);
  background: var(--color-surface-soft);
  color: var(--color-fg-muted);
}

/* 状态用颜色区分，但**不只靠颜色** —— 文案本身也说明了状态 */
.collab-bar__badge[data-status='connected'],
.collab-bar__badge[data-status='synced'] {
  color: var(--color-success);
  background: var(--color-surface-soft);
}

.collab-bar__badge[data-status='connecting'] {
  color: var(--color-warning);
  background: var(--color-surface-soft);
}

.collab-bar__badge[data-status='disconnected'],
.collab-bar__badge[data-status='rejected'] {
  color: var(--color-danger);
  background: var(--color-surface-soft);
}

.collab-bar__num:focus-visible,
.collab-bar__url:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 1px;
}

/* ---------------------------------------------------------------- 预览栏 */
.preview-title {
  margin: 0;
  font-size: 30px;
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: -0.01em;
  color: var(--color-fg);
}

.preview-note {
  margin: 8px 0 20px;
  padding-bottom: 16px;
  font-size: 12px;
  color: var(--color-fg-subtle);
  border-bottom: 1px solid var(--color-line);
}
</style>
