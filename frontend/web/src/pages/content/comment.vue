<script lang="ts" setup>
const {t} = useI18n()
/**
 * 评论管理（审核工作流 + 批量处理 + 管理员回复）
 *
 * 对齐 v3：`/content/comment`（列表）、`/pending`（待审数）、
 * `/{id}/approve|reject`（审核）、`/{id}`（编辑/删除）、`/batch/delete`（批量删除）；
 * 回复走公开提交端点 `/content/comment/public`（带登录态，后端对登录用户直接通过审核）。
 *
 * 三个标签页对应 `is_approved`：全部 / 待审核（false）/ 已通过（true）。
 */
import {ChatDotRound, Check, Close, Delete, Edit, Refresh, View} from '@element-plus/icons-vue'
import {computed, ref} from 'vue'

import {commentApi, type CommentItem, type CommentQuery} from '@/api'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage} from '@/utils/feedback'
import {formatDateTime, truncate} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.comment.commentManagement',
  permission: 'module_content:comment:view',
})

const list = useAdminList<CommentItem, CommentQuery>({
  fetcher: (params) => commentApi.list(params),
  defaultQuery: {keyword: '', article_id: undefined, is_approved: undefined},
  syncUrl: true,
})

// ---------------------------------------------------------------- 标签页
type TabName = 'all' | 'pending' | 'approved'

const activeTab = computed<TabName>({
  get: () => {
    const value = list.query.is_approved as boolean | undefined
    if (value === undefined) return 'all'
    return value ? 'approved' : 'pending'
  },
  set: (name: TabName) => {
    list.query.is_approved = name === 'all' ? undefined : name === 'approved'
    void list.search()
    void loadPendingCount()
  },
})

const pendingCount = ref(0)

async function loadPendingCount(): Promise<void> {
  try {
    const result = await commentApi.pending({page: 1, page_size: 1})
    pendingCount.value = result.total ?? 0
  } catch {
    pendingCount.value = 0
  }
}

// ---------------------------------------------------------------- 审核
async function approveRow(row: CommentItem): Promise<void> {
  await commentApi.approve(row.id)
  ElMessage.success(t('admin.content.comment.approveDone'))
  await Promise.all([list.reload(), loadPendingCount()])
}

async function rejectRow(row: CommentItem): Promise<void> {
  await commentApi.reject(row.id)
  ElMessage.success(t('admin.content.comment.rejectDone'))
  await Promise.all([list.reload(), loadPendingCount()])
}

/** 批量通过 / 拒绝：后端单次请求内逐条处理，返回实际处理条数 */
async function bulkDecide(approve: boolean): Promise<void> {
  if (!list.selectedCount.value) {
    ElMessage.warning(t('admin.content.comment.selectFirst'))
    return
  }
  const ids = [...list.selectedIds.value]
  const result = await commentApi.batchDecide(ids, approve)
  ElMessage.success(t('admin.common.batchDone', {n: result.affected}))
  list.clearSelection()
  await Promise.all([list.reload(), loadPendingCount()])
}

async function bulkApprove(): Promise<void> {
  await bulkDecide(true)
}

async function bulkReject(): Promise<void> {
  await bulkDecide(false)
}

async function bulkDelete(): Promise<void> {
  if (!list.selectedCount.value) {
    ElMessage.warning(t('admin.content.comment.selectFirst'))
    return
  }
  const ids = [...list.selectedIds.value]
  await list.remove(
    () => commentApi.batchDelete(ids),
    t('admin.content.comment.deleteSelectedConfirm', {n: ids.length}),
    t('admin.common.notice'),
    t('admin.content.comment.deleted'),
  )
  await loadPendingCount()
}

async function removeRow(row: CommentItem): Promise<void> {
  await list.remove(
    () => commentApi.remove(row.id),
    t('admin.content.comment.deleteConfirm'),
    t('admin.common.notice'),
    t('admin.content.comment.deleted'),
  )
  await loadPendingCount()
}

// ---------------------------------------------------------------- 编辑内容
const editVisible = ref(false)
const editTarget = ref<CommentItem | null>(null)
const editContent = ref('')
const editSaving = ref(false)

function openEdit(row: CommentItem): void {
  editTarget.value = row
  editContent.value = row.content
  editVisible.value = true
}

