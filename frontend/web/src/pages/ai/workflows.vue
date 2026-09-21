<script lang="ts" setup>
/**
 * AI 工作流（T5-11 批次 4；批次 20 接入**真实执行引擎**）
 *
 * 对齐 v3 `/ai/workflow`：执行记录查询与治理 + 发起任务（真实调用模型）。
 * 任务类型下拉来自后端 `/task-types`（与执行引擎同一份定义，不会出现前端有后端没有）。
 * 失败的任务会带 `error_message` 落库，页面可直接重跑。
 */
import {Plus, Refresh, Search, VideoPlay} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {onMounted, reactive, ref} from 'vue'

import {aiApi, type AiConfigItem, type AiTaskTypeItem, type AiWorkflowItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useTable} from '@/hooks/useTable'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ai.workflowTitle',
  permission: 'module_ai:workflow:view',
})

const {t} = useI18n()

interface AiWorkflowQueryForm extends PageQuery {
  user_id?: number
  task_type?: string
  status?: string
}

const {
  list,
  loading,
  total,
  page,
  pageSize,
  query,
  search,
  reset,
  load,
  onPageChange,
  onSizeChange,
} = useTable<AiWorkflowItem, AiWorkflowQueryForm>({
  fetcher: (params) => aiApi.listWorkflows(params),
  defaultQuery: {task_type: '', status: ''},
})

// ---- 任务类型 / 可用配置（发起任务用）----
const taskTypes = ref<AiTaskTypeItem[]>([])
const configs = ref<AiConfigItem[]>([])

async function loadMeta(): Promise<void> {
  try {
    const [types, configsPage] = await Promise.all([
      aiApi.listTaskTypes(),
      aiApi.listConfigs({page: 1, page_size: 100}),
    ])
    taskTypes.value = types
    configs.value = configsPage.items
  } catch {
    taskTypes.value = []
    configs.value = []
  }
}

onMounted(loadMeta)

function taskLabel(type?: string | null): string {
  return taskTypes.value.find((item) => item.task_type === type)?.label || type || '—'
}

function configLabel(config: AiConfigItem): string {
  return `${config.name || config.id}（${config.provider || 'openai'} · ${config.model || '-'}）`
}

const STATUS_TYPES: Record<string, string> = {
  pending: 'info',
  processing: 'warning',
  completed: 'success',
  failed: 'danger',
}

function statusType(status: string): string {
  return STATUS_TYPES[status] ?? 'info'
}

// ---- 发起任务（真实调用模型）----
const runVisible = ref(false)
const running = ref(false)
const runForm = reactive<{
  config_id: number | undefined;
  task_type: string;
  input: string;
  target_lang: string;
  max_tokens: number | undefined
}>({
  config_id: undefined,
  task_type: 'writing_assist',
  input: '',
  target_lang: '',
  max_tokens: undefined,
})

function openRun(): void {
  Object.assign(runForm, {
    config_id: configs.value.find((item) => item.is_active)?.id ?? configs.value[0]?.id,
    task_type: 'writing_assist',
    input: '',
    target_lang: '',
    max_tokens: undefined,
  })
  runVisible.value = true
}

async function submitRun(): Promise<void> {
  if (!runForm.config_id) {
    ElMessage.warning(t('admin.ai.executeConfigRequired'))
    return
  }
  if (!runForm.input.trim()) {
    ElMessage.warning(t('admin.ai.executeInputRequired'))
    return
  }
  running.value = true
  try {
    const result = await aiApi.executeWorkflow({
      config_id: runForm.config_id,
      task_type: runForm.task_type,
      input: runForm.input,
      target_lang: runForm.target_lang || undefined,
      max_tokens: runForm.max_tokens || undefined,
    })
    ElMessage.success(t('admin.ai.executeDone'))
    runVisible.value = false
    openResult(result)
    await load()
  } finally {
    running.value = false
  }
}

// ---- 结果查看 / 重跑 / 删除 ----
const resultVisible = ref(false)
const resultRow = ref<AiWorkflowItem | null>(null)

function openResult(row: AiWorkflowItem): void {
  resultRow.value = row
  resultVisible.value = true
}

function resultText(row: AiWorkflowItem | null): string {
  const data = row?.output_data as { text?: string } | undefined
  return data?.text || ''
}

function inputText(row: AiWorkflowItem | null): string {
  const data = row?.input_data as { input?: string } | undefined
  return data?.input || ''
}

function resultLatency(row: AiWorkflowItem | null): number | null {
  const data = row?.output_data as { latency_ms?: number } | undefined
  return data?.latency_ms ?? null
}

async function onRetry(row: AiWorkflowItem): Promise<void> {
  await ElMessageBox.confirm(t('admin.ai.retryConfirm'), t('admin.common.notice'), {type: 'info'})
  const result = await aiApi.retryWorkflow(row.id)
  ElMessage.success(t('admin.ai.executeDone'))
  openResult(result)
  await load()
}

