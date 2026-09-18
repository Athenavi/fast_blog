<script lang="ts" setup>
const {t} = useI18n()
/**
 * 文章管理（列表 / 筛选 / 分页 / 增删改 / 发布）
 *
 * 对齐 v3：`/content/article`，列表参数见 `ArticleQuery`（后端另支持
 * order_by / order）。正文目前用多行文本编辑（内容为 HTML/Markdown 源码），
 * 后续可替换为富文本编辑器而不影响其余部分。
 */
import {Delete, Edit, Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {reactive, ref} from 'vue'

import {articleApi, type ArticleItem, type ArticlePayload, categoryApi, type CategoryItem,} from '@/api'
import {articleStatusKey, articleStatusTag, formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'article.title',
  permission: 'module_content:article:view',
})

/** 与后端 STATUS_DRAFT / STATUS_PUBLISHED 一致 */
const STATUS_OPTIONS = [
  {label: t('common.draft'), value: 0},
  {label: t('common.published'), value: 1},
]

const loading = ref(false)
const list = ref<ArticleItem[]>([])
const total = ref(0)
const categories = ref<CategoryItem[]>([])
const selection = ref<ArticleItem[]>([])

const query = reactive({
  page: 1,
  page_size: 10,
  keyword: '',
  status: undefined as number | undefined,
  category_id: undefined as number | undefined,
})

