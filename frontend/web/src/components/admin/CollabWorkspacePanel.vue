<script lang="ts" setup>
/**
 * 协作管理 · 工作区面板
 *
 * 从 `pages/content/collaboration.vue` 的「工作区」标签页抽出：工作区列表及其
 * 新建 / 编辑 / 删除，外加"跳到成员与任务"的入口。
 *
 * 与页面之间只需要两件事通信：
 *  - `currentWorkspaceId`（双向）—— 它是**唯一跨标签页共享的状态**：「成员与任务」
 *    标签页要靠它决定加载哪个工作区的成员与任务；
 *  - `openMembers` —— 点"成员与任务"时请页面把标签页切过去。
 *
 * ## 搬移时顺带修掉的两个既有缺陷
 *
 * 1. **失败态形同虚设**：原页面里的 `loadFailed` 只有声明与三处读取，
 *    **从来没有被赋过值**，而 `loadWorkspaces` 的 `try/finally` 也没有 `catch` ——
 *    于是那段"加载失败 + 重试"的 UI 永远不会出现，请求失败会伪装成"暂无工作区"。
 * 2. **空态渲染两次**：原模板在 `AdminEmpty` 之外还有一个 `el-empty`，
 *    两者的显示条件完全相同（`!workspaceLoading && !workspaces.length`），
 *    空列表时会同时渲染两个空态。已删掉多余的那个。
 */
import {Delete, EditPen, Plus, Refresh, UserFilled} from '@element-plus/icons-vue'
import {computed, onMounted, reactive, ref} from 'vue'

import {collaborationApi, type WorkspaceItem} from '@/api'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

const props = defineProps<{
  /** 当前选中的工作区 id（由页面持有，因为「成员与任务」标签页也要用） */
  currentWorkspaceId: number | null
  /** 当前选中的工作区名（页面用它显示「当前工作区: xxx」） */
  currentWorkspaceName: string | null
}>()

const emit = defineEmits<{
  (e: 'update:currentWorkspaceId', id: number | null): void
  (e: 'update:currentWorkspaceName', name: string | null): void
  /** 请求页面切到「成员与任务」标签页（并选中该工作区） */
  (e: 'openMembers', id: number): void
}>()

/**
 * 选中某个工作区。
 *
 * id 与 name 必须**一起**上抛：页面要拿 id 给「成员与任务」决定加载谁，同时要拿
 * name 在那边的「当前工作区: xxx」里显示 —— 只给 id 的话页面就无从反查名字了
 * （工作区列表已经搬进本组件）。
 */
function selectWorkspace(id: number | null, name: string | null): void {
  emit('update:currentWorkspaceId', id)
  emit('update:currentWorkspaceName', name)
}

const {t} = useI18n()

const workspaces = ref<WorkspaceItem[]>([])
const workspaceLoading = ref(false)
/** 加载失败标记（原先它从未被赋值，失败态因此永不显示） */
const loadFailed = ref(false)

async function loadWorkspaces(): Promise<void> {
  workspaceLoading.value = true
  loadFailed.value = false
  try {
    workspaces.value = await collaborationApi.listWorkspaces()
    // 首次加载后自动选中第一个工作区，让「成员与任务」有默认对象
    const first = workspaces.value[0]
    if (props.currentWorkspaceId === null && first) {
      selectWorkspace(first.id, first.name ?? null)
    }
  } catch {
    workspaces.value = []
    loadFailed.value = true
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

function openWorkspaceCreate(): void {
  workspaceEditingId.value = null
  Object.assign(workspaceForm, {name: '', slug: '', description: ''})
  workspaceFormVisible.value = true
}

function openWorkspaceEdit(row: WorkspaceItem): void {
  workspaceEditingId.value = row.id
  Object.assign(workspaceForm, {
    name: row.name || '',
    slug: row.slug || '',
    description: row.description || '',
  })
  workspaceFormVisible.value = true
}

async function submitWorkspace(): Promise<void> {
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
      selectWorkspace(created.id, created.name ?? null)
    }
    ElMessage.success(t('admin.common.save'))
    workspaceFormVisible.value = false
    await loadWorkspaces()
  } finally {
    workspaceSaving.value = false
  }
}

async function onDeleteWorkspace(row: WorkspaceItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.content.collaboration.deleteWorkspaceConfirm', {name: row.name || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await collaborationApi.removeWorkspace(row.id)
  ElMessage.success(t('admin.common.delete'))
  if (props.currentWorkspaceId === row.id) selectWorkspace(null, null)
  await loadWorkspaces()
}

/**
 * 跳到「成员与任务」。
 *
 * 先把选中同步出去、再请页面切标签 —— 顺序不能反：页面切标签会触发 `onTabChange`，
 * 那里要读 `currentWorkspaceId` 来决定是否加载成员；若反过来，读到的会是旧值。
 */
function openMembers(row: WorkspaceItem): void {
  selectWorkspace(row.id, row.name ?? null)
  emit('openMembers', row.id)
}

onMounted(() => {
  loadWorkspaces().catch(() => undefined)
})

/**
 * 暴露 reload 给页面：「邀请」标签页里"接受邀请"成功后需要刷新工作区列表
 * （接受邀请可能让你加入一个新工作区），而那个动作发生在别的标签页，本组件无从感知。
 */
defineExpose({reload: loadWorkspaces})
</script>

<template>
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
      :title="loadFailed ? $t('admin.common.loadFailed') : $t('admin.content.collaboration.emptyTitle')"
      :variant="loadFailed ? 'error' : 'default'"
    >
      <el-button v-if="loadFailed" :icon="Refresh" @click="loadWorkspaces()">
        {{ $t('admin.common.retry') }}
      </el-button>
    </AdminEmpty>

    <!-- 原先这个 el-table 之后还有一个 el-empty，显示条件与上面的 AdminEmpty 完全相同，
         空列表时会叠加出两个空态，已删除 -->
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
  </el-card>

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
</template>

<style scoped>
/* table-toolbar 本身来自 styles/admin.css（全局），这里只补页面原先 scoped 覆盖的部分 */
:deep(.table-toolbar__title) {
  margin-right: 12px;
  font-weight: 600;
}
</style>
