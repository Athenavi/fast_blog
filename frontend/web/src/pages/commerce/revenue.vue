<script lang="ts" setup>
/**
 * 收益分成（T5-11 批次 7，commerce 域）
 *
 * 对齐 v3 `/commerce/revenue`：收益记录 / 提现申请 / 分成配置 / 平台统计（四标签）。
 * 新建收益记录时按该类型的分成配置计算平台费与创作者收益（无配置则 30/70 兜底），
 * 同时联动用户收益统计；提现状态流转 `pending → approved → completed` 或 `pending → rejected`。
 * 前台「我的收益」是另一组端点（`/mobile/revenue`），不在本页。
 * 真实打款通道属二期：`complete` 只做状态流转。
 */
import {Delete, EditPen, Plus, Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {
  type PayoutRequestItem,
  type PlatformRevenueStats,
  revenueApi,
  type RevenueRecordItem,
  type SharingConfigItem,
} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {formatMoney} from '@/utils/money'

/** 金额列统一格式化（el-table 的 formatter 钩子）：带币种符号与千分位，避免裸数字 */
function moneyCell(_row: unknown, _column: unknown, cellValue: unknown): string {
  return formatMoney(cellValue as number)
}

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.commerce.revenue.title',
  permission: 'module_commerce:revenue:view',
})

const {t} = useI18n()
const activeTab = ref('record')

const PAYOUT_TAG: Record<string, string> = {
  pending: 'info',
  approved: 'warning',
  completed: 'success',
  rejected: 'danger',
}

const REVENUE_TYPES = [
  'advertisement',
  'vip_subscription',
  'article_purchase',
  'donation',
  'other',
] as const

// ---------------------------------------------------------------- 收益记录
const recordState = useAdminList<RevenueRecordItem, PageQuery & { revenue_type?: string; user_id?: number }>({

  fetcher: (params) => revenueApi.listRecords(params),
  defaultQuery: {keyword: '', revenue_type: '', user_id: undefined},
})

// 模板沿用原有变量名：映射为同名 ref / 函数
const recordList = recordState.rows
const recordLoading = recordState.loading
const recordTotal = recordState.total
const recordPage = recordState.page
const recordPageSize = recordState.pageSize
const recordQuery = recordState.query
const recordSearch = recordState.search
const recordReset = recordState.reset
const recordLoad = recordState.reload
const onRecordPageChange = recordState.onPageChange
const onRecordSizeChange = recordState.onSizeChange
const recordFailed = recordState.failed

const recordFormVisible = ref(false)
const recordSaving = ref(false)
const recordForm = reactive({
  user_id: undefined as number | undefined,
  revenue_type: 'advertisement',
  amount: undefined as number | undefined,
  description: '',
  reference_type: '',
})

function openRecordCreate() {
  Object.assign(recordForm, {
    user_id: undefined,
    revenue_type: 'advertisement',
    amount: undefined,
    description: '',
    reference_type: '',
  })
  recordFormVisible.value = true
}

async function submitRecord() {
  if (recordForm.user_id === undefined || !recordForm.amount || recordForm.amount <= 0) {
    ElMessage.warning(t('admin.commerce.revenue.recordRequired'))
    return
  }
  recordSaving.value = true
  try {
    await revenueApi.createRecord({
      user_id: recordForm.user_id,
      revenue_type: recordForm.revenue_type,
      amount: recordForm.amount,
      description: recordForm.description.trim() || null,
      reference_type: recordForm.reference_type.trim() || null,
    })
    ElMessage.success(t('admin.common.save'))
    recordFormVisible.value = false
    await recordLoad()
  } finally {
    recordSaving.value = false
  }
}

