<script lang="ts" setup>
/**
 * 订单管理（后台独立页，`/commerce/shop/orders`）
 *
 * 数据源：v3 `/api/v3/commerce/shop`
 *  - 订单列表 `listOrders`（按状态 / 用户筛选；后端按当前用户 `data_scope` 过滤）
 *  - 订单统计 `orderStats`（窗口内总数 / 各状态计数 / 已结算金额）
 *  - 订单详情 `getOrder`（含明细行）
 *  - 状态流转 `markPaid` / `markShipped` / `markDelivered` / `cancelOrder` / `refundOrder`
 *
 * 状态机：pending → paid → shipped → delivered（可 cancel）；取消仅限未发货，会回滚库存。
 * 退款要求订单已支付，权限走 `revenue:edit`；其余读写复用 `payment:view|edit`。
 * 金额单位是「元」。
 */
import {Box, Refresh, Van, View} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {formatDateTime} from '@/utils/format'
import {formatMoney} from '@/utils/money'
import {onMounted, reactive, ref} from 'vue'

import {type OrderDetail, type OrderItem, type OrderQuery, type OrderStats, shopApi} from '@/api'
import {useAdminList} from '@/composables/useAdminList'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.commerce.shop.ordersTitle',
  permission: 'module_commerce:payment:view',
})

const {t} = useI18n()

/** 订单状态机顺序（用于筛选下拉与统计卡片） */
const STATUS_ORDER: string[] = ['pending', 'paid', 'shipped', 'delivered', 'cancelled', 'refunded']

const STATUS_LABELS: Record<string, string> = {
  pending: 'admin.commerce.shop.statusPending',
  paid: 'admin.commerce.shop.statusPaid',
  shipped: 'admin.commerce.shop.statusShipped',
  delivered: 'admin.commerce.shop.statusDelivered',
  cancelled: 'admin.commerce.shop.statusCancelled',
  refunded: 'admin.commerce.shop.statusRefunded',
}

function statusLabel(status?: string | null): string {
  return t(STATUS_LABELS[String(status)] ?? 'admin.commerce.shop.statusUnknown')
}

function statusTag(status?: string | null): string {
  if (status === 'paid' || status === 'delivered') return 'success'
  if (status === 'shipped') return 'primary'
  if (status === 'pending') return 'warning'
  if (status === 'refunded') return 'warning'
  if (status === 'cancelled') return 'info'
  return 'info'
}

function paymentTag(status?: string | null): string {
  if (status === 'paid') return 'success'
  if (status === 'refunded') return 'warning'
  if (status === 'unpaid') return 'info'
  return 'info'
}

// ---------------------------------------------------------------- 订单列表
const orderState = useAdminList<OrderItem, OrderQuery>({
  fetcher: (params) => shopApi.listOrders(params),
  defaultQuery: {status: undefined, user_id: undefined},
  syncUrl: true,
})

const orders = orderState.rows
const orderLoading = orderState.loading
const orderFailed = orderState.failed
const orderTotal = orderState.total
const orderPage = orderState.page
const orderPageSize = orderState.pageSize
const orderQuery = orderState.query
const orderSearch = orderState.search
const orderReset = orderState.reset
const orderReload = orderState.reload
const onOrderPageChange = orderState.onPageChange
const onOrderSizeChange = orderState.onSizeChange

// ---------------------------------------------------------------- 订单统计
const stats = ref<OrderStats | null>(null)
const statsLoading = ref(false)
const statsDays = ref(30)

async function loadStats(): Promise<void> {
  statsLoading.value = true
  try {
    stats.value = await shopApi.orderStats(statsDays.value)
  } finally {
    statsLoading.value = false
  }
}

// ---------------------------------------------------------------- 订单详情
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<OrderDetail | null>(null)

async function openDetail(row: OrderItem): Promise<void> {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await shopApi.getOrder(row.id)
  } finally {
    detailLoading.value = false
  }
}

// ---------------------------------------------------------------- 状态流转
type OrderAction = 'pay' | 'ship' | 'deliver' | 'cancel' | 'refund'

const ACTION_TITLES: Record<OrderAction, string> = {
  pay: 'admin.commerce.shop.actionPayTitle',
  ship: 'admin.commerce.shop.actionShipTitle',
  deliver: 'admin.commerce.shop.actionDeliverTitle',
  cancel: 'admin.commerce.shop.actionCancelTitle',
  refund: 'admin.commerce.shop.actionRefundTitle',
}

const actionVisible = ref(false)
const actionSaving = ref(false)
const actionType = ref<OrderAction>('pay')
const actionTarget = ref<OrderItem | null>(null)
const payForm = reactive({transaction_id: ''})
const refundForm = reactive({reason: '', restore_stock: true})

function openAction(row: OrderItem, action: OrderAction): void {
  actionTarget.value = row
  actionType.value = action
  payForm.transaction_id = ''
  refundForm.reason = ''
  refundForm.restore_stock = true
  actionVisible.value = true
}

