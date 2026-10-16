<script lang="ts" setup>
/**
 * 支付配置 · 交易面板
 *
 * 从 `pages/commerce/payment.vue` 的「交易」标签页抽出：交易列表（按关键字 / 状态 /
 * 币种筛选）及其新建 / 编辑 / 删除。
 *
 * 交易状态 → `el-tag` 类型的映射（`STATUS_TAG` + `statusTag`）原本挂在页面级，但全仓
 * 只有本面板的表格用它，因此一并搬进来，不再让页面为它保留导出。
 *
 * 加载时机与原实现一致：`useAdminList` 默认挂载即加载。
 */
import {Delete, EditPen, Plus} from '@element-plus/icons-vue'
import {computed, reactive, ref} from 'vue'

import {paymentApi, type PaymentTransactionItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {DEFAULT_CURRENCY, formatMoney} from '@/utils/money'

const {t} = useI18n()

const STATUS_TAG: Record<string, string> = {
  pending: 'info',
  completed: 'success',
  succeeded: 'success',
  paid: 'success',
  failed: 'danger',
  refunded: 'warning',
  cancelled: 'info',
}

function statusTag(status?: string | null): string {
  return STATUS_TAG[status || ''] || 'info'
}

const txState = useAdminList<PaymentTransactionItem, PageQuery & { status?: string; currency?: string }>({
  fetcher: (params) => paymentApi.listTransactions(params),
  defaultQuery: {keyword: '', status: '', currency: ''},
})

// 模板沿用原有变量名：映射为同名 ref / 函数
const txList = txState.rows
const txLoading = txState.loading
const txTotal = txState.total
const txPage = txState.page
const txPageSize = txState.pageSize
const txQuery = txState.query
const txSearch = txState.search
const txReset = txState.reset
const txLoad = txState.reload
const onTxPageChange = txState.onPageChange
const onTxSizeChange = txState.onSizeChange
const txFailed = txState.failed

const txFormVisible = ref(false)
const txEditingId = ref<number | null>(null)
const txSaving = ref(false)
const txForm = reactive({
  user: undefined as number | undefined,
  amount: undefined as number | undefined,
  gateway: undefined as number | undefined,
  order_id: '',
  currency: DEFAULT_CURRENCY,
  status: 'pending',
  transaction_id: '',
  payment_method: '',
})

const txFormTitle = computed(() =>
  txEditingId.value
    ? t('admin.commerce.payment.editTransaction')
    : t('admin.commerce.payment.createTransaction'),
)

function openTxCreate(): void {
  txEditingId.value = null
  Object.assign(txForm, {
    user: undefined,
    amount: undefined,
    gateway: undefined,
    order_id: '',
    currency: DEFAULT_CURRENCY,
    status: 'pending',
    transaction_id: '',
    payment_method: '',
  })
  txFormVisible.value = true
}

function openTxEdit(row: PaymentTransactionItem): void {
  txEditingId.value = row.id
  Object.assign(txForm, {
    user: row.user ?? undefined,
    amount: row.amount ?? undefined,
    gateway: row.gateway ?? undefined,
    order_id: row.order_id || '',
    currency: row.currency || DEFAULT_CURRENCY,
    status: row.status || 'pending',
    transaction_id: row.transaction_id || '',
    payment_method: row.payment_method || '',
  })
  txFormVisible.value = true
}

async function submitTx(): Promise<void> {
  if (txForm.user === undefined || !txForm.amount || txForm.amount <= 0) {
    ElMessage.warning(t('admin.commerce.payment.transactionRequired'))
    return
  }
  txSaving.value = true
  try {
    const payload = {
      user: txForm.user,
      amount: txForm.amount,
      gateway: txForm.gateway ?? null,
      order_id: txForm.order_id.trim() || null,
      currency: txForm.currency || DEFAULT_CURRENCY,
      status: txForm.status,
      transaction_id: txForm.transaction_id.trim() || null,
      payment_method: txForm.payment_method.trim() || null,
    }
    if (txEditingId.value) {
      await paymentApi.updateTransaction(txEditingId.value, payload)
    } else {
      await paymentApi.createTransaction(payload)
    }
    ElMessage.success(t('admin.common.save'))
    txFormVisible.value = false
    await txLoad()
  } finally {
    txSaving.value = false
  }
}

async function onDeleteTx(row: PaymentTransactionItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.commerce.payment.deleteTransactionConfirm', {name: row.order_id || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await paymentApi.removeTransaction(row.id)
  ElMessage.success(t('admin.common.delete'))
  await txLoad()
}
</script>

<template>
  <AdminListShell
    :failed="txFailed"
    :loading="txLoading"
    :page="txPage"
    :page-size="txPageSize"
    :rows="txList"
    :selectable="false"
    :total="txTotal"
    @refresh="txLoad"
    @reset="txReset"
    @search="txSearch"
    @page-change="onTxPageChange"
    @size-change="onTxSizeChange"
  >
    <template #filters>
      <el-form-item :label="$t('admin.commerce.payment.keyword')">
        <el-input v-model="txQuery.keyword" clearable style="width: 180px" @keyup.enter="txSearch()"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.txStatus')">
        <el-input v-model="txQuery.status" clearable style="width: 130px" @keyup.enter="txSearch()"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.currency')">
        <el-input v-model="txQuery.currency" clearable style="width: 100px" @keyup.enter="txSearch()"/>
      </el-form-item>
    </template>

    <template #actions>
      <el-button v-auth="'module_commerce:payment:create'" :icon="Plus" type="primary" @click="openTxCreate">
        {{ $t('admin.commerce.payment.createTransaction') }}
      </el-button>
    </template>

    <el-table-column :label="$t('admin.commerce.payment.orderId')" min-width="150"
                     prop="order_id" show-overflow-tooltip/>
    <el-table-column :label="$t('admin.commerce.payment.userId')" prop="user" width="90"/>
    <el-table-column :label="$t('admin.commerce.payment.amount')" align="right" width="150">
      <template #default="{ row }">
        {{ formatMoney((row as PaymentTransactionItem).amount, (row as PaymentTransactionItem).currency) }}
      </template>
    </el-table-column>
    <el-table-column :label="$t('admin.commerce.payment.txStatus')" align="center" width="110">
      <template #default="{ row }">
        <el-tag :type="statusTag((row as PaymentTransactionItem).status)" size="small">
          {{ (row as PaymentTransactionItem).status || '-' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column :label="$t('admin.commerce.payment.transactionId')" min-width="160"
                     prop="transaction_id" show-overflow-tooltip/>
    <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
      <template #default="{ row }">
        <el-button v-auth="'module_commerce:payment:edit'" :icon="EditPen" link type="primary"
                   @click="openTxEdit(row as PaymentTransactionItem)">
          {{ $t('admin.common.edit') }}
        </el-button>
        <el-button v-auth="'module_commerce:payment:delete'" :icon="Delete" link type="danger"
                   @click="onDeleteTx(row as PaymentTransactionItem)">
          {{ $t('admin.common.delete') }}
        </el-button>
      </template>
    </el-table-column>
  </AdminListShell>

  <!-- 交易表单 -->
  <el-drawer v-model="txFormVisible" :title="txFormTitle" destroy-on-close size="520px">
    <el-form :model="txForm" label-width="120px">
      <el-form-item :label="$t('admin.commerce.payment.userId')" required>
        <el-input-number v-model="txForm.user" :min="1" style="width: 100%"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.amount')" required>
        <el-input-number v-model="txForm.amount" :min="0.01" :precision="2" style="width: 100%"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.gatewayId')">
        <el-input-number v-model="txForm.gateway" :min="1" style="width: 100%"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.orderId')">
        <el-input v-model="txForm.order_id"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.currency')">
        <el-input v-model="txForm.currency"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.txStatus')">
        <el-select v-model="txForm.status" style="width: 100%">
          <el-option label="pending" value="pending"/>
          <el-option label="completed" value="completed"/>
          <el-option label="failed" value="failed"/>
          <el-option label="refunded" value="refunded"/>
          <el-option label="cancelled" value="cancelled"/>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.transactionId')">
        <el-input v-model="txForm.transaction_id"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.paymentMethod')">
        <el-input v-model="txForm.payment_method"/>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="txFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
      <el-button :loading="txSaving" type="primary" @click="submitTx">
        {{ $t('admin.common.save') }}
      </el-button>
    </template>
  </el-drawer>
</template>
