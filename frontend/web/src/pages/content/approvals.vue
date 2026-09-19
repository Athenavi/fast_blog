<script lang="ts" setup>
/**
 * 内容审批（T5-11 批次 2）
 *
 * 对齐 v3 `/content/approval`：审批单列表 + 详情（步骤）+ 通过/驳回。
 */
import {Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, reactive, ref} from 'vue'

import {approvalApi, type ApprovalRecordItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useTable} from '@/hooks/useTable'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.approval.title',
  permission: 'module_content:approval:view',
})

const {t} = useI18n()

interface ApprovalQueryForm extends PageQuery {
  content_type?: string
  status?: string
}

const {
  list, loading, total, page, pageSize, query, search, reset, load,
  onPageChange, onSizeChange,
} = useTable<ApprovalRecordItem, ApprovalQueryForm>({
  fetcher: (params) => approvalApi.list(params),
  defaultQuery: {content_type: '', status: ''},
})

const statusTag = (s?: string | null) =>
  s === 'approved' ? 'success' : s === 'rejected' ? 'danger' : 'warning'
const statusLabel = (s?: string | null) =>
  s === 'approved' ? t('admin.content.approval.statusApproved')
    : s === 'rejected' ? t('admin.content.approval.statusRejected')
      : t('admin.content.approval.statusPending')

// ---- 详情 ----
const detailVisible = ref(false)
const detail = ref<ApprovalRecordItem | null>(null)
const decisionVisible = ref(false)
const decisionForm = reactive({action: 'approve' as 'approve' | 'reject', comment: ''})
const deciding = ref(false)

const detailTitle = computed(() =>
  detail.value ? `${t('admin.content.approval.record')} #${detail.value.id}` : '')

async function openDetail(row: ApprovalRecordItem) {
  detail.value = await approvalApi.detail(row.id)
  detailVisible.value = true
}

function openDecision(action: 'approve' | 'reject') {
  decisionForm.action = action
  decisionForm.comment = ''
  decisionVisible.value = true
}

async function submitDecision() {
  if (!detail.value) return
  deciding.value = true
  try {
    detail.value = await approvalApi.decide(detail.value.id, {
      action: decisionForm.action,
      comment: decisionForm.comment || null,
    })
    ElMessage.success(t('admin.content.approval.decided'))
    decisionVisible.value = false
    await load()
  } finally {
    deciding.value = false
  }
}

async function onDelete(row: ApprovalRecordItem) {
  await ElMessageBox.confirm(t('admin.content.approval.deleteConfirm'), t('admin.common.notice'), {type: 'warning'})
  await approvalApi.remove(row.id)
  ElMessage.success(t('admin.common.delete'))
  await load()
}
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-form :inline="true" @submit.prevent="search()">
        <el-form-item :label="$t('admin.content.approval.contentType')">
          <el-select v-model="query.content_type" clearable style="width: 140px">
            <el-option label="article" value="article"/>
            <el-option label="page" value="page"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="query.status" clearable style="width: 140px">
            <el-option :label="$t('admin.content.approval.statusPending')" value="pending"/>
            <el-option :label="$t('admin.content.approval.statusApproved')" value="approved"/>
            <el-option :label="$t('admin.content.approval.statusRejected')" value="rejected"/>
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

      <el-table v-loading="loading" :data="list" border stripe>
        <el-table-column label="ID" prop="id" width="80"/>
        <el-table-column :label="$t('admin.content.approval.contentType')" prop="content_type" width="110"/>
        <el-table-column :label="$t('admin.content.approval.contentId')" prop="content_id" width="100"/>
        <el-table-column :label="$t('admin.content.approval.progress')" width="120">
          <template #default="{ row }">
            {{ (row as ApprovalRecordItem).current_level }} / {{ (row as ApprovalRecordItem).max_level }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.status')" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag((row as ApprovalRecordItem).status)" size="small">
              {{ statusLabel((row as ApprovalRecordItem).status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.content.approval.createdAt')" prop="created_at" width="170"/>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="200">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row as ApprovalRecordItem)">
              {{ $t('admin.content.approval.detail') }}
            </el-button>
            <el-button v-auth="'module_content:approval:delete'" link type="danger"
                       @click="onDelete(row as ApprovalRecordItem)">
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        :current-page="page" :page-size="pageSize" :total="total"
        background class="table-pagination" layout="total, sizes, prev, pager, next"
        @current-change="onPageChange" @size-change="onSizeChange"
      />
    </el-card>

    <!-- 详情 -->
    <el-drawer v-model="detailVisible" :title="detailTitle" destroy-on-close size="480px">
      <template v-if="detail">
        <div class="mb-4 flex items-center gap-2">
          <el-tag :type="statusTag(detail.status)">{{ statusLabel(detail.status) }}</el-tag>
          <span class="text-sm text-fg-subtle">{{ detail.content_type }} #{{ detail.content_id }}</span>
        </div>
        <el-steps :active="detail.current_level - (detail.status === 'approved' ? 0 : 1)" align-center>
          <el-step v-for="i in detail.max_level" :key="i" :title="`${$t('admin.content.approval.level')} ${i}`"/>
        </el-steps>

        <el-timeline v-if="detail.steps?.length" class="mt-6">
          <el-timeline-item
            v-for="step in detail.steps"
            :key="step.id"
            :timestamp="step.reviewed_at || ''"
            :type="step.action === 'approve' ? 'success' : 'danger'"
          >
            <div class="text-sm font-medium">
              {{
                step.action === 'approve' ? $t('admin.content.approval.actionApprove') : $t('admin.content.approval.actionReject')
              }}
              · {{ $t('admin.content.approval.level') }} {{ step.level }}
            </div>
            <div v-if="step.comment" class="text-sm text-fg-muted">{{ step.comment }}</div>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else :description="$t('admin.content.approval.noSteps')"/>

        <div v-if="detail.status === 'pending'" class="mt-4 flex gap-2">
          <el-button v-auth="'module_content:approval:act'" type="success" @click="openDecision('approve')">
            {{ $t('admin.content.approval.actionApprove') }}
          </el-button>
          <el-button v-auth="'module_content:approval:act'" type="danger" @click="openDecision('reject')">
            {{ $t('admin.content.approval.actionReject') }}
          </el-button>
        </div>
      </template>

      <el-dialog v-model="decisionVisible" :title="$t('admin.content.approval.decision')" append-to-body width="420px">
        <el-form :model="decisionForm" label-width="80px">
          <el-form-item :label="$t('admin.content.approval.commentLabel')">
            <el-input v-model="decisionForm.comment" :rows="3" type="textarea"/>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="decisionVisible = false">{{ $t('admin.common.cancel') }}</el-button>
          <el-button :loading="deciding" type="primary" @click="submitDecision">{{
              $t('admin.common.save')
            }}
          </el-button>
        </template>
      </el-dialog>
    </el-drawer>
  </div>
</template>
