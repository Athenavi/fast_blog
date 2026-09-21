<script lang="ts" setup>
/**
 * 协作管理（T5-11 批次 9，content 域）
 *
 * 对齐 v3 `/content/collaboration`：工作区 / 成员与任务 / 团队评论 / 协作邀请（四标签）。
 * 角色层级 `viewer < editor < admin < owner` 由后端强制（页面按钮只做提示性禁用）。
 * 实时协同的 WebSocket 通道不在此页 —— 那是文章编辑器的能力，用原生 WebSocket 直连。
 */
import {Delete, EditPen, Plus, Refresh, Search, UserFilled} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {
  collaborationApi,
  type InviteItem,
  type MemberItem,
  type TaskItem,
  type TeamCommentItem,
  type WorkspaceItem,
} from '@/api'
import type {PageQuery} from '@/api/types'
import {useTable} from '@/hooks/useTable'

/** 团队评论类型（与内容评论的 `CommentItem` 区分：前者挂在任意内容对象上，带 mentions / is_resolved） */
type CommentItem = TeamCommentItem

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.collaboration.title',
  permission: 'module_content:collaboration:view',
})

const {t} = useI18n()
const activeTab = ref('workspace')

const MEMBER_ROLES = ['viewer', 'editor', 'admin', 'owner'] as const
const TASK_STATUSES = ['pending', 'in_progress', 'completed', 'cancelled'] as const
const TASK_PRIORITIES = ['low', 'medium', 'high', 'urgent'] as const
const TASK_TAG: Record<string, string> = {
  pending: 'info',
  in_progress: 'warning',
  completed: 'success',
  cancelled: 'info',
}

// ---------------------------------------------------------------- 工作区
const workspaces = ref<WorkspaceItem[]>([])
const workspaceLoading = ref(false)
const currentWorkspaceId = ref<number | null>(null)

async function loadWorkspaces() {
  workspaceLoading.value = true
  try {
    workspaces.value = await collaborationApi.listWorkspaces()
    if (currentWorkspaceId.value === null && workspaces.value.length) {
      currentWorkspaceId.value = workspaces.value[0]?.id ?? null
    }
  } finally {
    workspaceLoading.value = false
  }
}

const workspaceFormVisible = ref(false)
const workspaceEditingId = ref<number | null>(null)
const workspaceSaving = ref(false)
const workspaceForm = reactive({name: '', slug: '', description: ''})

const workspaceFormTitle = computed(() =>
  workspaceEditingId.value
    ? t('admin.content.collaboration.editWorkspace')
    : t('admin.content.collaboration.createWorkspace'),
)

function openWorkspaceCreate() {
  workspaceEditingId.value = null
  Object.assign(workspaceForm, {name: '', slug: '', description: ''})
  workspaceFormVisible.value = true
}

function openWorkspaceEdit(row: WorkspaceItem) {
  workspaceEditingId.value = row.id
  Object.assign(workspaceForm, {
    name: row.name || '',
    slug: row.slug || '',
    description: row.description || '',
  })
  workspaceFormVisible.value = true
}

async function submitWorkspace() {
  if (!workspaceForm.name.trim()) {
    ElMessage.warning(t('admin.content.collaboration.nameRequired'))
    return
  }
  workspaceSaving.value = true
  try {
    const payload = {
      name: workspaceForm.name.trim(),
      slug: workspaceForm.slug.trim() || null,
      description: workspaceForm.description.trim() || null,
    }
    if (workspaceEditingId.value) {
      await collaborationApi.updateWorkspace(workspaceEditingId.value, payload)
    } else {
      const created = await collaborationApi.createWorkspace(payload)
      currentWorkspaceId.value = created.id
    }
    ElMessage.success(t('admin.common.save'))
    workspaceFormVisible.value = false
    await loadWorkspaces()
  } finally {
    workspaceSaving.value = false
  }
}

