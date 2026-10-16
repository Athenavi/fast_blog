<script lang="ts" setup>
/**
 * 通用工作流引擎控制台（/system/workflow）
 *
 * 对齐后端 13 个端点，分两个标签页：
 *  - 流程定义：定义列表（本地过滤）+ 新建 / 编辑抽屉 + 「校验」按钮（validate 端点）；
 *  - 实例与审批：实例列表 + 详情抽屉 + 执行 / 审批 / 驳回 / 取消，底部为执行历史。
 *
 * 定义结构由后端 `service.validate_definition` 做权威校验（非法一律 400），
 * 前端只用 JSON.parse 把关「是不是合法 JSON 对象」，不重复实现校验规则。
 * 定义 / 实例 / 历史端点**不是分页**结构，故用 http.get 取数组、列表壳关闭分页器。
 *
 * 权限（后端 controller `AuthControl`）：查看 `module_system:setting:view`，
 * 写入 / 执行 `module_system:setting:edit`。
 */
import {
  CircleCheck,
  CircleClose,
  Delete,
  DocumentChecked,
  Plus,
  Refresh,
  VideoPlay,
  View,
} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {workflowApi, type WorkflowDefinition, type WorkflowHistoryItem, type WorkflowInstance} from '@/api'
import AdminEmpty from '@/components/admin/AdminEmpty.vue'
import AdminListShell from '@/components/admin/AdminListShell.vue'
import AdminPage from '@/components/admin/AdminPage.vue'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.workflow.title',
  permission: 'module_system:setting:view',
})

const {t} = useI18n()
const activeTab = ref('definition')

/** 实例状态选项（`service.INSTANCE_STATUS` + `pending_approval`） */
const INSTANCE_STATUSES = ['pending', 'running', 'pending_approval', 'completed', 'failed', 'cancelled'] as const
const STATUS_TAG: Record<string, string> = {
  pending: 'info',
  running: 'primary',
  pending_approval: 'warning',
  completed: 'success',
  failed: 'danger',
  cancelled: 'info',
}

// ================================================================ 定义
const definitions = ref<WorkflowDefinition[]>([])
const definitionsLoading = ref(false)
const definitionsFailed = ref(false)
const definitionKeyword = ref('')

/** 本地按 workflow_id 子串过滤（定义列表无分页、无 keyword 参数） */
const filteredDefinitions = computed(() => {
  const kw = definitionKeyword.value.trim().toLowerCase()
  if (!kw) return definitions.value
  return definitions.value.filter((item) => (item.workflow_id ?? '').toLowerCase().includes(kw))
})

async function loadDefinitions(): Promise<void> {
  definitionsLoading.value = true
  definitionsFailed.value = false
  try {
    definitions.value = await workflowApi.listDefinitions()
  } catch {
    // 失败提示由 request 层统一弹出
    definitionsFailed.value = true
  } finally {
    definitionsLoading.value = false
  }
}

const definitionDrawerVisible = ref(false)
const definitionEditing = ref(false)
const definitionSaving = ref(false)
const definitionValidating = ref(false)
const definitionForm = reactive<{ workflow_id: string; json: string }>({
  workflow_id: '',
  json: '',
})

/** 新建定义时的示例模板（log 动作链），非占位数据，仅供用户改写 */
const DEFINITION_TEMPLATE = JSON.stringify(
  {
    nodes: [
      {id: 'start', type: 'action', config: {action: 'log', message: 'start'}, next: 'done'},
      {id: 'done', type: 'action', config: {action: 'log', message: 'done'}},
    ],
  },
  null,
  2,
)

function openDefinitionCreate(): void {
  definitionEditing.value = false
  definitionForm.workflow_id = ''
  definitionForm.json = DEFINITION_TEMPLATE
  definitionDrawerVisible.value = true
}

async function openDefinitionEdit(row: WorkflowDefinition): Promise<void> {
  const workflowId = row.workflow_id ?? ''
  try {
    const detail = await workflowApi.getDefinition(workflowId)
    definitionEditing.value = true
    definitionForm.workflow_id = workflowId
    definitionForm.json = JSON.stringify(detail, null, 2)
    definitionDrawerVisible.value = true
  } catch {
    // request 层已提示
  }
}

