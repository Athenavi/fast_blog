<script lang="ts" setup>
const {t} = useI18n()
/**
 * 内容审批（审批单列表 + 详情时间线 + 通过/驳回）
 *
 * 对齐 v3：`/content/approval`（列表/详情/决策/删除）。
 * 审批需要逐条阅读内容，因此这里**不提供批量操作**（避免误批）。
 */
import {Delete, Refresh, Search} from '@element-plus/icons-vue'
import {reactive, ref} from 'vue'

import {approvalApi, type ApprovalRecordItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage} from '@/utils/feedback'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.content.approval.title',
  permission: 'module_content:approval:view',
})

interface ApprovalQueryForm extends PageQuery {
  content_type?: string
  status?: string
}

const list = useAdminList<ApprovalRecordItem, ApprovalQueryForm>({
  fetcher: (params) => approvalApi.list(params),
  defaultQuery: {content_type: '', status: ''},
  syncUrl: true,
})

const STATUS_OPTIONS = computed(() => [
  {label: t('admin.content.approval.statusPending'), value: 'pending'},
  {label: t('admin.content.approval.statusApproved'), value: 'approved'},
  {label: t('admin.content.approval.statusRejected'), value: 'rejected'},
])

function statusTag(status?: string | null): 'success' | 'danger' | 'warning' {
  if (status === 'approved') return 'success'
  return status === 'rejected' ? 'danger' : 'warning'
}

function statusLabel(status?: string | null): string {
  if (status === 'approved') return t('admin.content.approval.statusApproved')
  if (status === 'rejected') return t('admin.content.approval.statusRejected')
  return t('admin.content.approval.statusPending')
}

// ---------------------------------------------------------------- 详情与决策
const detailVisible = ref(false)
const detail = ref<ApprovalRecordItem | null>(null)
const detailLoading = ref(false)
const decisionVisible = ref(false)
const deciding = ref(false)
const decisionForm = reactive({action: 'approve' as 'approve' | 'reject', comment: ''})

const detailTitle = computed(() =>
  detail.value ? `${t('admin.content.approval.record')} #${detail.value.id}` : '',
)

async function openDetail(row: ApprovalRecordItem): Promise<void> {
  detailVisible.value = true
  detailLoading.value = true
  try {
    detail.value = await approvalApi.detail(row.id)
  } catch {
    detail.value = null
  } finally {
    detailLoading.value = false
  }
}

function openDecision(action: 'approve' | 'reject'): void {
  decisionForm.action = action
  decisionForm.comment = ''
  decisionVisible.value = true
}

async function submitDecision(): Promise<void> {
  if (!detail.value) return
  deciding.value = true
  try {
    detail.value = await approvalApi.decide(detail.value.id, {
      action: decisionForm.action,
      comment: decisionForm.comment || null,
    })
    ElMessage.success(t('admin.content.approval.decided'))
    decisionVisible.value = false
    await list.reload()
  } finally {
    deciding.value = false
  }
}

async function removeRow(row: ApprovalRecordItem): Promise<void> {
  await list.remove(
    () => approvalApi.remove(row.id),
    t('admin.content.approval.deleteConfirm'),
    t('admin.common.notice'),
    t('admin.content.approval.deleted'),
  )
}

/** 步骤进度：已通过时展示满进度 */
function stepActive(record: ApprovalRecordItem): number {
  return record.status === 'approved' ? record.current_level : record.current_level - 1
}
</script>

