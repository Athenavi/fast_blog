<script lang="ts" setup>
/**
 * 部署脚本与执行日志（T5-11 批次 6）
 *
 * 对齐 v3 `/ops/deployment`：脚本档案 + 执行日志（双标签）。
 * **本页没有执行入口** —— 真实拉起脚本属高危动作，后端登记为二期，
 * 页面顶部用 el-alert 明示，避免「看起来能执行」的误导。
 * `parameters` 是后端 JSON 字符串列，这里用 JSON 文本编辑。
 */
import {Delete, EditPen, Plus, Refresh, Search, View} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {deploymentApi, type DeploymentLogItem, type DeploymentScriptItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useTable} from '@/hooks/useTable'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ops.deployment.title',
  permission: 'module_ops:deployment:view',
})

const {t} = useI18n()
const activeTab = ref('script')

// ---------------------------------------------------------------- 部署脚本
interface ScriptQueryForm extends PageQuery {
  keyword?: string
  script_type?: string
}

const {
  list: scriptList,
  loading: scriptLoading,
  total: scriptTotal,
  page: scriptPage,
  pageSize: scriptPageSize,
  query: scriptQuery,
  search: scriptSearch,
  reset: scriptReset,
  load: scriptLoad,
  onPageChange: onScriptPageChange,
  onSizeChange: onScriptSizeChange,
} = useTable<DeploymentScriptItem, ScriptQueryForm>({
  fetcher: (params) => deploymentApi.listScripts(params),
  defaultQuery: {keyword: '', script_type: ''},
  syncUrl: true,
})

const scriptFormVisible = ref(false)
const scriptEditingId = ref<number | null>(null)
const scriptSaving = ref(false)
const scriptForm = reactive({
  name: '',
  script_type: '',
  version: '',
  content: '',
  description: '',
  parameters_text: '',
  is_active: true,
})

const scriptFormTitle = computed(() =>
  scriptEditingId.value
    ? t('admin.ops.deployment.editScript')
    : t('admin.ops.deployment.createScript'),
)

function resetScriptForm() {
  Object.assign(scriptForm, {
    name: '',
    script_type: '',
    version: '',
    content: '',
    description: '',
    parameters_text: '',
    is_active: true,
  })
}

function openScriptCreate() {
  scriptEditingId.value = null
  resetScriptForm()
  scriptFormVisible.value = true
}

function openScriptEdit(row: DeploymentScriptItem) {
  scriptEditingId.value = row.id
  Object.assign(scriptForm, {
    name: row.name || '',
    script_type: row.script_type || '',
    version: row.version || '',
    content: row.content || '',
    description: row.description || '',
    parameters_text: row.parameters ? JSON.stringify(row.parameters, null, 2) : '',
    is_active: row.is_active,
  })
  scriptFormVisible.value = true
}

/** JSON 文本 → 对象 / 数组；空文本返回 null；非法 JSON 抛错由调用方提示 */
function parseParameters(text: string): Record<string, unknown> | unknown[] | null {
  const trimmed = text.trim()
  if (!trimmed) return null
  const parsed: unknown = JSON.parse(trimmed)
  if (Array.isArray(parsed) || (typeof parsed === 'object' && parsed !== null)) {
    return parsed as Record<string, unknown> | unknown[]
  }
  throw new Error('parameters must be an object or array')
}

async function submitScript() {
  if (!scriptForm.content.trim()) {
    ElMessage.warning(t('admin.ops.deployment.contentRequired'))
    return
  }
  let parameters: Record<string, unknown> | unknown[] | null
  try {
    parameters = parseParameters(scriptForm.parameters_text)
  } catch {
    ElMessage.warning(t('admin.ops.deployment.parametersInvalid'))
    return
  }
  scriptSaving.value = true
  try {
    const payload = {
      name: scriptForm.name.trim() || null,
      script_type: scriptForm.script_type.trim() || null,
      version: scriptForm.version.trim() || null,
      content: scriptForm.content,
      description: scriptForm.description.trim() || null,
      parameters,
      is_active: scriptForm.is_active,
    }
    if (scriptEditingId.value) {
      await deploymentApi.updateScript(scriptEditingId.value, payload)
    } else {
      await deploymentApi.createScript(payload)
    }
    ElMessage.success(t('admin.common.save'))
    scriptFormVisible.value = false
    await scriptLoad()
  } finally {
    scriptSaving.value = false
  }
}

