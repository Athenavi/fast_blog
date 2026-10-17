<script lang="ts" setup>
import {ArrowDown, Check, Picture} from '@element-plus/icons-vue'
import {onBeforeRouteLeave} from 'vue-router'
import {computed, ref} from 'vue'

import ArticleAssistPanel from '@/components/admin/ArticleAssistPanel.vue'
import ArticleCustomFieldsPanel from '@/components/admin/ArticleCustomFieldsPanel.vue'
import ArticlePreviewTokenPanel from '@/components/admin/ArticlePreviewTokenPanel.vue'
import DocWorkspace from '@/components/editor/DocWorkspace.vue'
import RichEditor from '@/components/site/RichEditor.vue'
import {useArticleForm} from '@/composables/useArticleForm'
import {useCategoryOptions} from '@/composables/useCategoryOptions'
import {useDocViewMode} from '@/composables/useDocViewMode'
import {useSaveShortcut} from '@/composables/useSaveShortcut'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {articleStatusKey, articleStatusTag, formatDateTime, localTimeZone} from '@/utils/format'
import {countContentUnits, headingsFromMarkdown} from '@/utils/content'
import {renderMarkdown} from '@/utils/markdown'

/**
 * 文章编辑（后台）
 *
 * 路由：`/content/article/new` 新建，`/content/article/{id}` 编辑。
 *
 * ## 版面
 *
 * 外壳是 `components/editor/DocWorkspace.vue`（与前台投稿页共用）：顶部一条文档栏、
 * 左侧可折叠大纲、中间**阅读宽度**的正文，发布设置收进右侧按需抽屉。
 * 因此这个页面里已经没有 `.admin-split`、iframe 预览、右栏常驻卡片这些东西了。
 *
 * ## 预览改成读当前缓冲区
 *
 * 原来是 iframe 指向 `/articles/id/{id}`，也就是**上次保存的版本**，于是每次校稿
 * 都要先保存、再点刷新，还得提醒用户"这里不是实时的"。现在分栏/阅读态直接
 * `renderMarkdown(form.content)`，写的同时就看到。
 *
 * **代价要说清楚**：iframe 那套带前台主题与页面框架，这一套只有 `prose-content`
 * 的正文排版。所以顶部「更多」里保留了「在新标签页打开前台页面」——
 * 看主题效果仍然走前台路由，看自己写的这段排成什么样走分栏。两者各有用处。
 *
 * ## 发布状态只有一个决策点
 *
 * 顶部主按钮（+ 下拉里的"转为草稿"）。抽屉里只读展示当前状态，
 * 避免"按钮说发布、单选说草稿"这种自相矛盾的界面。
 */

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.article.management',
  permission: 'module_content:article:view',
})

const {t} = useI18n()
const route = useRoute()
const router = useRouter()

const routeId = computed(() => String(route.params.id ?? 'new'))
const articleId = computed<number | null>(() => (routeId.value === 'new' ? null : Number(routeId.value)))

const {categories} = useCategoryOptions()
const {mode, setMode} = useDocViewMode()

const {
  form,
  publish,
  loading,
  saving,
  dirty,
  savedAt,
  notFound,
  isNew,
  markDirty,
  load,
  save,
  saveDraft,
  publishNow,
  draftAvailable,
  restoreDraft,
  discardDraft,
} = useArticleForm({
  mode: 'admin',
  articleId,
  messages: {
    titleRequired: t('admin.content.article.titleIsRequired'),
    saveFailed: t('common.operationFailed'),
    loadFailed: t('admin.content.article.notFound'),
  },
})

/** 正文可读状态：加载中/未找到时标题与保存动作都不该生效 */
const ready = computed(() => !loading.value && !notFound.value)

/** 保存失败时给贴近原因提示：标题为空 ↔ 其它错误 */
function notifyFailure(): void {
  ElMessage.warning(form.title.trim() ? t('common.operationFailed') : t('admin.content.article.titleIsRequired'))
}

/** 新建保存成功后进入编辑态（用 replace，避免"新建"留在历史里） */
async function replaceToEditIfNew(id: number | null): Promise<void> {
  if (id !== null && articleId.value === null) await router.replace(`/content/article/${id}`)
}

/**
 * 自定义字段面板引用
 *
 * 字段值挂在**已存在的内容实例**上，所以只能在文章保存拿到 id 之后写 ——
 * 这也是面板用 `defineExpose` 暴露 `save()`、而不是自带保存按钮的原因。
 */
