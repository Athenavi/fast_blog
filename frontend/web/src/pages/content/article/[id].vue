<script lang="ts" setup>
import {ArrowDown, ArrowLeft, Check, Picture, View} from '@element-plus/icons-vue'
import {onBeforeRouteLeave} from 'vue-router'
import {computed, ref} from 'vue'

import ArticleAssistPanel from '@/components/admin/ArticleAssistPanel.vue'
import ArticleCustomFieldsPanel from '@/components/admin/ArticleCustomFieldsPanel.vue'
import ArticlePreviewTokenPanel from '@/components/admin/ArticlePreviewTokenPanel.vue'
import RichEditor from '@/components/site/RichEditor.vue'
import {useArticleForm} from '@/composables/useArticleForm'
import {useCategoryOptions} from '@/composables/useCategoryOptions'
import {useSaveShortcut} from '@/composables/useSaveShortcut'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {articleStatusKey, articleStatusTag, formatDateTime, localTimeZone} from '@/utils/format'

/**
 * 文章编辑（独立页面）
 *
 * 路由：`/content/article/new` 新建，`/content/article/{id}` 编辑。
 * 左侧只放标题与正文；发布设置、摘要与别名，以及已各自独立成组件的
 * `ArticleAssistPanel` / `ArticlePreviewTokenPanel` 都在右栏。
 * 顶部固定操作条（返回 / 预览 / 保存 / 发布 ▾）。
 *
 * 正文用 Tiptap 富文本（复用 `components/site/RichEditor.vue`，与前台投稿同一套编辑器）。
 * 离开页面前若有未保存修改会二次确认；`useArticleForm` 另外会把未保存内容防抖暂存到本地，
 * 刷新/崩溃后顶部会出现"恢复"提示条。
 *
 * **发布状态只有一个决策点**：顶部主按钮（+ 下拉里的"转为草稿"）。右栏只读展示状态，
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

async function onPublishCommand(command: string): Promise<void> {
  if (command === 'publish') return onPublishNow()
  if (command === 'unpublish') return onUnpublish()
}

// ---------------------------------------------------------------- 预览
/** 右栏在"设置 / 并排预览"之间切换 */
const sidePanel = ref<'settings' | 'preview'>('settings')
/**
 * 全屏预览：把整个内容区让给 iframe。
 *
 * 并排预览在半屏宽度下几乎读不出排版效果（正文被压到 300px 上下），
 * 校稿时需要"就是前台那个样子"的宽度 —— 所以给一个不离开本页的全屏开关。
 */
const previewFullscreen = ref(false)
/** 定时发布时间是"本机时区"的墙上时间，界面要标出来 */
const timeZone = localTimeZone()
/** 自增即强制 iframe 重建，用来"刷新预览" */
const previewToken = ref(0)
const coverPickerOpen = ref(false)

/**
 * 正文字数。
 *
 * `form.content` 是 Tiptap 产出的 HTML，这里剥掉标签再统计**非空白字符数** ——
 * 中文写作里这就是"字数"，也正是编辑时唯一有用的一档量级（不需要词/字分别统计）。
 */
const wordCount = computed(() => String(form.content ?? '').replace(/<[^>]*>/g, '').replace(/\s+/g, '').length)

const previewUrl = computed(() =>
  articleId.value === null ? 'about:blank' : `/articles/id/${articleId.value}`,
)

function togglePreview(): void {
  if (articleId.value === null || articleId.value === undefined) {
    ElMessage.warning(t('admin.content.article.saveBeforePreview'))
    return
  }
  if (sidePanel.value === 'preview') {
    sidePanel.value = 'settings'
    previewFullscreen.value = false
    return
  }
  sidePanel.value = 'preview'
}

function refreshPreview(): void {
  previewToken.value += 1
}

function openPreviewNewTab(): void {
  if (articleId.value === null) return
  window.open(`/articles/id/${articleId.value}`, '_blank', 'noopener')
}