/** 解析定义 JSON，必须是对象（后端要求至少含 nodes） */
function parseDefinitionJson(): Record<string, unknown> | null {
  try {
    const parsed: unknown = JSON.parse(definitionForm.json)
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      ElMessage.warning(t('admin.system.workflow.definitionInvalid'))
      return null
    }
    return parsed as Record<string, unknown>
  } catch {
    ElMessage.warning(t('admin.system.workflow.definitionInvalid'))
    return null
  }
}

async function submitDefinition(): Promise<void> {
  if (!definitionForm.workflow_id.trim()) {
    ElMessage.warning(t('admin.system.workflow.workflowIdRequired'))
    return
  }
  const definition = parseDefinitionJson()
  if (!definition) return
  definitionSaving.value = true
  try {
    await workflowApi.registerDefinition(definitionForm.workflow_id.trim(), definition)
    ElMessage.success(t('admin.system.workflow.definitionSaved'))
    definitionDrawerVisible.value = false
    await loadDefinitions()
  } finally {
    definitionSaving.value = false
  }
}

async function validateDefinitionForm(): Promise<void> {
  const definition = parseDefinitionJson()
  if (!definition) return
  definitionValidating.value = true
  try {
    const result = await workflowApi.validateDefinition(definition)
    ElMessage.success(t('admin.system.workflow.definitionValid', {n: result.nodes.length}))
  } finally {
    definitionValidating.value = false
  }
}

async function removeDefinition(row: WorkflowDefinition): Promise<void> {
  const workflowId = row.workflow_id ?? ''
  try {
    await ElMessageBox.confirm(
      t('admin.system.workflow.deleteDefinitionConfirm', {id: workflowId}),
      t('admin.common.notice'),
      {type: 'warning'},
    )
  } catch {
    return
  }
  await workflowApi.deleteDefinition(workflowId)
  ElMessage.success(t('admin.common.delete'))
  await loadDefinitions()
}

// ================================================================ 实例
const instances = ref<WorkflowInstance[]>([])
const instancesLoading = ref(false)
const instancesFailed = ref(false)
const instanceStatusFilter = ref('')
const instanceLimit = ref(50)

async function loadInstances(): Promise<void> {
  instancesLoading.value = true
  instancesFailed.value = false
  try {
    instances.value = await workflowApi.listInstances({
      status: instanceStatusFilter.value || undefined,
      limit: instanceLimit.value,
    })
  } catch {
    instancesFailed.value = true
  } finally {
    instancesLoading.value = false
  }
}

function resetInstances(): void {
  instanceStatusFilter.value = ''
  instanceLimit.value = 50
  void loadInstances()
}

const detailVisible = ref(false)
const detailInstance = ref<WorkflowInstance | null>(null)
const detailLoading = ref(false)
/** 正在执行动作的实例 id（用于按钮 loading） */
const actionId = ref<string | null>(null)

const detailJson = computed(() =>
  detailInstance.value ? JSON.stringify(detailInstance.value, null, 2) : '',
)

/** 动作成功后：刷新列表、刷新已打开的详情、刷新历史 */
async function afterInstanceMutation(): Promise<void> {
  await loadInstances()
  if (detailInstance.value) {
    const currentId = detailInstance.value.instance_id
    try {
      detailInstance.value = await workflowApi.getInstance(currentId)
    } catch {
      // request 层已提示
    }
  }
  await loadHistory()
}

async function openInstanceDetail(row: WorkflowInstance): Promise<void> {
  detailVisible.value = true
  detailLoading.value = true
  detailInstance.value = null
  historyInstanceId.value = row.instance_id
  try {
    detailInstance.value = await workflowApi.getInstance(row.instance_id)
  } catch {
    // request 层已提示
  } finally {
    detailLoading.value = false
  }
}

