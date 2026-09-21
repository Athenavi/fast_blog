<script lang="ts" setup>
const {t} = useI18n()
/**
 * 页面管理（独立页面 CRUD，与「文章」分开：页面属于站点结构，可带层级与模板）
 *
 * 对齐 v3：`/content/page`。字段见 `PagePayload`；
 * 状态与文章一致（0 草稿 / 1 已发布），文案复用 `pageStatusKey` / `pageStatusTag`。
 */
import {Delete, Edit, Plus, Refresh, Search} from '@element-plus/icons-vue'
import {reactive, ref} from 'vue'

import {pageApi, type PageItem, type PagePayload} from '@/api'
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
const loading = ref(false)
const list = ref<PageItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const selection = ref<PageItem[]>([])

const query = reactive({
  keyword: undefined as string | undefined,
  status: undefined as number | undefined,
})

const parentOptions = ref<PageItem[]>([])

async function load(): Promise<void> {
  loading.value = true
  try {
    const result = await pageApi.list({
      page: page.value,
      page_size: pageSize.value,
      keyword: query.keyword || undefined,
      ...(query.status === undefined ? {} : {status: query.status}),
    })
    list.value = result.items ?? []
    total.value = result.total ?? 0
  } catch {
    // 错误提示由 request 拦截器统一处理，这里只保证表格状态干净
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

/** 父页面候选：一次拉 200 条，编辑时排除自身（后端仍会做深层校验） */
async function loadParentOptions(): Promise<void> {
  try {
    const result = await pageApi.list({page: 1, page_size: 200})
    parentOptions.value = result.items ?? []
  } catch {
    parentOptions.value = []
  }
}

function search(): void {
  page.value = 1
  void load()
}

function reset(): void {
  query.keyword = undefined
  query.status = undefined
  search()
}

function onPageChange(next: number): void {
  page.value = next
  void load()
}

function onSizeChange(size: number): void {
  pageSize.value = size
  page.value = 1
  void load()
}

function onSelectionChange(rows: PageItem[]): void {
  selection.value = rows
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
    await Promise.all([load(), loadParentOptions()])
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------- 行操作
async function togglePublish(row: PageItem): Promise<void> {
  const next = row.status !== 1
  await pageApi.publish(row.id, next)
  ElMessage.success(next ? t('admin.content.page.published') : t('admin.content.page.unpublished'))
  await load()
}

async function removeRow(row: PageItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.content.page.deleteConfirm', {title: row.title ?? row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await pageApi.remove(row.id)
  ElMessage.success(t('admin.content.page.deleted'))
  if (list.value.length === 1 && page.value > 1) page.value -= 1
  await load()
}

async function removeSelected(): Promise<void> {
  if (!selection.value.length) return
  await ElMessageBox.confirm(
    t('admin.content.page.deleteSelectedConfirm', {n: selection.value.length}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await pageApi.batchDelete(selection.value.map((item) => item.id))
  ElMessage.success(t('admin.content.page.deleted'))
  selection.value = []
  await load()
}

/** 已发布且有 slug 的页面可直接打开前台链接（前台路由为 /p/{slug}） */
function publicUrl(row: PageItem): string {
  return row.slug ? `/p/${row.slug}` : ''
}

onMounted(() => {
  void load()
  void loadParentOptions()
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-form :inline="true" @submit.prevent="search()">
        <el-form-item :label="$t('admin.content.page.keyword')">
          <el-input
            v-model="query.keyword"
            :placeholder="$t('admin.content.page.keywordPlaceholder')"
            clearable
            style="width: 200px"
            @keyup.enter="search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="query.status" :placeholder="$t('admin.common.all')" clearable style="width: 130px">
            <el-option v-for="option in STATUS_OPTIONS" :key="option.value" :label="option.label"
                       :value="option.value"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="search()">{{ $t('admin.common.search') }}</el-button>
          <el-button :icon="Refresh" @click="reset()">{{ $t('admin.common.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <div class="table-toolbar">
        <el-button v-auth="'module_content:page:create'" :icon="Plus" type="primary" @click="openCreate()">
          {{ $t('admin.content.page.createTitle') }}
        </el-button>
        <el-button
          v-auth="'module_content:page:delete'"
          :disabled="!selection.length"
          :icon="Delete"
          plain
          type="danger"
          @click="removeSelected()"
        >
          {{ $t('admin.content.page.deleteSelected') }}
        </el-button>
        <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: total}) }}</span>
      </div>

      <el-table v-loading="loading" :data="list" border stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="46"/>
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
      </el-table>

      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        background
        class="table-pagination"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </el-card>

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
  </div>
</template>

<style scoped>
.row-link {
  margin: 0 8px;
  font-size: 12px;
  color: var(--el-color-primary);
}
</style>
