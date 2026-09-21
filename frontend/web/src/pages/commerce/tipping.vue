<script lang="ts" setup>
/**
 * 打赏与提现管理（后台独立页，`/commerce/tipping`）
 *
 * 数据源：v3 `/api/v3/commerce/tipping`
 *  - 统计 `stats`（打赏笔数 / 已支付 / 金额 / 提现待办 / 打赏排行）
 *  - 提现列表 `withdrawals`（可按状态筛选）→ 审核 `review`（批准 / 驳回）
 *  - 标记已打款 `markPaid`：**必须填打款流水号**（不接受"无凭据已完成"）
 *
 * 打赏金额一律是**分**，展示时换算成元。提现是人工打款：插件层只有收款能力，
 * 没有代付 / 转账产品，所以不存在"自动打款"。
 */
import {Refresh} from '@element-plus/icons-vue'
import {ElMessage} from '@/utils/feedback'
import {onMounted, reactive, ref} from 'vue'

import {tippingApi, type TipStats, type WithdrawalItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {formatDateTime} from '@/utils/format'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.tipping.title',
  permission: 'module_commerce:tipping:view',
})

const {t} = useI18n()

function yuan(cents?: number | null): string {
  return ((cents ?? 0) / 100).toFixed(2)
}

const stats = ref<TipStats | null>(null)
const loading = ref(false)

interface WithdrawalQueryForm extends PageQuery {
  status?: string
}

const withdrawalState = useAdminList<WithdrawalItem, WithdrawalQueryForm>({
  fetcher: (params) => tippingApi.withdrawals(params),
  defaultQuery: {status: undefined},
  syncUrl: true,
})

// 模板沿用原有变量名（含 tableLoading / loadWithdrawals 这两个别名）
const list = withdrawalState.rows
const tableLoading = withdrawalState.loading
const tableFailed = withdrawalState.failed
const total = withdrawalState.total
const page = withdrawalState.page
const pageSize = withdrawalState.pageSize
const query = withdrawalState.query
const search = withdrawalState.search
const reset = withdrawalState.reset
const loadWithdrawals = withdrawalState.reload
const onPageChange = withdrawalState.onPageChange
const onSizeChange = withdrawalState.onSizeChange

const reviewDialog = ref(false)
const reviewTarget = ref<WithdrawalItem | null>(null)
const reviewForm = reactive<{ approve: boolean; comment: string }>({approve: true, comment: ''})

const paidDialog = ref(false)
const paidTarget = ref<WithdrawalItem | null>(null)
const paidForm = reactive<{ transaction_id: string; comment: string }>({transaction_id: '', comment: ''})

const submitting = ref(false)

const STATUS_LABELS: Record<string, string> = {
  pending: 'admin.tipping.wdStatusPending',
  approved: 'admin.tipping.wdStatusApproved',
  rejected: 'admin.tipping.wdStatusRejected',
  paid: 'admin.tipping.wdStatusPaid',
}

function statusLabel(status?: string | null): string {
  return t(STATUS_LABELS[String(status)] ?? 'admin.tipping.wdStatusUnknown')
}

function statusTag(status?: string | null): string {
  if (status === 'paid' || status === 'approved') return 'success'
  if (status === 'pending') return 'warning'
  if (status === 'rejected') return 'danger'
  return 'info'
}

async function loadStats(): Promise<void> {
  stats.value = await tippingApi.stats().catch(() => null)
}

async function load(): Promise<void> {
  loading.value = true
  try {
    await Promise.all([loadStats(), loadWithdrawals()])
  } finally {
    loading.value = false
  }
}

function openReview(row: WithdrawalItem, approve: boolean): void {
  reviewTarget.value = row
  reviewForm.approve = approve
  reviewForm.comment = ''
  reviewDialog.value = true
}

async function submitReview(): Promise<void> {
  if (!reviewTarget.value) return
  submitting.value = true
  try {
    await tippingApi.reviewWithdrawal(
      reviewTarget.value.id,
      reviewForm.approve,
      reviewForm.comment || undefined,
    )
    ElMessage.success(t('admin.tipping.reviewDone'))
    reviewDialog.value = false
    await load()
  } finally {
    submitting.value = false
  }
}

function openPaid(row: WithdrawalItem): void {
  paidTarget.value = row
  paidForm.transaction_id = ''
  paidForm.comment = ''
  paidDialog.value = true
}

