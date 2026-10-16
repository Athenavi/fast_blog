<script lang="ts" setup>
/**
 * 支付配置 · 加密支付面板
 *
 * 从 `pages/commerce/payment.vue` 的「加密支付」标签页抽出：链上支付记录列表及其
 * 新建 / 编辑 / 删除（钱包地址、链、代币、确认数）。
 *
 * 加载时机与原实现一致：`useAdminList` 默认挂载即加载。
 */
import {Delete, EditPen, Plus} from '@element-plus/icons-vue'
import {computed, reactive, ref} from 'vue'

import {type CryptoPaymentItem, paymentApi} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

const {t} = useI18n()

const cryptoState = useAdminList<CryptoPaymentItem, PageQuery & { blockchain?: string; status?: string }>({
  fetcher: (params) => paymentApi.listCrypto(params),
  defaultQuery: {keyword: '', blockchain: '', status: ''},
})

// 模板沿用原有变量名：映射为同名 ref / 函数
const cryptoList = cryptoState.rows
const cryptoLoading = cryptoState.loading
const cryptoTotal = cryptoState.total
const cryptoPage = cryptoState.page
const cryptoPageSize = cryptoState.pageSize
const cryptoQuery = cryptoState.query
const cryptoSearch = cryptoState.search
const cryptoReset = cryptoState.reset
const cryptoLoad = cryptoState.reload
const onCryptoPageChange = cryptoState.onPageChange
const onCryptoSizeChange = cryptoState.onSizeChange
const cryptoFailed = cryptoState.failed

const cryptoFormVisible = ref(false)
const cryptoEditingId = ref<number | null>(null)
const cryptoSaving = ref(false)
const cryptoForm = reactive({
  transaction: undefined as number | undefined,
  wallet_address: '',
  blockchain: '',
  token_symbol: '',
  tx_hash: '',
  confirmations: 0,
  required_confirmations: 6,
  status: 'waiting_payment',
})

const cryptoFormTitle = computed(() =>
  cryptoEditingId.value
    ? t('admin.commerce.payment.editCrypto')
    : t('admin.commerce.payment.createCrypto'),
)

function openCryptoCreate(): void {
  cryptoEditingId.value = null
  Object.assign(cryptoForm, {
    transaction: undefined,
    wallet_address: '',
    blockchain: '',
    token_symbol: '',
    tx_hash: '',
    confirmations: 0,
    required_confirmations: 6,
    status: 'waiting_payment',
  })
  cryptoFormVisible.value = true
}

function openCryptoEdit(row: CryptoPaymentItem): void {
  cryptoEditingId.value = row.id
  Object.assign(cryptoForm, {
    transaction: row.transaction ?? undefined,
    wallet_address: row.wallet_address || '',
    blockchain: row.blockchain || '',
    token_symbol: row.token_symbol || '',
    tx_hash: row.tx_hash || '',
    confirmations: row.confirmations ?? 0,
    required_confirmations: row.required_confirmations ?? 6,
    status: row.status || 'waiting_payment',
  })
  cryptoFormVisible.value = true
}

async function submitCrypto(): Promise<void> {
  // 编辑时后端只允许改 tx_hash / 确认数 / 状态，所以必填项只在新建时校验
  if (
    !cryptoEditingId.value &&
    (cryptoForm.transaction === undefined ||
      !cryptoForm.wallet_address.trim() ||
      !cryptoForm.blockchain.trim() ||
      !cryptoForm.token_symbol.trim())
  ) {
    ElMessage.warning(t('admin.commerce.payment.cryptoRequired'))
    return
  }
  cryptoSaving.value = true
  try {
    const payload = {
      transaction: cryptoForm.transaction,
      wallet_address: cryptoForm.wallet_address.trim(),
      blockchain: cryptoForm.blockchain.trim(),
      token_symbol: cryptoForm.token_symbol.trim(),
      tx_hash: cryptoForm.tx_hash.trim() || null,
      confirmations: cryptoForm.confirmations,
      required_confirmations: cryptoForm.required_confirmations,
      status: cryptoForm.status,
    }
    if (cryptoEditingId.value) {
      await paymentApi.updateCrypto(cryptoEditingId.value, payload)
    } else {
      await paymentApi.createCrypto(payload)
    }
    ElMessage.success(t('admin.common.save'))
    cryptoFormVisible.value = false
    await cryptoLoad()
  } finally {
    cryptoSaving.value = false
  }
}

