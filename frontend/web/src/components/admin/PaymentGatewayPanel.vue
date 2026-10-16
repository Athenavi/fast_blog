<script lang="ts" setup>
/**
 * 支付配置 · 支付网关面板
 *
 * 从 `pages/commerce/payment.vue` 的「支付网关」标签页抽出：网关列表（筛选 / 新建 /
 * 编辑 / 删除），外加一个联调用的「发起支付」。
 *
 * `initiate` 那套状态原本挂在页面级（dialog 也在 `</el-tabs>` 之外），但它的触发按钮
 * 就在本标签页的工具栏里，所以跟着一起搬过来 —— 这样它不必把三个 ref 暴露给页面。
 *
 * 加载时机与原实现一致：`useAdminList` 默认挂载即加载（原页面既没有 `onMounted`
 * 也没有 `@tab-change`，六个标签页的数据本来就在挂载时一起拉）。
 */
import {Delete, EditPen, Plus, Promotion} from '@element-plus/icons-vue'
import {computed, reactive, ref} from 'vue'

import {paymentApi, type PaymentGatewayItem} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

const {t} = useI18n()

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

function openGatewayCreate(): void {
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

function openGatewayEdit(row: PaymentGatewayItem): void {
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

/** 解析 config_data 文本框；必须是 JSON 对象（数组或标量都算非法） */
function parseConfigData(text: string): Record<string, unknown> | null {
  const trimmed = text.trim()
  if (!trimmed) return null
  const parsed: unknown = JSON.parse(trimmed)
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    throw new Error('config_data must be a JSON object')
  }
  return parsed as Record<string, unknown>
}

async function submitGateway(): Promise<void> {
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

async function onDeleteGateway(row: PaymentGatewayItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.commerce.payment.deleteGatewayConfirm', {name: row.name || row.id}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await paymentApi.removeGateway(row.id)
  ElMessage.success(t('admin.common.delete'))
  await gatewayLoad()
}

// ---------------------------------------------------------------- 发起支付（联调用）
const initiateVisible = ref(false)
const initiateSaving = ref(false)
const initiateResult = ref<string>('')
const initiateForm = reactive({order_id: '', amount: undefined as number | undefined, subject: ''})

function openInitiate(): void {
  Object.assign(initiateForm, {order_id: '', amount: undefined, subject: ''})
  initiateResult.value = ''
  initiateVisible.value = true
}

async function submitInitiate(): Promise<void> {
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
</script>

<template>
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
</template>

<style scoped>
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
</style>