async function onDeleteScript(row: DeploymentScriptItem) {
  await ElMessageBox.confirm(
    t('admin.ops.deployment.deleteScriptConfirm', {name: row.name || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await deploymentApi.removeScript(row.id)
  ElMessage.success(t('admin.common.delete'))
  await scriptLoad()
  await logLoad()
}

// ---------------------------------------------------------------- 执行日志
interface LogQueryForm extends PageQuery {
  script_id?: number
  status?: string
}

const {
  list: logList,
  loading: logLoading,
  total: logTotal,
  page: logPage,
  pageSize: logPageSize,
  query: logQuery,
  search: logSearch,
  reset: logReset,
  load: logLoad,
  onPageChange: onLogPageChange,
  onSizeChange: onLogSizeChange,
} = useTable<DeploymentLogItem, LogQueryForm>({
  fetcher: (params) => deploymentApi.listLogs(params),
  defaultQuery: {script_id: undefined, status: ''},
})

const logDetailVisible = ref(false)
const logDetailLoading = ref(false)
const logDetail = ref<DeploymentLogItem | null>(null)

async function openLogDetail(row: DeploymentLogItem) {
  logDetailVisible.value = true
  logDetailLoading.value = true
  logDetail.value = row
  try {
    logDetail.value = await deploymentApi.getLog(row.id)
  } finally {
    logDetailLoading.value = false
  }
}

async function onDeleteLog(row: DeploymentLogItem) {
  await ElMessageBox.confirm(
    t('admin.ops.deployment.deleteLogConfirm'),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await deploymentApi.removeLog(row.id)
  ElMessage.success(t('admin.common.delete'))
  await logLoad()
}

const scriptLabel = (id?: number | null) =>
  id === null || id === undefined ? '-' : (scriptList.value.find((s) => s.id === id)?.name || `#${id}`)
</script>

<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- 部署脚本档案 -->
      <el-tab-pane :label="$t('admin.ops.deployment.scripts')" name="script">
        <el-alert
          :closable="false"
          :title="$t('admin.ops.deployment.executeHint')"
          class="page-alert"
          show-icon
          type="info"
        />
        <el-card shadow="never">
          <el-form :inline="true" :model="scriptQuery" @submit.prevent="scriptSearch()">
            <el-form-item :label="$t('admin.common.search')">
              <el-input
                v-model="scriptQuery.keyword"
                :placeholder="$t('admin.ops.deployment.namePlaceholder')"
                clearable
                style="width: 200px"
                @keyup.enter="scriptSearch()"
              />
            </el-form-item>
            <el-form-item :label="$t('admin.ops.deployment.scriptType')">
              <el-input
                v-model="scriptQuery.script_type"
                :placeholder="$t('admin.ops.deployment.scriptTypePlaceholder')"
                clearable
                style="width: 160px"
                @keyup.enter="scriptSearch()"
              />
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="scriptSearch()">
                {{ $t('admin.common.search') }}
              </el-button>
              <el-button :icon="Refresh" @click="scriptReset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>

          <div class="table-toolbar">
            <el-button
              v-auth="'module_ops:deployment:edit'"
              :icon="Plus"
              type="primary"
              @click="openScriptCreate"
            >
              {{ $t('admin.ops.deployment.createScript') }}
            </el-button>
            <span class="table-toolbar__total">
              {{ $t('admin.common.totalItems', {n: scriptTotal}) }}
            </span>
          </div>

          <AdminTableSkeleton v-if="scriptLoading && !scriptList.length" :rows="5"/>

          <AdminEmpty v-else-if="!scriptLoading && !scriptList.length" :title="$t('admin.common.empty')"/>
          <el-table v-else v-loading="scriptLoading" :data="scriptList" border stripe>
            <el-table-column
              :label="$t('admin.ops.deployment.scriptName')"
              min-width="180"
              prop="name"
              show-overflow-tooltip
            />
            <el-table-column :label="$t('admin.ops.deployment.scriptType')" prop="script_type" width="130"/>
            <el-table-column :label="$t('admin.ops.deployment.version')" prop="version" width="110"/>
            <el-table-column
              :label="$t('admin.common.description')"
              min-width="200"
              prop="description"
              show-overflow-tooltip
            />
            <el-table-column :label="$t('admin.common.status')" align="center" width="100">
              <template #default="{ row }">
                <el-tag :type="(row as DeploymentScriptItem).is_active ? 'success' : 'info'" size="small">
                  {{
                    (row as DeploymentScriptItem).is_active ? $t('admin.common.enabled') : $t('admin.common.disabled')
                  }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
              <template #default="{ row }">
                <el-button
                  v-auth="'module_ops:deployment:edit'"
                  :icon="EditPen"
                  link
                  type="primary"
                  @click="openScriptEdit(row as DeploymentScriptItem)"
                >
                  {{ $t('admin.common.edit') }}
                </el-button>
                <el-button
                  v-auth="'module_ops:deployment:edit'"
                  :icon="Delete"
                  link
                  type="danger"
                  @click="onDeleteScript(row as DeploymentScriptItem)"
                >
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            :current-page="scriptPage"
            :page-size="scriptPageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="scriptTotal"
            background
            class="table-pagination"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="onScriptPageChange"
            @size-change="onScriptSizeChange"
          />
        </el-card>
      </el-tab-pane>

      <!-- 执行日志 -->
      <el-tab-pane :label="$t('admin.ops.deployment.logs')" name="log">
        <el-card shadow="never">
          <el-form :inline="true" :model="logQuery" @submit.prevent="logSearch()">
            <el-form-item :label="$t('admin.ops.deployment.scriptId')">
              <el-input-number
                v-model="logQuery.script_id"
                :min="1"
                :placeholder="$t('admin.ops.deployment.scriptIdPlaceholder')"
                clearable
                style="width: 150px"
              />
            </el-form-item>
            <el-form-item :label="$t('admin.ops.deployment.logStatus')">
              <el-input
                v-model="logQuery.status"
                clearable
                style="width: 140px"
                @keyup.enter="logSearch()"
              />
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="logSearch()">
                {{ $t('admin.common.search') }}
              </el-button>
              <el-button :icon="Refresh" @click="logReset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>

          <div class="table-toolbar">
            <span class="table-toolbar__total">
              {{ $t('admin.common.totalItems', {n: logTotal}) }}
            </span>
          </div>

          <el-table v-loading="logLoading" :data="logList" border stripe>
            <el-table-column :label="$t('admin.ops.deployment.scriptId')" width="150">
              <template #default="{ row }">
                {{ scriptLabel((row as DeploymentLogItem).script_id) }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.ops.deployment.logStatus')" width="120">
              <template #default="{ row }">{{ (row as DeploymentLogItem).status || '-' }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.ops.deployment.startedAt')" width="180">
              <template #default="{ row }">{{ (row as DeploymentLogItem).started_at || '-' }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.ops.deployment.completedAt')" width="180">
              <template #default="{ row }">{{ (row as DeploymentLogItem).completed_at || '-' }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.ops.deployment.logOutput')" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                {{ (row as DeploymentLogItem).error_message || (row as DeploymentLogItem).output || '-' }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="160">
              <template #default="{ row }">
                <el-button :icon="View" link type="primary" @click="openLogDetail(row as DeploymentLogItem)">
                  {{ $t('admin.ops.deployment.logDetail') }}
                </el-button>
                <el-button
                  v-auth="'module_ops:deployment:edit'"
                  :icon="Delete"
                  link
                  type="danger"
                  @click="onDeleteLog(row as DeploymentLogItem)"
                >
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            :current-page="logPage"
            :page-size="logPageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="logTotal"
            background
            class="table-pagination"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="onLogPageChange"
            @size-change="onLogSizeChange"
          />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 脚本：新建 / 编辑 -->
    <el-drawer v-model="scriptFormVisible" :title="scriptFormTitle" destroy-on-close size="620px">
      <el-form :model="scriptForm" label-width="120px">
        <el-form-item :label="$t('admin.ops.deployment.scriptName')">
          <el-input v-model="scriptForm.name" :placeholder="$t('admin.ops.deployment.namePlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.deployment.scriptType')">
          <el-input
            v-model="scriptForm.script_type"
            :placeholder="$t('admin.ops.deployment.scriptTypePlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.ops.deployment.version')">
          <el-input v-model="scriptForm.version"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="scriptForm.description" :autosize="{minRows: 2, maxRows: 4}" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.deployment.content')" required>
          <el-input
            v-model="scriptForm.content"
            :autosize="{minRows: 8, maxRows: 20}"
            type="textarea"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.ops.deployment.parameters')">
          <el-input
            v-model="scriptForm.parameters_text"
            :autosize="{minRows: 3, maxRows: 8}"
            :placeholder="$t('admin.ops.deployment.parametersHint')"
            type="textarea"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="scriptForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scriptFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="scriptSaving" type="primary" @click="submitScript">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-drawer>

    <!-- 日志详情 -->
    <el-drawer v-model="logDetailVisible" :title="$t('admin.ops.deployment.logDetail')" size="560px">
      <div v-loading="logDetailLoading" class="log-detail">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item :label="$t('admin.ops.deployment.scriptId')">
            {{ scriptLabel(logDetail?.script_id) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ops.deployment.logStatus')">
            {{ logDetail?.status || '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ops.deployment.startedAt')">
            {{ logDetail?.started_at || '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ops.deployment.completedAt')">
            {{ logDetail?.completed_at || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="log-detail__section">
          <div class="log-detail__label">{{ $t('admin.ops.deployment.logOutput') }}</div>
          <pre class="log-detail__pre">{{ logDetail?.output || $t('admin.ops.deployment.noOutput') }}</pre>
        </div>

        <div v-if="logDetail?.error_message" class="log-detail__section">
          <div class="log-detail__label">{{ $t('admin.ops.deployment.logError') }}</div>
          <pre class="log-detail__pre log-detail__pre--error">{{ logDetail.error_message }}</pre>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.page-alert {
  margin-bottom: 12px;
}

.log-detail__section {
  margin-top: 16px;
}

.log-detail__label {
  margin-bottom: 6px;
  font-weight: 600;
}

.log-detail__pre {
  max-height: 320px;
  padding: 10px 12px;
  overflow: auto;
  font-family: Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.log-detail__pre--error {
  color: var(--el-color-danger);
}
</style>
