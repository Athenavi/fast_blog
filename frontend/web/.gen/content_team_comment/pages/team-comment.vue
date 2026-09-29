<script lang="ts" setup>
/**
 * 团队内部评论（content 域）
 *
 * 对齐后端 v3 模块 `content/team_comment`（controller.py 为准）：
 *   按内容查评论树、发表 / 修改 / 删除评论、标记已解决、@ 到我的评论、评论统计。
 * 权限码复用 `module_content:collaboration:{view,create,edit,delete}`；
 * 写操作（修改 / 删除 / 解决）后端额外要求「评论作者或管理员」，页面按钮仅做提示性禁用。
 *
 * 与「协作管理」页的团队评论标签区分：那里的评论走 `content/collaboration/comment` 旧前缀，
 * 本页走 v3 独立的 `content/team_comment`。
 */
import {ChatDotRound, Delete, EditPen, Plus, Refresh, Select} from '@element-plus/icons-vue'
import {reactive, ref} from 'vue'

import {teamCommentApi, type TeamCommentListQuery, type TeamCommentOut, type TeamCommentStatistics} from '@/api'
import type {PageResult} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {formatDateTime, truncate} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.teamComment.title',
  permission: 'module_content:collaboration:view',
})

const {t} = useI18n()

/** 内容类型候选项（后端 `content_type` 为自由字符串，这里给出常见值） */
const CONTENT_TYPES = ['article', 'page', 'block', 'product'] as const

/** content_id 未填时不发请求，返回空页（列表接口要求该参数） */
function emptyPage(): PageResult<TeamCommentOut> {
  return {items: [], total: 0, page: 1, pageSize: 20, pages: 0}
}

// ---------------------------------------------------------------- 评论树列表
const list = useAdminList<TeamCommentOut, TeamCommentListQuery>({
  fetcher: (params) => {
    if (params.content_id === undefined || params.content_id === null) {
      return Promise.resolve(emptyPage())
    }
    return teamCommentApi.list({
      content_type: params.content_type,
      content_id: params.content_id,
      include_resolved: params.include_resolved,
      page: params.page,
      page_size: params.page_size,
    })
  },
  defaultQuery: {content_type: 'article', content_id: undefined, include_resolved: true},
  syncUrl: true,
  immediate: false,
})

// ---------------------------------------------------------------- 统计
const stats = ref<TeamCommentStatistics | null>(null)
const statsLoading = ref(false)

async function loadStatistics(): Promise<void> {
  statsLoading.value = true
  try {
    stats.value = await teamCommentApi.statistics({
      content_type: list.query.content_type || undefined,
      content_id: list.query.content_id,
    })
  } finally {
    statsLoading.value = false
  }
}

// ---------------------------------------------------------------- 查询 / 刷新
function hasContentId(): boolean {
  return list.query.content_id !== undefined && list.query.content_id !== null
}

async function onSearch(): Promise<void> {
  if (!hasContentId()) {
    ElMessage.warning(t('admin.content.teamComment.contentIdRequired'))
    return
  }
  await list.search()
  loadStatistics().catch(() => undefined)
}

async function onReset(): Promise<void> {
  await list.reset()
}

function refreshAll(): void {
  list.reload().catch(() => undefined)
  if (hasContentId()) loadStatistics().catch(() => undefined)
}

// ---------------------------------------------------------------- 发表评论
const createVisible = ref(false)
const createSaving = ref(false)
const createForm = reactive({
  content_type: 'article',
  content_id: undefined as number | undefined,
  text: '',
  parent_id: undefined as number | undefined,
  mentionsText: '',
})

/** 逗号 / 空白分隔的用户 ID → 去重正整数数组；空则 null（后端按可选处理） */
function parseMentions(text: string): number[] | null {
  const items = text
    .split(/[,\s]+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => Number(part))
    .filter((value) => Number.isInteger(value) && value > 0)
  return items.length ? items : null
}

function openCreate(parentId?: number): void {
  Object.assign(createForm, {
    content_type: list.query.content_type || 'article',
    content_id: list.query.content_id,
    text: '',
    parent_id: parentId,
    mentionsText: '',
  })
  createVisible.value = true
}

async function submitCreate(): Promise<void> {
  if (createForm.content_id === undefined || createForm.content_id === null) {
    ElMessage.warning(t('admin.content.teamComment.contentIdRequired'))
    return
  }
  if (!createForm.text.trim()) {
    ElMessage.warning(t('admin.content.teamComment.textRequired'))
    return
  }
  createSaving.value = true
  try {
    await teamCommentApi.create({
      content_type: createForm.content_type,
      content_id: createForm.content_id,
      text: createForm.text.trim(),
      parent_id: createForm.parent_id ?? null,
      mentions: parseMentions(createForm.mentionsText),
    })
    ElMessage.success(t('admin.content.teamComment.created'))
    createVisible.value = false
    await list.reload()
    loadStatistics().catch(() => undefined)
  } finally {
    createSaving.value = false
  }
}