async function loadList(): Promise<void> {
  loading.value = true
  try {
    // 显式收敛空值：Element Plus 清空下拉后会给出空字符串
    const data = await articleApi.list({
      page: query.page,
      page_size: query.page_size,
      ...(query.keyword ? {keyword: query.keyword} : {}),
      ...(query.status === undefined ? {} : {status: query.status}),
      ...(query.category_id === undefined ? {} : {category_id: query.category_id}),
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadCategories(): Promise<void> {
  try {
    categories.value = await categoryApi.tree()
  } catch {
    categories.value = []
  }
}

function onSearch(): void {
  query.page = 1
  loadList()
}

function onReset(): void {
  query.keyword = ''
  query.status = undefined
  query.category_id = undefined
  query.page = 1
  loadList()
}

function onSelectionChange(rows: ArticleItem[]): void {
  selection.value = rows
}

function categoryName(id?: number | null): string {
  if (!id) return '-'
  return categories.value.find((item) => item.id === id)?.name ?? String(id)
}

// ---------------------------------------------------------------- 编辑
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)

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
    sort_order: 0,
    scheduled_publish_at: null,
  }
}

const form = reactive<ArticlePayload>(emptyForm())

function openCreate(): void {
  editingId.value = null
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

async function openEdit(row: ArticleItem): Promise<void> {
  editingId.value = row.id
  Object.assign(form, emptyForm())
  dialogVisible.value = true
  try {
    const detail = await articleApi.detail(row.id)
    Object.assign(form, {
      title: detail.title ?? '',
      slug: detail.slug ?? '',
      excerpt: detail.excerpt ?? '',
      content: detail.content ?? '',
      cover_image: detail.cover_image ?? '',
      category_id: detail.category_id ?? null,
      tags: detail.tags ?? [],
      status: detail.status ?? 0,
      hidden: detail.hidden,
      is_featured: detail.is_featured,
      is_sticky: detail.is_sticky,
      is_vip_only: detail.is_vip_only,
      required_vip_level: detail.required_vip_level,
      sort_order: detail.sort_order,
      scheduled_publish_at: detail.scheduled_publish_at ?? null,
    })
  } catch {
    // 详情失败已由 request 拦截器统一提示
  }
}

async function submitForm(): Promise<void> {
  const title = (form.title ?? '').trim()
  if (!title) {
    ElMessage.warning(t('admin.content.article.titleIsRequired'))
    return
  }

  saving.value = true
  try {
    const payload: ArticlePayload = {...form, title}
    if (editingId.value) {
      await articleApi.update(editingId.value, payload)
      ElMessage.success(t('admin.content.article.saved'))
    } else {
      await articleApi.create(payload)
      ElMessage.success(t('admin.content.article.created'))
    }
    dialogVisible.value = false
    await loadList()
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------- 行内操作
async function togglePublish(row: ArticleItem): Promise<void> {
  const next = row.status !== 1
  await articleApi.publish(row.id, next)
  ElMessage.success(next ? t('common.published') : t('admin.content.article.movedToDraft'))
  await loadList()
}

async function removeRow(row: ArticleItem): Promise<void> {
  await ElMessageBox.confirm(t('admin.content.article.deleteConfirm', {title: row.title}), t('admin.common.notice'), {type: 'warning'})
  await articleApi.remove(row.id)
  ElMessage.success(t('admin.content.article.deleted'))
  await loadList()
}

async function removeSelected(): Promise<void> {
  if (!selection.value.length) {
    ElMessage.warning(t('admin.content.article.selectArticlesToDeleteFirst'))
    return
  }
  await ElMessageBox.confirm(
    t('admin.content.article.deleteSelectedConfirm', {n: selection.value.length}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await articleApi.batchDelete(selection.value.map((item) => item.id))
  ElMessage.success(t('admin.content.article.deleted'))
  await loadList()
}

onMounted(async () => {
  await Promise.all([loadCategories(), loadList()])
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-form :inline="true" @submit.prevent>
        <el-form-item :label="$t('admin.content.article.keyword')">
          <el-input v-model="query.keyword" :placeholder="$t('admin.content.article.titleKeyword')" clearable
                    style="width: 200px"
                    @keyup.enter="onSearch"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="query.status" :placeholder="$t('admin.common.all')" clearable style="width: 130px">
            <el-option v-for="item in STATUS_OPTIONS" :key="item.value" :label="item.label" :value="item.value"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('article.category')">
          <el-select v-model="query.category_id" :placeholder="$t('admin.common.all')" clearable style="width: 160px">
            <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="onSearch">{{ $t('admin.common.search') }}</el-button>
          <el-button :icon="Refresh" @click="onReset">{{ $t('admin.common.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar">
        <el-button v-auth="'module_content:article:create'" :icon="Plus" type="primary" @click="openCreate">
          {{ $t('admin.content.article.newArticle') }}
        </el-button>
        <el-button
          v-auth="'module_content:article:delete'"
          :disabled="!selection.length"
          :icon="Delete"
          plain
          type="danger"
          @click="removeSelected"
        >
          {{ $t('common.batchDelete') }}
        </el-button>
        <el-button :icon="Refresh" circle @click="loadList"/>
      </div>

      <el-table v-loading="loading" :data="list" row-key="id" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="46"/>
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column :label="$t('admin.system.menu.itemTitle')" min-width="240">
          <template #default="{row}">
            <span class="title-cell">{{ row.title }}</span>
            <el-tag v-if="row.is_sticky" class="ml-1" size="small" type="warning">
              {{ $t('admin.content.article.featured') }}
            </el-tag>
            <el-tag v-if="row.is_featured" class="ml-1" size="small" type="success">
              {{ $t('admin.content.article.recommended') }}
            </el-tag>
            <el-tag v-if="row.hidden" class="ml-1" size="small" type="info">{{
                $t('admin.content.article.hidden')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('article.category')" width="120">
          <template #default="{row}">{{ categoryName(row.category_id) }}</template>
        </el-table-column>
        <el-table-column :label="$t('article.tags')" min-width="150">
          <template #default="{row}">
            <el-tag v-for="tag in (row.tags || []).slice(0, 3)" :key="tag" class="mr-1" size="small">{{ tag }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.status')" width="90">
          <template #default="{row}">
            <el-tag :type="articleStatusTag(row.status)" size="small">{{ t(articleStatusKey(row.status)) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('article.views')" prop="views" width="80"/>
        <el-table-column :label="$t('admin.content.article.scheduledPublish')" width="170">
          <template #default="{row}">
            <el-tag v-if="row.scheduled_publish_at" size="small" type="warning">
              {{ formatDateTime(row.scheduled_publish_at) }}
            </el-tag>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.updatedAt')" width="170">
          <template #default="{row}">{{ formatDateTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="210">
          <template #default="{row}">
            <el-button v-auth="'module_content:article:edit'" :icon="Edit" link type="primary" @click="openEdit(row)">
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button v-auth="'module_content:article:publish'" link type="primary" @click="togglePublish(row)">
              {{ row.status === 1 ? t('admin.content.article.moveToDraft') : t('admin.content.article.publish') }}
            </el-button>
            <el-button v-auth="'module_content:article:delete'" :icon="Delete" link type="danger"
                       @click="removeRow(row)">
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :page-sizes="[10, 20, 50]"
        :total="total"
        class="pagination"
        layout="total, sizes, prev, pager, next"
        @current-change="loadList"
        @size-change="onSearch"
      />
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? t('admin.content.article.editArticle') : t('admin.content.article.newArticle')"
      destroy-on-close
      top="5vh"
      width="820px"
    >
      <el-form :model="form" label-width="90px">
        <el-form-item :label="$t('admin.system.menu.itemTitle')" required>
          <el-input v-model="form.title" :placeholder="$t('admin.content.article.articleTitle')" maxlength="255"
                    show-word-limit/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.article.alias')">
          <el-input v-model="form.slug" :placeholder="$t('admin.content.article.urlAliasLeaveBlankToGenerate')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.article.summary')">
          <el-input v-model="form.excerpt" :rows="2" maxlength="255" show-word-limit type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.article.cover')">
          <el-input v-model="form.cover_image" :placeholder="$t('admin.content.article.coverImageUrl')"/>
        </el-form-item>
        <el-form-item :label="$t('article.category')">
          <el-select v-model="form.category_id" :placeholder="$t('admin.content.article.pleaseSelect')" clearable
                     style="width: 100%">
            <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('article.tags')">
          <el-select
            v-model="form.tags"
            allow-create
            default-first-option
            filterable
            multiple
            :placeholder="$t('admin.content.article.pressEnterToAdd')"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.content.article.content')">
          <el-input v-model="form.content" :placeholder="$t('admin.content.article.htmlMarkdownSourceSupported')"
                    :rows="10" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-radio-group v-model="form.status">
            <el-radio v-for="item in STATUS_OPTIONS" :key="item.value" :value="item.value">{{ item.label }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('admin.content.article.properties')">
          <el-checkbox v-model="form.is_sticky">{{ $t('admin.content.article.featured') }}</el-checkbox>
          <el-checkbox v-model="form.is_featured">{{ $t('admin.content.article.recommended') }}</el-checkbox>
          <el-checkbox v-model="form.hidden">{{ $t('admin.content.article.hidden') }}</el-checkbox>
          <el-checkbox v-model="form.is_vip_only">{{ $t('admin.content.article.vipOnly') }}</el-checkbox>
        </el-form-item>
        <el-form-item :label="$t('admin.widget.order')">
          <el-input-number v-model="form.sort_order" :min="0"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.article.scheduledPublish')">
          <el-date-picker
            v-model="form.scheduled_publish_at"
            :placeholder="$t('admin.content.article.leaveBlankToPublishImmediately')"
            style="width: 100%"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.title-cell {
  font-weight: 500;
}

.ml-1 {
  margin-left: 4px;
}

.muted {
  color: var(--el-text-color-secondary);
}

.mr-1 {
  margin-right: 4px;
}

.pagination {
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