async function submitEdit(): Promise<void> {
  const content = editContent.value.trim()
  if (!content) {
    ElMessage.warning(t('admin.content.comment.commentContentIsRequired'))
    return
  }
  if (!editTarget.value) return
  editSaving.value = true
  try {
    await commentApi.update(editTarget.value.id, content)
    ElMessage.success(t('admin.content.comment.saved'))
    editVisible.value = false
    await list.reload()
  } finally {
    editSaving.value = false
  }
}

// ---------------------------------------------------------------- 管理员回复
const replyVisible = ref(false)
const replyTarget = ref<CommentItem | null>(null)
const replyContent = ref('')
const replySending = ref(false)

function openReply(row: CommentItem): void {
  replyTarget.value = row
  replyContent.value = ''
  replyVisible.value = true
}

async function submitReply(): Promise<void> {
  const content = replyContent.value.trim()
  if (!content) {
    ElMessage.warning(t('admin.content.comment.commentContentIsRequired'))
    return
  }
  if (!replyTarget.value) return
  replySending.value = true
  try {
    await commentApi.reply(replyTarget.value.id, content)
    ElMessage.success(t('admin.content.comment.replySent'))
    replyVisible.value = false
    await Promise.all([list.reload(), loadPendingCount()])
  } finally {
    replySending.value = false
  }
}

// ---------------------------------------------------------------- 展示辅助
function authorLabel(row: CommentItem): string {
  if (row.author_name) return row.author_name
  if (row.user_id) return t('admin.content.comment.anonymousUser', {id: row.user_id})
  return '-'
}

/** 垃圾评分较高时高亮（后端 spam_score 为 0~1 的浮点） */
function spamType(score?: number | null): 'danger' | 'warning' | 'info' {
  if (score === null || score === undefined) return 'info'
  if (score >= 0.7) return 'danger'
  return score >= 0.4 ? 'warning' : 'info'
}

function openArticle(row: CommentItem): void {
  window.open(`/articles/id/${row.article_id}`, '_blank', 'noopener')
}

onMounted(() => {
  // 列表由 useAdminList 的 immediate 自动加载，这里只补待审数量
  void loadPendingCount()
})
</script>