async function submitAction(): Promise<void> {
  if (!actionTarget.value) return
  const target = actionTarget.value
  if (actionType.value === 'cancel') {
    try {
      await ElMessageBox.confirm(
        t('admin.commerce.shop.cancelConfirm', {no: target.order_number}),
        t('admin.common.notice'),
        {type: 'warning'},
      )
    } catch {
      return
    }
  }
  actionSaving.value = true
  try {
    if (actionType.value === 'pay') {
      await shopApi.markPaid(target.id, payForm.transaction_id.trim() || undefined)
    } else if (actionType.value === 'ship') {
      await shopApi.markShipped(target.id)
    } else if (actionType.value === 'deliver') {
      await shopApi.markDelivered(target.id)
    } else if (actionType.value === 'cancel') {
      await shopApi.cancelOrder(target.id)
    } else {
      await shopApi.refundOrder(target.id, {
        restore_stock: refundForm.restore_stock,
        reason: refundForm.reason.trim() || null,
      })
    }
    ElMessage.success(t('admin.commerce.shop.actionDone'))
    actionVisible.value = false
    await Promise.all([orderReload(), loadStats()])
  } finally {
    actionSaving.value = false
  }
}

onMounted(loadStats)
</script>

<template>
  <AdminPage
    :desc="$t('admin.commerce.shop.ordersDesc')"
    :title="$t('admin.commerce.shop.ordersTitle')"
  >
    <!-- 订单统计 -->
    <el-card class="mb-4" shadow="never">
      <template #header>
        <div class="flex items-center justify-between">
          <span>{{ $t('admin.commerce.shop.statsTitle') }}</span>
          <div class="flex items-center gap-2">
            <el-select v-model="statsDays" style="width: 120px" @change="loadStats()">
              <el-option :label="$t('admin.commerce.shop.days7')" :value="7"/>
              <el-option :label="$t('admin.commerce.shop.days30')" :value="30"/>
              <el-option :label="$t('admin.commerce.shop.days90')" :value="90"/>
            </el-select>
            <el-button :icon="Refresh" :loading="statsLoading" @click="loadStats()">
              {{ $t('admin.common.refresh') }}
            </el-button>
          </div>
        </div>
      </template>

      <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.commerce.shop.totalOrders') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.total_orders ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.commerce.shop.settledAmount') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ formatMoney(stats?.settled_amount) }}</p>
        </el-card>
        <el-card v-for="s in STATUS_ORDER" :key="s" shadow="never">
          <p class="text-xs text-fg-muted">{{ statusLabel(s) }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.by_status?.[s] ?? 0 }}</p>
        </el-card>
      </div>
    </el-card>

    <!-- 订单列表 -->
    <AdminListShell
      :failed="orderFailed"
      :loading="orderLoading"
      :page="orderPage"
      :page-size="orderPageSize"
      :rows="orders"
      :selectable="false"
      :total="orderTotal"
      @refresh="orderReload"
      @reset="orderReset"
      @search="orderSearch"
      @page-change="onOrderPageChange"
      @size-change="onOrderSizeChange"
    >
      <template #filters>
        <el-form-item :label="$t('admin.common.status')">
          <el-select
            v-model="orderQuery.status"
            :placeholder="$t('admin.common.all')"
            clearable
            style="width: 140px"
            @change="orderSearch()"
          >
            <el-option v-for="s in STATUS_ORDER" :key="s" :label="statusLabel(s)" :value="s"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.commerce.shop.userId')">
          <el-input-number v-model="orderQuery.user_id" :min="1" controls-position="right"/>
        </el-form-item>
      </template>

      <el-table-column
        :label="$t('admin.commerce.shop.orderNumber')"
        min-width="180"
        prop="order_number"
        show-overflow-tooltip
      />
      <el-table-column :label="$t('admin.commerce.shop.userId')" prop="user_id" width="90"/>
      <el-table-column :label="$t('admin.commerce.shop.totalAmount')" align="right" width="130">
        <template #default="{ row }">{{ formatMoney((row as OrderItem).total_amount) }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.status')" align="center" width="110">
        <template #default="{ row }">
          <el-tag :type="statusTag((row as OrderItem).status)" size="small">
            {{ statusLabel((row as OrderItem).status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.commerce.shop.paymentStatus')" align="center" width="110">
        <template #default="{ row }">
          <el-tag :type="paymentTag((row as OrderItem).payment_status)" size="small">
            {{ (row as OrderItem).payment_status || '-' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        :label="$t('admin.commerce.shop.paymentMethod')"
        min-width="120"
        prop="payment_method"
        show-overflow-tooltip
      />
      <el-table-column :label="$t('admin.common.createdAt')" width="170">
        <template #default="{ row }">{{ formatDateTime((row as OrderItem).created_at) }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.common.actions')" fixed="right" width="360">
        <template #default="{ row }">
          <el-button :icon="View" link type="primary" @click="openDetail(row as OrderItem)">
            {{ $t('admin.commerce.shop.detail') }}
          </el-button>
          <el-button
            v-if="(row as OrderItem).status === 'pending'"
            v-auth="'module_commerce:payment:edit'"
            link
            type="success"
            @click="openAction(row as OrderItem, 'pay')"
          >
            {{ $t('admin.commerce.shop.actionPay') }}
          </el-button>
          <el-button
            v-if="(row as OrderItem).status === 'paid'"
            v-auth="'module_commerce:payment:edit'"
            :icon="Van"
            link
            type="primary"
            @click="openAction(row as OrderItem, 'ship')"
          >
            {{ $t('admin.commerce.shop.actionShip') }}
          </el-button>
          <el-button
            v-if="(row as OrderItem).status === 'shipped'"
            v-auth="'module_commerce:payment:edit'"
            :icon="Box"
            link
            type="success"
            @click="openAction(row as OrderItem, 'deliver')"
          >
            {{ $t('admin.commerce.shop.actionDeliver') }}
          </el-button>
          <el-button
            v-if="['pending', 'paid'].includes(String((row as OrderItem).status))"
            v-auth="'module_commerce:payment:edit'"
            link
            type="danger"
            @click="openAction(row as OrderItem, 'cancel')"
          >
            {{ $t('admin.commerce.shop.actionCancel') }}
          </el-button>
          <el-button
            v-if="['paid', 'shipped', 'delivered'].includes(String((row as OrderItem).status))"
            v-auth="'module_commerce:revenue:edit'"
            link
            type="warning"
            @click="openAction(row as OrderItem, 'refund')"
          >
            {{ $t('admin.commerce.shop.actionRefund') }}
          </el-button>
        </template>
      </el-table-column>
    </AdminListShell>

    <!-- 订单详情 -->
    <el-drawer v-model="detailVisible" :title="$t('admin.commerce.shop.detailTitle')" size="640px">
      <div v-loading="detailLoading">
        <el-descriptions v-if="detail" :column="1" border>
          <el-descriptions-item :label="$t('admin.commerce.shop.orderNumber')">
            {{ detail?.order_number }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.commerce.shop.userId')">
            {{ detail?.user_id ?? '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.common.status')">
            {{ statusLabel(detail?.status) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.commerce.shop.paymentStatus')">
            {{ detail?.payment_status || '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.commerce.shop.totalAmount')">
            {{ formatMoney(detail?.total_amount) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.commerce.shop.shippingAmount')">
            {{ formatMoney(detail?.shipping_amount) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.commerce.shop.discountAmount')">
            {{ formatMoney(detail?.discount_amount) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.commerce.shop.paymentMethod')">
            {{ detail?.payment_method || '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.commerce.shop.transactionId')">
            {{ detail?.transaction_id || '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.commerce.shop.shippingAddress')">
            {{ detail?.shipping_address || '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.commerce.shop.notes')">
            {{ detail?.notes || '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.common.createdAt')">
            {{ formatDateTime(detail?.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.commerce.shop.paidAt')">
            {{ formatDateTime(detail?.paid_at) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.commerce.shop.shippedAt')">
            {{ formatDateTime(detail?.shipped_at) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.commerce.shop.deliveredAt')">
            {{ formatDateTime(detail?.delivered_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <el-table v-if="detail" :data="detail.items" border class="mt-4" stripe>
          <el-table-column
            :label="$t('admin.commerce.shop.productName')"
            min-width="160"
            prop="product_name"
            show-overflow-tooltip
          />
          <el-table-column :label="$t('admin.commerce.shop.quantity')" align="center" prop="quantity" width="90"/>
          <el-table-column :label="$t('admin.commerce.shop.unitPrice')" align="right" width="120">
            <template #default="{ row }">{{ formatMoney(row.unit_price) }}</template>
          </el-table-column>
          <el-table-column :label="$t('admin.commerce.shop.lineTotal')" align="right" width="120">
            <template #default="{ row }">{{ formatMoney(row.total_price) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>

    <!-- 状态流转 -->
    <el-dialog v-model="actionVisible" :title="$t(ACTION_TITLES[actionType])" width="460px">
      <el-form label-width="120px">
        <el-form-item :label="$t('admin.commerce.shop.orderNumber')">
          <span>{{ actionTarget?.order_number }}</span>
        </el-form-item>
        <el-form-item v-if="actionType === 'pay'" :label="$t('admin.commerce.shop.transactionId')">
          <el-input
            v-model="payForm.transaction_id"
            :placeholder="$t('admin.commerce.shop.transactionPlaceholder')"
          />
        </el-form-item>
        <template v-if="actionType === 'refund'">
          <el-form-item :label="$t('admin.commerce.shop.refundReason')">
            <el-input v-model="refundForm.reason" :rows="2" type="textarea"/>
          </el-form-item>
          <el-form-item :label="$t('admin.commerce.shop.restoreStock')">
            <el-switch v-model="refundForm.restore_stock"/>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="actionVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="actionSaving" type="primary" @click="submitAction()">
          {{ $t('admin.common.submit') }}
        </el-button>
      </template>
    </el-dialog>
  </AdminPage>
</template>