const customFieldsRef = ref<InstanceType<typeof ArticleCustomFieldsPanel> | null>(null)

/**
 * 保存文章成功后顺带写入自定义字段值
 *
 * **字段值失败不回滚文章**：此时文章已经存下了，回滚只会丢掉用户的正文。
 * 面板内部会给出"文章已保存，但字段值写入失败"的提示，用户可单独重试。
 * 面板未渲染（当前没有 slug=article 的内容类型）时 `?.` 直接跳过。
 */
async function saveCustomFields(id: number | null): Promise<void> {
  if (id === null) return
  await customFieldsRef.value?.save(id)
}

/** 保存但不改变发布状态（Ctrl/Cmd + S 走这里：已发布的文章不会被静默撤回草稿） */
async function onSave(): Promise<void> {
  const result = await save()
  if (!result.ok) return notifyFailure()
  await replaceToEditIfNew(result.id)
  await saveCustomFields(result.id ?? articleId.value)
  ElMessage.success(t('admin.content.article.saved'))
}

useSaveShortcut(() => onSave(), {enabled: () => !saving.value && !loading.value})

async function onPublishNow(): Promise<void> {
  const result = await publishNow()
  if (!result.ok) return notifyFailure()
  await replaceToEditIfNew(result.id)
  await saveCustomFields(result.id ?? articleId.value)
  ElMessage.success(t('common.published'))
}

/** 转为草稿：保存内容并把状态改回草稿（发布状态只能从顶部这一处改） */
async function onUnpublish(): Promise<void> {
  const result = await saveDraft()
  if (!result.ok) return notifyFailure()
  await replaceToEditIfNew(result.id)
  await saveCustomFields(result.id ?? articleId.value)
  ElMessage.success(t('admin.content.article.movedToDraft'))
}

function onAction(command: string): void {
  if (command === 'publish') void onPublishNow()
  else if (command === 'unpublish') void onUnpublish()
  else if (command === 'openFront') openFrontPage()
}

// ---------------------------------------------------------------- 派生信息

/**
 * 大纲与字数都读 `form.content`（Markdown 源码），与右侧预览同源。
 *
 * 理由见 `utils/content.ts` 的头部说明：不这么统一的话，"目录列出的节"与
 * "预览里出现的节"会有机会对不上，而点错一格比没有目录更让人困惑。
 */
const outline = computed(() => headingsFromMarkdown(form.content))
const stats = computed(() => countContentUnits(form.content))

/** 分栏/阅读态的正文渲染结果 —— 走项目内唯一渲染出口 `renderMarkdown` */
const previewHtml = computed(() => renderMarkdown(form.content))

/** 定时发布时间是"本机时区"的墙上时间，界面要标出来 */
const timeZone = localTimeZone()
const coverPickerOpen = ref(false)

function onTitleInput(value: string): void {
  form.title = value
  markDirty()
}

function onCoverSelected(url: string): void {
  form.cover_image = url
  markDirty()
}

/** 看前台主题与页面框架仍然走前台路由（工作台内的预览只渲染正文排版） */
function openFrontPage(): void {
  if (articleId.value === null) return
  window.open(`/articles/id/${articleId.value}`, '_blank', 'noopener')
}

function goBack(): void {
  void router.push('/content/article')
}

// 未保存修改的离开确认
onBeforeRouteLeave(async () => {
  if (!dirty.value) return true
  try {
    await ElMessageBox.confirm(t('admin.content.article.unsavedChanges'), t('admin.common.notice'), {
      type: 'warning',
    })
    return true
  } catch {
    return false
  }
})

onMounted(() => {
  void load()
})

// ---------------------------------------------------------------- 内容助手
/**
 * 采纳建议标签：写入表单并标记未保存（无权限时按钮已由 v-auth 隐藏）。
 *
 * 面板本体（5 个标签页、各自的加载/失败/空三态、列表样式）在
 * `components/admin/ArticleAssistPanel.vue`；这里只留下与**表单状态**相关的那一件事。
 */
function adoptTag(tag: string): void {
  if (!tag || form.tags.includes(tag)) return
  form.tags = [...form.tags, tag]
  markDirty()
}
</script>