// ---------------------------------------------------------------- 修改评论
const editVisible = ref(false)
const editSaving = ref(false)
const editTarget = ref<TeamCommentOut | null>(null)
const editText = ref('')

function openEdit(row: TeamCommentOut): void {
  editTarget.value = row
  editText.value = row.text || ''
  editVisible.value = true
}

async function submitEdit(): Promise<void> {
  if (!editTarget.value) return
  if (!editText.value.trim()) {
    ElMessage.warning(t('admin.content.teamComment.textRequired'))
    return
  }
  editSaving.value = true
  try {
    await teamCommentApi.update(editTarget.value.id, {text: editText.value.trim()})
    ElMessage.success(t('admin.content.teamComment.saved'))
    editVisible.value = false
    await list.reload()
  } finally {
    editSaving.value = false
  }
}

// ---------------------------------------------------------------- 解决 / 删除
async function onResolve(row: TeamCommentOut): Promise<void> {
  await teamCommentApi.resolve(row.id)
  ElMessage.success(t('admin.content.teamComment.resolvedDone'))
  await list.reload()
  loadStatistics().catch(() => undefined)
}

async function onDelete(row: TeamCommentOut): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.content.teamComment.deleteConfirm', {id: row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await teamCommentApi.remove(row.id)
  ElMessage.success(t('admin.common.delete'))
  await list.reload()
  loadStatistics().catch(() => undefined)
}

// ---------------------------------------------------------------- @ 到我的评论
const mentionsVisible = ref(false)
const mentionsLoading = ref(false)
const mentionsUnreadOnly = ref(false)
const mentions = ref<TeamCommentOut[]>([])

async function loadMentions(): Promise<void> {
  mentionsLoading.value = true
  try {
    mentions.value = await teamCommentApi.mentions({
      limit: 50,
      unread_only: mentionsUnreadOnly.value,
    })
  } finally {
    mentionsLoading.value = false
  }
}

function reloadMentions(): void {
  loadMentions().catch(() => undefined)
}

function openMentions(): void {
  mentionsVisible.value = true
  reloadMentions()
}
</script>

