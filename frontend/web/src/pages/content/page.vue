<script lang="ts" setup>
const {t} = useI18n()
/**
 * 页面管理（独立页面 CRUD，与「文章」分开：页面属于站点结构，可带层级与模板）
 *
 * 对齐 v3：`/content/page`。字段见 `PagePayload`；
 * 状态与文章一致（0 草稿 / 1 已发布），文案复用 `pageStatusKey` / `pageStatusTag`。
 */
import {Delete, Edit, Plus} from '@element-plus/icons-vue'
import {reactive, ref} from 'vue'

import {pageApi, type PageItem, type PagePayload} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {formatDateTime, pageStatusKey, pageStatusTag} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.page.pageManagement',
  permission: 'module_content:page:view',
})

/** 与后端 STATUS_DRAFT / STATUS_PUBLISHED 一致 */
const STATUS_OPTIONS = computed(() => [
  {label: t('common.draft'), value: 0},
  {label: t('common.published'), value: 1},
])

// ---------------------------------------------------------------- 列表
interface PageQueryForm extends PageQuery {
  status?: number
}

const list = useAdminList<PageItem, PageQueryForm>({
  fetcher: (params) => pageApi.list(params),
  defaultQuery: {keyword: undefined, status: undefined},
  syncUrl: true,
})

/** 父页面候选：一次拉 200 条，编辑时排除自身（后端仍会做深层校验） */
const parentOptions = ref<PageItem[]>([])

async function loadParentOptions(): Promise<void> {
  try {
    const result = await pageApi.list({page: 1, page_size: 200})
    parentOptions.value = result.items ?? []
  } catch {
    parentOptions.value = []
  }
}

// ---------------------------------------------------------------- 新建 / 编辑
const dialogVisible = ref(false)
const formRef = ref()
const saving = ref(false)
const editingId = ref<number | null>(null)

function emptyForm(): PagePayload {
  return {
    title: '',
    slug: '',
    content: '',
    excerpt: '',
    template: '',
    status: 0,
    parent_id: null,
    order_index: 0,
    meta_title: '',
    meta_description: '',
    meta_keywords: '',
  }
}

const form = reactive<PagePayload>(emptyForm())

const formRules = computed(() => ({
  title: [{required: true, message: t('admin.content.page.titleRequired'), trigger: 'blur'}],
}))

function openCreate(parent?: PageItem): void {
  editingId.value = null
  Object.assign(form, emptyForm(), parent ? {parent_id: parent.id} : {})
  dialogVisible.value = true
}

async function openEdit(row: PageItem): Promise<void> {
  const detail = await pageApi.detail(row.id)
  editingId.value = row.id
  Object.assign(form, {
    title: detail.title ?? '',
    slug: detail.slug ?? '',
    content: detail.content ?? '',
    excerpt: detail.excerpt ?? '',
    template: detail.template ?? '',
    status: detail.status ?? 0,
    parent_id: detail.parent_id ?? null,
    order_index: detail.order_index ?? 0,
    meta_title: detail.meta_title ?? '',
    meta_description: detail.meta_description ?? '',
    meta_keywords: detail.meta_keywords ?? '',
  })
  dialogVisible.value = true
}

