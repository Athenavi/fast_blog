<script lang="ts" setup>
/**
 * 协作管理 · 成员与任务面板
 *
 * 从 `pages/content/collaboration.vue` 的「成员与任务」标签页抽出：上半是成员列表
 * （改角色 / 移除），下半是任务列表（新建 / 改状态 / 删除）。
 *
 * ## 加载时机刻意与原实现保持一致
 *
 * 原页面不是"进页面就拉取"，而是 `onTabChange` 里**切到该标签才拉取**
 * （避免一进协作页就并发打出所有标签页的请求）。这里用 `active` 属性 +
 * `watch(..., {immediate: true})` 还原同一时机，并且保留原来的短路条件：
 * 工作区 id 为空时什么都不拉。
 *
 * 顺带删掉一个死常量：原页面的 `TASK_TAG` 定义了但从未被引用过。
 */
import {Delete, Plus, Refresh, Search} from '@element-plus/icons-vue'
import {reactive, ref, watch} from 'vue'

import {collaborationApi, type MemberItem, type TaskItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

const props = defineProps<{
  /** 当前选中的工作区 id（由页面持有）；为 null 时没有可加载的成员与任务 */
  workspaceId: number | null
  /** 当前选中的工作区名，用于顶部「当前工作区: xxx」 */
  workspaceName: string | null
  /** 本标签页是否激活 —— 对应原实现的"切到该标签才拉取" */
  active: boolean
}>()

const {t} = useI18n()

const MEMBER_ROLES = ['viewer', 'editor', 'admin', 'owner'] as const
const TASK_STATUSES = ['pending', 'in_progress', 'completed', 'cancelled'] as const
const TASK_PRIORITIES = ['low', 'medium', 'high', 'urgent'] as const

// ---------------------------------------------------------------- 成员
const members = ref<MemberItem[]>([])
const memberLoading = ref(false)
const memberFormVisible = ref(false)
const memberSaving = ref(false)
const memberForm = reactive({user_id: undefined as number | undefined, role: 'viewer' as string})

async function loadMembers(): Promise<void> {
  if (props.workspaceId === null) return
  memberLoading.value = true
  try {
    members.value = await collaborationApi.listMembers(props.workspaceId)
  } finally {
    memberLoading.value = false
  }
}

function openMemberCreate(): void {
  Object.assign(memberForm, {user_id: undefined, role: 'viewer'})
  memberFormVisible.value = true
}

async function submitMember(): Promise<void> {
  if (props.workspaceId === null || memberForm.user_id === undefined) {
    ElMessage.warning(t('admin.content.collaboration.userIdRequired'))
    return
  }
  memberSaving.value = true
  try {
    await collaborationApi.addMember(props.workspaceId, {
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

async function onChangeRole(row: MemberItem, role: string): Promise<void> {
  if (props.workspaceId === null || row.user_id === null || row.user_id === undefined) return
  await collaborationApi.updateMemberRole(props.workspaceId, row.user_id, role as never)
  ElMessage.success(t('admin.common.save'))
  await loadMembers()
}

async function onRemoveMember(row: MemberItem): Promise<void> {
  if (props.workspaceId === null || row.user_id === null || row.user_id === undefined) return
  await ElMessageBox.confirm(
    t('admin.content.collaboration.removeMemberConfirm', {name: row.username || row.user_id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await collaborationApi.removeMember(props.workspaceId, row.user_id)
  ElMessage.success(t('admin.common.delete'))
  await loadMembers()
}

// ---------------------------------------------------------------- 任务
const taskState = useAdminList<TaskItem, PageQuery & { status?: string }>({
  fetcher: (params) => collaborationApi.listTasks(props.workspaceId ?? 0, params),
  defaultQuery: {status: ''},
  syncUrl: true,
  // 由下面的 watch 决定何时拉取，而不是挂载即拉
  immediate: false,
})

// 模板沿用原有变量名：映射为同名 ref / 函数
const taskList = taskState.rows
const taskLoading = taskState.loading
const taskTotal = taskState.total
const taskPage = taskState.page
const taskPageSize = taskState.pageSize
const taskSearch = taskState.search
const taskReset = taskState.reset
const taskLoad = taskState.reload
const onTaskPageChange = taskState.onPageChange
const onTaskSizeChange = taskState.onSizeChange

const taskFormVisible = ref(false)
const taskSaving = ref(false)
const taskForm = reactive({
  title: '',
  description: '',
  priority: 'medium' as string,
  assigned_to: undefined as number | undefined,
})

function openTaskCreate(): void {
  Object.assign(taskForm, {title: '', description: '', priority: 'medium', assigned_to: undefined})
  taskFormVisible.value = true
}

async function submitTask(): Promise<void> {
  if (props.workspaceId === null || !taskForm.title.trim()) {
    ElMessage.warning(t('admin.content.collaboration.titleRequired'))
    return
  }
  taskSaving.value = true
  try {
    await collaborationApi.createTask(props.workspaceId, {
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

async function onChangeTaskStatus(row: TaskItem, status: string): Promise<void> {
  await collaborationApi.updateTask(row.id, {status})
  ElMessage.success(t('admin.common.save'))
  await taskLoad()
}

async function onDeleteTask(row: TaskItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.content.collaboration.deleteTaskConfirm', {name: row.title || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await collaborationApi.removeTask(row.id)
  ElMessage.success(t('admin.common.delete'))
  await taskLoad()
}

// ---------------------------------------------------------------- 加载时机
/** 对应原页面 `onTabChange` 里切到本标签时做的事 */
function loadAll(): void {
  if (props.workspaceId === null) return
  void loadMembers()
  void taskLoad()
}

// immediate 让"直接落在这个标签页"的情况也能拉到数据（默认标签是「工作区」，通常不会）
watch(
  () => props.active,
  (isActive) => {
    if (isActive) loadAll()
  },
  {immediate: true},
)
</script>

<template>
  <el-alert :closable="false" class="mb-3" show-icon type="info">
    <template #title>
      {{ $t('admin.content.collaboration.currentWorkspace') }}:
      {{ workspaceName || '-' }}
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
      <el-button v-auth="'module_content:collaboration:create'" :disabled="workspaceId === null"
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
</template>

<style scoped>
/* 这几个类来自 styles/admin.css（全局），此处只补页面原先 scoped 覆盖的部分 */
.mb-3 {
  margin-bottom: 12px;
}

:deep(.table-toolbar__title) {
  margin-right: 12px;
  font-weight: 600;
}
</style>
