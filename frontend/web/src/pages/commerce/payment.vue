<script lang="ts" setup>
/**
 * 支付管理（T5-11 批次 7，commerce 域）
 *
 * 对齐 v3 `/commerce/payment`：支付网关 / 交易 / 加密支付 / 税务配置（四标签）。
 * 网关的 `config_data` **只入不出** —— 响应只有 `has_config_data`，编辑时留空即保持原值。
 * 「发起支付」走 `/commerce/payment/initiate`，实际由 payment-gateway 插件执行
 * （金额按**元**填写，服务端转发插件时转成分）。
 *
 * 追加：**税务计算**子能力（与 `tax-config` CRUD 是两套东西）——
 *   - 税务试算 `POST /commerce/payment/tax/calculate`（税率来自 `tax_configs` 真表）
 *   - 解析税率 `GET /commerce/payment/tax/resolve`
 *   - 税务报表 `GET /commerce/payment/tax/report`（权限 `module_commerce:revenue:view`）
 */
import {Delete, EditPen, Plus, Promotion, Search} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {DEFAULT_CURRENCY, formatMoney} from '@/utils/money'
import {computed, reactive, ref} from 'vue'

import {
  type CryptoPaymentItem,
  paymentApi,
  type PaymentGatewayItem,
  type PaymentTransactionItem,
  type TaxCalculateResult,
  type TaxConfigItem,
  type TaxRateResult,
  type TaxReportResult,
} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.commerce.payment.title',
  permission: 'module_commerce:payment:view',
})

const {t} = useI18n()
const activeTab = ref('gateway')

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

// ---------------------------------------------------------------- 网关
const gatewayState = useAdminList<PaymentGatewayItem, PageQuery & { provider?: string; is_active?: boolean }>({

  fetcher: (params) => paymentApi.listGateways(params),
  defaultQuery: {keyword: '', provider: '', is_active: undefined},
  syncUrl: true,
})

// 模板沿用原有变量名：映射为同名 ref / 函数
const gatewayList = gatewayState.rows
const gatewayLoading = gatewayState.loading
const gatewayTotal = gatewayState.total
const gatewayPage = gatewayState.page
const gatewayPageSize = gatewayState.pageSize
const gatewayQuery = gatewayState.query
const gatewaySearch = gatewayState.search
const gatewayReset = gatewayState.reset
const gatewayLoad = gatewayState.reload
const onGatewayPageChange = gatewayState.onPageChange
const onGatewaySizeChange = gatewayState.onSizeChange
const gatewayFailed = gatewayState.failed

const gatewayFormVisible = ref(false)
const gatewayEditingId = ref<number | null>(null)
const gatewaySaving = ref(false)
const gatewayForm = reactive({
  name: '',
  provider: '',
  config_data_text: '',
  is_active: false,
  supported_currencies: 'USD,CNY',
})

const gatewayFormTitle = computed(() =>
  gatewayEditingId.value
    ? t('admin.commerce.payment.editGateway')
    : t('admin.commerce.payment.createGateway'),
)

function openGatewayCreate() {
  gatewayEditingId.value = null
  Object.assign(gatewayForm, {
    name: '',
    provider: '',
    config_data_text: '',
    is_active: false,
    supported_currencies: 'USD,CNY',
  })
  gatewayFormVisible.value = true
}

function openGatewayEdit(row: PaymentGatewayItem) {
  gatewayEditingId.value = row.id
  Object.assign(gatewayForm, {
    name: row.name || '',
    provider: row.provider || '',
    // 明文拿不到：留空表示"保持原值"
    config_data_text: '',
    is_active: row.is_active,
    supported_currencies: row.supported_currencies || 'USD,CNY',
  })
  gatewayFormVisible.value = true
}

function parseConfigData(text: string): Record<string, unknown> | null {
  const trimmed = text.trim()
  if (!trimmed) return null
  const parsed: unknown = JSON.parse(trimmed)
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    throw new Error('config_data must be a JSON object')
  }
  return parsed as Record<string, unknown>
}

