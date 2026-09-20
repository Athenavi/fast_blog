<script lang="ts" setup>
/**
 * 积分中心（`/points`）
 *
 * - 我的积分：余额 / 累计获得 / 累计消耗 / **每日签到**（幂等，一天一次）/ 流水；
 * - 公开只读：排行榜、积分规则、兑换项；
 * - **兑换真实发放**：选中套餐后调 `/exchange`，服务端在同一事务里扣分 + 写流水 + 开通订阅；
 * - 管理员（`module_gamification:points:view`）额外可看统计、改规则、加减分。
 *
 * 注意：v3 **没有** v2 的 `record-action`（前端自报动作加分 = 可任意刷分），
 * 所以本页面不存在任何「上报行为换积分」的入口。
 */
import {
  type ExchangeRule,
  type LeaderboardItem,
  type PointsAccount,
  pointsApi,
  type PointsRule,
  type PointsStats,
  type PointsTransaction,
  vipApi,
  type VipPlanItem,
} from '@/api'
import {formatDateTime} from '@/utils/format'
import {useUserStore} from '@/store/modules/user'

definePageMeta({layout: 'default', middleware: 'auth', title: 'points.title'})

const {t} = useI18n()
const userStore = useUserStore()

/** 管理端（统计 / 规则 / 加减分）需要查看权限 */
const canManage = computed(() => userStore.hasPermission('module_gamification:points:view'))

type TabKey = 'history' | 'leaderboard' | 'rules' | 'manage'
const tabs = computed<Array<{ key: TabKey; label: string }>>(() => {
  const items: Array<{ key: TabKey; label: string }> = [
    {key: 'history', label: t('points.tabHistory')},
    {key: 'leaderboard', label: t('points.tabLeaderboard')},
    {key: 'rules', label: t('points.tabRules')},
  ]
  if (canManage.value) items.push({key: 'manage', label: t('points.tabManage')})
  return items
})
const activeTab = ref<TabKey>('history')