async function runInstance(row: WorkflowInstance): Promise<void> {
  actionId.value = row.instance_id
  try {
    await workflowApi.execute(row.instance_id)
    ElMessage.success(t('admin.system.workflow.executed'))
    await afterInstanceMutation()
  } finally {
    actionId.value = null
  }
}

async function approveInstance(row: WorkflowInstance): Promise<void> {
  let comment = ''
  try {
    const result = await ElMessageBox.prompt(
      t('admin.system.workflow.approvePrompt'),
      t('admin.common.notice'),
      {inputPlaceholder: t('admin.system.workflow.commentPlaceholder'), inputValue: ''},
    )
    comment = String((result as { value?: string }).value ?? '')
  } catch {
    return
  }
  actionId.value = row.instance_id
  try {
    await workflowApi.approve(row.instance_id, comment)
    ElMessage.success(t('admin.system.workflow.approved'))
    await afterInstanceMutation()
  } finally {
    actionId.value = null
  }
}

async function rejectInstance(row: WorkflowInstance): Promise<void> {
  let comment = ''
  try {
    const result = await ElMessageBox.prompt(
      t('admin.system.workflow.rejectPrompt'),
      t('admin.common.notice'),
      {inputPlaceholder: t('admin.system.workflow.commentPlaceholder'), inputValue: ''},
    )
    comment = String((result as { value?: string }).value ?? '')
  } catch {
    return
  }
  actionId.value = row.instance_id
  try {
    await workflowApi.reject(row.instance_id, comment)
    ElMessage.success(t('admin.system.workflow.rejected'))
    await afterInstanceMutation()
  } finally {
    actionId.value = null
  }
}

async function cancelInstance(row: WorkflowInstance): Promise<void> {
  try {
    await ElMessageBox.confirm(
      t('admin.system.workflow.cancelConfirm', {id: row.instance_id}),
      t('admin.common.notice'),
      {type: 'warning'},
    )
  } catch {
    return
  }
  actionId.value = row.instance_id
  try {
    await workflowApi.cancel(row.instance_id)
    ElMessage.success(t('admin.system.workflow.cancelled'))
    await afterInstanceMutation()
  } finally {
    actionId.value = null
  }
}

// ---- 新建实例
const instanceFormVisible = ref(false)
const instanceSaving = ref(false)
const instanceForm = reactive<{ workflow_id: string; contextText: string }>({
  workflow_id: '',
  contextText: '{}',
})

function openInstanceCreate(): void {
  instanceForm.workflow_id = definitions.value[0]?.workflow_id ?? ''
  instanceForm.contextText = '{}'
  instanceFormVisible.value = true
}

async function submitInstance(): Promise<void> {
  if (!instanceForm.workflow_id) {
    ElMessage.warning(t('admin.system.workflow.instanceWorkflowRequired'))
    return
  }
  let context: Record<string, unknown> = {}
  try {
    const parsed: unknown = JSON.parse(instanceForm.contextText || '{}')
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      ElMessage.warning(t('admin.system.workflow.contextInvalid'))
      return
    }
    context = parsed as Record<string, unknown>
  } catch {
    ElMessage.warning(t('admin.system.workflow.contextInvalid'))
    return
  }
  instanceSaving.value = true
  try {
    await workflowApi.createInstance(instanceForm.workflow_id, context)
    ElMessage.success(t('admin.system.workflow.instanceCreated'))
    instanceFormVisible.value = false
    await loadInstances()
    await loadHistory()
  } finally {
    instanceSaving.value = false
  }
}

// ================================================================ 历史
const historyItems = ref<WorkflowHistoryItem[]>([])
const historyLoading = ref(false)
const historyFailed = ref(false)
const historyInstanceId = ref('')

async function loadHistory(): Promise<void> {
  historyLoading.value = true
  historyFailed.value = false
  try {
    historyItems.value = await workflowApi.history({
      instance_id: historyInstanceId.value || undefined,
      limit: 100,
    })
  } catch {
    historyFailed.value = true
  } finally {
    historyLoading.value = false
  }
}

const reloading = computed(
  () => definitionsLoading.value || instancesLoading.value || historyLoading.value,
)