function onCoverSelected(url: string): void {
  form.cover_image = url
  markDirty()
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

// 内容助手与草稿预览令牌各自整块搬进了 `components/admin/*Panel.vue`：
// 它们只依赖 `articleId`，在组件内部自行挂载加载并监听 id 变化，
// 页面不再需要为它们保留状态、函数或生命周期钩子。
</script>

<template>
  <div class="admin-page">
    <!-- 顶部操作条 -->
    <div class="editor-bar">
      <el-button :icon="ArrowLeft" link @click="goBack">
        {{ $t('admin.content.article.backToList') }}
      </el-button>
      <span class="editor-bar__title">
        {{ isNew ? $t('admin.content.article.createTitle') : $t('admin.content.article.editArticle') }}
      </span>
      <el-tag v-if="dirty" size="small" type="warning">{{ $t('admin.content.article.unsavedChanges') }}</el-tag>
      <span v-else-if="savedAt" class="editor-bar__saved">
        {{ $t('admin.content.article.savedAt', {time: savedAt}) }}
      </span>

      <span class="editor-bar__spacer"/>

      <el-button :icon="View" @click="togglePreview">
        {{ sidePanel === 'preview' ? $t('admin.content.article.exitPreview') : $t('admin.content.article.preview') }}
      </el-button>
      <el-button v-auth="'module_content:article:edit'" :loading="saving" @click="onSave">
        {{ $t('admin.common.save') }}
      </el-button>
      <!-- 发布状态只有这一处控件：主按钮 + 下拉（已发布时才出现"转为草稿"） -->
      <el-dropdown trigger="click" @command="onPublishCommand">
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
                publish.status === 1 ? $t('admin.content.article.updatePublished') : $t('admin.content.article.publishNow')
              }}
            </el-dropdown-item>
            <el-dropdown-item v-if="publish.status === 1" command="unpublish" divided>
              {{ $t('admin.content.article.moveToDraft') }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <!-- 本地暂存的未保存内容：让用户自己决定恢复还是丢弃 -->
    <el-alert
      v-if="draftAvailable"
      :closable="false"
      class="draft-alert"
      show-icon
      type="warning"
    >
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

    <!-- 加载骨架按编辑器的真实形状给：标题 + 工具栏 + 正文块。
         原来是 `:rows="8"` 的通用灰条，看起来像要加载一个列表，与编辑器的形态不符 -->
    <el-skeleton v-if="loading" animated class="editor-skeleton admin-card">
      <template #template>
        <el-skeleton-item class="editor-skeleton__title" variant="h1"/>
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

    <div
      v-else
      :class="[
        'admin-split',
        {
          'admin-split--preview': sidePanel === 'preview',
        },
      ]"
    >
      <!-- 左：写作主体。**只放标题与正文** —— 别名/摘要这类元信息全部归右栏，
           不再插在标题与正文之间打断写作动线（此前它们挡在正文上方，改一段正文
           要先滚过两个表单字段） -->
      <section class="editor-main admin-card">
        <header class="editor-main__head">
          <el-input
            v-model="form.title"
            :aria-label="$t('admin.content.article.articleTitle')"
            :placeholder="$t('admin.content.article.articleTitle')"
            class="editor-title"
            maxlength="200"
            @input="markDirty()"
          />
          <div class="editor-main__meta">
            <span>{{ $t('admin.content.article.wordCount', {n: wordCount}) }}</span>
            <span v-if="form.slug" class="editor-main__permalink">/{{ form.slug }}</span>
          </div>
        </header>

        <!-- 正文：**不再套 el-form-item** —— 那只是把它当布局容器用，
             而 el-form-item 会带上标签与下边距，把编辑器往下压一截 -->
        <div class="editor-body">
          <RichEditor
            v-model="form.content"
            :placeholder="$t('admin.content.article.content')"
            @update:model-value="markDirty()"
          />
        </div>
      </section>

      <!-- 右：发布设置与元信息（切到预览时替换为并排预览） -->
      <div v-if="sidePanel === 'settings'" class="editor-side">
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
              <p class="form-hint">{{ $t('admin.content.article.scheduledTimeZoneHint', {zone: timeZone}) }}</p>
            </el-form-item>

            <el-form-item :label="$t('admin.content.article.category')">
              <el-select v-model="form.category_id" :placeholder="$t('admin.content.article.pleaseSelect')" clearable
                         style="width: 100%" @change="markDirty()">
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
              <img v-if="form.cover_image" :alt="$t('admin.content.article.cover')" :src="form.cover_image"
                   class="cover-preview" decoding="async"/>
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

        <!-- 摘要与别名：**从左侧正文区移过来**。它们是"写作时瞥一眼、发布前调一次"的字段，
             此前夹在标题与正文之间，改一段正文要先滚过两个表单字段 -->
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

        <!-- 内容助手：自带 5 个标签页以及各自的「加载中 / 加载失败可重试 / 暂无数据」
             三态，与页面主体没有耦合，独立成组件（此前它连加载态都没有） -->
        <ArticleAssistPanel :article-id="articleId" @adopt="adoptTag"/>

        <!-- 草稿预览令牌：生成/复制/撤销/清理自成一体，独立成组件 -->
        <ArticlePreviewTokenPanel :article-id="articleId"/>
      </div>

      <!-- 右：并排预览（iframe 直接加载前台详情页，所见即所得） -->
      <div
        v-else
        :class="['editor-preview', 'admin-card', {'editor-preview--full': previewFullscreen}]"
      >
        <div class="editor-preview__bar">
          <span class="editor-preview__title">{{ $t('admin.content.article.preview') }}</span>
          <!-- 预览读的是**已保存**的版本：存在未保存修改时把同一句提示加粗强调，
               否则用户会以为"我的改动没生效" -->
          <span :class="['editor-preview__hint', {'editor-preview__hint--warn': dirty}]">
            {{ $t('admin.content.article.previewHint') }}
          </span>
          <span class="editor-preview__spacer"/>
          <el-button link @click="refreshPreview">{{ $t('admin.common.refresh') }}</el-button>
          <!-- 并排预览只有半屏宽，正文被压到 300px 上下 —— 校稿要的是"前台那个宽度" -->
          <el-button link @click="previewFullscreen = !previewFullscreen">
            {{
              previewFullscreen
                ? $t('admin.content.article.previewExitFullscreen')
                : $t('admin.content.article.previewFullscreen')
            }}
          </el-button>
          <el-button link @click="openPreviewNewTab">
            {{ $t('admin.content.article.openInNewTab') }}
          </el-button>
        </div>
        <iframe
          :key="previewToken"
          :src="previewUrl"
          :title="$t('admin.content.article.preview')"
          class="editor-preview__frame"
        />
      </div>
    </div>
  </div>

  <!-- 封面：从媒体库挑图 / 上传 / 外链 -->
  <AdminMediaPickerDialog v-model="coverPickerOpen" @select="onCoverSelected"/>