async function onDeleteCrypto(row: CryptoPaymentItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.commerce.payment.deleteCryptoConfirm', {name: row.tx_hash || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await paymentApi.removeCrypto(row.id)
  ElMessage.success(t('admin.common.delete'))
  await cryptoLoad()
}
</script>

<template>
  <AdminListShell
    :failed="cryptoFailed"
    :loading="cryptoLoading"
    :page="cryptoPage"
    :page-size="cryptoPageSize"
    :rows="cryptoList"
    :selectable="false"
    :total="cryptoTotal"
    @refresh="cryptoLoad"
    @reset="cryptoReset"
    @search="cryptoSearch"
    @page-change="onCryptoPageChange"
    @size-change="onCryptoSizeChange"
  >
    <template #filters>
      <el-form-item :label="$t('admin.commerce.payment.keyword')">
        <el-input v-model="cryptoQuery.keyword" clearable style="width: 200px"
                  @keyup.enter="cryptoSearch()"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.blockchain')">
        <el-input v-model="cryptoQuery.blockchain" clearable style="width: 130px"
                  @keyup.enter="cryptoSearch()"/>
      </el-form-item>
    </template>

    <template #actions>
      <el-button v-auth="'module_commerce:payment:create'" :icon="Plus" type="primary"
                 @click="openCryptoCreate">
        {{ $t('admin.commerce.payment.createCrypto') }}
      </el-button>
    </template>

    <el-table-column :label="$t('admin.commerce.payment.transactionId')" prop="transaction" width="110"/>
    <el-table-column :label="$t('admin.commerce.payment.blockchain')" prop="blockchain" width="110"/>
    <el-table-column :label="$t('admin.commerce.payment.token')" prop="token_symbol" width="90"/>
    <el-table-column :label="$t('admin.commerce.payment.wallet')" min-width="180"
                     prop="wallet_address" show-overflow-tooltip/>
    <el-table-column :label="$t('admin.commerce.payment.confirmations')" align="center" width="110">
      <template #default="{ row }">
        {{ (row as CryptoPaymentItem).confirmations }}/{{ (row as CryptoPaymentItem).required_confirmations }}
      </template>
    </el-table-column>
    <el-table-column :label="$t('admin.common.status')" width="130">
      <template #default="{ row }">{{ (row as CryptoPaymentItem).status || '-' }}</template>
    </el-table-column>
    <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
      <template #default="{ row }">
        <el-button v-auth="'module_commerce:payment:edit'" :icon="EditPen" link type="primary"
                   @click="openCryptoEdit(row as CryptoPaymentItem)">
          {{ $t('admin.common.edit') }}
        </el-button>
        <el-button v-auth="'module_commerce:payment:delete'" :icon="Delete" link type="danger"
                   @click="onDeleteCrypto(row as CryptoPaymentItem)">
          {{ $t('admin.common.delete') }}
        </el-button>
      </template>
    </el-table-column>
  </AdminListShell>

  <!-- 加密支付表单 -->
  <el-drawer v-model="cryptoFormVisible" :title="cryptoFormTitle" destroy-on-close size="520px">
    <el-form :model="cryptoForm" label-width="140px">
      <el-form-item :label="$t('admin.commerce.payment.gatewayId')" required>
        <el-input-number v-model="cryptoForm.transaction" :min="1" style="width: 100%"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.blockchain')" required>
        <el-input v-model="cryptoForm.blockchain" placeholder="ethereum / bitcoin"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.token')" required>
        <el-input v-model="cryptoForm.token_symbol" placeholder="ETH / BTC / USDT"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.wallet')" required>
        <el-input v-model="cryptoForm.wallet_address"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.txHash')">
        <el-input v-model="cryptoForm.tx_hash"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.confirmations')">
        <el-input-number v-model="cryptoForm.confirmations" :min="0" style="width: 100%"/>
      </el-form-item>
      <el-form-item :label="$t('admin.commerce.payment.requiredConfirmations')">
        <el-input-number v-model="cryptoForm.required_confirmations" :min="0" style="width: 100%"/>
      </el-form-item>
      <el-form-item :label="$t('admin.common.status')">
        <el-input v-model="cryptoForm.status"/>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="cryptoFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
      <el-button :loading="cryptoSaving" type="primary" @click="submitCrypto">
        {{ $t('admin.common.save') }}
      </el-button>
    </template>
  </el-drawer>
</template>
