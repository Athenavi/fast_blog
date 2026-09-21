<script lang="ts" setup>
const {t} = useI18n()
/**
 * 文章编辑（独立页面）
 *
 * 路由：`/content/article/new` 新建，`/content/article/{id}` 编辑。
 * 左侧是内容主体（标题 / 摘要 / 别名 / 富文本正文），右侧是发布设置与元信息，
 * 顶部固定操作条（返回 / 预览 / 保存草稿 / 立即发布）。
 *
 * 正文用 Tiptap 富文本（复用 `components/site/RichEditor.vue`，与前台投稿同一套编辑器）。
 * 离开页面前若有未保存修改会二次确认。
 */
import {ArrowLeft, Check, View} from '@element-plus/icons-vue'
import {onBeforeRouteLeave} from 'vue-router'
import {computed, reactive, ref} from 'vue'

import {articleApi, type ArticlePayload,} from '@/api'
import RichEditor from '@/components/site/RichEditor.vue'
import {useCategoryOptions} from '@/composables/useCategoryOptions'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.article.management',
  permission: 'module_content:article:view',
})

const route = useRoute()
const router = useRouter()

const routeId = computed(() => String(route.params.id ?? 'new'))
const isNew = computed(() => routeId.value === 'new')
const articleId = computed(() => (isNew.value ? null : Number(routeId.value)))

const loading = ref(false)
const saving = ref(false)
const notFound = ref(false)
/** 是否有未保存修改（用于离开确认与按钮态） */
const dirty = ref(false)
const savedAt = ref<string | null>(null)

const {categories} = useCategoryOptions()

function emptyForm(): ArticlePayload {
  return {
    title: '',
    slug: '',
    excerpt: '',
    content: '',
    cover_image: '',
    category_id: null,
    tags: [],
    status: 0,
    hidden: false,
    is_featured: false,
    is_sticky: false,
    is_vip_only: false,
    required_vip_level: 0,
    post_type: 'article',
    sort_order: 0,
    scheduled_publish_at: null,
  }
}

const form = reactive<ArticlePayload>(emptyForm())

async function loadArticle(): Promise<void> {
  if (isNew.value || articleId.value === null) return
  loading.value = true
  try {
    const detail = await articleApi.detail(articleId.value)
    Object.assign(form, {
      title: detail.title ?? '',
      slug: detail.slug ?? '',
      excerpt: detail.excerpt ?? '',
      content: detail.content ?? '',
      cover_image: detail.cover_image ?? '',
      category_id: detail.category_id ?? null,
      tags: detail.tags ?? [],
      status: detail.status ?? 0,
      hidden: detail.hidden ?? false,
      is_featured: detail.is_featured ?? false,
      is_sticky: detail.is_sticky ?? false,
      is_vip_only: detail.is_vip_only ?? false,
      required_vip_level: detail.required_vip_level ?? 0,
      post_type: detail.post_type ?? 'article',
      sort_order: detail.sort_order ?? 0,
      scheduled_publish_at: detail.scheduled_publish_at ?? null,
    })
    dirty.value = false
  } catch {
    notFound.value = true
  } finally {
    loading.value = false
  }
}

/** 保存（`statusOverride` 用于"保存草稿"/"立即发布"两个动作） */
async function save(statusOverride?: number): Promise<boolean> {
  const title = (form.title ?? '').trim()
  if (!title) {
    ElMessage.warning(t('admin.content.article.titleIsRequired'))
    return false
  }

  const payload: ArticlePayload = {
    ...form,
    title,
    status: statusOverride ?? form.status ?? 0,
  }

  saving.value = true
  try {
    if (articleId.value === null) {
      const created = await articleApi.create(payload)
      form.status = payload.status
      dirty.value = false
      savedAt.value = formatDateTime(new Date().toISOString())
      ElMessage.success(t('admin.content.article.created'))
      // 用 replace 避免"新建"留在历史里，之后刷新就是编辑态
      await router.replace(`/content/article/${created.id}`)
    } else {
      await articleApi.update(articleId.value, payload)
      form.status = payload.status
      dirty.value = false
      savedAt.value = formatDateTime(new Date().toISOString())
      ElMessage.success(t('admin.content.article.saved'))
    }
    return true
  } catch {
    return false
  } finally {
    saving.value = false
  }
}

async function saveDraft(): Promise<void> {
  await save(0)
}

async function publishNow(): Promise<void> {
  const ok = await save(1)
  if (ok && articleId.value !== null) {
    await articleApi.publish(articleId.value, true)
    ElMessage.success(t('common.published'))
  }
}

function goBack(): void {
  void router.push('/content/article')
}