<template>
  <AdminPage :desc="$t('admin.content.approval.desc')" :title="$t('admin.content.approval.title')">
    <AdminListShell
      :empty-desc="list.hasFilters.value ? $t('admin.content.approval.emptyFiltered') : $t('admin.content.approval.emptyDesc')"
      :empty-title="list.hasFilters.value ? $t('admin.content.approval.emptyFiltered') : $t('admin.content.approval.emptyTitle')"
      :failed="list.failed.value"
      :loading="list.loading.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      :rows="list.rows.value"
      :selectable="false"
      :total="list.total.value"
      @refresh="list.reload"
      @reset="list.reset"
      @search="list.search"
      @page-change="list.onPageChange"
      @size-change="list.onSizeChange"
    >
      <template #filters>
        <el-form-item :label="$t('admin.content.approval.contentType')">
          <el-select v-model="list.query.content_type" :placeholder="$t('admin.common.all')" clearable
                     style="width: 140px">
            <el-option label="article" value="article"/>
            <el-option label="page" value="page"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-select v-model="list.query.status" :placeholder="$t('admin.common.all')" clearable
                     style="width: 140px">
            <el-option v-for="item in STATUS_OPTIONS" :key="item.value" :label="item.label" :value="item.value"/>
          </el-select>
        </el-form-item>
      </template>

      <template #actions>
        <el-button :icon="Search" type="primary" @click="list.search()">{{ $t('admin.common.search') }}</el-button>
      </template>

      <el-table-column label="ID" prop="id" width="80"/>
      <el-table-column :label="$t('admin.content.approval.contentType')" prop="content_type" width="110"/>
      <el-table-column :label="$t('admin.content.approval.contentId')" prop="content_id" width="100"/>
      <el-table-column :label="$t('admin.content.approval.progress')" width="120">
        <template #default="{row}">
          {{ row.current_level }} / {{ row.max_level }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.status')" width="110">
        <template #default="{row}">
          <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.content.approval.createdAt')" width="170">
        <template #default="{row}">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="180">
        <template #default="{row}">
          <el-button link type="primary" @click="openDetail(row as ApprovalRecordItem)">
            {{ $t('admin.content.approval.detail') }}
          </el-button>
          <el-button v-auth="'module_content:approval:delete'" :icon="Delete" link type="danger"
                     @click="removeRow(row as ApprovalRecordItem)">
            {{ $t('admin.common.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>

    <!-- 审批详情 -->
    <el-drawer v-model="detailVisible" :title="detailTitle" destroy-on-close size="520px">
      <div v-loading="detailLoading" class="approval-detail">
        <template v-if="detail">
          <div class="approval-detail__head">
            <el-tag :type="statusTag(detail.status)">{{ statusLabel(detail.status) }}</el-tag>
            <span class="admin-cell-sub">{{ detail.content_type }} #{{ detail.content_id }}</span>
          </div>

          <el-steps :active="stepActive(detail)" align-center>
            <el-step v-for="i in detail.max_level" :key="i"
                     :title="`${$t('admin.content.approval.level')} ${i}`"/>
          </el-steps>

          <el-timeline v-if="detail.steps?.length" class="approval-detail__timeline">
            <el-timeline-item
              v-for="step in detail.steps"
              :key="step.id"
              :timestamp="formatDateTime(step.reviewed_at)"
              :type="step.action === 'approve' ? 'success' : 'danger'"
            >
              <div class="admin-cell-title">
                {{
                  step.action === 'approve'
                    ? $t('admin.content.approval.actionApprove')
                    : $t('admin.content.approval.actionReject')
                }}
                · {{ $t('admin.content.approval.level') }} {{ step.level }}
              </div>
              <div v-if="step.comment" class="admin-cell-sub">{{ step.comment }}</div>
            </el-timeline-item>
          </el-timeline>
          <AdminEmpty v-else :title="$t('admin.content.approval.noSteps')"/>

          <div v-if="detail.status === 'pending'" class="approval-detail__actions">
            <el-button v-auth="'module_content:approval:act'" type="success" @click="openDecision('approve')">
              {{ $t('admin.content.approval.actionApprove') }}
            </el-button>
            <el-button v-auth="'module_content:approval:act'" type="danger" @click="openDecision('reject')">
              {{ $t('admin.content.approval.actionReject') }}
            </el-button>
          </div>
        </template>

        <AdminEmpty v-else-if="!detailLoading" :title="$t('admin.common.loadFailed')" variant="error">
          <el-button :icon="Refresh" @click="detail && openDetail(detail)">
            {{ $t('admin.common.retry') }}
          </el-button>
        </AdminEmpty>
      </div>

      <el-dialog v-model="decisionVisible" :title="$t('admin.content.approval.decision')" append-to-body
                 width="420px">
        <el-form :model="decisionForm" label-width="80px">
          <el-form-item :label="$t('admin.content.approval.commentLabel')">
            <el-input v-model="decisionForm.comment" :rows="3" type="textarea"/>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="decisionVisible = false">{{ $t('admin.common.cancel') }}</el-button>
          <el-button :loading="deciding" type="primary" @click="submitDecision">
            {{ $t('admin.common.save') }}
          </el-button>
        </template>
      </el-dialog>
    </el-drawer>
  </AdminPage>
</template>

<style scoped>
.approval-detail {
  display: flex;
  flex-direction: column;
  gap: var(--admin-gap);
}

.approval-detail__head {
  display: flex;
  align-items: center;
  gap: var(--admin-gap-sm);
}

.approval-detail__timeline {
  padding-left: 4px;
}

.approval-detail__actions {
  display: flex;
  gap: var(--admin-gap-sm);
}
</style>