const account = ref<PointsAccount | null>(null)
const transactions = ref<PointsTransaction[]>([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 20

const board = ref<LeaderboardItem[]>([])
const rules = ref<PointsRule[]>([])
const exchangeRules = ref<ExchangeRule[]>([])
const stats = ref<PointsStats | null>(null)
const plans = ref<VipPlanItem[]>([])
const selectedPlanId = ref<number | null>(null)

const loading = ref(false)
const failed = ref(false)
const busy = ref(false)
const notice = ref('')
const error = ref('')

/** 规则行 = 规则本体 + 编辑缓冲（放在同一个对象里，模板 v-model 就不会碰到可空下标） */
interface RuleRow {
  rule: PointsRule
  draft: { points: number; daily_limit: number; is_active: boolean; sort_order: number }
}

const ruleRows = ref<RuleRow[]>([])
const adjustForm = reactive({user_id: '', amount: '', reason: ''})

function flash(message: string): void {
  notice.value = message
  error.value = ''
}

function complain(thrown: unknown): void {
  error.value = thrown instanceof Error ? thrown.message : t('common.networkError')
  notice.value = ''
}

async function loadAccount(): Promise<void> {
  account.value = await pointsApi.mine()
}

async function loadHistory(): Promise<void> {
  const result = await pointsApi.history({page: page.value, page_size: PAGE_SIZE})
  transactions.value = result.items ?? []
  total.value = result.total ?? 0
}

async function loadPublic(): Promise<void> {
  const [boardRows, rulesRaw, exchangeRows] = await Promise.all([
    pointsApi.leaderboard(20),
    pointsApi.rules(),
    pointsApi.exchangeRules(),
  ])
  board.value = boardRows ?? []
  rules.value = rulesRaw ?? []
  exchangeRules.value = exchangeRows ?? []
  ruleRows.value = (rulesRaw ?? []).map((rule) => ({
    rule,
    draft: {
      points: rule.points ?? 0,
      daily_limit: rule.daily_limit ?? 0,
      is_active: rule.is_active,
      sort_order: rule.sort_order ?? 0,
    },
  }))
}

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    await Promise.all([loadAccount(), loadHistory(), loadPublic()])
    if (canManage.value) {
      stats.value = await pointsApi.stats().catch(() => null)
    }
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

async function checkin(): Promise<void> {
  busy.value = true
  try {
    const result = await pointsApi.checkin()
    account.value = result
    flash(t('points.checkinSuccess', {awarded: result.awarded}))
    await loadHistory()
  } catch (thrown) {
    complain(thrown)
  } finally {
    busy.value = false
  }
}

/** 兑换：必须先选套餐 —— 服务端据 plan_id 真实开通订阅 */
async function exchange(rule: ExchangeRule): Promise<void> {
  error.value = ''
  if (!plans.value.length) {
    try {
      const result = await vipApi.plans({page: 1, page_size: 50})
      plans.value = (result.items ?? []).filter((plan) => plan.is_active)
    } catch (thrown) {
      complain(thrown)
      return
    }
  }
  if (!plans.value.length) {
    error.value = t('points.noPlans')
    return
  }
  if (selectedPlanId.value === null) {
    error.value = t('points.pickPlan')
    return
  }
  busy.value = true
  try {
    const result = await pointsApi.exchange(rule.action, selectedPlanId.value)
    account.value = result.account
    flash(t('points.exchangeSuccess', {cost: rule.cost}))
    await loadHistory()
  } catch (thrown) {
    complain(thrown)
  } finally {
    busy.value = false
  }
}

async function saveRule(row: RuleRow): Promise<void> {
  busy.value = true
  try {
    await pointsApi.updateRule(row.rule.id, {
      points: Number(row.draft.points),
      daily_limit: Number(row.draft.daily_limit),
      is_active: row.draft.is_active,
      sort_order: Number(row.draft.sort_order),
    })
    flash(t('points.ruleSaved'))
    await loadPublic()
  } catch (thrown) {
    complain(thrown)
  } finally {
    busy.value = false
  }
}

async function adjust(sign: 1 | -1): Promise<void> {
  const userId = Number(adjustForm.user_id)
  const amount = Number(adjustForm.amount)
  if (!userId || !amount) {
    error.value = t('points.adjustInvalid')
    return
  }
  busy.value = true
  try {
    if (sign > 0) {
      await pointsApi.grant(userId, amount, adjustForm.reason || undefined)
      flash(t('points.adjustGranted', {amount, userId}))
    } else {
      await pointsApi.deduct(userId, amount, adjustForm.reason || undefined)
      flash(t('points.adjustDeducted', {amount, userId}))
    }
    stats.value = await pointsApi.stats().catch(() => null)
  } catch (thrown) {
    complain(thrown)
  } finally {
    busy.value = false
  }
}

function goPage(next: number): void {
  if (next < 1 || (total.value > 0 && (next - 1) * PAGE_SIZE >= total.value)) return
  page.value = next
  void loadHistory()
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-wide px-4 py-10">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('points.title') }}</h1>
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('points.subtitle') }}</p>
      </div>
      <Button :disabled="loading" size="sm" variant="outline" @click="load()">
        <Icon class="h-4 w-4" name="refresh-cw"/>
        {{ $t('common.refresh') }}
      </Button>
    </div>

    <p v-if="notice" class="mt-4 rounded-card border border-line bg-surface-soft px-4 py-2.5 text-sm text-fg">
      {{ notice }}
    </p>
    <p v-if="error" class="mt-4 rounded-card border border-danger/40 bg-surface-soft px-4 py-2.5 text-sm text-danger">
      {{ error }}
    </p>

    <div v-if="loading" class="mt-6 space-y-3">
      <Skeleton class="h-24 w-full"/>
      <Skeleton class="h-40 w-full"/>
    </div>

    <EmptyState
      v-else-if="failed"
      :description="$t('common.networkError')"
      :title="$t('points.loadFailed')"
    >
      <Button class="mt-3" size="sm" variant="outline" @click="load()">{{ $t('common.retry') }}</Button>
    </EmptyState>

    <template v-else>
      <!-- 账户概览 + 签到 -->
      <section class="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div class="rounded-card border border-line bg-surface p-4">
          <p class="text-xs text-fg-muted">{{ $t('points.balance') }}</p>
          <p class="mt-1 text-2xl font-semibold text-primary">{{ account?.balance ?? 0 }}</p>
          <Button
            :disabled="busy || (account?.checked_in_today ?? false)"
            :variant="account?.checked_in_today ? 'outline' : 'default'"
            class="mt-3 w-full"
            size="sm"
            @click="checkin()"
          >
            <Icon class="h-4 w-4" name="calendar-days"/>
            {{ account?.checked_in_today ? $t('points.checkedIn') : $t('points.checkin') }}
          </Button>
        </div>
        <div class="rounded-card border border-line bg-surface p-4">
          <p class="text-xs text-fg-muted">{{ $t('points.earned') }}</p>
          <p class="mt-1 text-2xl font-semibold text-fg">{{ account?.total_earned ?? 0 }}</p>
          <p class="mt-3 text-xs text-fg-subtle">
            {{ $t('points.lastCheckin') }}:
            {{ account?.last_checkin_at ? formatDateTime(account.last_checkin_at) : $t('points.never') }}
          </p>
        </div>
        <div class="rounded-card border border-line bg-surface p-4">
          <p class="text-xs text-fg-muted">{{ $t('points.spent') }}</p>
          <p class="mt-1 text-2xl font-semibold text-fg">{{ account?.total_spent ?? 0 }}</p>
        </div>
      </section>

      <!-- 兑换 -->
      <section v-if="exchangeRules.length" class="mt-4 rounded-card border border-line bg-surface p-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 class="text-sm font-semibold text-fg">{{ $t('points.exchangeTitle') }}</h2>
          <label class="flex items-center gap-2 text-sm text-fg-muted">
            {{ $t('points.pickPlan') }}
            <select
              v-model.number="selectedPlanId"
              class="rounded-card border border-line bg-surface px-2 py-1 text-sm text-fg"
            >
              <option :value="null">{{ $t('points.planPlaceholder') }}</option>
              <option v-for="plan in plans" :key="plan.id" :value="plan.id">
                {{ plan.name }}（{{ plan.duration_days }} {{ $t('points.days') }}）
              </option>
            </select>
          </label>
        </div>
        <ul class="mt-3 flex flex-wrap gap-2">
          <li v-for="rule in exchangeRules" :key="rule.action">
            <Button
              :disabled="busy || (account?.balance ?? 0) < rule.cost"
              size="sm"
              variant="outline"
              @click="exchange(rule)"
            >
              {{ rule.description || rule.action }} · {{ rule.cost }} {{ $t('points.pointsUnit') }}
            </Button>
          </li>
        </ul>
      </section>

      <!-- tabs -->
      <div class="mt-8 flex gap-1 border-b border-line">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="activeTab === tab.key ? 'border-primary font-medium text-primary' : 'border-transparent text-fg-muted hover:text-fg'"
          class="-mb-px border-b-2 px-3 py-2 text-sm"
          type="button"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- 流水 -->
      <section v-if="activeTab === 'history'" class="mt-4">
        <p v-if="!transactions.length" class="py-8 text-center text-sm text-fg-muted">
          {{ $t('points.emptyHistory') }}
        </p>
        <ul v-else class="divide-y divide-line rounded-card border border-line bg-surface">
          <li
            v-for="row in transactions"
            :key="row.id"
            class="flex items-center justify-between gap-3 px-4 py-3"
          >
            <div class="min-w-0">
              <p class="truncate text-sm text-fg">{{ row.description || row.action }}</p>
              <p class="mt-0.5 text-xs text-fg-subtle">
                {{ row.action }} · {{ formatDateTime(row.created_at) }}
              </p>
            </div>
            <div class="shrink-0 text-right">
              <p :class="(row.amount ?? 0) >= 0 ? 'text-primary' : 'text-danger'" class="text-sm font-medium">
                {{ (row.amount ?? 0) > 0 ? '+' : '' }}{{ row.amount ?? 0 }}
              </p>
              <p class="text-xs text-fg-subtle">{{ $t('points.balanceAfter') }} {{ row.balance_after ?? 0 }}</p>
            </div>
          </li>
        </ul>
        <div v-if="total > PAGE_SIZE" class="mt-6 flex items-center justify-between text-sm text-fg-muted">
          <span>{{ $t('points.pageInfo', {page, total}) }}</span>
          <div class="flex gap-2">
            <Button :disabled="page <= 1" size="sm" variant="outline" @click="goPage(page - 1)">
              {{ $t('points.prevPage') }}
            </Button>
            <Button
              :disabled="page * PAGE_SIZE >= total"
              size="sm"
              variant="outline"
              @click="goPage(page + 1)"
            >
              {{ $t('points.nextPage') }}
            </Button>
          </div>
        </div>
      </section>

      <!-- 排行榜 -->
      <section v-else-if="activeTab === 'leaderboard'" class="mt-4">
        <p v-if="!board.length" class="py-8 text-center text-sm text-fg-muted">
          {{ $t('points.emptyLeaderboard') }}
        </p>
        <ul v-else class="divide-y divide-line rounded-card border border-line bg-surface">
          <li
            v-for="row in board"
            :key="row.user_id"
            class="flex items-center justify-between gap-3 px-4 py-3"
          >
            <div class="flex min-w-0 items-center gap-3">
              <span class="w-8 shrink-0 text-sm font-medium text-fg-subtle">#{{ row.rank }}</span>
              <span class="truncate text-sm text-fg">{{ row.username || row.user_id }}</span>
            </div>
            <span class="shrink-0 text-sm font-medium text-primary">{{ row.balance }}</span>
          </li>
        </ul>
      </section>

      <!-- 规则 -->
      <section v-else-if="activeTab === 'rules'" class="mt-4">
        <ul class="divide-y divide-line rounded-card border border-line bg-surface">
          <li
            v-for="rule in rules"
            :key="rule.id"
            class="flex flex-wrap items-center justify-between gap-2 px-4 py-3"
          >
            <div>
              <p class="text-sm text-fg">{{ rule.description || rule.action }}</p>
              <p class="mt-0.5 text-xs text-fg-subtle">
                {{ rule.action }} · {{ $t('points.ruleDailyLimit') }}:
                {{ rule.daily_limit || $t('points.unlimited') }}
              </p>
            </div>
            <div class="flex items-center gap-2">
              <Badge :variant="rule.is_active ? 'success' : 'secondary'">
                {{ rule.is_active ? $t('points.ruleActive') : $t('points.ruleInactive') }}
              </Badge>
              <span :class="(rule.points ?? 0) >= 0 ? 'text-primary' : 'text-danger'" class="text-sm font-medium">
                {{ (rule.points ?? 0) > 0 ? '+' : '' }}{{ rule.points ?? 0 }}
              </span>
            </div>
          </li>
        </ul>
      </section>

      <!-- 管理 -->
      <section v-else-if="activeTab === 'manage'" class="mt-4 space-y-6">
        <div v-if="stats" class="grid grid-cols-2 gap-3 lg:grid-cols-3">
          <div class="rounded-card border border-line bg-surface p-4">
            <p class="text-xs text-fg-muted">{{ $t('points.statAccounts') }}</p>
            <p class="mt-1 text-xl font-semibold text-fg">{{ stats.total_accounts }}</p>
          </div>
          <div class="rounded-card border border-line bg-surface p-4">
            <p class="text-xs text-fg-muted">{{ $t('points.statBalance') }}</p>
            <p class="mt-1 text-xl font-semibold text-fg">{{ stats.total_balance }}</p>
          </div>
          <div class="rounded-card border border-line bg-surface p-4">
            <p class="text-xs text-fg-muted">{{ $t('points.statEarned') }}</p>
            <p class="mt-1 text-xl font-semibold text-fg">{{ stats.total_earned }}</p>
          </div>
          <div class="rounded-card border border-line bg-surface p-4">
            <p class="text-xs text-fg-muted">{{ $t('points.statSpent') }}</p>
            <p class="mt-1 text-xl font-semibold text-fg">{{ stats.total_spent }}</p>
          </div>
          <div class="rounded-card border border-line bg-surface p-4">
            <p class="text-xs text-fg-muted">{{ $t('points.statTransactions') }}</p>
            <p class="mt-1 text-xl font-semibold text-fg">{{ stats.transaction_count }}</p>
          </div>
          <div class="rounded-card border border-line bg-surface p-4">
            <p class="text-xs text-fg-muted">{{ $t('points.statRules') }}</p>
            <p class="mt-1 text-xl font-semibold text-fg">{{ stats.active_rules }}</p>
          </div>
        </div>

        <!-- 规则编辑 -->
        <div>
          <h2 class="text-sm font-semibold text-fg">{{ $t('points.ruleEditTitle') }}</h2>
          <ul class="mt-3 divide-y divide-line rounded-card border border-line bg-surface">
            <li v-for="row in ruleRows" :key="row.rule.id" class="px-4 py-3">
              <div class="flex flex-wrap items-end gap-3">
                <div class="min-w-40">
                  <p class="text-sm text-fg">{{ row.rule.description || row.rule.action }}</p>
                  <p class="text-xs text-fg-subtle">{{ row.rule.action }}</p>
                </div>
                <label class="text-xs text-fg-muted">
                  {{ $t('points.rulePoints') }}
                  <input
                    v-model.number="row.draft.points"
                    class="mt-1 block w-24 rounded-card border border-line bg-surface px-2 py-1 text-sm text-fg"
                    type="number"
                  >
                </label>
                <label class="text-xs text-fg-muted">
                  {{ $t('points.ruleDailyLimit') }}
                  <input
                    v-model.number="row.draft.daily_limit"
                    class="mt-1 block w-24 rounded-card border border-line bg-surface px-2 py-1 text-sm text-fg"
                    min="0"
                    type="number"
                  >
                </label>
                <label class="text-xs text-fg-muted">
                  {{ $t('points.ruleSort') }}
                  <input
                    v-model.number="row.draft.sort_order"
                    class="mt-1 block w-20 rounded-card border border-line bg-surface px-2 py-1 text-sm text-fg"
                    type="number"
                  >
                </label>
                <label class="flex items-center gap-1.5 text-xs text-fg-muted">
                  <input v-model="row.draft.is_active" type="checkbox">
                  {{ $t('points.ruleActive') }}
                </label>
                <Button :disabled="busy" size="sm" variant="outline" @click="saveRule(row)">
                  <Icon class="h-4 w-4" name="save"/>
                  {{ $t('points.ruleSave') }}
                </Button>
              </div>
            </li>
          </ul>
        </div>

        <!-- 加减分 -->
        <div>
          <h2 class="text-sm font-semibold text-fg">{{ $t('points.adjustTitle') }}</h2>
          <div class="mt-3 flex flex-wrap items-end gap-3 rounded-card border border-line bg-surface p-4">
            <label class="text-xs text-fg-muted">
              {{ $t('points.adjustUser') }}
              <input
                v-model="adjustForm.user_id"
                :placeholder="$t('points.adjustUserPlaceholder')"
                class="mt-1 block w-32 rounded-card border border-line bg-surface px-2 py-1 text-sm text-fg"
              >
            </label>
            <label class="text-xs text-fg-muted">
              {{ $t('points.adjustAmount') }}
              <input
                v-model="adjustForm.amount"
                class="mt-1 block w-28 rounded-card border border-line bg-surface px-2 py-1 text-sm text-fg"
                min="1"
                type="number"
              >
            </label>
            <label class="min-w-48 flex-1 text-xs text-fg-muted">
              {{ $t('points.adjustReason') }}
              <input
                v-model="adjustForm.reason"
                class="mt-1 block w-full rounded-card border border-line bg-surface px-2 py-1 text-sm text-fg"
              >
            </label>
            <div class="flex gap-2">
              <Button :disabled="busy" size="sm" @click="adjust(1)">{{ $t('points.grant') }}</Button>
              <Button :disabled="busy" size="sm" variant="danger" @click="adjust(-1)">
                {{ $t('points.deduct') }}
              </Button>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
