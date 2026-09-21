<script lang="ts" setup>
/**
 * 打赏与收益（`/tipping`）
 *
 * 数据源：v3 `/api/v3/commerce/tipping`
 *  - 收益概要 `earnings`：`available` = 已结算 − 已占用（待审 + 已批准未打款），才是可提现额；
 *  - 提现是**人工打款**：`pending → approved / rejected → paid`，置 `paid` 时由管理员登记打款流水号；
 *  - 打赏收入只有在网关回调**验签通过**后才计入（pending 的不对外展示、也不算收益）。
 *
 * 金额单位是**分**，展示时统一换算成元。
 */
import {
  type TipConfig,
  type TipEarnings,
  type TipItem,
  tippingApi,
  type TipRankingItem,
  type WithdrawalItem,
} from '@/api'
import {formatDateTime} from '@/utils/format'

definePageMeta({layout: 'default', middleware: 'auth', title: 'tipping.title'})

const {t} = useI18n()

const PAGE_SIZE = 20

type TabKey = 'received' | 'mine' | 'withdrawals' | 'ranking'

const activeTab = ref<TabKey>('received')
const tabs = computed<Array<{ key: TabKey; label: string }>>(() => [
  {key: 'received', label: t('tipping.tabReceived')},
  {key: 'mine', label: t('tipping.tabMine')},
  {key: 'withdrawals', label: t('tipping.tabWithdrawals')},
  {key: 'ranking', label: t('tipping.tabRanking')},
])

const config = ref<TipConfig | null>(null)
const earnings = ref<TipEarnings | null>(null)

const received = ref<TipItem[]>([])
const receivedTotal = ref(0)
const receivedPage = ref(1)

const sent = ref<TipItem[]>([])
const sentTotal = ref(0)
const sentPage = ref(1)

const withdrawals = ref<WithdrawalItem[]>([])
const withdrawalsTotal = ref(0)
const withdrawalsPage = ref(1)

const ranking = ref<TipRankingItem[]>([])

const loading = ref(true)
const failed = ref(false)
const busy = ref(false)
const notice = ref('')
const error = ref('')

const withdrawing = ref(false)
const withdrawForm = reactive({amount: '', method: '', account: '', account_name: ''})

/** 分 → 元（保留两位） */
function yuan(cents?: number | null): string {
  return ((cents ?? 0) / 100).toFixed(2)
}

/** 分 → 元，去掉无意义的小数位（用于预设金额展示） */
function shortYuan(cents?: number | null): string {
  const value = (cents ?? 0) / 100
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}

const TIP_STATUS_LABELS: Record<string, string> = {
  pending: 'tipping.tipStatusPending',
  paid: 'tipping.tipStatusPaid',
  failed: 'tipping.tipStatusFailed',
  refunded: 'tipping.tipStatusRefunded',
}

const WITHDRAWAL_STATUS_LABELS: Record<string, string> = {
  pending: 'tipping.wdStatusPending',
  approved: 'tipping.wdStatusApproved',
  rejected: 'tipping.wdStatusRejected',
  paid: 'tipping.wdStatusPaid',
}

const METHOD_LABELS: Record<string, string> = {
  alipay: 'tipping.methodAlipay',
  wechat: 'tipping.methodWechat',
  bank: 'tipping.methodBank',
}

function tipStatusLabel(status?: string | null): string {
  return t(TIP_STATUS_LABELS[String(status)] ?? 'tipping.tipStatusUnknown')
}

function withdrawalStatusLabel(status?: string | null): string {
  return t(WITHDRAWAL_STATUS_LABELS[String(status)] ?? 'tipping.wdStatusUnknown')
}

function methodLabel(method?: string | null): string {
  const key = METHOD_LABELS[String(method)]
  return key ? t(key) : String(method ?? '-')
}

function statusVariant(status?: string | null): 'default' | 'success' | 'secondary' | 'danger' | 'warning' {
  if (status === 'paid' || status === 'approved') return 'success'
  if (status === 'pending') return 'warning'
  if (status === 'failed' || status === 'rejected') return 'danger'
  return 'secondary'
}