/** 顶部刷新：三个只读加载并行，互不阻塞 */
function reloadAll(): void {
  void Promise.allSettled([loadDefinitions(), loadInstances(), loadHistory()])
}

onMounted(() => {
  void Promise.allSettled([loadDefinitions(), loadInstances(), loadHistory()])
})
</script>

<template>
  <AdminPage :desc="$t('admin.system.workflow.desc')" :title="$t('admin.system.workflow.title')">
    <template #actions>
      <el-button :icon="Refresh" :loading="reloading" @click="reloadAll">
        {{ $t('admin.common.refresh') }}
      </el-button>
    </template>

    <el-tabs v-model="activeTab">
      <!-- ============ 流程定义 ============ -->
      <el-tab-pane :label="$t('admin.system.workflow.tabDefinitions')" name="definition">
        <AdminListShell
          :failed="definitionsFailed"
          :loading="definitionsLoading"
          :page="1"
          :page-size="filteredDefinitions.length || 1"
          :paginate="false"
          :rows="filteredDefinitions"
          :selectable="false"
          :total="filteredDefinitions.length"
          row-key="workflow_id"
          @refresh="loadDefinitions"
          @reset="definitionKeyword = ''"
          @search="loadDefinitions"
        >
          <template #filters>
            <el-form-item :label="$t('admin.system.workflow.keyword')">
              <el-input
                v-model="definitionKeyword"
                :placeholder="$t('admin.system.workflow.keywordPlaceholder')"
                clearable
                style="width: 220px"
              />
            </el-form-item>
          </template>

          <template #actions>
            <el-button
              v-auth="'module_system:setting:edit'"
              :icon="Plus"
              type="primary"
              @click="openDefinitionCreate"
            >
              {{ $t('admin.system.workflow.createDefinition') }}
            </el-button>
          </template>

          <el-table-column
            :label="$t('admin.system.workflow.workflowId')"
            min-width="200"
            prop="workflow_id"
            show-overflow-tooltip
          />
          <el-table-column :label="$t('admin.system.workflow.nodeCount')" align="right" width="100">
            <template #default="{ row }">
              {{ (row as WorkflowDefinition).nodes?.length ?? 0 }}
            </template>
          </el-table-column>
          <el-table-column
            :label="$t('admin.system.workflow.updatedAt')"
            min-width="180"
            prop="updated_at"
            show-overflow-tooltip
          />
          <el-table-column
            :label="$t('admin.system.workflow.updatedBy')"
            align="right"
            prop="updated_by"
            width="110"
          />
          <el-table-column :label="$t('admin.common.actions')" fixed="right" width="200">
            <template #default="{ row }">
              <el-button
                v-auth="'module_system:setting:edit'"
                link
                type="primary"
                @click="openDefinitionEdit(row as WorkflowDefinition)"
              >
                {{ $t('admin.common.edit') }}
              </el-button>
              <el-button
                v-auth="'module_system:setting:edit'"
                :icon="Delete"
                link
                type="danger"
                @click="removeDefinition(row as WorkflowDefinition)"
              >
                {{ $t('admin.common.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </AdminListShell>
      </el-tab-pane>

      <!-- ============ 实例与审批 ============ -->
      <el-tab-pane :label="$t('admin.system.workflow.tabInstances')" name="instance">
        <AdminListShell
          :failed="instancesFailed"
          :loading="instancesLoading"
          :page="1"
          :page-size="instances.length || 1"
          :paginate="false"
          :rows="instances"
          :selectable="false"
          :total="instances.length"
          row-key="instance_id"
          @refresh="loadInstances"
          @reset="resetInstances"
          @search="loadInstances"
        >
          <template #filters>
            <el-form-item :label="$t('admin.system.workflow.status')">
              <el-select v-model="instanceStatusFilter" clearable style="width: 180px">
                <el-option
                  v-for="item in INSTANCE_STATUSES"
                  :key="item"
                  :label="$t(`admin.system.workflow.status_${item}`)"
                  :value="item"
                />
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('admin.system.workflow.limit')">
              <el-input-number v-model="instanceLimit" :max="500" :min="1" style="width: 140px"/>
            </el-form-item>
          </template>

          <template #actions>
            <el-button
              v-auth="'module_system:setting:edit'"
              :icon="Plus"
              type="primary"
              @click="openInstanceCreate"
            >
              {{ $t('admin.system.workflow.createInstance') }}
            </el-button>
          </template>

          <el-table-column
            :label="$t('admin.system.workflow.instanceId')"
            min-width="200"
            prop="instance_id"
            show-overflow-tooltip
          />
          <el-table-column
            :label="$t('admin.system.workflow.workflowId')"
            min-width="160"
            prop="workflow_id"
            show-overflow-tooltip
          />
          <el-table-column :label="$t('admin.system.workflow.status')" align="center" width="130">
            <template #default="{ row }">
              <el-tag
                :type="(STATUS_TAG[(row as WorkflowInstance).status] || 'info') as never"
                size="small"
              >
                {{ $t(`admin.system.workflow.status_${(row as WorkflowInstance).status}`) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            :label="$t('admin.system.workflow.currentNode')"
            min-width="140"
            prop="current_node_id"
            show-overflow-tooltip
          />
          <el-table-column
            :label="$t('admin.system.workflow.createdAt')"
            min-width="180"
            prop="created_at"
            show-overflow-tooltip
          />
          <el-table-column :label="$t('admin.common.actions')" fixed="right" width="300">
            <template #default="{ row }">
              <el-button :icon="View" link type="info" @click="openInstanceDetail(row as WorkflowInstance)">
                {{ $t('admin.system.workflow.detail') }}
              </el-button>
              <el-button
                v-auth="'module_system:setting:edit'"
                :disabled="(row as WorkflowInstance).status === 'pending_approval' || ['completed', 'failed', 'cancelled'].includes((row as WorkflowInstance).status)"
                :icon="VideoPlay"
                :loading="actionId === (row as WorkflowInstance).instance_id"
                link
                type="primary"
                @click="runInstance(row as WorkflowInstance)"
              >
                {{ $t('admin.system.workflow.execute') }}
              </el-button>
              <el-button
                v-auth="'module_system:setting:edit'"
                :disabled="(row as WorkflowInstance).status !== 'pending_approval'"
                :icon="CircleCheck"
                :loading="actionId === (row as WorkflowInstance).instance_id"
                link
                type="success"
                @click="approveInstance(row as WorkflowInstance)"
              >
                {{ $t('admin.system.workflow.approve') }}
              </el-button>
              <el-button
                v-auth="'module_system:setting:edit'"
                :disabled="(row as WorkflowInstance).status !== 'pending_approval'"
                :icon="CircleClose"
                :loading="actionId === (row as WorkflowInstance).instance_id"
                link
                type="danger"
                @click="rejectInstance(row as WorkflowInstance)"
              >
                {{ $t('admin.system.workflow.reject') }}
              </el-button>
              <el-button
                v-auth="'module_system:setting:edit'"
                :disabled="['completed', 'failed', 'cancelled'].includes((row as WorkflowInstance).status)"
                :loading="actionId === (row as WorkflowInstance).instance_id"
                link
                type="warning"
                @click="cancelInstance(row as WorkflowInstance)"
              >
                {{ $t('admin.system.workflow.cancel') }}
              </el-button>
            </template>
          </el-table-column>
        </AdminListShell>

        <!-- 执行历史 -->
        <el-divider/>
        <div class="table-toolbar">
          <span class="table-toolbar__title">{{ $t('admin.system.workflow.historyTitle') }}</span>
          <el-input
            v-model="historyInstanceId"
            :placeholder="$t('admin.system.workflow.historyFilterPlaceholder')"
            clearable
            style="width: 240px"
            @keyup.enter="loadHistory"
          />
          <el-button :icon="Refresh" :loading="historyLoading" @click="loadHistory">
            {{ $t('admin.common.refresh') }}
          </el-button>
        </div>
        <el-table v-loading="historyLoading" :data="historyItems" border size="small" stripe>
          <el-table-column
            :label="$t('admin.system.workflow.historyTimestamp')"
            min-width="180"
            prop="timestamp"
            show-overflow-tooltip
          />
          <el-table-column
            :label="$t('admin.system.workflow.instanceId')"
            min-width="160"
            prop="instance_id"
            show-overflow-tooltip
          />
          <el-table-column
            :label="$t('admin.system.workflow.workflowId')"
            min-width="140"
            prop="workflow_id"
            show-overflow-tooltip
          />
          <el-table-column
            :label="$t('admin.system.workflow.historyEvent')"
            prop="event"
            width="160"
          />
        </el-table>
        <AdminEmpty
          v-if="!historyLoading && !historyItems.length"
          :title="historyFailed ? $t('admin.common.loadFailed') : $t('admin.system.workflow.historyEmpty')"
          :variant="historyFailed ? 'error' : 'default'"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- ============ 新建 / 编辑定义抽屉 ============ -->
    <el-drawer
      v-model="definitionDrawerVisible"
      :title="definitionEditing ? $t('admin.system.workflow.editDefinition') : $t('admin.system.workflow.createDefinition')"
      destroy-on-close
      size="560px"
    >
      <el-form :model="definitionForm" label-width="120px">
        <el-form-item :label="$t('admin.system.workflow.workflowId')" required>
          <el-input v-model="definitionForm.workflow_id" :disabled="definitionEditing"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.workflow.definitionJson')" required>
          <el-input
            v-model="definitionForm.json"
            :autosize="{minRows: 12, maxRows: 24}"
            :placeholder="$t('admin.system.workflow.definitionJsonPlaceholder')"
            type="textarea"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :icon="DocumentChecked" :loading="definitionValidating" @click="validateDefinitionForm">
          {{ $t('admin.system.workflow.validate') }}
        </el-button>
        <el-button @click="definitionDrawerVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="definitionSaving" type="primary" @click="submitDefinition">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-drawer>

    <!-- ============ 新建实例对话框 ============ -->
    <el-dialog
      v-model="instanceFormVisible"
      :title="$t('admin.system.workflow.createInstance')"
      width="520px"
    >
      <el-form :model="instanceForm" label-width="120px">
        <el-form-item :label="$t('admin.system.workflow.workflowId')" required>
          <el-select v-model="instanceForm.workflow_id" filterable style="width: 100%">
            <el-option
              v-for="item in definitions"
              :key="item.workflow_id"
              :label="item.workflow_id"
              :value="item.workflow_id as string"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.system.workflow.instanceContext')">
          <el-input
            v-model="instanceForm.contextText"
            :autosize="{minRows: 4, maxRows: 12}"
            :placeholder="$t('admin.system.workflow.instanceContextPlaceholder')"
            type="textarea"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="instanceFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="instanceSaving" type="primary" @click="submitInstance">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- ============ 实例详情抽屉 ============ -->
    <el-drawer
      v-model="detailVisible"
      :title="$t('admin.system.workflow.detail')"
      destroy-on-close
      size="640px"
    >
      <div v-loading="detailLoading">
        <el-descriptions v-if="detailInstance" :column="1" border size="small">
          <el-descriptions-item :label="$t('admin.system.workflow.instanceId')">
            {{ detailInstance.instance_id }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.system.workflow.workflowId')">
            {{ detailInstance.workflow_id }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.system.workflow.status')">
            {{ $t(`admin.system.workflow.status_${detailInstance.status}`) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.system.workflow.currentNode')">
            {{ detailInstance.current_node_id ?? '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.system.workflow.awaitingNode')">
            {{ detailInstance.awaiting_node ?? '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.system.workflow.error')">
            {{ detailInstance.error ?? '-' }}
          </el-descriptions-item>
        </el-descriptions>
        <pre v-if="detailInstance" class="detail-json">{{ detailJson }}</pre>
      </div>
    </el-drawer>
  </AdminPage>
</template>

<style scoped>
.table-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.table-toolbar__title {
  font-size: 14px;
  font-weight: 600;
}

.detail-json {
  margin: 12px 0 0;
  padding: 12px;
  overflow: auto;
  font-size: 12px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}
</style>
