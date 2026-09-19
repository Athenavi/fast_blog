<script lang="ts" setup>
/**
 * AI 工作流记录（T5-11 批次 4）
 *
 * 对齐 v3 `/ai/workflow`：执行记录查询与治理。任务实际执行引擎为二期，
 * 记录由执行端写入（status: pending/processing/completed/failed）。
 */
import {Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

import {aiApi, type AiWorkflowItem} from '@/api'
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

const STATUS_TYPES: Record<string, string> = {
  pending: 'info',
  processing: 'warning',
  completed: 'success',
  failed: 'danger',
}

function statusType(status: string): string {
  return STATUS_TYPES[status] ?? 'info'
}

async function onDelete(row: AiWorkflowItem) {
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
            <el-option :label="$t('admin.ai.taskWriting')" value="writing_assist"/>
            <el-option :label="$t('admin.ai.taskSeo')" value="seo_optimize"/>
            <el-option :label="$t('admin.ai.taskTag')" value="tag_recommend"/>
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
        <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: total}) }}</span>
      </div>

      <!-- 表格 -->
      <el-table v-loading="loading" :data="list" border stripe>
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column :label="$t('admin.ai.userId')" prop="user_id" width="90"/>
        <el-table-column :label="$t('admin.ai.taskType')" width="130">
          <template #default="{ row }">
            {{
              (row as AiWorkflowItem).task_type === 'writing_assist'
                ? $t('admin.ai.taskWriting')
                : (row as AiWorkflowItem).task_type === 'seo_optimize'
                  ? $t('admin.ai.taskSeo')
                  : (row as AiWorkflowItem).task_type === 'tag_recommend'
                    ? $t('admin.ai.taskTag')
                    : (row as AiWorkflowItem).task_type || '—'
            }}
          </template>
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
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="100">
          <template #default="{ row }">
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
  </div>
</template>