/** 提现实际到账（扣除手续费后的估算，服务端为准） */
const withdrawPreview = computed(() => {
  const cents = Math.round(Number(withdrawForm.amount || 0) * 100)
  const rate = config.value?.withdraw_fee_rate ?? 0
  if (!cents) return ''
  const fee = Math.round(cents * rate)
  return t('tipping.withdrawFeeHint', {
    fee: yuan(fee),
    actual: yuan(cents - fee),
    rate: Math.round(rate * 100),
  })
})

async function loadSummary(): Promise<void> {
  const [cfg, summary] = await Promise.all([
    tippingApi.config().catch(() => null),
    tippingApi.earnings(),
  ])
  config.value = cfg
  earnings.value = summary
  if (cfg && !withdrawForm.method) withdrawForm.method = cfg.withdraw_methods[0] ?? ''
}

async function loadTab(): Promise<void> {
  if (activeTab.value === 'received') {
    const result = await tippingApi.received({page: receivedPage.value, page_size: PAGE_SIZE})
    received.value = result.items ?? []
    receivedTotal.value = result.total ?? 0
  } else if (activeTab.value === 'mine') {
    const result = await tippingApi.mine({page: sentPage.value, page_size: PAGE_SIZE})
    sent.value = result.items ?? []
    sentTotal.value = result.total ?? 0
  } else if (activeTab.value === 'withdrawals') {
    const result = await tippingApi.myWithdrawals({page: withdrawalsPage.value, page_size: PAGE_SIZE})
    withdrawals.value = result.items ?? []
    withdrawalsTotal.value = result.total ?? 0
  } else {
    ranking.value = (await tippingApi.ranking(20)) ?? []
  }
}

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    await Promise.all([loadSummary(), loadTab()])
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