async function submitGateway() {
  if (!gatewayForm.name.trim() || !gatewayForm.provider.trim()) {
    ElMessage.warning(t('admin.commerce.payment.gatewayRequired'))
    return
  }
  let configData: Record<string, unknown> | null = null
  try {
    configData = parseConfigData(gatewayForm.config_data_text)
  } catch {
    ElMessage.warning(t('admin.commerce.payment.configInvalid'))
    return
  }
  gatewaySaving.value = true
  try {
    const base = {
      name: gatewayForm.name.trim(),
      provider: gatewayForm.provider.trim(),
      is_active: gatewayForm.is_active,
      supported_currencies: gatewayForm.supported_currencies,
    }
    if (gatewayEditingId.value) {
      // 编辑时 config_data 留空 => 不下发该字段 => 保持原值
      await paymentApi.updateGateway(gatewayEditingId.value, {
        ...base,
        ...(configData ? {config_data: configData} : {}),
      })
    } else {
      await paymentApi.createGateway({...base, config_data: configData})
    }
    ElMessage.success(t('admin.common.save'))
    gatewayFormVisible.value = false
    await gatewayLoad()
  } finally {
    gatewaySaving.value = false
  }
}

async function onDeleteGateway(row: PaymentGatewayItem) {
  await ElMessageBox.confirm(
    t('admin.commerce.payment.deleteGatewayConfirm', {name: row.name || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await paymentApi.removeGateway(row.id)
  ElMessage.success(t('admin.common.delete'))
  await gatewayLoad()
}

// ---------------------------------------------------------------- 交易
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

function openTxCreate() {
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

function openTxEdit(row: PaymentTransactionItem) {
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

async function submitTx() {
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

async function onDeleteTx(row: PaymentTransactionItem) {
  await ElMessageBox.confirm(
    t('admin.commerce.payment.deleteTransactionConfirm', {name: row.order_id || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await paymentApi.removeTransaction(row.id)
  ElMessage.success(t('admin.common.delete'))
  await txLoad()
}

// ---------------------------------------------------------------- 加密支付
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

function openCryptoCreate() {
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

function openCryptoEdit(row: CryptoPaymentItem) {
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

async function submitCrypto() {
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

async function onDeleteCrypto(row: CryptoPaymentItem) {
  await ElMessageBox.confirm(
    t('admin.commerce.payment.deleteCryptoConfirm', {name: row.tx_hash || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await paymentApi.removeCrypto(row.id)
  ElMessage.success(t('admin.common.delete'))
  await cryptoLoad()
}

// ---------------------------------------------------------------- 税务配置
const taxState = useAdminList<TaxConfigItem, PageQuery & { country?: string; tax_type?: string }>({

  fetcher: (params) => paymentApi.listTaxConfigs(params),
  defaultQuery: {keyword: '', country: '', tax_type: ''},
})

// 模板沿用原有变量名：映射为同名 ref / 函数
const taxList = taxState.rows
const taxLoading = taxState.loading
const taxTotal = taxState.total
const taxPage = taxState.page
const taxPageSize = taxState.pageSize
const taxQuery = taxState.query
const taxSearch = taxState.search
const taxReset = taxState.reset
const taxLoad = taxState.reload
const onTaxPageChange = taxState.onPageChange
const onTaxSizeChange = taxState.onSizeChange
const taxFailed = taxState.failed

const taxFormVisible = ref(false)
const taxEditingId = ref<number | null>(null)
const taxSaving = ref(false)
const taxForm = reactive({
  country: '',
  region: '',
  tax_type: '',
  rate: undefined as number | undefined,
  description: '',
  is_active: true,
})

const taxFormTitle = computed(() =>
  taxEditingId.value
    ? t('admin.commerce.payment.editTax')
    : t('admin.commerce.payment.createTax'),
)

function openTaxCreate() {
  taxEditingId.value = null
  Object.assign(taxForm, {
    country: '',
    region: '',
    tax_type: '',
    rate: undefined,
    description: '',
    is_active: true,
  })
  taxFormVisible.value = true
}

function openTaxEdit(row: TaxConfigItem) {
  taxEditingId.value = row.id
  Object.assign(taxForm, {
    country: row.country || '',
    region: row.region || '',
    tax_type: row.tax_type || '',
    rate: row.rate ?? undefined,
    description: row.description || '',
    is_active: row.is_active,
  })
  taxFormVisible.value = true
}

async function submitTax() {
  if (taxForm.country.trim().length !== 2 || !taxForm.tax_type.trim() || taxForm.rate === undefined) {
    ElMessage.warning(t('admin.commerce.payment.taxRequired'))
    return
  }
  taxSaving.value = true
  try {
    const payload = {
      country: taxForm.country.trim().toUpperCase(),
      region: taxForm.region.trim() || null,
      tax_type: taxForm.tax_type.trim(),
      rate: taxForm.rate,
      description: taxForm.description.trim() || null,
      is_active: taxForm.is_active,
    }
    if (taxEditingId.value) {
      await paymentApi.updateTaxConfig(taxEditingId.value, payload)
    } else {
      await paymentApi.createTaxConfig(payload)
    }
    ElMessage.success(t('admin.common.save'))
    taxFormVisible.value = false
    await taxLoad()
  } finally {
    taxSaving.value = false
  }
}

async function onDeleteTax(row: TaxConfigItem) {
  await ElMessageBox.confirm(
    t('admin.commerce.payment.deleteTaxConfirm', {
      name: `${row.country || ''} ${row.tax_type || ''}`.trim() || row.id,
    }),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await paymentApi.removeTaxConfig(row.id)
  ElMessage.success(t('admin.common.delete'))
  await taxLoad()
}

// ---------------------------------------------------------------- 发起支付（联调用）
const initiateVisible = ref(false)
const initiateSaving = ref(false)
const initiateResult = ref<string>('')
const initiateForm = reactive({order_id: '', amount: undefined as number | undefined, subject: ''})

function openInitiate() {
  Object.assign(initiateForm, {order_id: '', amount: undefined, subject: ''})
  initiateResult.value = ''
  initiateVisible.value = true
}

async function submitInitiate() {
  if (!initiateForm.order_id.trim() || !initiateForm.amount) {
    ElMessage.warning(t('admin.commerce.payment.initiateRequired'))
    return
  }
  initiateSaving.value = true
  try {
    const result = await paymentApi.initiate({
      order_id: initiateForm.order_id.trim(),
      amount: initiateForm.amount,
      subject: initiateForm.subject,
    })
    initiateResult.value = JSON.stringify(result, null, 2)
  } finally {
    initiateSaving.value = false
  }
}

// ---------------------------------------------------------------- 税务试算（税率来自 tax_configs）
const taxCalcForm = reactive({
  amount: undefined as number | undefined,
  country: '',
  region: '',
  tax_type: '',
  inclusive: false,
  vat_number: '',
})
const taxCalcSaving = ref(false)
const taxRateLoading = ref(false)
const taxCalcResult = ref<TaxCalculateResult | null>(null)
const taxRateResult = ref<TaxRateResult | null>(null)

async function resolveTaxRate() {
  if (taxCalcForm.country.trim().length !== 2) {
    ElMessage.warning(t('admin.commerce.payment.taxCalcCountryRequired'))
    return
  }
  taxRateLoading.value = true
  try {
    taxRateResult.value = await paymentApi.resolveTaxRate({
      country: taxCalcForm.country.trim().toUpperCase(),
      ...(taxCalcForm.region.trim() ? {region: taxCalcForm.region.trim()} : {}),
      ...(taxCalcForm.tax_type.trim() ? {tax_type: taxCalcForm.tax_type.trim()} : {}),
    })
  } finally {
    taxRateLoading.value = false
  }
}

async function submitTaxCalc() {
  if (!taxCalcForm.amount || taxCalcForm.amount <= 0 || taxCalcForm.country.trim().length !== 2) {
    ElMessage.warning(t('admin.commerce.payment.taxCalcRequired'))
    return
  }
  taxCalcSaving.value = true
  try {
    taxCalcResult.value = await paymentApi.calculateTax({
      amount: taxCalcForm.amount,
      country: taxCalcForm.country.trim().toUpperCase(),
      region: taxCalcForm.region.trim() || null,
      tax_type: taxCalcForm.tax_type.trim() || null,
      inclusive: taxCalcForm.inclusive,
      vat_number: taxCalcForm.vat_number.trim() || null,
    })
  } finally {
    taxCalcSaving.value = false
  }
}

// ---------------------------------------------------------------- 税务报表（权限：module_commerce:revenue:view）
const taxReportQuery = reactive({days: 30, currency: ''})
const taxReportLoading = ref(false)
const taxReport = ref<TaxReportResult | null>(null)

async function loadTaxReport() {
  taxReportLoading.value = true
  try {
    taxReport.value = await paymentApi.taxReport({
      days: taxReportQuery.days,
      ...(taxReportQuery.currency.trim()
        ? {currency: taxReportQuery.currency.trim().toUpperCase()}
        : {}),
    })
  } finally {
    taxReportLoading.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- 支付网关 -->
      <el-tab-pane :label="$t('admin.commerce.payment.gateways')" name="gateway">
        <AdminListShell
          :failed="gatewayFailed"
          :loading="gatewayLoading"
          :page="gatewayPage"
          :page-size="gatewayPageSize"
          :rows="gatewayList"
          :selectable="false"
          :total="gatewayTotal"
          @refresh="gatewayLoad"
          @reset="gatewayReset"
          @search="gatewaySearch"
          @page-change="onGatewayPageChange"
          @size-change="onGatewaySizeChange"
        >
          <template #filters>
            <el-form-item :label="$t('admin.commerce.payment.keyword')">
              <el-input v-model="gatewayQuery.keyword" clearable style="width: 180px"
                        @keyup.enter="gatewaySearch()"/>
            </el-form-item>
            <el-form-item :label="$t('admin.commerce.payment.provider')">
              <el-input v-model="gatewayQuery.provider" clearable style="width: 140px"
                        @keyup.enter="gatewaySearch()"/>
            </el-form-item>
          </template>

          <template #actions>
            <el-button v-auth="'module_commerce:payment:create'" :icon="Plus" type="primary"
                       @click="openGatewayCreate">
              {{ $t('admin.commerce.payment.createGateway') }}
            </el-button>
            <el-button :icon="Promotion" @click="openInitiate">
              {{ $t('admin.commerce.payment.initiate') }}
            </el-button>
          </template>

          <el-table-column :label="$t('admin.common.name')" min-width="150" prop="name" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.commerce.payment.provider')" prop="provider" width="120"/>
          <el-table-column :label="$t('admin.commerce.payment.currencies')" min-width="140"
                           prop="supported_currencies" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.commerce.payment.hasConfig')" align="center" width="110">
            <template #default="{ row }">
              <el-tag :type="(row as PaymentGatewayItem).has_config_data ? 'success' : 'info'" size="small">
                {{ (row as PaymentGatewayItem).has_config_data ? $t('admin.common.yes') : $t('admin.common.no') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.common.status')" align="center" width="100">
            <template #default="{ row }">
              <el-tag :type="(row as PaymentGatewayItem).is_active ? 'success' : 'info'" size="small">
                {{ (row as PaymentGatewayItem).is_active ? $t('admin.common.enabled') : $t('admin.common.disabled') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
            <template #default="{ row }">
              <el-button v-auth="'module_commerce:payment:edit'" :icon="EditPen" link type="primary"
                         @click="openGatewayEdit(row as PaymentGatewayItem)">
                {{ $t('admin.common.edit') }}
              </el-button>
              <el-button v-auth="'module_commerce:payment:delete'" :icon="Delete" link type="danger"
                         @click="onDeleteGateway(row as PaymentGatewayItem)">
                {{ $t('admin.common.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </AdminListShell>
      </el-tab-pane>

      <!-- 交易 -->
      <el-tab-pane :label="$t('admin.commerce.payment.transactions')" name="transaction">
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
      </el-tab-pane>

      <!-- 加密支付 -->
      <el-tab-pane :label="$t('admin.commerce.payment.crypto')" name="crypto">
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
      </el-tab-pane>

      <!-- 税务配置 -->
      <el-tab-pane :label="$t('admin.commerce.payment.taxConfigs')" name="tax">
        <AdminListShell
          :failed="taxFailed"
          :loading="taxLoading"
          :page="taxPage"
          :page-size="taxPageSize"
          :rows="taxList"
          :selectable="false"
          :total="taxTotal"
          @refresh="taxLoad"
          @reset="taxReset"
          @search="taxSearch"
          @page-change="onTaxPageChange"
          @size-change="onTaxSizeChange"
        >
          <template #filters>
            <el-form-item :label="$t('admin.commerce.payment.country')">
              <el-input v-model="taxQuery.country" clearable style="width: 100px" @keyup.enter="taxSearch()"/>
            </el-form-item>
            <el-form-item :label="$t('admin.commerce.payment.taxType')">
              <el-input v-model="taxQuery.tax_type" clearable style="width: 130px" @keyup.enter="taxSearch()"/>
            </el-form-item>
          </template>

          <template #actions>
            <el-button v-auth="'module_commerce:payment:create'" :icon="Plus" type="primary" @click="openTaxCreate">
              {{ $t('admin.commerce.payment.createTax') }}
            </el-button>
          </template>

          <el-table-column :label="$t('admin.commerce.payment.country')" prop="country" width="100"/>
          <el-table-column :label="$t('admin.commerce.payment.region')" min-width="130" prop="region"/>
          <el-table-column :label="$t('admin.commerce.payment.taxType')" min-width="130" prop="tax_type"/>
          <el-table-column :label="$t('admin.commerce.payment.rate')" align="right" prop="rate" width="100"/>
          <el-table-column :label="$t('admin.common.status')" align="center" width="100">
            <template #default="{ row }">
              <el-tag :type="(row as TaxConfigItem).is_active ? 'success' : 'info'" size="small">
                {{ (row as TaxConfigItem).is_active ? $t('admin.common.enabled') : $t('admin.common.disabled') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.common.actions')" fixed="right" width="150">
            <template #default="{ row }">
              <el-button v-auth="'module_commerce:payment:edit'" :icon="EditPen" link type="primary"
                         @click="openTaxEdit(row as TaxConfigItem)">
                {{ $t('admin.common.edit') }}
              </el-button>
              <el-button v-auth="'module_commerce:payment:delete'" :icon="Delete" link type="danger"
                         @click="onDeleteTax(row as TaxConfigItem)">
                {{ $t('admin.common.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </AdminListShell>
      </el-tab-pane>

      <!-- 税务试算 -->
      <el-tab-pane :label="$t('admin.commerce.payment.taxCalc')" name="taxCalc">
        <div class="admin-card tax-calc">
          <el-alert :closable="false" :title="$t('admin.commerce.payment.taxCalcHint')" class="mb-3"
                    show-icon type="info"/>
          <el-form :model="taxCalcForm" label-width="150px" style="max-width: 620px">
            <el-form-item :label="$t('admin.commerce.payment.amount')" required>
              <el-input-number v-model="taxCalcForm.amount" :min="0.01" :precision="2" style="width: 100%"/>
            </el-form-item>
            <el-form-item :label="$t('admin.commerce.payment.country')" required>
              <el-input v-model="taxCalcForm.country" maxlength="2" placeholder="CN"/>
            </el-form-item>
            <el-form-item :label="$t('admin.commerce.payment.region')">
              <el-input v-model="taxCalcForm.region"/>
            </el-form-item>
            <el-form-item :label="$t('admin.commerce.payment.taxType')">
              <el-input v-model="taxCalcForm.tax_type" placeholder="VAT / GST / Sales Tax"/>
            </el-form-item>
            <el-form-item :label="$t('admin.commerce.payment.taxCalcInclusive')">
              <el-switch v-model="taxCalcForm.inclusive"/>
            </el-form-item>
            <el-form-item :label="$t('admin.commerce.payment.taxCalcVat')">
              <el-input v-model="taxCalcForm.vat_number"
                        :placeholder="$t('admin.commerce.payment.taxCalcVatPlaceholder')"/>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Search" :loading="taxRateLoading" @click="resolveTaxRate">
                {{ $t('admin.commerce.payment.taxCalcResolve') }}
              </el-button>
              <el-button :loading="taxCalcSaving" type="primary" @click="submitTaxCalc">
                {{ $t('admin.commerce.payment.taxCalc') }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-descriptions v-if="taxRateResult" :column="3" :title="$t('admin.commerce.payment.taxCalcResolved')" border
                           class="mb-3">
            <el-descriptions-item :label="$t('admin.commerce.payment.country')">
              {{ taxRateResult.country || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.commerce.payment.region')">
              {{ taxRateResult.region || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.commerce.payment.taxType')">
              {{ taxRateResult.tax_type || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.commerce.payment.rate')">
              {{ taxRateResult.rate }}
            </el-descriptions-item>
          </el-descriptions>

          <el-descriptions v-if="taxCalcResult" :column="3" :title="$t('admin.commerce.payment.taxCalcResult')"
                           border>
            <el-descriptions-item :label="$t('admin.commerce.payment.taxCalcRate')">
              {{ taxCalcResult.rate }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.commerce.payment.taxCalcConfiguredRate')">
              {{ taxCalcResult.configured_rate }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.commerce.payment.taxCalcExempt')">
              {{ taxCalcResult.exempt ? $t('admin.common.yes') : $t('admin.common.no') }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.commerce.payment.taxCalcNet')">
              {{ taxCalcResult.net }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.commerce.payment.taxCalcTax')">
              {{ taxCalcResult.tax }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('admin.commerce.payment.taxCalcTotal')">
              {{ taxCalcResult.total }}
            </el-descriptions-item>
            <el-descriptions-item v-if="taxCalcResult.exemption_reason"
                                  :label="$t('admin.commerce.payment.taxCalcExemptReason')"
                                  :span="3">
              {{ taxCalcResult.exemption_reason }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </el-tab-pane>

      <!-- 税务报表 -->
      <el-tab-pane :label="$t('admin.commerce.payment.taxReport')" name="taxReport">
        <div class="admin-card">
          <el-alert :closable="false" :title="$t('admin.commerce.payment.taxReportHint')" class="mb-3"
                    show-icon type="info"/>
          <el-form :inline="true" class="admin-filter">
            <el-form-item :label="$t('admin.commerce.payment.taxReportDays')">
              <el-input-number v-model="taxReportQuery.days" :max="365" :min="1"/>
            </el-form-item>
            <el-form-item :label="$t('admin.commerce.payment.currency')">
              <el-input v-model="taxReportQuery.currency" maxlength="3" placeholder="USD" style="width: 110px"/>
            </el-form-item>
            <el-form-item>
              <el-button v-auth="'module_commerce:revenue:view'" :loading="taxReportLoading" type="primary"
                         @click="loadTaxReport">
                {{ $t('admin.commerce.payment.taxReportLoad') }}
              </el-button>
            </el-form-item>
          </el-form>

          <template v-if="taxReport">
            <div class="admin-toolbar">
              <span>{{ $t('admin.commerce.payment.taxReportPeriod', {n: taxReport.period_days}) }}</span>
              <span class="admin-toolbar__spacer"/>
              <span class="tax-report-statuses">{{ taxReport.settled_statuses.join(', ') }}</span>
            </div>

            <h4 class="tax-report-heading">{{ $t('admin.commerce.payment.taxReportConfigs') }}</h4>
            <el-table :data="taxReport.tax_configs" border stripe>
              <el-table-column :label="$t('admin.commerce.payment.country')" prop="country" width="100"/>
              <el-table-column :label="$t('admin.commerce.payment.region')" min-width="120" prop="region"/>
              <el-table-column :label="$t('admin.commerce.payment.taxType')" min-width="120" prop="tax_type"/>
              <el-table-column :label="$t('admin.commerce.payment.rate')" align="right" prop="rate" width="100"/>
              <el-table-column :label="$t('admin.commerce.payment.taxReportEffectiveFrom')" min-width="170"
                               prop="effective_from"/>
              <el-table-column :label="$t('admin.commerce.payment.taxReportEffectiveTo')" min-width="170"
                               prop="effective_to"/>
            </el-table>

            <h4 class="tax-report-heading">{{ $t('admin.commerce.payment.taxReportSettled') }}</h4>
            <el-table :data="taxReport.settled_transactions" border stripe>
              <el-table-column :label="$t('admin.commerce.payment.currency')" prop="currency" width="110"/>
              <el-table-column :label="$t('admin.commerce.payment.taxReportTransactions')" prop="transactions"
                               width="140"/>
              <el-table-column :label="$t('admin.commerce.payment.amount')" align="right" prop="amount"/>
            </el-table>
          </template>
          <AdminEmpty v-else :desc="$t('admin.commerce.payment.taxReportEmptyDesc')"
                      :title="$t('admin.commerce.payment.taxReportEmpty')"/>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 网关表单 -->
    <el-drawer v-model="gatewayFormVisible" :title="gatewayFormTitle" destroy-on-close size="520px">
      <el-form :model="gatewayForm" label-width="120px">
        <el-form-item :label="$t('admin.common.name')" required>
          <el-input v-model="gatewayForm.name"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.payment.provider')" required>
          <el-input v-model="gatewayForm.provider" :placeholder="$t('admin.commerce.payment.providerPlaceholder')"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.payment.currencies')">
          <el-input v-model="gatewayForm.supported_currencies"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.payment.configData')">
          <el-input v-model="gatewayForm.config_data_text" :autosize="{minRows: 4, maxRows: 10}"
                    :placeholder="$t('admin.commerce.payment.configDataHint')" type="textarea"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="gatewayForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="gatewayFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="gatewaySaving" type="primary" @click="submitGateway">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-drawer>

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

    <!-- 税务配置表单 -->
    <el-drawer v-model="taxFormVisible" :title="taxFormTitle" destroy-on-close size="480px">
      <el-form :model="taxForm" label-width="120px">
        <el-form-item :label="$t('admin.commerce.payment.country')" required>
          <el-input v-model="taxForm.country" maxlength="2" placeholder="CN"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.payment.region')">
          <el-input v-model="taxForm.region"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.payment.taxType')" required>
          <el-input v-model="taxForm.tax_type" placeholder="VAT / GST / Sales Tax"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.payment.rate')" required>
          <el-input-number v-model="taxForm.rate" :min="0" :precision="2" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.description')">
          <el-input v-model="taxForm.description"/>
        </el-form-item>
        <el-form-item :label="$t('admin.common.status')">
          <el-switch v-model="taxForm.is_active"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="taxFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="taxSaving" type="primary" @click="submitTax">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-drawer>

    <!-- 发起支付（联调） -->
    <el-dialog v-model="initiateVisible" :title="$t('admin.commerce.payment.initiate')" width="520px">
      <el-alert :closable="false" :title="$t('admin.commerce.payment.initiateHint')" class="mb-3"
                show-icon type="info"/>
      <el-form :model="initiateForm" label-width="100px">
        <el-form-item :label="$t('admin.commerce.payment.orderId')" required>
          <el-input v-model="initiateForm.order_id"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.payment.amountYuan')" required>
          <el-input-number v-model="initiateForm.amount" :min="0.01" :precision="2" style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.payment.subject')">
          <el-input v-model="initiateForm.subject"/>
        </el-form-item>
      </el-form>
      <pre v-if="initiateResult" class="initiate-result">{{ initiateResult }}</pre>
      <template #footer>
        <el-button @click="initiateVisible = false">{{ $t('admin.common.close') }}</el-button>
        <el-button :loading="initiateSaving" type="primary" @click="submitInitiate">
          {{ $t('admin.commerce.payment.initiate') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.tx-currency {
  margin-left: 4px;
  color: var(--el-text-color-secondary);
}

.mb-3 {
  margin-bottom: 12px;
}

.initiate-result {
  max-height: 220px;
  padding: 10px 12px;
  overflow: auto;
  font-family: Menlo, Consolas, monospace;
  font-size: 12px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.tax-calc {
  padding: var(--admin-gap-lg);
}

.tax-report-heading {
  margin: 16px 0 8px;
  font-size: 14px;
  font-weight: 600;
}

.tax-report-statuses {
  color: var(--el-text-color-secondary);
}
</style>