async function onDeleteWorkspace(row: WorkspaceItem) {
  await ElMessageBox.confirm(
    t('admin.content.collaboration.deleteWorkspaceConfirm', {name: row.name || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await collaborationApi.removeWorkspace(row.id)
  ElMessage.success(t('admin.common.delete'))
  if (currentWorkspaceId.value === row.id) currentWorkspaceId.value = null
  await loadWorkspaces()
}

function openMembers(row: WorkspaceItem) {
  currentWorkspaceId.value = row.id
  activeTab.value = 'member'
}

// ---------------------------------------------------------------- 成员
const members = ref<MemberItem[]>([])
const memberLoading = ref(false)
const memberFormVisible = ref(false)
const memberSaving = ref(false)
const memberForm = reactive({user_id: undefined as number | undefined, role: 'viewer' as string})

async function loadMembers() {
  if (currentWorkspaceId.value === null) return
  memberLoading.value = true
  try {
    members.value = await collaborationApi.listMembers(currentWorkspaceId.value)
  } finally {
    memberLoading.value = false
  }
}

function openMemberCreate() {
  Object.assign(memberForm, {user_id: undefined, role: 'viewer'})
  memberFormVisible.value = true
}

async function submitMember() {
  if (currentWorkspaceId.value === null || memberForm.user_id === undefined) {
    ElMessage.warning(t('admin.content.collaboration.userIdRequired'))
    return
  }
  memberSaving.value = true
  try {
    await collaborationApi.addMember(currentWorkspaceId.value, {
      user_id: memberForm.user_id,
      role: memberForm.role as never,
    })
    ElMessage.success(t('admin.common.save'))
    memberFormVisible.value = false
    await loadMembers()
  } finally {
    memberSaving.value = false
  }
}

async function onChangeRole(row: MemberItem, role: string) {
  if (currentWorkspaceId.value === null || row.user_id === null || row.user_id === undefined) return
  await collaborationApi.updateMemberRole(currentWorkspaceId.value, row.user_id, role as never)
  ElMessage.success(t('admin.common.save'))
  await loadMembers()
}

async function onRemoveMember(row: MemberItem) {
  if (currentWorkspaceId.value === null || row.user_id === null || row.user_id === undefined) return
  await ElMessageBox.confirm(
    t('admin.content.collaboration.removeMemberConfirm', {name: row.username || row.user_id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await collaborationApi.removeMember(currentWorkspaceId.value, row.user_id)
  ElMessage.success(t('admin.common.delete'))
  await loadMembers()
}

// ---------------------------------------------------------------- 任务
const {
  list: taskList,
  loading: taskLoading,
  total: taskTotal,
  page: taskPage,
  pageSize: taskPageSize,
  query: taskQuery,
  search: taskSearch,
  reset: taskReset,
  load: taskLoad,
  onPageChange: onTaskPageChange,
  onSizeChange: onTaskSizeChange,
} = useTable<TaskItem, PageQuery & { status?: string }>({
  fetcher: (params) =>
    collaborationApi.listTasks(currentWorkspaceId.value ?? 0, params),
  defaultQuery: {status: ''},
  syncUrl: true,
  immediate: false,
})

const taskFormVisible = ref(false)
const taskSaving = ref(false)
const taskForm = reactive({
  title: '',
  description: '',
  priority: 'medium' as string,
  assigned_to: undefined as number | undefined,
})

function openTaskCreate() {
  Object.assign(taskForm, {title: '', description: '', priority: 'medium', assigned_to: undefined})
  taskFormVisible.value = true
}

async function submitTask() {
  if (currentWorkspaceId.value === null || !taskForm.title.trim()) {
    ElMessage.warning(t('admin.content.collaboration.titleRequired'))
    return
  }
  taskSaving.value = true
  try {
    await collaborationApi.createTask(currentWorkspaceId.value, {
      title: taskForm.title.trim(),
      description: taskForm.description.trim() || null,
      priority: taskForm.priority,
      assigned_to: taskForm.assigned_to ?? null,
    })
    ElMessage.success(t('admin.common.save'))
    taskFormVisible.value = false
    await taskLoad()
  } finally {
    taskSaving.value = false
  }
}

async function onChangeTaskStatus(row: TaskItem, status: string) {
  await collaborationApi.updateTask(row.id, {status})
  ElMessage.success(t('admin.common.save'))
  await taskLoad()
}

async function onDeleteTask(row: TaskItem) {
  await ElMessageBox.confirm(
    t('admin.content.collaboration.deleteTaskConfirm', {name: row.title || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await collaborationApi.removeTask(row.id)
  ElMessage.success(t('admin.common.delete'))
  await taskLoad()
}

// ---------------------------------------------------------------- 团队评论
const commentForm = reactive({content_type: 'article', content_id: undefined as number | undefined})
const comments = ref<CommentItem[]>([])
const commentLoading = ref(false)
const commentPage = ref(1)
const commentTotal = ref(0)
const commentPageSize = ref(20)
const commentSearching = ref(false)
const newComment = reactive({text: '', parent_id: undefined as number | undefined, mentionsText: ''})

async function loadComments() {
  if (commentForm.content_id === undefined) {
    ElMessage.warning(t('admin.content.collaboration.contentIdRequired'))
    return
  }
  commentLoading.value = true
  commentSearching.value = true
  try {
    const result = await collaborationApi.listComments({
      content_type: commentForm.content_type,
      content_id: commentForm.content_id,
      page: commentPage.value,
      page_size: commentPageSize.value,
    })
    comments.value = result.items ?? []
    commentTotal.value = result.total ?? 0
  } finally {
    commentLoading.value = false
    commentSearching.value = false
  }
}

function parseMentions(text: string): number[] | null {
  const items = text
    .split(/[,\s]+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => Number(part))
    .filter((value) => Number.isInteger(value) && value > 0)
  return items.length ? items : null
}

async function submitComment() {
  if (commentForm.content_id === undefined || !newComment.text.trim()) {
    ElMessage.warning(t('admin.content.collaboration.commentRequired'))
    return
  }
  await collaborationApi.createComment({
    content_type: commentForm.content_type,
    content_id: commentForm.content_id,
    text: newComment.text.trim(),
    parent_id: newComment.parent_id ?? null,
    mentions: parseMentions(newComment.mentionsText),
  })
  ElMessage.success(t('admin.content.collaboration.commented'))
  Object.assign(newComment, {text: '', parent_id: undefined, mentionsText: ''})
  await loadComments()
}

async function onResolveComment(row: CommentItem) {
  await collaborationApi.resolveComment(row.id)
  ElMessage.success(t('admin.content.collaboration.resolved'))
  await loadComments()
}

async function onDeleteComment(row: CommentItem) {
  await ElMessageBox.confirm(
    t('admin.content.collaboration.deleteCommentConfirm', {name: row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await collaborationApi.removeComment(row.id)
  ElMessage.success(t('admin.common.delete'))
  await loadComments()
}

async function onPageComments(next: number) {
  commentPage.value = next
  await loadComments()
}

// ---------------------------------------------------------------- 邀请
const {
  list: inviteList,
  loading: inviteLoading,
  total: inviteTotal,
  page: invitePage,
  pageSize: invitePageSize,
  query: inviteQuery,
  search: inviteSearch,
  reset: inviteReset,
  load: inviteLoad,
  onPageChange: onInvitePageChange,
  onSizeChange: onInviteSizeChange,
} = useTable<InviteItem, PageQuery & { target_type?: string }>({
  fetcher: (params) => collaborationApi.listInvites(params),
  defaultQuery: {keyword: '', target_type: ''},
  syncUrl: true,
})

const inviteFormVisible = ref(false)
const inviteSaving = ref(false)
const inviteForm = reactive({
  target_type: 'workspace' as string,
  target_id: undefined as number | undefined,
  permission: 'edit',
  expire_hours: 24,
  max_uses: 0,
})

function openInviteCreate() {
  Object.assign(inviteForm, {
    target_type: 'workspace',
    target_id: currentWorkspaceId.value ?? undefined,
    permission: 'edit',
    expire_hours: 24,
    max_uses: 0,
  })
  inviteFormVisible.value = true
}

async function submitInvite() {
  if (inviteForm.target_id === undefined) {
    ElMessage.warning(t('admin.content.collaboration.targetIdRequired'))
    return
  }
  inviteSaving.value = true
  try {
    const created = await collaborationApi.createInvite({
      target_type: inviteForm.target_type as never,
      target_id: inviteForm.target_id,
      permission: inviteForm.permission,
      expire_hours: inviteForm.expire_hours,
      max_uses: inviteForm.max_uses,
    })
    inviteFormVisible.value = false
    await inviteLoad()
    ElMessageBox.alert(
      t('admin.content.collaboration.inviteCreatedHint', {code: created.invite_code || ''}),
      t('admin.common.notice'),
    ).catch(() => undefined)
  } finally {
    inviteSaving.value = false
  }
}

async function onRevokeInvite(row: InviteItem) {
  await ElMessageBox.confirm(
    t('admin.content.collaboration.revokeConfirm', {name: row.invite_code || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await collaborationApi.revokeInvite(row.id)
  ElMessage.success(t('admin.common.delete'))
  await inviteLoad()
}

const acceptCode = ref('')
const accepting = ref(false)

async function onAcceptInvite() {
  if (!acceptCode.value.trim()) {
    ElMessage.warning(t('admin.content.collaboration.codeRequired'))
    return
  }
  accepting.value = true
  try {
    await collaborationApi.acceptInvite(acceptCode.value.trim())
    ElMessage.success(t('admin.content.collaboration.accepted'))
    acceptCode.value = ''
    await loadWorkspaces()
    await inviteLoad()
  } finally {
    accepting.value = false
  }
}

onMounted(() => {
  loadWorkspaces().catch(() => undefined)
})

// 切到「成员与任务」标签时按需拉取（工作区可能在别处被改选）
function onTabChange(name: string | number) {
  if (name === 'member' && currentWorkspaceId.value !== null) {
    loadMembers().catch(() => undefined)
    taskLoad().catch(() => undefined)
  }
}
</script>

<template>
  <div class="page-container">
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- 工作区 -->
      <el-tab-pane :label="$t('admin.content.collaboration.workspaces')" name="workspace">
        <el-card shadow="never">
          <div class="table-toolbar">
            <el-button v-auth="'module_content:collaboration:create'" :icon="Plus" type="primary"
                       @click="openWorkspaceCreate">
              {{ $t('admin.content.collaboration.createWorkspace') }}
            </el-button>
            <el-button :icon="Refresh" @click="loadWorkspaces()">{{ $t('admin.common.refresh') }}</el-button>
          </div>

          <AdminTableSkeleton v-if="workspaceLoading && !workspaces.length" :rows="5"/>
          <AdminEmpty
            v-else-if="!workspaceLoading && !workspaces.length"
            :desc="$t('admin.content.collaboration.emptyDesc')"
            :title="$t('admin.content.collaboration.emptyTitle')"
          />

          <el-table v-else v-loading="workspaceLoading" :data="workspaces" border stripe>
            <el-table-column :label="$t('admin.common.name')" min-width="160" prop="name"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.content.collaboration.slug')" min-width="140" prop="slug"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.content.collaboration.memberCount')" prop="member_count"
                             width="100"/>
            <el-table-column :label="$t('admin.content.collaboration.myRole')" prop="role" width="110"/>
            <el-table-column :label="$t('admin.common.status')" align="center" width="100">
              <template #default="{ row }">
                <el-tag :type="(row as WorkspaceItem).is_active ? 'success' : 'info'" size="small">
                  {{ (row as WorkspaceItem).is_active ? $t('admin.common.enabled') : $t('admin.common.disabled') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="240">
              <template #default="{ row }">
                <el-button :icon="UserFilled" link type="primary" @click="openMembers(row as WorkspaceItem)">
                  {{ $t('admin.content.collaboration.membersAndTasks') }}
                </el-button>
                <el-button v-auth="'module_content:collaboration:edit'" :icon="EditPen" link type="primary"
                           @click="openWorkspaceEdit(row as WorkspaceItem)">
                  {{ $t('admin.common.edit') }}
                </el-button>
                <el-button v-auth="'module_content:collaboration:delete'" :icon="Delete" link type="danger"
                           @click="onDeleteWorkspace(row as WorkspaceItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!workspaceLoading && !workspaces.length"
                    :description="$t('admin.content.collaboration.noWorkspaces')"/>
        </el-card>
      </el-tab-pane>

      <!-- 成员与任务 -->
      <el-tab-pane :label="$t('admin.content.collaboration.membersAndTasks')" name="member">
        <el-alert :closable="false" class="mb-3" show-icon type="info">
          <template #title>
            {{ $t('admin.content.collaboration.currentWorkspace') }}:
            {{ workspaces.find((item) => item.id === currentWorkspaceId)?.name || '-' }}
          </template>
        </el-alert>

        <el-card class="mb-3" shadow="never">
          <div class="table-toolbar">
            <span class="table-toolbar__title">{{ $t('admin.content.collaboration.members') }}</span>
            <el-button v-auth="'module_content:collaboration:edit'" :icon="Plus" size="small"
                       type="primary" @click="openMemberCreate">
              {{ $t('admin.content.collaboration.addMember') }}
            </el-button>
            <el-button :icon="Refresh" size="small" @click="loadMembers()">
              {{ $t('admin.common.refresh') }}
            </el-button>
          </div>
          <el-table v-loading="memberLoading" :data="members" border size="small" stripe>
            <el-table-column :label="$t('admin.content.collaboration.userId')" prop="user_id" width="100"/>
            <el-table-column :label="$t('admin.content.collaboration.username')" min-width="140"
                             prop="username"/>
            <el-table-column :label="$t('admin.content.collaboration.email')" min-width="180" prop="email"/>
            <el-table-column :label="$t('admin.content.collaboration.role')" width="150">
              <template #default="{ row }">
                <el-select :disabled="(row as MemberItem).role === 'owner'"
                           :model-value="(row as MemberItem).role"
                           size="small" @change="(value: string) => onChangeRole(row as MemberItem, value)">
                  <el-option v-for="item in MEMBER_ROLES" :key="item" :label="item" :value="item"/>
                </el-select>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.content.collaboration.joinedAt')" min-width="160"
                             prop="joined_at"/>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="100">
              <template #default="{ row }">
                <el-button v-auth="'module_content:collaboration:edit'" :disabled="(row as MemberItem).role === 'owner'"
                           :icon="Delete" link type="danger"
                           @click="onRemoveMember(row as MemberItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="never">
          <div class="table-toolbar">
            <span class="table-toolbar__title">{{ $t('admin.content.collaboration.tasks') }}</span>
            <el-button v-auth="'module_content:collaboration:create'" :disabled="currentWorkspaceId === null"
                       :icon="Plus" size="small" type="primary" @click="openTaskCreate">
              {{ $t('admin.content.collaboration.createTask') }}
            </el-button>
            <el-button :icon="Search" size="small" @click="taskSearch()">
              {{ $t('admin.common.search') }}
            </el-button>
            <el-button :icon="Refresh" size="small" @click="taskReset()">
              {{ $t('admin.common.reset') }}
            </el-button>
          </div>
          <el-table v-loading="taskLoading" :data="taskList" border size="small" stripe>
            <el-table-column :label="$t('admin.content.collaboration.title')" min-width="180" prop="title"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.content.collaboration.status')" width="150">
              <template #default="{ row }">
                <el-select :model-value="(row as TaskItem).status" size="small"
                           @change="(value: string) => onChangeTaskStatus(row as TaskItem, value)">
                  <el-option v-for="item in TASK_STATUSES" :key="item" :label="item" :value="item"/>
                </el-select>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.content.collaboration.priority')" width="110">
              <template #default="{ row }">
                <el-tag size="small">{{ (row as TaskItem).priority || '-' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.content.collaboration.assignedTo')" prop="assigned_to"
                             width="120"/>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="100">
              <template #default="{ row }">
                <el-button v-auth="'module_content:collaboration:delete'" :icon="Delete" link type="danger"
                           @click="onDeleteTask(row as TaskItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination :current-page="taskPage" :page-size="taskPageSize" :page-sizes="[10, 20, 50]"
                         :total="taskTotal" background class="table-pagination"
                         layout="total, sizes, prev, pager, next"
                         @current-change="onTaskPageChange" @size-change="onTaskSizeChange"/>
        </el-card>
      </el-tab-pane>

      <!-- 团队评论 -->
      <el-tab-pane :label="$t('admin.content.collaboration.comments')" name="comment">
        <el-card shadow="never">
          <el-form :inline="true" @submit.prevent="loadComments()">
            <el-form-item :label="$t('admin.content.collaboration.contentType')">
              <el-input v-model="commentForm.content_type" style="width: 130px"/>
            </el-form-item>
            <el-form-item :label="$t('admin.content.collaboration.contentId')">
              <el-input-number v-model="commentForm.content_id" :min="1" style="width: 130px"/>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="loadComments()">
                {{ $t('admin.common.search') }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-table v-loading="commentLoading" :data="comments" border size="small" stripe>
            <el-table-column :label="$t('admin.content.collaboration.author')" prop="author_name" width="140"/>
            <el-table-column :label="$t('admin.content.collaboration.text')" min-width="240" prop="text"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.content.collaboration.mentions')" min-width="120">
              <template #default="{ row }">
                {{ ((row as CommentItem).mentions ?? []).join(', ') || '-' }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.content.collaboration.resolved')" align="center" width="100">
              <template #default="{ row }">
                <el-tag :type="(row as CommentItem).is_resolved ? 'success' : 'info'" size="small">
                  {{ (row as CommentItem).is_resolved ? $t('admin.common.yes') : $t('admin.common.no') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="160">
              <template #default="{ row }">
                <el-button v-auth="'module_content:collaboration:edit'"
                           :disabled="(row as CommentItem).is_resolved" link type="success"
                           @click="onResolveComment(row as CommentItem)">
                  {{ $t('admin.content.collaboration.resolve') }}
                </el-button>
                <el-button v-auth="'module_content:collaboration:delete'" :icon="Delete" link type="danger"
                           @click="onDeleteComment(row as CommentItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination :current-page="commentPage" :page-size="commentPageSize" :total="commentTotal"
                         background class="table-pagination" layout="total, prev, pager, next"
                         @current-change="onPageComments"/>

          <el-divider/>
          <el-form :model="newComment" label-width="110px">
            <el-form-item :label="$t('admin.content.collaboration.text')">
              <el-input v-model="newComment.text" :autosize="{minRows: 3, maxRows: 8}" type="textarea"/>
            </el-form-item>
            <el-form-item :label="$t('admin.content.collaboration.parentId')">
              <el-input-number v-model="newComment.parent_id" :min="1" style="width: 160px"/>
            </el-form-item>
            <el-form-item :label="$t('admin.content.collaboration.mentions')">
              <el-input v-model="newComment.mentionsText"
                        :placeholder="$t('admin.content.collaboration.mentionsPlaceholder')"/>
            </el-form-item>
            <el-form-item>
              <el-button v-auth="'module_content:collaboration:create'" type="primary"
                         @click="submitComment">
                {{ $t('admin.content.collaboration.comment') }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 协作邀请 -->
      <el-tab-pane :label="$t('admin.content.collaboration.invites')" name="invite">
        <el-card shadow="never">
          <el-form :inline="true" :model="inviteQuery" @submit.prevent="inviteSearch()">
            <el-form-item :label="$t('admin.content.collaboration.keyword')">
              <el-input v-model="inviteQuery.keyword" clearable style="width: 180px"
                        @keyup.enter="inviteSearch()"/>
            </el-form-item>
            <el-form-item :label="$t('admin.content.collaboration.targetType')">
              <el-select v-model="inviteQuery.target_type" clearable style="width: 150px">
                <el-option label="article" value="article"/>
                <el-option label="workspace" value="workspace"/>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="inviteSearch()">
                {{ $t('admin.common.search') }}
              </el-button>
              <el-button :icon="Refresh" @click="inviteReset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>

          <div class="table-toolbar">
            <el-button v-auth="'module_content:collaboration:create'" :icon="Plus" type="primary"
                       @click="openInviteCreate">
              {{ $t('admin.content.collaboration.createInvite') }}
            </el-button>
            <el-input v-model="acceptCode" :placeholder="$t('admin.content.collaboration.acceptPlaceholder')"
                      style="width: 280px"/>
            <el-button v-auth="'module_content:collaboration:create'" :loading="accepting"
                       @click="onAcceptInvite">
              {{ $t('admin.content.collaboration.accept') }}
            </el-button>
            <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: inviteTotal}) }}</span>
          </div>

          <el-table v-loading="inviteLoading" :data="inviteList" border stripe>
            <el-table-column :label="$t('admin.content.collaboration.inviteCode')" min-width="240"
                             prop="invite_code" show-overflow-tooltip/>
            <el-table-column :label="$t('admin.content.collaboration.targetType')" prop="target_type"
                             width="120"/>
            <el-table-column :label="$t('admin.content.collaboration.targetId')" prop="target_id" width="100"/>
            <el-table-column :label="$t('admin.content.collaboration.permission')" prop="permission"
                             width="100"/>
            <el-table-column :label="$t('admin.content.collaboration.usage')" align="center" width="110">
              <template #default="{ row }">
                {{ (row as InviteItem).use_count }}/{{ (row as InviteItem).max_uses || '∞' }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.content.collaboration.expiresAt')" min-width="170"
                             prop="expires_at"/>
            <el-table-column :label="$t('admin.common.status')" align="center" width="100">
              <template #default="{ row }">
                <el-tag :type="(row as InviteItem).is_active ? 'success' : 'info'" size="small">
                  {{ (row as InviteItem).is_active ? $t('admin.common.enabled') : $t('admin.common.disabled') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="120">
              <template #default="{ row }">
                <el-button v-auth="'module_content:collaboration:delete'"
                           :disabled="!(row as InviteItem).is_active" :icon="Delete" link type="danger"
                           @click="onRevokeInvite(row as InviteItem)">
                  {{ $t('admin.content.collaboration.revoke') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination :current-page="invitePage" :page-size="invitePageSize"
                         :page-sizes="[10, 20, 50, 100]" :total="inviteTotal" background
                         class="table-pagination" layout="total, sizes, prev, pager, next, jumper"
                         @current-change="onInvitePageChange" @size-change="onInviteSizeChange"/>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 工作区表单 -->
    <el-drawer v-model="workspaceFormVisible" :title="workspaceFormTitle" destroy-on-close size="460px">
      <el-form :model="workspaceForm" label-width="110px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="workspaceForm.name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.collaboration.slug')">
          <el-input v-model="workspaceForm.slug"
                    :placeholder="$t('admin.content.collaboration.slugPlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="workspaceForm.description" :autosize="{minRows: 2, maxRows: 5}" type="textarea"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="workspaceFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="workspaceSaving" type="primary" @click="submitWorkspace">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-drawer>

    <!-- 成员表单 -->
    <el-dialog v-model="memberFormVisible" :title="$t('admin.content.collaboration.addMember')" width="420px">
      <el-form :model="memberForm" label-width="100px">
        <el-form-item :label="$t('admin.content.collaboration.userId')" required>
          <el-input-number v-model="memberForm.user_id" :min="1" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.collaboration.role')">
          <el-select v-model="memberForm.role" style="width: 100%">
            <el-option v-for="item in MEMBER_ROLES.filter((r) => r !== 'owner')" :key="item"
                       :label="item" :value="item"/>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="memberFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="memberSaving" type="primary" @click="submitMember">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 任务表单 -->
    <el-dialog v-model="taskFormVisible" :title="$t('admin.content.collaboration.createTask')" width="460px">
      <el-form :model="taskForm" label-width="110px">
        <el-form-item :label="$t('admin.content.collaboration.title')" required>
          <el-input v-model="taskForm.title"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="taskForm.description" :autosize="{minRows: 2, maxRows: 5}" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.collaboration.priority')">
          <el-select v-model="taskForm.priority" style="width: 100%">
            <el-option v-for="item in TASK_PRIORITIES" :key="item" :label="item" :value="item"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.content.collaboration.assignedTo')">
          <el-input-number v-model="taskForm.assigned_to" :min="1" style="width: 100%"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="taskFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="taskSaving" type="primary" @click="submitTask">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 邀请表单 -->
    <el-dialog v-model="inviteFormVisible" :title="$t('admin.content.collaboration.createInvite')"
               width="460px">
      <el-form :model="inviteForm" label-width="120px">
        <el-form-item :label="$t('admin.content.collaboration.targetType')" required>
          <el-select v-model="inviteForm.target_type" style="width: 100%">
            <el-option label="workspace" value="workspace"/>
            <el-option label="article" value="article"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.content.collaboration.targetId')" required>
          <el-input-number v-model="inviteForm.target_id" :min="1" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.collaboration.permission')">
          <el-select v-model="inviteForm.permission" style="width: 100%">
            <el-option label="edit" value="edit"/>
            <el-option label="view" value="view"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.content.collaboration.expireHours')">
          <el-input-number v-model="inviteForm.expire_hours" :max="720" :min="1" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.content.collaboration.maxUses')">
          <el-input-number v-model="inviteForm.max_uses" :min="0" style="width: 100%"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="inviteFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="inviteSaving" type="primary" @click="submitInvite">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.mb-3 {
  margin-bottom: 12px;
}

.table-toolbar__title {
  margin-right: 12px;
  font-weight: 600;
}
</style>