async function submitPaid(): Promise<void> {
  if (!paidTarget.value) return
  if (!paidForm.transaction_id.trim()) {
    ElMessage.warning(t('admin.tipping.transactionRequired'))
    return
  }
  submitting.value = true
  try {
    await tippingApi.markPaid(
      paidTarget.value.id,
      paidForm.transaction_id.trim(),
      paidForm.comment || undefined,
    )
    ElMessage.success(t('admin.tipping.paidDone'))
    paidDialog.value = false
    await load()
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="table-toolbar">
        <span class="table-toolbar__total">{{ $t('admin.tipping.statsTitle') }}</span>
        <el-button :icon="Refresh" @click="load()">{{ $t('admin.common.refresh') }}</el-button>
      </div>

      <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.tipping.tipCount') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.tip_count ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.tipping.paidCount') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.paid_count ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.tipping.paidAmount') }}</p>
          <p class="mt-1 text-xl font-semibold">¥{{ yuan(stats?.paid_amount) }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.tipping.withdrawalPending') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.withdrawal_pending ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.tipping.totalAmount') }}</p>
          <p class="mt-1 text-xl font-semibold">¥{{ yuan(stats?.total_amount) }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.tipping.withdrawalCount') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.withdrawal_count ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.tipping.withdrawalPaid') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.withdrawal_paid ?? 0 }}</p>
        </el-card>
      </div>
    </el-card>

    <el-card class="mt-4" shadow="never">
      <template #header>
        <div class="flex items-center justify-between">
          <span>{{ $t('admin.tipping.withdrawalsTitle') }}</span>
          <el-form :inline="true" @submit.prevent="search()">
            <el-form-item>
              <el-select v-model="query.status" :placeholder="$t('admin.common.all')" clearable
                         style="width: 140px" @change="search()">
                <el-option :label="$t('admin.tipping.wdStatusPending')" value="pending"/>
                <el-option :label="$t('admin.tipping.wdStatusApproved')" value="approved"/>
                <el-option :label="$t('admin.tipping.wdStatusRejected')" value="rejected"/>
                <el-option :label="$t('admin.tipping.wdStatusPaid')" value="paid"/>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button @click="reset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>
        </div>
      </template>

      <AdminTableSkeleton v-if="tableLoading && !list.length" :rows="5"/>

      <AdminEmpty
        v-else-if="!tableLoading && !list.length"
        :title="tableFailed ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
        :variant="tableFailed ? 'error' : 'default'"
      >
        <el-button v-if="tableFailed" :icon="Refresh" @click="loadWithdrawals()">
          {{ $t('admin.common.retry') }}
        </el-button>
      </AdminEmpty>
      <el-table v-else v-loading="tableLoading" :data="list" border stripe>
        <el-table-column :label="$t('admin.tipping.user')" min-width="120">
          <template #default="{ row }">{{ row.username || `#${row.user_id}` }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.tipping.amount')" width="110">
          <template #default="{ row }">¥{{ yuan(row.amount) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.tipping.fee')" width="100">
          <template #default="{ row }">¥{{ yuan(row.fee) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.tipping.actualAmount')" width="110">
          <template #default="{ row }">¥{{ yuan(row.actual_amount) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.tipping.method')" prop="method" width="100"/>
        <el-table-column :label="$t('admin.tipping.accountName')" min-width="120" prop="account_name"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.common.status')" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.tipping.transactionId')" min-width="140" prop="transaction_id"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.tipping.reviewComment')" min-width="140" prop="review_comment"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.common.createdAt')" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="230">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending'"
              v-auth="'module_commerce:tipping:edit'"
              link
              type="success"
              @click="openReview(row as WithdrawalItem, true)"
            >
              {{ $t('admin.tipping.approve') }}
            </el-button>
            <el-button
              v-if="row.status === 'pending'"
              v-auth="'module_commerce:tipping:edit'"
              link
              type="danger"
              @click="openReview(row as WithdrawalItem, false)"
            >
              {{ $t('admin.tipping.reject') }}
            </el-button>
            <el-button
              v-if="row.status === 'approved'"
              v-auth="'module_commerce:tipping:edit'"
              link
              type="primary"
              @click="openPaid(row as WithdrawalItem)"
            >
              {{ $t('admin.tipping.markPaid') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

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

    <el-card v-if="stats?.top_authors?.length" class="mt-4" shadow="never">
      <template #header>
        <span>{{ $t('admin.tipping.topAuthors') }}</span>
      </template>
      <el-table :data="stats?.top_authors ?? []" border stripe>
        <el-table-column :label="$t('admin.tipping.rank')" prop="rank" width="80"/>
        <el-table-column :label="$t('admin.tipping.user')" min-width="140">
          <template #default="{ row }">{{ row.username || `#${row.author_id}` }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.tipping.receivedTotal')" width="140">
          <template #default="{ row }">¥{{ yuan(row.total) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.tipping.tipCount')" prop="count" width="120"/>
      </el-table>
    </el-card>

    <!-- 审核 -->
    <el-dialog v-model="reviewDialog" :title="$t('admin.tipping.reviewTitle')" width="520px">
      <el-form label-width="100px">
        <el-form-item :label="$t('admin.tipping.user')">
          <span>{{ reviewTarget?.username || `#${reviewTarget?.user_id}` }}</span>
        </el-form-item>
        <el-form-item :label="$t('admin.tipping.amount')">
          <span>¥{{ yuan(reviewTarget?.amount) }}</span>
        </el-form-item>
        <el-form-item :label="$t('admin.tipping.result')">
          <el-radio-group v-model="reviewForm.approve">
            <el-radio :value="true">{{ $t('admin.tipping.approve') }}</el-radio>
            <el-radio :value="false">{{ $t('admin.tipping.reject') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('admin.tipping.reviewComment')">
          <el-input v-model="reviewForm.comment" :rows="3" type="textarea"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialog = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="submitting" type="primary" @click="submitReview()">
          {{ $t('admin.common.submit') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 标记已打款 -->
    <el-dialog v-model="paidDialog" :title="$t('admin.tipping.paidTitle')" width="520px">
      <el-form label-width="100px">
        <el-form-item :label="$t('admin.tipping.user')">
          <span>{{ paidTarget?.username || `#${paidTarget?.user_id}` }}</span>
        </el-form-item>
        <el-form-item :label="$t('admin.tipping.actualAmount')">
          <span>¥{{ yuan(paidTarget?.actual_amount) }}</span>
        </el-form-item>
        <el-form-item :label="$t('admin.tipping.transactionId')" required>
          <el-input v-model="paidForm.transaction_id"
                    :placeholder="$t('admin.tipping.transactionPlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.tipping.reviewComment')">
          <el-input v-model="paidForm.comment" :rows="3" type="textarea"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="paidDialog = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="submitting" type="primary" @click="submitPaid()">
          {{ $t('admin.tipping.markPaid') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