<template>
  <div class="admin-page">
    <DocWorkspace
      :dirty="dirty"
      :editable="ready"
      :items="outline"
      :mode="mode"
      :saved-at="savedAt"
      :saving="saving"
      :title="form.title"
      :units="stats.units"
      :minutes="stats.minutes"
      :title-placeholder="$t('admin.content.article.articleTitle')"
      :title-maxlength="200"
      @update:mode="setMode"
      @update:title="onTitleInput"
    >
      <!-- 面包屑：列表 → 本页。返回入口也在这里，顶部不再单独放一条工具条 -->
      <template #breadcrumb>
        <span class="crumb">{{ $t('admin.content.article.management') }}</span>
        <Icon class="h-3 w-3" name="chevron-right"/>
        <span class="crumb crumb--current">
          {{ isNew ? $t('admin.content.article.newArticle') : $t('admin.content.article.editArticle') }}
        </span>
      </template>

      <!-- 栏内第二行：发布状态（只读）。未保存/已保存由外壳统一表达 -->
      <template #status>
        <el-tag :type="articleStatusTag(publish.status)" size="small">
          {{ $t(articleStatusKey(publish.status)) }}
        </el-tag>
      </template>

      <template v-if="ready" #actions>
        <el-dropdown trigger="click" @command="onAction">
          <el-button v-auth="'module_content:article:edit'" :icon="Check" :loading="saving" type="primary">
            {{
              publish.status === 1 ? $t('admin.content.article.updatePublished') : $t('admin.content.article.publishNow')
            }}
            <el-icon class="el-icon--right">
              <ArrowDown/>
            </el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="publish">
                {{
                  publish.status === 1
                    ? $t('admin.content.article.updatePublished')
                    : $t('admin.content.article.publishNow')
                }}
              </el-dropdown-item>
              <el-dropdown-item v-if="publish.status === 1" command="unpublish" divided>
                {{ $t('admin.content.article.moveToDraft') }}
              </el-dropdown-item>
              <el-dropdown-item v-if="articleId !== null" command="openFront" divided>
                {{ $t('admin.content.article.openInNewTab') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button v-auth="'module_content:article:edit'" :loading="saving" @click="onSave">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>

      <!-- 本地暂存的未保存内容：让用户自己决定恢复还是丢弃 -->
      <template v-if="draftAvailable" #banner>
        <el-alert :closable="false" class="draft-alert" show-icon type="warning">
          <template #title>
            {{ $t('common.localDraftFound', {time: formatDateTime(draftAvailable.savedAt)}) }}
          </template>
          <div class="draft-alert__actions">
            <el-button size="small" type="primary" @click="restoreDraft">
              {{ $t('common.localDraftRestore') }}
            </el-button>
            <el-button size="small" @click="discardDraft">
              {{ $t('common.localDraftDiscard') }}
            </el-button>
          </div>
        </el-alert>
      </template>

      <!-- 标题下方的元信息：最终 URL 前缀一眼能看到，定时发布时提醒时区 -->
      <template #meta>
        <span v-if="form.slug" class="permalink">/{{ form.slug }}</span>
        <span v-if="publish.scheduled_publish_at" class="scheduled">
          {{ $t('admin.content.article.scheduledPublish') }}
          {{ formatDateTime(publish.scheduled_publish_at) }}（{{ timeZone }}）
        </span>
      </template>

      <template #document>
        <el-skeleton v-if="loading" animated class="editor-skeleton">
          <template #template>
            <div class="editor-skeleton__toolbar">
              <el-skeleton-item v-for="n in 10" :key="n" class="editor-skeleton__tool" variant="text"/>
            </div>
            <div class="editor-skeleton__body">
              <el-skeleton-item v-for="n in 7" :key="n" class="editor-skeleton__line" variant="text"/>
            </div>
          </template>
        </el-skeleton>

        <AdminEmpty v-else-if="notFound" :desc="$t('admin.content.article.notFound')" variant="error">
          <el-button @click="goBack">{{ $t('admin.content.article.backToList') }}</el-button>
        </AdminEmpty>

        <!-- 正文：不套 el-form-item —— 那只是把布局容器用错了，
             el-form-item 会带标签与下边距，把编辑器往下压一截 -->
        <RichEditor
          v-else
          v-model="form.content"
          :placeholder="$t('admin.content.article.content')"
          @update:model-value="markDirty()"
        />
      </template>

      <template #preview>
        <!--
          标题用 <p> 而不是 <h1>：外壳按「正文里第 N 个标题元素」定位目录项，
          这里多出一个 h 标签会让整条目录的跳转全体错位一格。
        -->
        <p class="preview-title">{{ form.title || $t('editor.doc.titlePlaceholder') }}</p>
        <p class="preview-note">{{ $t('editor.doc.previewNote') }}</p>
        <!-- eslint-disable-next-line vue/no-v-html —— renderMarkdown 是项目内唯一的渲染+净化出口 -->
        <div class="prose-content" v-html="previewHtml"/>
      </template>

      <!-- 设置抽屉：只有外壳知道它何时开关，内容由页面提供 -->
      <template v-if="ready" #settings>
        <div class="settings-stack">
          <el-card shadow="never">
            <template #header>{{ $t('admin.content.article.publishSettings') }}</template>

            <el-form label-position="top">
              <!-- 状态只读：发布/撤稿统一由顶部主按钮控制，避免"两个地方都能改状态" -->
              <el-form-item :label="$t('admin.content.article.currentStatus')">
                <div class="status-row">
                  <el-tag :type="articleStatusTag(publish.status)" size="small">
                    {{ $t(articleStatusKey(publish.status)) }}
                  </el-tag>
                  <span class="status-row__hint">{{ $t('admin.content.article.statusHint') }}</span>
                </div>
              </el-form-item>

              <el-form-item :label="$t('admin.content.article.scheduledPublish')">
                <el-date-picker
                  v-model="publish.scheduled_publish_at"
                  :placeholder="$t('admin.content.article.leaveBlankToPublishImmediately')"
                  style="width: 100%"
                  type="datetime"
                  value-format="YYYY-MM-DDTHH:mm:ss"
                  @change="markDirty()"
                />
                <!-- 时间串不带偏移量，把时区标出来，避免多时区协作时互相误解 -->
                <p class="form-hint">
                  {{ $t('admin.content.article.scheduledTimeZoneHint', {zone: timeZone}) }}
                </p>
              </el-form-item>

              <el-form-item :label="$t('admin.content.article.category')">
                <el-select
                  v-model="form.category_id"
                  :placeholder="$t('admin.content.article.pleaseSelect')"
                  clearable
                  style="width: 100%"
                  @change="markDirty()"
                >
                  <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id"/>
                </el-select>
              </el-form-item>

              <el-form-item :label="$t('admin.content.article.tags')">
                <el-select
                  v-model="form.tags"
                  :placeholder="$t('admin.content.article.pressEnterToAdd')"
                  allow-create
                  default-first-option
                  filterable
                  multiple
                  style="width: 100%"
                  @change="markDirty()"
                />
              </el-form-item>

              <el-form-item :label="$t('admin.content.article.cover')">
                <div class="cover-field">
                  <el-input
                    v-model="form.cover_image"
                    :placeholder="$t('admin.content.article.coverImageUrl')"
                    @input="markDirty()"
                  />
                  <el-button :icon="Picture" @click="coverPickerOpen = true">
                    {{ $t('admin.content.article.pickFromLibrary') }}
                  </el-button>
                </div>
                <img
                  v-if="form.cover_image"
                  :alt="$t('admin.content.article.cover')"
                  :src="form.cover_image"
                  class="cover-preview"
                  decoding="async"
                />
              </el-form-item>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>{{ $t('admin.content.article.properties') }}</template>

            <el-form label-position="top">
              <el-form-item :label="$t('admin.content.article.featured')">
                <el-switch v-model="publish.is_sticky" @change="markDirty()"/>
              </el-form-item>
              <el-form-item :label="$t('admin.content.article.recommended')">
                <el-switch v-model="publish.is_featured" @change="markDirty()"/>
              </el-form-item>
              <el-form-item :label="$t('admin.content.article.hidden')">
                <el-switch v-model="publish.hidden" @change="markDirty()"/>
              </el-form-item>
              <el-form-item :label="$t('admin.content.article.vipOnly')">
                <el-switch v-model="form.is_vip_only" @change="markDirty()"/>
              </el-form-item>
              <el-form-item v-if="form.is_vip_only" :label="$t('admin.content.article.requiredVipLevel')">
                <el-input-number v-model="form.required_vip_level" :min="0" @change="markDirty()"/>
              </el-form-item>
              <el-form-item :label="$t('admin.content.article.sort')">
                <el-input-number v-model="publish.sort_order" :min="0" @change="markDirty()"/>
              </el-form-item>
            </el-form>
          </el-card>

          <!-- 摘要与别名：写作时瞥一眼、发布前调一次的字段，收在抽屉里而不是挡在正文前 -->
          <el-card shadow="never">
            <template #header>{{ $t('admin.content.article.summaryAndSeo') }}</template>

            <el-form label-position="top">
              <el-form-item :label="$t('admin.content.article.summary')">
                <el-input
                  v-model="form.excerpt"
                  :maxlength="255"
                  :rows="3"
                  show-word-limit
                  type="textarea"
                  @input="markDirty()"
                />
              </el-form-item>

              <el-form-item :label="$t('admin.content.article.alias')">
                <el-input
                  v-model="form.slug"
                  :placeholder="$t('admin.content.article.urlAliasLeaveBlankToGenerate')"
                  @input="markDirty()"
                >
                  <template #prepend>/</template>
                </el-input>
                <p class="form-hint">{{ $t('admin.content.article.aliasHint') }}</p>
              </el-form-item>
            </el-form>
          </el-card>

          <!-- 自定义字段：按「内容类型（slug=article）的字段定义」动态渲染。
               没有这样的内容类型时整个面板不渲染，不影响现有写作流程 -->
          <ArticleCustomFieldsPanel ref="customFieldsRef" :article-id="articleId"/>

          <!-- 内容助手与草稿预览令牌各自整块独立成组件：它们只依赖 articleId，
               在组件内部自行挂载加载并监听 id 变化 -->
          <ArticleAssistPanel :article-id="articleId" @adopt="adoptTag"/>
          <ArticlePreviewTokenPanel :article-id="articleId"/>
        </div>
      </template>
    </DocWorkspace>
  </div>

  <!-- 封面：从媒体库挑图 / 上传 / 外链 -->
  <AdminMediaPickerDialog v-model="coverPickerOpen" @select="onCoverSelected"/>
</template>

<style scoped>
/*
 * 外壳的文档栏/大纲栏/纸张留白都由 `DocWorkspace` 自己管，
 * 这里只剩它管不着的那几样：面包屑文字、预览标题、抽屉里的表单。
 */
.crumb {
  color: var(--color-fg-muted);
  white-space: nowrap;
}

.crumb--current {
  font-weight: 500;
  color: var(--color-fg);
}

.permalink,
.scheduled {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.permalink {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

/* ---------------------------------------------------------------- 加载骨架 */
/*
 * 形状按编辑器的真实结构给：工具栏一条 + 正文若干行。
 * 标题那一行不用画 —— 外壳的大标题在那里已经摆着了。
 * 原来是 `:rows="8"` 的通用灰条，看起来像要加载一个列表，与编辑器的形态不符。
 */
.editor-skeleton__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--admin-gap-xs);
  align-items: center;
  padding: var(--admin-gap-sm);
  border: 1px solid var(--admin-line);
  border-radius: var(--admin-radius);
  height: auto;
  width: 100%;
}

.editor-skeleton__tool {
  width: 28px;
  height: 28px;
}

.editor-skeleton__body {
  display: flex;
  flex-direction: column;
  gap: var(--admin-gap-sm);
  margin-top: var(--admin-gap);
}

/* 正文行按真实段落的长度分布给宽度，比每行等宽更像"一篇文章" */
.editor-skeleton__line {
  height: 14px;
}

.editor-skeleton__line:nth-child(odd) {
  width: 96%;
}

.editor-skeleton__line:nth-child(even) {
  width: 88%;
}

.editor-skeleton__line:last-child {
  width: 54%;
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
  border-bottom: 1px solid var(--color-line);
  font-size: 12px;
  color: var(--color-fg-subtle);
}

/* ---------------------------------------------------------------- 设置抽屉 */
/*
 * 抽屉宽 420px，卡片之间留固定间距；`el-card` 默认带自己的阴影，
 * 这里统一 `shadow="never"`，靠外壳的背景色分层。
 */
.settings-stack {
  display: flex;
  flex-direction: column;
  gap: var(--admin-gap);
}

.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--admin-gap-sm);
  align-items: center;
}

.status-row__hint {
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

.cover-field {
  display: flex;
  gap: var(--admin-gap-sm);
  width: 100%;
}

/* 表单提示文字。此前模板里已经用了 `class="form-hint"`（定时发布的时区提示），
   但全项目没有任何地方定义它 —— 那些提示一直是裸文本。 */
.form-hint {
  margin: var(--admin-gap-xs) 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--admin-fg-subtle);
}

.cover-preview {
  width: 100%;
  margin-top: 8px;
  border: 1px solid var(--admin-line);
  border-radius: var(--admin-radius-sm);
  object-fit: cover;
}

.draft-alert {
  flex-wrap: wrap;
}

.draft-alert__actions {
  display: flex;
  gap: var(--admin-gap-sm);
  margin-top: var(--admin-gap-xs);
}
</style>