async function submitForm(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload: PagePayload = {...form, title: (form.title ?? '').trim()}
    if (editingId.value) {
      await pageApi.update(editingId.value, payload)
      ElMessage.success(t('admin.content.page.saved'))
    } else {
      await pageApi.create(payload)
      ElMessage.success(t('admin.content.page.created'))
    }
    dialogVisible.value = false
    await Promise.all([list.reload(), loadParentOptions()])
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------- 行操作
async function togglePublish(row: PageItem): Promise<void> {
  const next = row.status !== 1
  await pageApi.publish(row.id, next)
  ElMessage.success(next ? t('admin.content.page.published') : t('admin.content.page.unpublished'))
  await list.reload()
}

async function removeRow(row: PageItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.content.page.deleteConfirm', {title: row.title ?? row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await pageApi.remove(row.id)
  ElMessage.success(t('admin.content.page.deleted'))
  // 删掉本页最后一条时回退一页，避免停在空页
  if (list.rows.value.length === 1 && list.page.value > 1) list.page.value -= 1
  await list.reload()
}

async function removeSelected(): Promise<void> {
  if (!list.selectedCount.value) return
  await ElMessageBox.confirm(
    t('admin.content.page.deleteSelectedConfirm', {n: list.selectedCount.value}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await pageApi.batchDelete(list.selectedIds.value)
  ElMessage.success(t('admin.content.page.deleted'))
  list.clearSelection()
  await list.reload()
}

/** 已发布且有 slug 的页面可直接打开前台链接（前台路由为 /p/{slug}） */
function publicUrl(row: PageItem): string {
  return row.slug ? `/p/${row.slug}` : ''
}

onMounted(loadParentOptions)
</script>

<template>
  <AdminPage :desc="$t('admin.content.page.desc')" :title="$t('admin.content.page.pageManagement')">
    <AdminListShell
      :empty-desc="list.hasFilters.value
        ? $t('admin.content.page.emptyFiltered')
        : $t('admin.content.page.emptyDesc')"
      :empty-title="$t('admin.content.page.emptyTitle')"
      :failed="list.failed.value"
      :loading="list.loading.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      :rows="list.rows.value"
      :selection-count="list.selectedCount.value"
      :total="list.total.value"
      @refresh="list.reload"
      @reset="list.reset"
      @search="list.search"
      @clear-selection="list.clearSelection"
      @page-change="list.onPageChange"
      @selection-change="list.onSelectionChange"
      @size-change="list.onSizeChange"
    >
      <template #filters>
        <el-form-item :label="$t('admin.content.page.keyword')">
          <el-input
            v-model="list.query.keyword"
            clearable
            :placeholder="$t('admin.content.page.keywordPlaceholder')"
            style="width: 200px"
            @keyup.enter="list.search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="list.query.status" :placeholder="$t('admin.common.all')" clearable style="width: 130px">
            <el-option v-for="option in STATUS_OPTIONS" :key="option.value" :label="option.label"
                       :value="option.value"/>
          </el-select>
        </el-form-item>
      </template>

      <template #actions>
        <el-button v-auth="'module_content:page:create'" :icon="Plus" type="primary" @click="openCreate()">
          {{ $t('admin.content.page.createTitle') }}
        </el-button>
      </template>

      <template #bulk>
        <el-button
          v-auth="'module_content:page:delete'"
          :icon="Delete"
          plain
          type="danger"
          @click="removeSelected()"
        >
          {{ $t('admin.content.page.deleteSelected') }}
        </el-button>
      </template>

      <el-table-column label="ID" prop="id" width="70"/>
      <el-table-column :label="$t('admin.content.page.title')" min-width="200" prop="title"
                       show-overflow-tooltip/>
      <el-table-column :label="$t('admin.content.page.slug')" min-width="160" prop="slug"/>
      <el-table-column :label="$t('admin.content.page.template')" width="140">
        <template #default="{ row }">{{ row.template || '-' }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.status')" width="100">
        <template #default="{ row }">
          <el-tag :type="pageStatusTag(row.status)" size="small">
            {{ $t(pageStatusKey(row.status)) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.content.page.orderIndex')" prop="order_index" width="90"/>
      <el-table-column :label="$t('admin.common.updatedAt')" width="170">
        <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="330">
        <template #default="{ row }">
          <el-button v-auth="'module_content:page:edit'" :icon="Edit" link type="primary"
                     @click="openEdit(row as PageItem)">
            {{ $t('admin.common.edit') }}
          </el-button>
          <el-button v-auth="'module_content:page:publish'" link type="primary"
                     @click="togglePublish(row as PageItem)">
            {{ row.status === 1 ? $t('admin.content.page.unpublish') : $t('admin.content.page.publish') }}
          </el-button>
          <el-link
            v-if="row.status === 1 && publicUrl(row as PageItem)"
            :href="publicUrl(row as PageItem)"
            :underline="false"
            class="row-link"
            target="_blank"
          >
            {{ $t('admin.content.page.viewPublic') }}
          </el-link>
          <el-button v-auth="'module_content:page:delete'" :icon="Delete" link type="danger"
                     @click="removeRow(row as PageItem)">
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? $t('admin.content.page.editTitle') : $t('admin.content.page.createTitle')"
      destroy-on-close
      top="6vh"
      width="760px"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item :label="$t('admin.content.page.title')" prop="title">
          <el-input v-model="form.title" maxlength="200" show-word-limit/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.page.slug')">
          <el-input v-model="form.slug" :placeholder="$t('admin.content.page.slugPlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.page.parent')">
          <el-select v-model="form.parent_id" :placeholder="$t('admin.content.page.topLevelPage')" clearable
                     style="width: 100%">
            <el-option
              v-for="item in parentOptions.filter((node) => node.id !== editingId)"
              :key="item.id"
              :label="item.title ?? ''"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.content.page.template')">
          <el-input v-model="form.template" :placeholder="$t('admin.content.page.templatePlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.page.orderIndex')">
          <el-input-number v-model="form.order_index" :min="0"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.page.excerpt')">
          <el-input v-model="form.excerpt" :rows="2" maxlength="255" show-word-limit type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.page.content')">
          <el-input
            v-model="form.content"
            :placeholder="$t('admin.content.article.htmlMarkdownSourceSupported')"
            :rows="10"
            type="textarea"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="form.status" style="width: 200px">
            <el-option v-for="option in STATUS_OPTIONS" :key="option.value" :label="option.label"
                       :value="option.value"/>
          </el-select>
        </el-form-item>

        <el-divider content-position="left">{{ $t('admin.content.page.seo') }}</el-divider>
        <el-form-item :label="$t('admin.content.page.metaTitle')">
          <el-input v-model="form.meta_title" maxlength="200" show-word-limit/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.page.metaDescription')">
          <el-input v-model="form.meta_description" :rows="2" maxlength="255" show-word-limit type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.page.metaKeywords')">
          <el-input v-model="form.meta_keywords" :placeholder="$t('admin.content.page.metaKeywordsPlaceholder')"/>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>
  </AdminPage>
</template>

<style scoped>
.row-link {
  margin: 0 8px;
  font-size: 12px;
  color: var(--el-color-primary);
}
</style>