async function onDelete(row: AiWorkflowItem): Promise<void> {
  await ElMessageBox.confirm(t('admin.ai.deleteWorkflowConfirm'), t('admin.common.notice'), {type: 'warning'})
  await aiApi.removeWorkflow(row.id)
  ElMessage.success(t('admin.common.delete'))
  await load()
}
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <!-- 搜索区 -->
      <el-form :inline="true" :model="query" @submit.prevent="search()">
        <el-form-item :label="$t('admin.ai.userId')">
          <el-input-number v-model="query.user_id" :min="1" controls-position="right" style="width: 130px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ai.taskType')">
          <el-select v-model="query.task_type" :placeholder="$t('admin.common.all')" clearable style="width: 170px">
            <el-option
              v-for="item in taskTypes"
              :key="item.task_type"
              :label="item.label"
              :value="item.task_type"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.ai.status')">
          <el-select v-model="query.status" :placeholder="$t('admin.common.all')" clearable style="width: 120px">
            <el-option label="pending" value="pending"/>
            <el-option label="processing" value="processing"/>
            <el-option label="completed" value="completed"/>
            <el-option label="failed" value="failed"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="search()">{{ $t('admin.common.search') }}</el-button>
          <el-button :icon="Refresh" @click="reset()">{{ $t('admin.common.reset') }}</el-button>
        </el-form-item>
      </el-form>

      <div class="table-toolbar">
        <el-button
          v-auth="'module_ai:workflow:execute'"
          :icon="Plus"
          type="primary"
          @click="openRun"
        >
          {{ $t('admin.ai.executeTask') }}
        </el-button>
        <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: total}) }}</span>
      </div>

      <!-- 表格 -->
      <el-table v-loading="loading" :data="list" border stripe>
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column :label="$t('admin.ai.userId')" prop="user_id" width="90"/>
        <el-table-column :label="$t('admin.ai.taskType')" width="130">
          <template #default="{ row }">{{ taskLabel((row as AiWorkflowItem).task_type) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.ai.modelUsed')" min-width="130" prop="model_used" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.ai.tokensUsed')" prop="tokens_used" width="110"/>
        <el-table-column :label="$t('admin.ai.status')" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType((row as AiWorkflowItem).status)" size="small">
              {{ (row as AiWorkflowItem).status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.ai.errorMessage')" min-width="150" prop="error_message"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.common.createdAt')" min-width="160" prop="created_at"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="210">
          <template #default="{ row }">
            <el-button link type="primary" @click="openResult(row as AiWorkflowItem)">
              {{ $t('admin.ai.viewResult') }}
            </el-button>
            <el-button
              v-auth="'module_ai:workflow:execute'"
              :icon="VideoPlay"
              link
              type="success"
              @click="onRetry(row as AiWorkflowItem)"
            >
              {{ $t('admin.ai.retry') }}
            </el-button>
            <el-button
              v-auth="'module_ai:workflow:delete'"
              link
              type="danger"
              @click="onDelete(row as AiWorkflowItem)"
            >
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
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

    <!-- 发起任务（真实调用模型） -->
    <el-dialog v-model="runVisible" :title="$t('admin.ai.executeTask')" width="620px">
      <el-form :model="runForm" label-width="110px">
        <el-form-item :label="$t('admin.ai.taskConfig')" required>
          <el-select v-model="runForm.config_id" style="width: 100%">
            <el-option
              v-for="config in configs"
              :key="config.id"
              :label="configLabel(config)"
              :value="config.id"
            />
          </el-select>
          <div class="form-hint">{{ $t('admin.ai.taskConfigHint') }}</div>
        </el-form-item>
        <el-form-item :label="$t('admin.ai.taskType')" required>
          <el-select v-model="runForm.task_type" style="width: 100%">
            <el-option
              v-for="item in taskTypes"
              :key="item.task_type"
              :label="item.label"
              :value="item.task_type"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="runForm.task_type === 'translate'" :label="$t('admin.ai.targetLang')">
          <el-input v-model="runForm.target_lang" :placeholder="$t('admin.ai.targetLangPlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ai.taskInput')" required>
          <el-input
            v-model="runForm.input"
            :autosize="{minRows: 5, maxRows: 14}"
            :placeholder="$t('admin.ai.taskInputPlaceholder')"
            type="textarea"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.ai.maxTokens')">
          <el-input-number v-model="runForm.max_tokens" :max="128000" :min="1"
                           :placeholder="$t('admin.ai.maxTokensHint')"
                           controls-position="right"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="runVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="running" type="primary" @click="submitRun">
          {{ $t('admin.ai.execute') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 结果查看 -->
    <el-dialog v-model="resultVisible" :title="$t('admin.ai.resultTitle')" width="680px">
      <template v-if="resultRow">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item :label="$t('admin.ai.taskType')">{{
              taskLabel(resultRow.task_type)
            }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ai.status')">{{ resultRow.status }}</el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ai.modelUsed')">{{
              resultRow.model_used || '—'
            }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ai.tokensUsed')">{{ resultRow.tokens_used }}</el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ai.latency')">
            {{ resultLatency(resultRow) ?? '—' }} ms
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.common.createdAt')">{{
              resultRow.created_at || '—'
            }}
          </el-descriptions-item>
        </el-descriptions>

        <el-alert
          v-if="resultRow.error_message"
          :closable="false"
          :title="$t('admin.ai.errorMessage')"
          class="mt-3"
          type="error"
        >
          {{ resultRow.error_message }}
        </el-alert>

        <div class="block">
          <div class="block__title">{{ $t('admin.ai.taskInput') }}</div>
          <pre class="block__body">{{ inputText(resultRow) || '—' }}</pre>
        </div>
        <div class="block">
          <div class="block__title">{{ $t('admin.ai.resultText') }}</div>
          <pre class="block__body">{{ resultText(resultRow) || '—' }}</pre>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.form-hint {
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-secondary);
}

.block {
  margin-top: 12px;
}

.block__title {
  margin-bottom: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.block__body {
  max-height: 240px;
  margin: 0;
  padding: 10px;
  overflow: auto;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.mt-3 {
  margin-top: 12px;
}
</style>