async function onDeleteRecord(row: RevenueRecordItem) {
  await ElMessageBox.confirm(
    t('admin.commerce.revenue.deleteRecordConfirm', {name: row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await revenueApi.removeRecord(row.id)
  ElMessage.success(t('admin.common.delete'))
  await recordLoad()
}

// ---------------------------------------------------------------- 提现申请
const payoutState = useAdminList<PayoutRequestItem, PageQuery & { status?: string; user_id?: number }>({

  fetcher: (params) => revenueApi.listPayouts(params),
  defaultQuery: {keyword: '', status: '', user_id: undefined},
})

// 模板沿用原有变量名：映射为同名 ref / 函数
const payoutList = payoutState.rows
const payoutLoading = payoutState.loading
const payoutTotal = payoutState.total
const payoutPage = payoutState.page
const payoutPageSize = payoutState.pageSize
const payoutQuery = payoutState.query
const payoutSearch = payoutState.search
const payoutReset = payoutState.reset
const payoutLoad = payoutState.reload
const onPayoutPageChange = payoutState.onPageChange
const onPayoutSizeChange = payoutState.onSizeChange
const payoutFailed = payoutState.failed

const payoutActing = ref<number | null>(null)

async function decidePayout(row: PayoutRequestItem, action: 'approve' | 'complete' | 'reject') {
  const label = t(`admin.commerce.revenue.action_${action}`)
  let notes = ''
  try {
    const result = await ElMessageBox.prompt(
      t('admin.commerce.revenue.decisionPrompt', {action: label, name: row.id}),
      t('admin.common.notice'),
      {inputPlaceholder: t('admin.commerce.revenue.notesPlaceholder'), type: 'warning'},
    )
    notes = (result as { value?: string }).value || ''
  } catch {
    return
  }
  payoutActing.value = row.id
  try {
    if (action === 'approve') await revenueApi.approvePayout(row.id, notes)
    else if (action === 'complete') await revenueApi.completePayout(row.id, notes)
    else await revenueApi.rejectPayout(row.id, notes)
    ElMessage.success(label)
    await payoutLoad()
  } finally {
    payoutActing.value = null
  }
}

// ---------------------------------------------------------------- 分成配置
const configList = ref<SharingConfigItem[]>([])
const configLoading = ref(false)
const configFormVisible = ref(false)
const configSaving = ref(false)
const configEditing = ref<SharingConfigItem | null>(null)
const configForm = reactive({
  platform_percentage: undefined as number | undefined,
  creator_percentage: undefined as number | undefined,
  min_payout_amount: undefined as number | undefined,
  description: '',
  is_active: true,
})

async function loadConfigs() {
  configLoading.value = true
  try {
    configList.value = await revenueApi.listConfigs()
  } finally {
    configLoading.value = false
  }
}

function openConfigEdit(row: SharingConfigItem) {
  configEditing.value = row
  Object.assign(configForm, {
    platform_percentage: row.platform_percentage ?? undefined,
    creator_percentage: row.creator_percentage ?? undefined,
    min_payout_amount: row.min_payout_amount ?? undefined,
    description: row.description || '',
    is_active: row.is_active,
  })
  configFormVisible.value = true
}

async function submitConfig() {
  const revenueType = configEditing.value?.revenue_type
  if (!revenueType) return
  configSaving.value = true
  try {
    await revenueApi.updateConfig(revenueType, {
      platform_percentage: configForm.platform_percentage,
      creator_percentage: configForm.creator_percentage,
      min_payout_amount: configForm.min_payout_amount,
      description: configForm.description.trim() || null,
      is_active: configForm.is_active,
    })
    ElMessage.success(t('admin.common.save'))
    configFormVisible.value = false
    await loadConfigs()
  } finally {
    configSaving.value = false
  }
}

// ---------------------------------------------------------------- 平台统计
const stats = ref<PlatformRevenueStats | null>(null)
const statsLoading = ref(false)

async function loadStats() {
  statsLoading.value = true
  try {
    stats.value = await revenueApi.platformStats()
  } finally {
    statsLoading.value = false
  }
}

const statsCards = computed(() => {
  const data = stats.value
  return [
    {key: 'total_revenue', value: data?.total_revenue ?? 0},
    {key: 'total_platform_fee', value: data?.total_platform_fee ?? 0},
    {key: 'total_creator_earnings', value: data?.total_creator_earnings ?? 0},
    {key: 'record_count', value: data?.record_count ?? 0},
    {key: 'total_payouts', value: data?.total_payouts ?? 0},
    {key: 'pending_payouts', value: data?.pending_payouts ?? 0},
  ]
})

const payoutStatRows = computed(() =>
  Object.entries(stats.value?.payouts ?? {}).map(([status, item]) => ({status, ...item})),
)

onMounted(() => {
  loadConfigs().catch(() => undefined)
  loadStats().catch(() => undefined)
})
</script>

<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- 收益记录 -->
      <el-tab-pane :label="$t('admin.commerce.revenue.records')" name="record">
        <el-card shadow="never">
          <el-form :inline="true" :model="recordQuery" @submit.prevent="recordSearch()">
            <el-form-item :label="$t('admin.commerce.revenue.keyword')">
              <el-input v-model="recordQuery.keyword" clearable style="width: 180px"
                        @keyup.enter="recordSearch()"/>
            </el-form-item>
            <el-form-item :label="$t('admin.commerce.revenue.revenueType')">
              <el-select v-model="recordQuery.revenue_type" :placeholder="$t('admin.common.all')"
                         clearable style="width: 170px">
                <el-option v-for="item in REVENUE_TYPES" :key="item" :label="item" :value="item"/>
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('admin.commerce.revenue.userId')">
              <el-input-number v-model="recordQuery.user_id" :min="1" clearable style="width: 130px"/>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="recordSearch()">
                {{ $t('admin.common.search') }}
              </el-button>
              <el-button :icon="Refresh" @click="recordReset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>

          <div class="table-toolbar">
            <el-button v-auth="'module_commerce:revenue:create'" :icon="Plus" type="primary"
                       @click="openRecordCreate">
              {{ $t('admin.commerce.revenue.createRecord') }}
            </el-button>
            <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: recordTotal}) }}</span>
          </div>

          <AdminTableSkeleton v-if="recordLoading && !recordList.length" :rows="5"/>

          <AdminEmpty
            v-else-if="!recordLoading && !recordList.length"
            :title="recordFailed ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
            :variant="recordFailed ? 'error' : 'default'"
          >
            <el-button v-if="recordFailed" :icon="Refresh" @click="recordLoad()">
              {{ $t('admin.common.retry') }}
            </el-button>
          </AdminEmpty>

          <el-table v-else v-loading="recordLoading" :data="recordList" border stripe>
            <el-table-column :label="$t('admin.commerce.revenue.userId')" prop="user_id" width="90"/>
            <el-table-column :label="$t('admin.commerce.revenue.revenueType')" min-width="150"
                             prop="revenue_type"/>
            <el-table-column :label="$t('admin.commerce.revenue.amount')" align="right" prop="amount"
                             :formatter="moneyCell"
                             width="110"/>
            <el-table-column :label="$t('admin.commerce.revenue.platformFee')" align="right" prop="platform_fee"
                             :formatter="moneyCell"
                             width="120"/>
            <el-table-column :label="$t('admin.commerce.revenue.creatorEarnings')" align="right" prop="creator_earnings"
                             :formatter="moneyCell"
                             width="130"/>
            <el-table-column :label="$t('admin.common.status')" width="110">
              <template #default="{ row }">{{ (row as RevenueRecordItem).status || '-' }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.description')" min-width="160" prop="description"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="100">
              <template #default="{ row }">
                <el-button v-auth="'module_commerce:revenue:delete'" :icon="Delete" link type="danger"
                           @click="onDeleteRecord(row as RevenueRecordItem)">
                  {{ $t('admin.common.delete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination :current-page="recordPage" :page-size="recordPageSize"
                         :page-sizes="[10, 20, 50, 100]" :total="recordTotal" background
                         class="table-pagination" layout="total, sizes, prev, pager, next, jumper"
                         @current-change="onRecordPageChange" @size-change="onRecordSizeChange"/>
        </el-card>
      </el-tab-pane>

      <!-- 提现申请 -->
      <el-tab-pane :label="$t('admin.commerce.revenue.payouts')" name="payout">
        <el-card shadow="never">
          <el-form :inline="true" :model="payoutQuery" @submit.prevent="payoutSearch()">
            <el-form-item :label="$t('admin.commerce.revenue.userId')">
              <el-input-number v-model="payoutQuery.user_id" :min="1" clearable style="width: 130px"/>
            </el-form-item>
            <el-form-item :label="$t('admin.common.status')">
              <el-select v-model="payoutQuery.status" :placeholder="$t('admin.common.all')" clearable
                         style="width: 140px">
                <el-option label="pending" value="pending"/>
                <el-option label="approved" value="approved"/>
                <el-option label="completed" value="completed"/>
                <el-option label="rejected" value="rejected"/>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" type="primary" @click="payoutSearch()">
                {{ $t('admin.common.search') }}
              </el-button>
              <el-button :icon="Refresh" @click="payoutReset()">{{ $t('admin.common.reset') }}</el-button>
            </el-form-item>
          </el-form>

          <div class="table-toolbar">
            <span class="table-toolbar__total">{{ $t('admin.common.totalItems', {n: payoutTotal}) }}</span>
          </div>

          <el-table v-loading="payoutLoading" :data="payoutList" border stripe>
            <el-table-column :label="$t('admin.commerce.revenue.userId')" prop="user_id" width="90"/>
            <el-table-column :label="$t('admin.commerce.revenue.amount')" align="right" prop="amount"
                             :formatter="moneyCell"
                             width="110"/>
            <el-table-column :label="$t('admin.commerce.revenue.paymentMethod')" prop="payment_method"
                             width="130"/>
            <el-table-column :label="$t('admin.commerce.revenue.paymentAccount')" min-width="160"
                             prop="payment_account" show-overflow-tooltip/>
            <el-table-column :label="$t('admin.common.status')" align="center" width="110">
              <template #default="{ row }">
                <el-tag :type="(PAYOUT_TAG[(row as PayoutRequestItem).status || ''] || 'info') as never"
                        size="small">
                  {{ (row as PayoutRequestItem).status || '-' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.commerce.revenue.adminNotes')" min-width="150"
                             prop="admin_notes" show-overflow-tooltip/>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="220">
              <template #default="{ row }">
                <el-button
                  v-auth="'module_commerce:revenue:edit'"
                  :disabled="(row as PayoutRequestItem).status !== 'pending'"
                  :loading="payoutActing === (row as PayoutRequestItem).id"
                  link type="success"
                  @click="decidePayout(row as PayoutRequestItem, 'approve')"
                >
                  {{ $t('admin.commerce.revenue.action_approve') }}
                </el-button>
                <el-button
                  v-auth="'module_commerce:revenue:edit'"
                  :disabled="(row as PayoutRequestItem).status !== 'approved'"
                  :loading="payoutActing === (row as PayoutRequestItem).id"
                  link type="primary"
                  @click="decidePayout(row as PayoutRequestItem, 'complete')"
                >
                  {{ $t('admin.commerce.revenue.action_complete') }}
                </el-button>
                <el-button
                  v-auth="'module_commerce:revenue:edit'"
                  :disabled="(row as PayoutRequestItem).status !== 'pending'"
                  :loading="payoutActing === (row as PayoutRequestItem).id"
                  link type="danger"
                  @click="decidePayout(row as PayoutRequestItem, 'reject')"
                >
                  {{ $t('admin.commerce.revenue.action_reject') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination :current-page="payoutPage" :page-size="payoutPageSize"
                         :page-sizes="[10, 20, 50, 100]" :total="payoutTotal" background
                         class="table-pagination" layout="total, sizes, prev, pager, next, jumper"
                         @current-change="onPayoutPageChange" @size-change="onPayoutSizeChange"/>
        </el-card>
      </el-tab-pane>

      <!-- 分成配置 -->
      <el-tab-pane :label="$t('admin.commerce.revenue.configs')" name="config">
        <el-card shadow="never">
          <el-alert :closable="false" :title="$t('admin.commerce.revenue.configHint')" class="mb-3"
                    show-icon type="info"/>
          <el-table v-loading="configLoading" :data="configList" border stripe>
            <el-table-column :label="$t('admin.commerce.revenue.revenueType')" min-width="170"
                             prop="revenue_type"/>
            <el-table-column :label="$t('admin.commerce.revenue.platformPercentage')" align="right"
                             prop="platform_percentage" width="140"/>
            <el-table-column :label="$t('admin.commerce.revenue.creatorPercentage')" align="right"
                             prop="creator_percentage" width="140"/>
            <el-table-column :label="$t('admin.commerce.revenue.minPayoutAmount')" align="right"
                             :formatter="moneyCell" prop="min_payout_amount" width="140"/>
            <el-table-column :label="$t('admin.common.status')" align="center" width="100">
              <template #default="{ row }">
                <el-tag :type="(row as SharingConfigItem).is_active ? 'success' : 'info'" size="small">
                  {{ (row as SharingConfigItem).is_active ? $t('admin.common.enabled') : $t('admin.common.disabled') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.common.actions')" fixed="right" width="100">
              <template #default="{ row }">
                <el-button v-auth="'module_commerce:revenue:edit'" :icon="EditPen" link type="primary"
                           @click="openConfigEdit(row as SharingConfigItem)">
                  {{ $t('admin.common.edit') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!configLoading && !configList.length" :description="$t('admin.commerce.revenue.noConfigs')"/>
        </el-card>
      </el-tab-pane>

      <!-- 平台统计 -->
      <el-tab-pane :label="$t('admin.commerce.revenue.stats')" name="stats">
        <el-card v-loading="statsLoading" shadow="never">
          <div class="table-toolbar">
            <el-button :icon="Refresh" @click="loadStats()">{{ $t('admin.common.refresh') }}</el-button>
          </div>
          <div class="stats-grid">
            <div v-for="card in statsCards" :key="card.key" class="stats-card">
              <div class="stats-card__label">{{ $t(`admin.commerce.revenue.stat_${card.key}`) }}</div>
              <div class="stats-card__value">{{ card.value }}</div>
            </div>
          </div>

          <h4 class="stats-title">{{ $t('admin.commerce.revenue.byType') }}</h4>
          <el-table :data="stats?.by_type ?? []" border size="small" stripe>
            <el-table-column :label="$t('admin.commerce.revenue.revenueType')" min-width="170"
                             prop="revenue_type"/>
            <el-table-column :label="$t('admin.commerce.revenue.recordCount')" prop="count" width="120"/>
            <el-table-column :label="$t('admin.commerce.revenue.amount')" align="right" prop="amount"
                             :formatter="moneyCell"
                             width="140"/>
          </el-table>

          <h4 class="stats-title">{{ $t('admin.commerce.revenue.payouts') }}</h4>
          <el-table :data="payoutStatRows" border size="small" stripe>
            <el-table-column :label="$t('admin.common.status')" min-width="140" prop="status"/>
            <el-table-column :label="$t('admin.commerce.revenue.recordCount')" prop="count" width="120"/>
            <el-table-column :label="$t('admin.commerce.revenue.amount')" align="right" prop="amount"
                             :formatter="moneyCell"
                             width="140"/>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 新建收益记录 -->
    <el-drawer v-model="recordFormVisible" :title="$t('admin.commerce.revenue.createRecord')"
               destroy-on-close size="480px">
      <el-form :model="recordForm" label-width="130px">
        <el-form-item :label="$t('admin.commerce.revenue.userId')" required>
          <el-input-number v-model="recordForm.user_id" :min="1" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.revenue.revenueType')" required>
          <el-select v-model="recordForm.revenue_type" style="width: 100%">
            <el-option v-for="item in REVENUE_TYPES" :key="item" :label="item" :value="item"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.revenue.amount')" required>
          <el-input-number v-model="recordForm.amount" :min="0.01" :precision="2" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="recordForm.description"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.revenue.referenceType')">
          <el-input v-model="recordForm.reference_type"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="recordFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="recordSaving" type="primary" @click="submitRecord">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-drawer>

    <!-- 编辑分成配置 -->
    <el-drawer v-model="configFormVisible"
               :title="$t('admin.commerce.revenue.editConfig', {type: configEditing?.revenue_type || ''})"
               destroy-on-close size="480px">
      <el-form :model="configForm" label-width="150px">
        <el-form-item :label="$t('admin.commerce.revenue.platformPercentage')">
          <el-input-number v-model="configForm.platform_percentage" :max="100" :min="0" :precision="2"
                           style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.revenue.creatorPercentage')">
          <el-input-number v-model="configForm.creator_percentage" :max="100" :min="0" :precision="2"
                           style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.revenue.minPayoutAmount')">
          <el-input-number v-model="configForm.min_payout_amount" :min="0" :precision="2"
                           style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="configForm.description" :autosize="{minRows: 2, maxRows: 4}" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="configForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="configSaving" type="primary" @click="submitConfig">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.mb-3 {
  margin-bottom: 12px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.stats-card {
  padding: 14px 16px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
}

.stats-card__label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.stats-card__value {
  margin-top: 6px;
  font-size: 20px;
  font-weight: 600;
}

.stats-title {
  margin: 20px 0 10px;
}
</style>