</template>

<style scoped>
.editor-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--admin-gap-sm);
  padding: var(--admin-gap-sm) var(--admin-gap);
  border: 1px solid var(--admin-line);
  border-radius: var(--admin-radius-lg);
  background: var(--admin-surface);
  box-shadow: var(--admin-shadow-card);
  position: sticky;
  top: 0;
  z-index: 5;
}

.editor-bar__title {
  font-weight: 600;
  color: var(--admin-fg);
}

.editor-bar__saved {
  font-size: var(--admin-font-sm);
  color: var(--admin-fg-subtle);
}

.editor-bar__spacer {
  flex: 1 1 auto;
}

.draft-alert {
  flex-wrap: wrap;
}

.draft-alert__actions {
  display: flex;
  gap: var(--admin-gap-sm);
  margin-top: var(--admin-gap-xs);
}

/* ---------------------------------------------------------------- 写作主体 */
.editor-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: var(--admin-gap-lg);
}

.editor-main__head {
  flex: 0 0 auto;
}

/* 标题：不画四边描边（22px 的大标题套表单框很丑），改用**下划线**表达"可编辑"，
   并让它成为唯一的焦点指示。
   原先这里是 `box-shadow: none; padding-left: 0` —— 而 Element Plus 画输入框边框与
   焦点环的**唯一手段就是 box-shadow**，抹掉之后标题看起来是一段静态文字，
   键盘用户也完全看不到焦点在哪。 */
.editor-title :deep(.el-input__wrapper) {
  box-shadow: none;
  padding-right: 0;
  padding-left: 0;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  transition: border-color 0.15s ease;
}

.editor-title :deep(.el-input__wrapper:hover) {
  border-bottom-color: var(--admin-line-strong);
}