function preview(): void {
  if (articleId.value === null) {
    ElMessage.warning(t('admin.content.article.saveDraft'))
    return
  }
  window.open(`/articles/id/${articleId.value}`, '_blank', 'noopener')
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
  void loadArticle()
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

      <el-button :icon="View" @click="preview">{{ $t('admin.content.article.preview') }}</el-button>
      <el-button v-auth="'module_content:article:edit'" :loading="saving" @click="saveDraft">
        {{ $t('admin.content.article.saveDraft') }}
      </el-button>
      <el-button v-auth="'module_content:article:edit'" :icon="Check" :loading="saving" type="primary"
                 @click="publishNow">
        {{ $t('admin.content.article.publishNow') }}
      </el-button>
    </div>

    <el-skeleton v-if="loading" :rows="8" animated/>

    <AdminEmpty v-else-if="notFound" :desc="$t('admin.content.article.notFound')" variant="error">
      <el-button @click="goBack">{{ $t('admin.content.article.backToList') }}</el-button>
    </AdminEmpty>

    <div v-else class="admin-split">
      <!-- 左：内容主体 -->
      <div class="editor-main admin-card admin-card--pad">
        <el-input
          v-model="form.title"
          :placeholder="$t('admin.content.article.articleTitle')"
          class="editor-title"
          maxlength="200"
          @input="dirty = true"
        />

        <el-form label-position="top">
          <el-form-item :label="$t('admin.content.article.alias')">
            <el-input
              v-model="form.slug"
              :placeholder="$t('admin.content.article.urlAliasLeaveBlankToGenerate')"
              @input="dirty = true"
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
              @input="dirty = true"
            />
          </el-form-item>

          <el-form-item :label="$t('admin.content.article.content')">
            <div class="editor-body">
              <RichEditor v-model="form.content" :placeholder="$t('admin.content.article.content')"
                          @update:model-value="dirty = true"/>
            </div>
          </el-form-item>
        </el-form>
      </div>

      <!-- 右：发布设置与元信息 -->
      <div class="editor-side">
        <el-card shadow="never">
          <template #header>{{ $t('admin.content.article.publishSettings') }}</template>

          <el-form label-position="top">
            <el-form-item :label="$t('admin.common.status')">
              <el-radio-group v-model="form.status" @change="dirty = true">
                <el-radio :value="0">{{ $t('common.draft') }}</el-radio>
                <el-radio :value="1">{{ $t('common.published') }}</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item :label="$t('admin.content.article.scheduledPublish')">
              <el-date-picker
                v-model="form.scheduled_publish_at"
                :placeholder="$t('admin.content.article.leaveBlankToPublishImmediately')"
                style="width: 100%"
                type="datetime"
                value-format="YYYY-MM-DDTHH:mm:ss"
                @change="dirty = true"
              />
            </el-form-item>

            <el-form-item :label="$t('admin.content.article.category')">
              <el-select v-model="form.category_id" :placeholder="$t('admin.content.article.pleaseSelect')" clearable
                         style="width: 100%" @change="dirty = true">
                <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id"/>
              </el-select>
            </el-form-item>

            <el-form-item label="Tags">
              <el-select
                v-model="form.tags"
                :placeholder="$t('admin.content.article.pressEnterToAdd')"
                allow-create
                default-first-option
                filterable
                multiple
                style="width: 100%"
                @change="dirty = true"
              />
            </el-form-item>

            <el-form-item :label="$t('admin.content.article.cover')">
              <el-input
                v-model="form.cover_image"
                :placeholder="$t('admin.content.article.coverImageUrl')"
                @input="dirty = true"
              />
              <img v-if="form.cover_image" :src="form.cover_image" alt="" class="cover-preview" decoding="async"/>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never">
          <template #header>{{ $t('admin.content.article.properties') }}</template>

          <el-form label-position="top">
            <el-form-item :label="$t('admin.content.article.featured')">
              <el-switch v-model="form.is_sticky" @change="dirty = true"/>
            </el-form-item>
            <el-form-item :label="$t('admin.content.article.recommended')">
              <el-switch v-model="form.is_featured" @change="dirty = true"/>
            </el-form-item>
            <el-form-item :label="$t('admin.content.article.hidden')">
              <el-switch v-model="form.hidden" @change="dirty = true"/>
            </el-form-item>
            <el-form-item :label="$t('admin.content.article.vipOnly')">
              <el-switch v-model="form.is_vip_only" @change="dirty = true"/>
            </el-form-item>
            <el-form-item v-if="form.is_vip_only" :label="$t('admin.content.article.requiredVipLevel')">
              <el-input-number v-model="form.required_vip_level" :min="0" @change="dirty = true"/>
            </el-form-item>
            <el-form-item :label="$t('admin.content.article.sort')">
              <el-input-number v-model="form.sort_order" :min="0" @change="dirty = true"/>
            </el-form-item>
          </el-form>
        </el-card>
      </div>
    </div>
  </div>
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

.cover-preview {
  width: 100%;
  margin-top: 8px;
  border: 1px solid var(--admin-line);
  border-radius: var(--admin-radius-sm);
  object-fit: cover;
}
</style>
