<script lang="ts" setup>
/**
 * 评论管理（审核 / 编辑 / 删除）
 *
 * 对齐 v3：`/content/comment` 列表、`/pending` 待审核、
 * `/{id}/approve|reject` 审核、`/batch/delete` 批量删除。
 */
import {Delete, Edit, Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {reactive, ref} from 'vue'

import {commentApi, type CommentItem} from '@/api'
import {formatDateTime, truncate} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: '评论',
  permission: 'module_content:comment:view',
})

const STATUS_TABS = [
  {label: '全部', value: 'all'},
  {label: '待审核', value: 'pending'},
  {label: '已通过', value: 'approved'},
]

const activeTab = ref<'all' | 'pending' | 'approved'>('all')

const loading = ref(false)
const list = ref<CommentItem[]>([])
const total = ref(0)
const selection = ref<CommentItem[]>([])

const query = reactive({page: 1, page_size: 20, keyword: ''})

async function loadList(): Promise<void> {
  loading.value = true
  try {
    const base = {page: query.page, page_size: query.page_size}
    const data =
      activeTab.value === 'pending'
        ? await commentApi.pending(base)
        : await commentApi.list({
          ...base,
          ...(activeTab.value === 'approved' ? {is_approved: true} : {}),
        })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onTabChange(): void {
  query.page = 1
  loadList()
}

function onSelectionChange(rows: CommentItem[]): void {
  selection.value = rows
}

/** 简易关键词过滤（后端列表未提供 keyword 参数，这里做前端过滤当前页） */
const filtered = computed(() => {
  const keyword = query.keyword.trim().toLowerCase()
  if (!keyword) return list.value
  return list.value.filter(
    (item) =>
      (item.content || '').toLowerCase().includes(keyword) ||
      (item.author_name || '').toLowerCase().includes(keyword),
  )
})

// ---------------------------------------------------------------- 审核
async function approve(row: CommentItem): Promise<void> {
  await commentApi.approve(row.id)
  ElMessage.success('已通过')
  await loadList()
}

async function reject(row: CommentItem): Promise<void> {
  await commentApi.reject(row.id)
  ElMessage.success('已拒绝')
  await loadList()
}

// ---------------------------------------------------------------- 编辑
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const editingContent = ref('')

function openEdit(row: CommentItem): void {
  editingId.value = row.id
  editingContent.value = row.content
  dialogVisible.value = true
}

async function submitEdit(): Promise<void> {
  const content = editingContent.value.trim()
  if (!content) {
    ElMessage.warning('评论内容不能为空')
    return
  }
  saving.value = true
  try {
    await commentApi.update(editingId.value as number, content)
    ElMessage.success('已保存')
    dialogVisible.value = false
    await loadList()
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------- 删除
async function removeRow(row: CommentItem): Promise<void> {
  await ElMessageBox.confirm(`确定删除该评论吗？`, '提示', {type: 'warning'})
  await commentApi.remove(row.id)
  ElMessage.success('已删除')
  await loadList()
}

async function removeSelected(): Promise<void> {
  if (!selection.value.length) {
    ElMessage.warning('请先选择要删除的评论')
    return
  }
  await ElMessageBox.confirm(
    `确定删除选中的 ${selection.value.length} 条评论吗？`,
    '提示',
    {type: 'warning'},
  )
  await commentApi.batchDelete(selection.value.map((item) => item.id))
  ElMessage.success('已删除')
  await loadList()
}

onMounted(loadList)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <el-tab-pane v-for="tab in STATUS_TABS" :key="tab.value" :label="tab.label" :name="tab.value"/>
      </el-tabs>

      <div class="toolbar">
        <el-input v-model="query.keyword" clearable placeholder="按内容或作者过滤当前页" style="width: 240px"/>
        <el-button :icon="Refresh" circle @click="loadList"/>
        <el-button
          v-auth="'module_content:comment:delete'"
          :disabled="!selection.length"
          :icon="Delete"
          plain
          type="danger"
          @click="removeSelected"
        >
          批量删除
        </el-button>
      </div>

      <el-table v-loading="loading" :data="filtered" row-key="id" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="46"/>
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column label="文章" prop="article_id" width="80"/>
        <el-table-column label="作者" width="150">
          <template #default="{row}">
            <div class="author">
              <span>{{ row.author_name || `用户#${row.user_id ?? '-'}` }}</span>
              <span v-if="row.author_email" class="email">{{ row.author_email }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="内容" min-width="280">
          <template #default="{row}">
            <span class="content-cell">{{ truncate(row.content, 90) }}</span>
            <el-tag v-if="row.parent_id" class="ml-1" size="small" type="info">回复</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{row}">
            <el-tag :type="row.is_approved ? 'success' : 'warning'" size="small">
              {{ row.is_approved ? '已通过' : '待审核' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="点赞" prop="likes" width="70"/>
        <el-table-column label="时间" width="170">
          <template #default="{row}">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" width="200">
          <template #default="{row}">
            <template v-if="!row.is_approved">
              <el-button v-auth="'module_content:comment:approve'" link type="success" @click="approve(row)">
                通过
              </el-button>
              <el-button v-auth="'module_content:comment:approve'" link type="warning" @click="reject(row)">
                拒绝
              </el-button>
            </template>
            <el-button v-auth="'module_content:comment:edit'" :icon="Edit" link type="primary" @click="openEdit(row)">
              编辑
            </el-button>
            <el-button v-auth="'module_content:comment:delete'" :icon="Delete" link type="danger"
                       @click="removeRow(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :page-sizes="[20, 50, 100]"
        :total="total"
        class="pagination"
        layout="total, sizes, prev, pager, next"
        @current-change="loadList"
        @size-change="onTabChange"
      />
    </el-card>

    <el-dialog v-model="dialogVisible" destroy-on-close title="编辑评论" width="620px">
      <el-input v-model="editingContent" :rows="6" maxlength="5000" show-word-limit type="textarea"/>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button :loading="saving" type="primary" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.author {
  display: flex;
  flex-direction: column;
}

.email {
  font-size: 12px;
  color: #909399;
}

.content-cell {
  color: #303133;
}

.ml-1 {
  margin-left: 4px;
}

.pagination {
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
