<script lang="ts" setup>
/**
 * 文章管理（列表 / 筛选 / 分页 / 增删改 / 发布）
 *
 * 对齐 v3：`/content/article`，列表参数见 `ArticleQuery`（后端另支持
 * order_by / order）。正文目前用多行文本编辑（内容为 HTML/Markdown 源码），
 * 后续可替换为富文本编辑器而不影响其余部分。
 */
import {Delete, Edit, Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from 'element-plus'
import {reactive, ref} from 'vue'

import {
  articleApi,
  categoryApi,
  type ArticleItem,
  type ArticlePayload,
  type CategoryItem,
} from '@/api'
import {articleStatusTag, articleStatusText, formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '文章',
  permission: 'module_content:article:view',
})

/** 与后端 STATUS_DRAFT / STATUS_PUBLISHED 一致 */
const STATUS_OPTIONS = [
  {label: '草稿', value: 0},
  {label: '已发布', value: 1},
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
    })
  } catch {
    // 详情失败已由 request 拦截器统一提示
  }
}

async function submitForm(): Promise<void> {
  const title = (form.title ?? '').trim()
  if (!title) {
    ElMessage.warning('请填写标题')
    return
  }

  saving.value = true
  try {
    const payload: ArticlePayload = {...form, title}
    if (editingId.value) {
      await articleApi.update(editingId.value, payload)
      ElMessage.success('已保存')
    } else {
      await articleApi.create(payload)
      ElMessage.success('已创建')
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
  ElMessage.success(next ? '已发布' : '已转为草稿')
  await loadList()
}

async function removeRow(row: ArticleItem): Promise<void> {
  await ElMessageBox.confirm(`确定删除《${row.title}》吗？`, '提示', {type: 'warning'})
  await articleApi.remove(row.id)
  ElMessage.success('已删除')
  await loadList()
}

async function removeSelected(): Promise<void> {
  if (!selection.value.length) {
    ElMessage.warning('请先选择要删除的文章')
    return
  }
  await ElMessageBox.confirm(
    `确定删除选中的 ${selection.value.length} 篇文章吗？`,
    '提示',
    {type: 'warning'},
  )
  await articleApi.batchDelete(selection.value.map((item) => item.id))
  ElMessage.success('已删除')
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
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" clearable placeholder="标题关键词" style="width: 200px"
                    @keyup.enter="onSearch"/>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部" style="width: 130px">
            <el-option v-for="item in STATUS_OPTIONS" :key="item.value" :label="item.label" :value="item.value"/>
          </el-select>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="query.category_id" clearable placeholder="全部" style="width: 160px">
            <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="onSearch">查询</el-button>
          <el-button :icon="Refresh" @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar">
        <el-button v-auth="'module_content:article:create'" :icon="Plus" type="primary" @click="openCreate">
          新建文章
        </el-button>
        <el-button
          v-auth="'module_content:article:delete'"
          :disabled="!selection.length"
          :icon="Delete"
          plain
          type="danger"
          @click="removeSelected"
        >
          批量删除
        </el-button>
        <el-button :icon="Refresh" circle @click="loadList"/>
      </div>

      <el-table v-loading="loading" :data="list" row-key="id" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="46"/>
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column label="标题" min-width="240">
          <template #default="{row}">
            <span class="title-cell">{{ row.title }}</span>
            <el-tag v-if="row.is_sticky" class="ml-1" size="small" type="warning">置顶</el-tag>
            <el-tag v-if="row.is_featured" class="ml-1" size="small" type="success">推荐</el-tag>
            <el-tag v-if="row.hidden" class="ml-1" size="small" type="info">隐藏</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分类" width="120">
          <template #default="{row}">{{ categoryName(row.category_id) }}</template>
        </el-table-column>
        <el-table-column label="标签" min-width="150">
          <template #default="{row}">
            <el-tag v-for="tag in (row.tags || []).slice(0, 3)" :key="tag" class="mr-1" size="small">{{ tag }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{row}">
            <el-tag :type="articleStatusTag(row.status)" size="small">{{ articleStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="浏览" prop="views" width="80"/>
        <el-table-column label="更新时间" width="170">
          <template #default="{row}">{{ formatDateTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" width="210">
          <template #default="{row}">
            <el-button v-auth="'module_content:article:edit'" :icon="Edit" link type="primary" @click="openEdit(row)">
              编辑
            </el-button>
            <el-button v-auth="'module_content:article:publish'" link type="primary" @click="togglePublish(row)">
              {{ row.status === 1 ? '转草稿' : '发布' }}
            </el-button>
            <el-button v-auth="'module_content:article:delete'" :icon="Delete" link type="danger"
                       @click="removeRow(row)">
              删除
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
      :title="editingId ? '编辑文章' : '新建文章'"
      destroy-on-close
      top="5vh"
      width="820px"
    >
      <el-form :model="form" label-width="90px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="255" placeholder="文章标题" show-word-limit/>
        </el-form-item>
        <el-form-item label="别名">
          <el-input v-model="form.slug" placeholder="URL 别名（留空由后端生成）"/>
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="form.excerpt" :rows="2" maxlength="255" show-word-limit type="textarea"/>
        </el-form-item>
        <el-form-item label="封面">
          <el-input v-model="form.cover_image" placeholder="封面图 URL"/>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category_id" clearable placeholder="请选择" style="width: 100%">
            <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id"/>
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="form.tags"
            allow-create
            default-first-option
            filterable
            multiple
            placeholder="输入后回车添加"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="正文">
          <el-input v-model="form.content" :rows="10" placeholder="支持 HTML / Markdown 源码" type="textarea"/>
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio v-for="item in STATUS_OPTIONS" :key="item.value" :value="item.value">{{ item.label }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="属性">
          <el-checkbox v-model="form.is_sticky">置顶</el-checkbox>
          <el-checkbox v-model="form.is_featured">推荐</el-checkbox>
          <el-checkbox v-model="form.hidden">隐藏</el-checkbox>
          <el-checkbox v-model="form.is_vip_only">仅 VIP</el-checkbox>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0"/>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">保存</el-button>
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

.mr-1 {
  margin-right: 4px;
}

.pagination {
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