<template>
  <AdminPage :desc="$t('admin.content.comment.desc')" :title="$t('admin.content.comment.commentManagement')">
    <template #actions>
      <el-button :icon="Refresh" @click="list.reload(), loadPendingCount()">
        {{ $t('admin.common.refresh') }}
      </el-button>
    </template>

    <el-tabs v-model="activeTab">
      <el-tab-pane :label="$t('admin.content.comment.tabsAll')" name="all"/>
      <el-tab-pane name="pending">
        <template #label>
          <span class="tab-label">
            {{ $t('admin.content.comment.tabsPending') }}
            <el-badge v-if="pendingCount > 0" :value="pendingCount" class="tab-badge" type="warning"/>
          </span>
        </template>
      </el-tab-pane>
      <el-tab-pane :label="$t('admin.content.comment.tabsApproved')" name="approved"/>
    </el-tabs>

    <AdminListShell
      :empty-desc="list.hasFilters.value ? $t('admin.content.comment.emptyFiltered') : $t('admin.content.comment.emptyDesc')"
      :empty-title="list.hasFilters.value ? $t('admin.content.comment.emptyFiltered') : $t('admin.content.comment.emptyTitle')"
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
        <el-form-item :label="$t('admin.content.comment.keyword')">
          <el-input
            v-model="list.query.keyword"
            :placeholder="$t('admin.content.comment.keywordPlaceholder')"
            clearable
            style="width: 220px"
            @keyup.enter="list.search()"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.content.comment.articleId')">
          <el-input-number v-model="list.query.article_id" :controls="false" :min="1" style="width: 120px"
                           @change="list.search()"/>
        </el-form-item>
      </template>

      <template #bulk>
        <el-button v-auth="'module_content:comment:approve'" plain type="primary" @click="bulkApprove">
          {{ $t('admin.content.comment.batchApprove') }}
        </el-button>
        <el-button v-auth="'module_content:comment:approve'" plain @click="bulkReject">
          {{ $t('admin.content.comment.batchReject') }}
        </el-button>
        <el-button v-auth="'module_content:comment:delete'" plain type="danger" @click="bulkDelete">
          {{ $t('admin.common.delete') }}
        </el-button>
      </template>

      <el-table-column :label="$t('admin.content.comment.author')" width="180">
        <template #default="{row}">
          <div class="admin-cell-title">{{ authorLabel(row as CommentItem) }}</div>
          <div class="admin-cell-sub">{{ row.author_email || '-' }}</div>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.content.comment.content')" min-width="300">
        <template #default="{row}">
          <div class="comment-content">{{ truncate(row.content, 120) }}</div>
          <div v-if="row.spam_reasons" class="admin-cell-sub">
            {{ $t('admin.content.comment.reasons') }}: {{ row.spam_reasons }}
          </div>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.content.comment.article')" width="120">
        <template #default="{row}">
          <el-link :underline="false" type="primary" @click="openArticle(row as CommentItem)">
            #{{ row.article_id }}
          </el-link>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.content.comment.likes')" prop="likes" width="80"/>

      <el-table-column :label="$t('admin.content.comment.spamScore')" width="110">
        <template #default="{row}">
          <el-tag v-if="row.spam_score != null" :type="spamType(row.spam_score)" size="small">
            {{ Number(row.spam_score).toFixed(2) }}
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.common.status')" width="110">
        <template #default="{row}">
          <el-tag :type="row.is_approved ? 'success' : 'warning'" size="small">
            {{
              row.is_approved ? $t('admin.content.comment.statusApproved') : $t('admin.content.comment.statusPending')
            }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column :label="$t('admin.common.createdAt')" width="170">
        <template #default="{row}">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>

      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="300">
        <template #default="{row}">
          <el-button v-if="!row.is_approved" v-auth="'module_content:comment:approve'" :icon="Check" link
                     type="primary" @click="approveRow(row as CommentItem)">
            {{ $t('admin.content.comment.approve') }}
          </el-button>
          <el-button v-else v-auth="'module_content:comment:approve'" :icon="Close" link
                     @click="rejectRow(row as CommentItem)">
            {{ $t('admin.content.comment.reject') }}
          </el-button>
          <el-button :icon="ChatDotRound" link type="primary" @click="openReply(row as CommentItem)">
            {{ $t('admin.content.comment.reply') }}
          </el-button>
          <el-button v-auth="'module_content:comment:edit'" :icon="Edit" link @click="openEdit(row as CommentItem)">
            {{ $t('admin.common.edit') }}
          </el-button>
          <el-button v-auth="'module_content:comment:delete'" :icon="Delete" link type="danger"
                     @click="removeRow(row as CommentItem)">
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>

    <!-- 编辑内容 -->
    <el-dialog v-model="editVisible" :title="$t('admin.content.comment.editComment')" width="640px">
      <el-input v-model="editContent" :rows="6" type="textarea"/>
      <template #footer>
        <el-button @click="editVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="editSaving" type="primary" @click="submitEdit">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- 管理员回复 -->
    <el-dialog v-model="replyVisible" :title="$t('admin.content.comment.reply')" width="640px">
      <div v-if="replyTarget" class="reply-quote">
        <div class="reply-quote__meta">
          <span class="admin-cell-title">{{ authorLabel(replyTarget) }}</span>
          <span class="admin-cell-sub">{{ formatDateTime(replyTarget.created_at) }}</span>
        </div>
        <p class="reply-quote__text">{{ replyTarget.content }}</p>
      </div>
      <el-input v-model="replyContent" :placeholder="$t('admin.content.comment.replyPlaceholder')" :rows="4"
                type="textarea"/>
      <template #footer>
        <el-button @click="replyVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :icon="View" :loading="replySending" type="primary" @click="submitReply">
          {{ $t('admin.content.comment.replySend') }}
        </el-button>
      </template>
    </el-dialog>
  </AdminPage>
</template>

<style scoped>
.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.tab-badge {
  transform: translateY(-2px);
}

.comment-content {
  color: var(--admin-fg);
  line-height: 1.5;
}

.reply-quote {
  margin-bottom: var(--admin-gap);
  padding: var(--admin-gap-sm) var(--admin-gap);
  border-left: 3px solid var(--admin-line-strong);
  border-radius: var(--admin-radius-sm);
  background: var(--admin-surface-soft);
}

.reply-quote__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.reply-quote__text {
  margin: 0;
  color: var(--admin-fg-muted);
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
}
</style>
