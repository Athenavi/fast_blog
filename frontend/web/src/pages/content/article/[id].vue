<script lang="ts" setup>
import {ArrowDown, ArrowLeft, Check, Picture, View} from '@element-plus/icons-vue'
import {onBeforeRouteLeave} from 'vue-router'
import {computed, ref} from 'vue'

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
 * 左侧是内容主体（标题 / 摘要 / 别名 / 富文本正文），右侧是发布设置与元信息，
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

/** 保存但不改变发布状态（Ctrl/Cmd + S 走这里：已发布的文章不会被静默撤回草稿） */
async function onSave(): Promise<void> {
  const result = await save()
  if (!result.ok) return notifyFailure()
  await replaceToEditIfNew(result.id)
  ElMessage.success(t('admin.content.article.saved'))
}

useSaveShortcut(() => onSave(), {enabled: () => !saving.value && !loading.value})

async function onPublishNow(): Promise<void> {
  const result = await publishNow()
  if (!result.ok) return notifyFailure()
  await replaceToEditIfNew(result.id)
  ElMessage.success(t('common.published'))
}

/** 转为草稿：保存内容并把状态改回草稿（发布状态只能从顶部这一处改） */
async function onUnpublish(): Promise<void> {
  const result = await saveDraft()
  if (!result.ok) return notifyFailure()
  await replaceToEditIfNew(result.id)
  ElMessage.success(t('admin.content.article.movedToDraft'))
}

async function onPublishCommand(command: string): Promise<void> {
  if (command === 'publish') return onPublishNow()
  if (command === 'unpublish') return onUnpublish()
}

// ---------------------------------------------------------------- 预览
/** 右栏在"设置 / 并排预览"之间切换 */
const sidePanel = ref<'settings' | 'preview'>('settings')
/** 定时发布时间是"本机时区"的墙上时间，界面要标出来 */
const timeZone = localTimeZone()
/** 自增即强制 iframe 重建，用来"刷新预览" */
const previewToken = ref(0)
const coverPickerOpen = ref(false)

const previewUrl = computed(() =>
  articleId.value === null ? 'about:blank' : `/articles/id/${articleId.value}`,
)

function togglePreview(): void {
  if (articleId.value === null || articleId.value === undefined) {
    ElMessage.warning(t('admin.content.article.saveBeforePreview'))
    return
  }
  sidePanel.value = sidePanel.value === 'preview' ? 'settings' : 'preview'
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

    <el-skeleton v-if="loading" :rows="8" animated/>

    <AdminEmpty v-else-if="notFound" :desc="$t('admin.content.article.notFound')" variant="error">
      <el-button @click="goBack">{{ $t('admin.content.article.backToList') }}</el-button>
    </AdminEmpty>

    <div v-else :class="['admin-split', {'admin-split--preview': sidePanel === 'preview'}]">
      <!-- 左：内容主体 -->
      <div class="editor-main admin-card admin-card--pad">
        <el-input
          v-model="form.title"
          :placeholder="$t('admin.content.article.articleTitle')"
          class="editor-title"
          maxlength="200"
          @input="markDirty()"
        />

        <el-form label-position="top">
          <el-form-item :label="$t('admin.content.article.alias')">
            <el-input
              v-model="form.slug"
              :placeholder="$t('admin.content.article.urlAliasLeaveBlankToGenerate')"
              @input="markDirty()"
            >
              <template #prepend>/</template>
            </el-input>
          </el-form-item>

          <el-form-item :label="$t('admin.content.article.summary')">
            <el-input
              v-model="form.excerpt"
              :maxlength="255"
              :rows="2"
              show-word-limit
              type="textarea"
              @input="markDirty()"
            />
          </el-form-item>

          <el-form-item :label="$t('admin.content.article.content')">
            <div class="editor-body">
              <RichEditor v-model="form.content" :placeholder="$t('admin.content.article.content')"
                          @update:model-value="markDirty()"/>
            </div>
          </el-form-item>
        </el-form>
      </div>

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
      </div>

      <!-- 右：并排预览（iframe 直接加载前台详情页，所见即所得） -->
      <div v-else class="editor-preview admin-card">
        <div class="editor-preview__bar">
          <span class="editor-preview__title">{{ $t('admin.content.article.preview') }}</span>
          <span class="editor-preview__hint">{{ $t('admin.content.article.previewHint') }}</span>
          <span class="editor-preview__spacer"/>
          <el-button link @click="refreshPreview">{{ $t('admin.common.refresh') }}</el-button>
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

.editor-main {
  min-width: 0;
}

.editor-title :deep(.el-input__wrapper) {
  box-shadow: none;
  padding-left: 0;
}

.editor-title :deep(.el-input__inner) {
  font-size: 22px;
  font-weight: 600;
  height: 44px;
}

.editor-body {
  width: 100%;
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