<template>
  <AdminPage :desc="$t('admin.content.teamComment.desc')" :title="$t('admin.content.teamComment.title')">
    <template #actions>
      <el-button v-auth="'module_content:collaboration:create'" :icon="Plus" type="primary" @click="openCreate()">
        {{ $t('admin.content.teamComment.createComment') }}
      </el-button>
      <el-button :icon="ChatDotRound" @click="openMentions">
        {{ $t('admin.content.teamComment.myMentions') }}
      </el-button>
      <el-button :icon="Refresh" @click="refreshAll">{{ $t('admin.common.refresh') }}</el-button>
    </template>

    <el-card v-loading="statsLoading" class="mb-3" shadow="never">
      <div class="stat-row">
        <div class="stat-item">
          <span class="stat-item__label">{{ $t('admin.content.teamComment.totalComments') }}</span>
          <span class="stat-item__value">{{ stats?.total_comments ?? '-' }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-item__label">{{ $t('admin.content.teamComment.resolvedComments') }}</span>
          <span class="stat-item__value">{{ stats?.resolved_comments ?? '-' }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-item__label">{{ $t('admin.content.teamComment.unresolvedComments') }}</span>
          <span class="stat-item__value">{{ stats?.unresolved_comments ?? '-' }}</span>
        </div>
      </div>
      <el-table v-if="stats && stats.by_author.length" :data="stats.by_author" class="mt-2" size="small">
        <el-table-column :label="$t('admin.content.teamComment.authorId')" prop="author_id" width="140"/>
        <el-table-column :label="$t('admin.content.teamComment.count')" prop="count"/>
      </el-table>
    </el-card>

    <AdminListShell
      :empty-desc="$t('admin.content.teamComment.emptyDesc')"
      :empty-title="$t('admin.content.teamComment.emptyTitle')"
      :failed="list.failed.value"
      :loading="list.loading.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      :rows="list.rows.value"
      :selectable="false"
      :total="list.total.value"
      @refresh="refreshAll"
      @reset="onReset"
      @search="onSearch"
      @page-change="list.onPageChange"
      @size-change="list.onSizeChange"
    >
      <template #filters>
        <el-form-item :label="$t('admin.content.teamComment.contentType')">
          <el-select v-model="list.query.content_type" style="width: 140px" @change="onSearch">
            <el-option v-for="item in CONTENT_TYPES" :key="item" :label="item" :value="item"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.content.teamComment.contentId')">
          <el-input-number v-model="list.query.content_id" :controls="false" :min="1" style="width: 140px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.teamComment.includeResolved')">
          <el-switch v-model="list.query.include_resolved" @change="onSearch"/>
        </el-form-item>
      </template>

      <template #actions>
        <el-button v-auth="'module_content:collaboration:create'" :icon="Plus" type="primary" @click="openCreate()">
          {{ $t('admin.content.teamComment.createComment') }}
        </el-button>
      </template>

      <el-table-column label="ID" prop="id" width="80"/>
      <el-table-column :label="$t('admin.content.teamComment.author')" width="150">
        <template #default="{row}">{{ (row as TeamCommentOut).author_name || '-' }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.content.teamComment.text')" min-width="280">
        <template #default="{row}">{{ truncate((row as TeamCommentOut).text, 120) }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.content.teamComment.mentions')" min-width="140">
        <template #default="{row}">
          <span v-if="(row as TeamCommentOut).mentions.length">{{ (row as TeamCommentOut).mentions.join(', ') }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.content.teamComment.resolved')" align="center" width="100">
        <template #default="{row}">
          <el-tag :type="(row as TeamCommentOut).is_resolved ? 'success' : 'warning'" size="small">
            {{
              (row as TeamCommentOut).is_resolved
                ? $t('admin.common.enabled')
                : $t('admin.content.teamComment.unresolved')
            }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.content.teamComment.createdAt')" width="170">
        <template #default="{row}">{{ formatDateTime((row as TeamCommentOut).created_at) }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="240">
        <template #default="{row}">
          <el-button :icon="ChatDotRound" link type="primary"
                     @click="openCreate((row as TeamCommentOut).id)">
            {{ $t('admin.content.teamComment.reply') }}
          </el-button>
          <el-button v-if="!(row as TeamCommentOut).is_resolved" v-auth="'module_content:collaboration:edit'"
                     :icon="Select" link type="primary" @click="onResolve(row as TeamCommentOut)">
            {{ $t('admin.content.teamComment.resolve') }}
          </el-button>
          <el-button v-auth="'module_content:collaboration:edit'" :icon="EditPen" link
                     @click="openEdit(row as TeamCommentOut)">
            {{ $t('admin.common.edit') }}
          </el-button>
          <el-button v-auth="'module_content:collaboration:delete'" :icon="Delete" link type="danger"
                     @click="onDelete(row as TeamCommentOut)">
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>

    <!-- 发表评论 -->
    <el-dialog v-model="createVisible" :title="$t('admin.content.teamComment.createComment')" width="640px">
      <el-form label-width="110px">
        <el-form-item :label="$t('admin.content.teamComment.contentType')">
          <el-select v-model="createForm.content_type" style="width: 200px">
            <el-option v-for="item in CONTENT_TYPES" :key="item" :label="item" :value="item"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.content.teamComment.contentId')" required>
          <el-input-number v-model="createForm.content_id" :controls="false" :min="1" style="width: 200px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.teamComment.text')" required>
          <el-input v-model="createForm.text" :rows="4" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.teamComment.parentId')">
          <el-input-number v-model="createForm.parent_id" :controls="false" :min="1" style="width: 200px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.teamComment.mentions')">
          <el-input v-model="createForm.mentionsText"
                    :placeholder="$t('admin.content.teamComment.mentionsPlaceholder')"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="createSaving" type="primary" @click="submitCreate">
          {{ $t('admin.content.teamComment.createComment') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 修改评论 -->
    <el-dialog v-model="editVisible" :title="$t('admin.content.teamComment.editComment')" width="640px">
      <el-input v-model="editText" :rows="6" type="textarea"/>
      <template #footer>
        <el-button @click="editVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="editSaving" type="primary" @click="submitEdit">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- @ 到我的评论 -->
    <el-dialog v-model="mentionsVisible" :title="$t('admin.content.teamComment.myMentions')" width="760px">
      <el-form :inline="true">
        <el-form-item :label="$t('admin.content.teamComment.unreadOnly')">
          <el-switch v-model="mentionsUnreadOnly" @change="reloadMentions"/>
        </el-form-item>
      </el-form>
      <el-table v-loading="mentionsLoading" :data="mentions" border size="small">
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column :label="$t('admin.content.teamComment.contentType')" prop="content_type" width="110"/>
        <el-table-column :label="$t('admin.content.teamComment.contentId')" prop="content_id" width="90"/>
        <el-table-column :label="$t('admin.content.teamComment.author')" prop="author_name" width="130"/>
        <el-table-column :label="$t('admin.content.teamComment.text')" min-width="220">
          <template #default="{row}">{{ truncate((row as TeamCommentOut).text, 80) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.content.teamComment.createdAt')" width="170">
          <template #default="{row}">{{ formatDateTime((row as TeamCommentOut).created_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!mentionsLoading && !mentions.length"
                :description="$t('admin.content.teamComment.mentionsEmpty')"/>
    </el-dialog>
  </AdminPage>
</template>

<style scoped>
.stat-row {
  display: flex;
  gap: var(--admin-gap-lg, 24px);
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-item__label {
  color: var(--admin-fg-muted, #909399);
  font-size: 13px;
}

.stat-item__value {
  color: var(--admin-fg, #303133);
  font-size: 22px;
  font-weight: 600;
}
</style>