async function switchTab(key: TabKey): Promise<void> {
  activeTab.value = key
  loading.value = true
  try {
    await loadTab()
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

async function submitWithdraw(): Promise<void> {
  notice.value = ''
  error.value = ''
  const cents = Math.round(Number(withdrawForm.amount || 0) * 100)
  if (!cents) {
    error.value = t('tipping.withdrawAmountRequired')
    return
  }
  if (config.value && cents < config.value.min_withdraw) {
    error.value = t('tipping.withdrawTooSmall', {min: shortYuan(config.value.min_withdraw)})
    return
  }
  if (earnings.value && cents > earnings.value.available) {
    error.value = t('tipping.withdrawTooMuch', {available: yuan(earnings.value.available)})
    return
  }
  if (!withdrawForm.method || !withdrawForm.account.trim() || !withdrawForm.account_name.trim()) {
    error.value = t('tipping.withdrawAccountRequired')
    return
  }

  withdrawing.value = true
  try {
    await tippingApi.withdraw({
      amount: cents,
      method: withdrawForm.method,
      account: withdrawForm.account.trim(),
      account_name: withdrawForm.account_name.trim(),
    })
    notice.value = t('tipping.withdrawSuccess')
    withdrawForm.amount = ''
    withdrawForm.account = ''
    withdrawForm.account_name = ''
    activeTab.value = 'withdrawals'
    await Promise.all([loadSummary(), loadTab()])
  } catch (thrown) {
    error.value = thrown instanceof Error ? thrown.message : t('common.networkError')
  } finally {
    withdrawing.value = false
  }
}

function goPage(kind: TabKey, next: number): void {
  if (next < 1) return
  if (kind === 'received') {
    if ((next - 1) * PAGE_SIZE >= receivedTotal.value) return
    receivedPage.value = next
  } else if (kind === 'mine') {
    if ((next - 1) * PAGE_SIZE >= sentTotal.value) return
    sentPage.value = next
  } else {
    if ((next - 1) * PAGE_SIZE >= withdrawalsTotal.value) return
    withdrawalsPage.value = next
  }
  void loadTab()
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-wide px-4 py-10">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('tipping.title') }}</h1>
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('tipping.subtitle') }}</p>
      </div>
      <Button :disabled="loading" size="sm" variant="outline" @click="load()">
        <Icon class="h-4 w-4" name="refresh-cw"/>
        {{ $t('common.refresh') }}
      </Button>
    </div>

    <p v-if="notice" class="mt-5 rounded-card border border-line bg-surface-soft px-4 py-2.5 text-sm text-fg">
      {{ notice }}
    </p>
    <p v-if="error" class="mt-5 rounded-card border border-danger/40 bg-surface-soft px-4 py-2.5 text-sm text-danger">
      {{ error }}
    </p>

    <div v-if="loading && !earnings" class="mt-6 space-y-3">
      <Skeleton class="h-24 w-full"/>
      <Skeleton class="h-60 w-full"/>
    </div>

    <ErrorState
      v-else-if="failed && !earnings"
      :description="$t('common.networkError')"
      :title="$t('tipping.loadFailed')"
      @retry="load()"
    />

    <template v-else>
      <!-- 收益概览 -->
      <section class="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div class="rounded-card border border-line bg-surface p-4">
          <p class="text-xs text-fg-muted">{{ $t('tipping.available') }}</p>
          <p class="mt-1 text-xl font-semibold text-primary">¥{{ yuan(earnings?.available) }}</p>
        </div>
        <div class="rounded-card border border-line bg-surface p-4">
          <p class="text-xs text-fg-muted">{{ $t('tipping.totalReceived') }}</p>
          <p class="mt-1 text-xl font-semibold text-fg">¥{{ yuan(earnings?.total_received) }}</p>
        </div>
        <div class="rounded-card border border-line bg-surface p-4">
          <p class="text-xs text-fg-muted">{{ $t('tipping.pendingAmount') }}</p>
          <p class="mt-1 text-xl font-semibold text-fg">¥{{ yuan(earnings?.pending) }}</p>
        </div>
        <div class="rounded-card border border-line bg-surface p-4">
          <p class="text-xs text-fg-muted">{{ $t('tipping.withdrawn') }}</p>
          <p class="mt-1 text-xl font-semibold text-fg">¥{{ yuan(earnings?.withdrawn) }}</p>
        </div>
      </section>

      <!-- 提现 -->
      <section class="mt-4 rounded-card border border-line bg-surface p-5">
        <h2 class="text-base font-semibold text-fg">{{ $t('tipping.withdrawTitle') }}</h2>
        <p class="mt-1 text-xs text-fg-subtle">
          {{
            $t('tipping.withdrawHint', {
              min: shortYuan(config?.min_withdraw),
              available: yuan(earnings?.available),
            })
          }}
        </p>

        <div class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('tipping.withdrawAmount') }}</label>
            <Input v-model="withdrawForm.amount" :placeholder="$t('tipping.withdrawAmountPlaceholder')"
                   inputmode="decimal"/>
          </div>
          <div>
            <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('tipping.withdrawMethod') }}</label>
            <select
              v-model="withdrawForm.method"
              class="w-full rounded-control border border-line bg-surface px-3 py-2 text-sm text-fg"
            >
              <option v-for="item in config?.withdraw_methods ?? []" :key="item" :value="item">
                {{ methodLabel(item) }}
              </option>
            </select>
          </div>
          <div>
            <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('tipping.withdrawAccount') }}</label>
            <Input v-model="withdrawForm.account" :placeholder="$t('tipping.withdrawAccountPlaceholder')"/>
          </div>
          <div>
            <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('tipping.withdrawAccountName') }}</label>
            <Input v-model="withdrawForm.account_name"/>
          </div>
        </div>

        <div class="mt-3 flex flex-wrap items-center justify-between gap-2">
          <span class="text-xs text-fg-subtle">{{ withdrawPreview }}</span>
          <Button :disabled="withdrawing" size="sm" @click="submitWithdraw">
            <Icon v-if="withdrawing" class="h-4 w-4 animate-spin" name="loader-circle"/>
            <Icon v-else class="h-4 w-4" name="wallet"/>
            {{ $t('tipping.withdrawSubmit') }}
          </Button>
        </div>
      </section>

      <!-- 列表 -->
      <div class="mt-8 flex flex-wrap gap-2">
        <Button
          v-for="tab in tabs"
          :key="tab.key"
          :variant="activeTab === tab.key ? 'default' : 'outline'"
          size="sm"
          @click="switchTab(tab.key)"
        >
          {{ tab.label }}
        </Button>
      </div>

      <div class="mt-4">
        <div v-if="loading" class="space-y-3">
          <Skeleton v-for="i in 4" :key="i" class="h-16 w-full"/>
        </div>

        <!-- 我收到的 -->
        <template v-else-if="activeTab === 'received'">
          <p v-if="!received.length" class="py-10 text-center text-sm text-fg-muted">
            {{ $t('tipping.emptyReceived') }}
          </p>
          <ul v-else class="divide-y divide-line rounded-card border border-line bg-surface">
            <li v-for="item in received" :key="item.id"
                class="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
              <div class="min-w-0">
                <p class="flex items-center gap-2 text-sm font-medium text-fg">
                  <span class="text-primary">¥{{ item.amount_yuan }}</span>
                  <Badge :variant="statusVariant(item.status)">{{ tipStatusLabel(item.status) }}</Badge>
                </p>
                <p class="mt-0.5 truncate text-xs text-fg-muted">
                  {{ $t('tipping.fromUser', {name: item.username || $t('tipping.userFallback', {id: item.user_id})}) }}
                  <span v-if="item.article_id"> · {{ $t('tipping.articleRef', {id: item.article_id}) }}</span>
                </p>
                <p v-if="item.message" class="mt-0.5 truncate text-xs text-fg-subtle">{{ item.message }}</p>
              </div>
              <span class="text-xs text-fg-subtle">{{ formatDateTime(item.paid_at || item.created_at) }}</span>
            </li>
          </ul>
          <div v-if="receivedTotal > PAGE_SIZE" class="mt-4 flex items-center justify-between text-sm text-fg-muted">
            <span>{{ $t('tipping.total', {n: receivedTotal}) }}</span>
            <div class="flex gap-2">
              <Button :disabled="receivedPage <= 1" size="sm" variant="outline"
                      @click="goPage('received', receivedPage - 1)">
                {{ $t('fans.prevPage') }}
              </Button>
              <Button :disabled="receivedPage * PAGE_SIZE >= receivedTotal" size="sm" variant="outline"
                      @click="goPage('received', receivedPage + 1)">
                {{ $t('fans.nextPage') }}
              </Button>
            </div>
          </div>
        </template>

        <!-- 我发出的 -->
        <template v-else-if="activeTab === 'mine'">
          <p v-if="!sent.length" class="py-10 text-center text-sm text-fg-muted">
            {{ $t('tipping.emptyMine') }}
          </p>
          <ul v-else class="divide-y divide-line rounded-card border border-line bg-surface">
            <li v-for="item in sent" :key="item.id" class="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
              <div class="min-w-0">
                <p class="flex items-center gap-2 text-sm font-medium text-fg">
                  <span class="text-primary">¥{{ item.amount_yuan }}</span>
                  <Badge :variant="statusVariant(item.status)">{{ tipStatusLabel(item.status) }}</Badge>
                </p>
                <p class="mt-0.5 truncate text-xs text-fg-muted">
                  {{
                    $t('tipping.toUser', {name: item.author_name || $t('tipping.userFallback', {id: item.author_id})})
                  }}
                  <span v-if="item.article_id"> · {{ $t('tipping.articleRef', {id: item.article_id}) }}</span>
                </p>
                <p v-if="item.order_no" class="mt-0.5 truncate text-xs text-fg-subtle">
                  {{ $t('tipping.orderNo') }}: {{ item.order_no }}
                </p>
              </div>
              <span class="text-xs text-fg-subtle">{{ formatDateTime(item.paid_at || item.created_at) }}</span>
            </li>
          </ul>
          <div v-if="sentTotal > PAGE_SIZE" class="mt-4 flex items-center justify-between text-sm text-fg-muted">
            <span>{{ $t('tipping.total', {n: sentTotal}) }}</span>
            <div class="flex gap-2">
              <Button :disabled="sentPage <= 1" size="sm" variant="outline" @click="goPage('mine', sentPage - 1)">
                {{ $t('fans.prevPage') }}
              </Button>
              <Button :disabled="sentPage * PAGE_SIZE >= sentTotal" size="sm" variant="outline"
                      @click="goPage('mine', sentPage + 1)">
                {{ $t('fans.nextPage') }}
              </Button>
            </div>
          </div>
        </template>

        <!-- 提现记录 -->
        <template v-else-if="activeTab === 'withdrawals'">
          <p v-if="!withdrawals.length" class="py-10 text-center text-sm text-fg-muted">
            {{ $t('tipping.emptyWithdrawals') }}
          </p>
          <ul v-else class="divide-y divide-line rounded-card border border-line bg-surface">
            <li v-for="item in withdrawals" :key="item.id" class="px-4 py-3">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="flex items-center gap-2 text-sm font-medium text-fg">
                  <span>¥{{ yuan(item.amount) }}</span>
                  <Badge :variant="statusVariant(item.status)">{{ withdrawalStatusLabel(item.status) }}</Badge>
                  <span class="text-xs font-normal text-fg-subtle">{{ methodLabel(item.method) }}</span>
                </p>
                <span class="text-xs text-fg-subtle">{{ formatDateTime(item.created_at) }}</span>
              </div>
              <p class="mt-1 text-xs text-fg-muted">
                {{ $t('tipping.feeAndActual', {fee: yuan(item.fee), actual: yuan(item.actual_amount)}) }}
              </p>
              <p v-if="item.review_comment" class="mt-1 text-xs text-fg-subtle">{{ item.review_comment }}</p>
              <p v-if="item.transaction_id" class="mt-1 text-xs text-fg-subtle">
                {{ $t('tipping.paidTransaction', {no: item.transaction_id}) }}
              </p>
            </li>
          </ul>
          <div v-if="withdrawalsTotal > PAGE_SIZE" class="mt-4 flex items-center justify-between text-sm text-fg-muted">
            <span>{{ $t('tipping.total', {n: withdrawalsTotal}) }}</span>
            <div class="flex gap-2">
              <Button :disabled="withdrawalsPage <= 1" size="sm" variant="outline"
                      @click="goPage('withdrawals', withdrawalsPage - 1)">
                {{ $t('fans.prevPage') }}
              </Button>
              <Button :disabled="withdrawalsPage * PAGE_SIZE >= withdrawalsTotal" size="sm" variant="outline"
                      @click="goPage('withdrawals', withdrawalsPage + 1)">
                {{ $t('fans.nextPage') }}
              </Button>
            </div>
          </div>
        </template>

        <!-- 排行 -->
        <template v-else>
          <p v-if="!ranking.length" class="py-10 text-center text-sm text-fg-muted">
            {{ $t('tipping.emptyRanking') }}
          </p>
          <ol v-else class="divide-y divide-line rounded-card border border-line bg-surface">
            <li v-for="row in ranking" :key="row.author_id" class="flex items-center gap-3 px-4 py-3">
              <span class="w-6 shrink-0 text-sm font-semibold text-fg-subtle">{{ row.rank }}</span>
              <span
                class="flex h-9 w-9 shrink-0 items-center justify-center rounded-pill bg-surface-soft text-fg-muted">
                <Icon class="h-4 w-4" name="user"/>
              </span>
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium text-fg">
                  {{ row.username || $t('tipping.userFallback', {id: row.author_id}) }}
                </p>
                <p class="text-xs text-fg-subtle">{{ $t('tipping.tipCount', {n: row.count}) }}</p>
              </div>
              <span class="text-sm font-semibold text-primary">¥{{ yuan(row.total) }}</span>
            </li>
          </ol>
        </template>
      </div>
    </template>
  </div>
</template>