.editor-title :deep(.el-input__wrapper:focus-within) {
  border-bottom-color: var(--admin-primary);
}

.editor-title :deep(.el-input__inner) {
  height: 44px;
  font-size: 22px;
  font-weight: 600;
}

/* 标题下方的量级信息：正文字数与最终 URL 前缀（一眼看到 slug 长什么样） */
.editor-main__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--admin-gap-sm);
  align-items: center;
  margin-top: var(--admin-gap-xs);
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

.editor-main__permalink {
  overflow: hidden;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 编辑器：给出确定的可写高度，并让**滚动发生在编辑器内部** ——
   这样工具栏不会被正文滚出视野（此前滚动属于页面，长文时工具栏一路滚走）。
   用 min-height 而不是"算视口剩余高度"：后者要跟着顶栏高度走，太脆。 */
.editor-body {
  display: flex;
  flex: 1 1 auto;
  min-width: 0;
  min-height: clamp(420px, 62vh, 760px);
  margin-top: var(--admin-gap-sm);
}

/* 接管 RichEditor 的高度。它自身只设了 overflow/border/border-radius/background，
   不设 display/flex，且 `.rich-editor__body` 在它那边没有任何规则 ——
   所以这两条不会与它的 scoped 样式争特异性，不依赖加载顺序。 */
.editor-body :deep(.rich-editor) {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
}

.editor-body :deep(.rich-editor__body) {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}

/* 表单提示文字。此前模板里已经用了 `class="form-hint"`（定时发布的时区提示），
   但全项目没有任何地方定义它 —— 那些提示一直是裸文本。 */
.form-hint {
  margin: var(--admin-gap-xs) 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--admin-fg-subtle);
}

/* ---------------------------------------------------------------- 加载骨架 */
.editor-skeleton {
  padding: var(--admin-gap-lg);
}

.editor-skeleton__title {
  width: 62%;
  height: 32px;
}

.editor-skeleton__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--admin-gap-xs);
  align-items: center;
  margin-top: var(--admin-gap);
  padding: var(--admin-gap-sm);
  border: 1px solid var(--admin-line);
  border-radius: var(--admin-radius);
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

.editor-side {
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

/* 并排预览：把右栏（或整行）让给 iframe */
.admin-split--preview {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

/* 这层覆盖必须自己处理断点：scoped 规则特异性高于 admin.css 里 .admin-split 的媒体查询 */
@media (max-width: 1280px) {
  .admin-split--preview {
    grid-template-columns: minmax(0, 1fr);
  }
}

.editor-preview {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 70vh;
  overflow: hidden;
}

/* 全屏预览：铺满视口。
   刻意用 position: fixed 而不是"在 grid 里把左栏藏起来" —— 左栏用 display:none 会让
   ProseMirror 在不可见状态下测量异常，用 v-if 卸载又会丢撤销历史。 */
.editor-preview--full {
  position: fixed;
  inset: 0;
  z-index: 2000;
  min-height: 0;
  border: 0;
  border-radius: 0;
}

.editor-preview--full .editor-preview__frame {
  min-height: 0;
}

.editor-preview__bar {
  display: flex;
  gap: var(--admin-gap-sm);
  align-items: center;
  padding: var(--admin-gap-sm) var(--admin-gap);
  border-bottom: 1px solid var(--admin-line);
}

.editor-preview__title {
  font-weight: 600;
  color: var(--admin-fg);
}

.editor-preview__hint {
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

/* 有未保存修改时，"预览显示的是已保存版本"这句要更醒目。
   不用 warning 色：12px 小字上它的对比度不够（a11y 基线里已有 color-contrast 违规，
   不值得再添一处） */
.editor-preview__hint--warn {
  font-weight: 500;
  color: var(--admin-fg);
}

.editor-preview__spacer {
  flex: 1 1 auto;
}

.editor-preview__frame {
  flex: 1 1 auto;
  width: 100%;
  min-height: 70vh;
  background: var(--admin-surface);
  border: 0;
}

.cover-preview {
  width: 100%;
  margin-top: 8px;
  border: 1px solid var(--admin-line);
  border-radius: var(--admin-radius-sm);
  object-fit: cover;
}
</style>
