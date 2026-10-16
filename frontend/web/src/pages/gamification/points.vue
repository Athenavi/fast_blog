<script lang="ts" setup>
/**
 * 积分管理（后台独立页，`/gamification/points`）
 *
 * 数据源：v3 `/api/v3/gamification/points`
 *  - 统计 `stats`（账户数 / 总余额 / 累计获得 / 累计消耗 / 流水条数 / 生效规则数 / 榜首）
 *  - 规则表 `rules`（点数 / 日上限 / 启停 / 排序，**可配置**：v2 是类内常量）
 *  - 管理员加减分 `grant` / `deduct`（真实写流水并更新余额）
 *
 * 前台用户侧（我的余额 / 签到 / 兑换）在 `/points`；本页只做管理操作，
 * 避免同一个功能在两处各有一套入口（原先前台页内嵌的「管理」tab 已移除）。
 */
import {Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {
  type ExchangeRule,
  type LeaderboardItem,
  pointsApi,
  type PointsLevel,
  type PointsMeResult,
  type PointsRule,
  type PointsStats,
} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.gamification.points.title',
  permission: 'module_gamification:points:view',
})

const {t} = useI18n()

/** 行内编辑需要一份可变副本（规则本体 + 编辑缓冲） */
interface RuleRow {
  rule: PointsRule
  draft: { points: number; daily_limit: number; is_active: boolean; sort_order: number }
}

const loading = ref(false)
/** 列表加载失败（用于错误态与重试） */
const loadFailed = ref(false)
const saving = ref(false)
const stats = ref<PointsStats | null>(null)
const exchangeRules = ref<ExchangeRule[]>([])
const rows = ref<RuleRow[]>([])

const adjust = reactive<{ user_id: string; amount: string; reason: string }>({
  user_id: '',
  amount: '',
  reason: '',
})

const scope = ref<'grant' | 'deduct'>('grant')

async function load(): Promise<void> {
  loading.value = true
  try {
    const [summary, rules, exchanges] = await Promise.all([
      pointsApi.stats(),
      pointsApi.rules(),
      pointsApi.exchangeRules().catch(() => [] as ExchangeRule[]),
    ])
    stats.value = summary
    exchangeRules.value = exchanges ?? []
    rows.value = (rules ?? []).map((rule) => ({
      rule,
      draft: {
        points: rule.points ?? 0,
        daily_limit: rule.daily_limit ?? 0,
        is_active: rule.is_active,
        sort_order: rule.sort_order ?? 0,
      },
    }))
  } catch {
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

async function saveRule(row: RuleRow): Promise<void> {
  saving.value = true
  try {
    await pointsApi.updateRule(row.rule.id, {
      points: Number(row.draft.points),
      daily_limit: Number(row.draft.daily_limit),
      is_active: row.draft.is_active,
      sort_order: Number(row.draft.sort_order),
    })
    ElMessage.success(t('admin.common.save'))
    await load()
  } finally {
    saving.value = false
  }
}

async function submitAdjust(): Promise<void> {
  const userId = Number(adjust.user_id)
  const amount = Number(adjust.amount)
  if (!userId || !amount || amount <= 0) {
    ElMessage.warning(t('admin.gamification.points.adjustInvalid'))
    return
  }
  saving.value = true
  try {
    if (scope.value === 'grant') {
      await pointsApi.grant(userId, amount, adjust.reason || undefined)
    } else {
      await pointsApi.deduct(userId, amount, adjust.reason || undefined)
    }
    ElMessage.success(
      t(scope.value === 'grant' ? 'admin.gamification.points.granted' : 'admin.gamification.points.deducted', {
        amount,
        userId,
      }),
    )
    adjust.amount = ''
    adjust.reason = ''
    await load()
  } finally {
    saving.value = false
  }
}

const topHolders = computed(() => stats.value?.top_holders ?? [])

onMounted(load)

// ---------------------------------------------------------------- 我的账户 / 排行榜 / 等级 / 手动奖励
/** 我的积分账户（仅认证）：余额 + 当前等级 + 最近流水，一次拿齐 */
const me = ref<PointsMeResult | null>(null)
/** 我的账户 + 排行榜加载态与错误态 */
const auxLoading = ref(false)
const auxFailed = ref(false)
/** 排行榜（公开，`ranking` 端点） */
const ranking = ref<LeaderboardItem[]>([])
/** 等级详情查询（公开，纯函数） */
const levelScore = ref(0)
const levelResult = ref<PointsLevel | null>(null)
const levelBusy = ref(false)
/** 手动奖励（管理员，需权限 + 二次确认） */
const award = reactive<{ user_id: string; amount: string; reason: string }>({
  user_id: '',
  amount: '',
  reason: '',
})
const awarding = ref(false)

async function loadAuxiliary(): Promise<void> {
  auxLoading.value = true
  auxFailed.value = false
  try {
    const [meData, boardRows] = await Promise.all([pointsApi.me(), pointsApi.ranking(20)])
    me.value = meData
    ranking.value = boardRows ?? []
  } catch {
    auxFailed.value = true
  } finally {
    auxLoading.value = false
  }
}

async function queryLevel(): Promise<void> {
  const score = Number(levelScore.value)
  if (!Number.isFinite(score)) {
    ElMessage.warning(t('admin.gamification.points.levelInvalid'))
    return
  }
  levelBusy.value = true
  try {
    levelResult.value = await pointsApi.level(Math.trunc(score))
  } finally {
    levelBusy.value = false
  }
}

async function submitAward(): Promise<void> {
  const userId = Number(award.user_id)
  const amount = Number(award.amount)
  if (!userId || !amount || amount <= 0) {
    ElMessage.warning(t('admin.gamification.points.adjustInvalid'))
    return
  }
  try {
    await ElMessageBox.confirm(
      t('admin.gamification.points.awardConfirmMessage', {amount, userId}),
      t('admin.gamification.points.awardConfirmTitle'),
      {type: 'warning'},
    )
  } catch {
    return
  }
  awarding.value = true
  try {
    await pointsApi.award(userId, amount, award.reason || undefined)
    ElMessage.success(t('admin.gamification.points.granted', {amount, userId}))
    award.amount = ''
    award.reason = ''
    await Promise.all([load(), loadAuxiliary()])
  } finally {
    awarding.value = false
  }
}

onMounted(loadAuxiliary)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="table-toolbar">
        <span class="table-toolbar__total">{{ $t('admin.gamification.points.statsTitle') }}</span>
        <el-button :icon="Refresh" @click="load()">{{ $t('admin.common.refresh') }}</el-button>
      </div>

      <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.gamification.points.totalAccounts') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.total_accounts ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.gamification.points.totalBalance') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.total_balance ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.gamification.points.totalEarned') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.total_earned ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.gamification.points.totalSpent') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.total_spent ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.gamification.points.transactionCount') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.transaction_count ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.gamification.points.activeRules') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.active_rules ?? 0 }}</p>
        </el-card>
      </div>
    </el-card>

    <!-- 管理员加减分 -->
    <el-card class="mt-4" shadow="never">
      <template #header>
        <span>{{ $t('admin.gamification.points.adjustTitle') }}</span>
      </template>

      <el-form :inline="true" @submit.prevent="submitAdjust()">
        <el-form-item :label="$t('admin.gamification.points.userId')">
          <el-input v-model="adjust.user_id" :placeholder="$t('admin.gamification.points.userIdPlaceholder')"
                    style="width: 140px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.gamification.points.amount')">
          <el-input v-model="adjust.amount" style="width: 120px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.gamification.points.reason')">
          <el-input v-model="adjust.reason" style="width: 220px"/>
        </el-form-item>
        <el-form-item>
          <el-radio-group v-model="scope">
            <el-radio-button value="grant">{{ $t('admin.gamification.points.grant') }}</el-radio-button>
            <el-radio-button value="deduct">{{ $t('admin.gamification.points.deduct') }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button v-auth="'module_gamification:points:edit'" :loading="saving" type="primary"
                     @click="submitAdjust()">
            {{ $t('admin.common.submit') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 规则表 -->
    <el-card class="mt-4" shadow="never">
      <template #header>
        <span>{{ $t('admin.gamification.points.rulesTitle') }}</span>
      </template>

      <AdminTableSkeleton v-if="loading && !rows.length" :rows="5"/>
      <AdminEmpty
        v-else-if="!loading && !rows.length"
        :title="loadFailed ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
        :variant="loadFailed ? 'error' : 'default'"
      >
        <el-button v-if="loadFailed" :icon="Refresh" @click="load()">
          {{ $t('admin.common.retry') }}
        </el-button>
      </AdminEmpty>
      <el-table v-else v-loading="loading" :data="rows" border stripe>
        <el-table-column :label="$t('admin.gamification.points.action')" min-width="160" prop="rule.action"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.gamification.points.description')" min-width="200" prop="rule.description"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.gamification.points.points')" width="140">
          <template #default="{ row }">
            <el-input-number v-model="row.draft.points" :max="10000" :min="-10000" controls-position="right"
                             size="small"/>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.gamification.points.dailyLimit')" width="130">
          <template #default="{ row }">
            <el-input-number v-model="row.draft.daily_limit" :max="1000" :min="0" controls-position="right"
                             size="small"/>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.gamification.points.sortOrder')" width="120">
          <template #default="{ row }">
            <el-input-number v-model="row.draft.sort_order" :max="999" :min="0" controls-position="right"
                             size="small"/>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.status')" width="90">
          <template #default="{ row }">
            <el-switch v-model="row.draft.is_active"/>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="100">
          <template #default="{ row }">
            <el-button v-auth="'module_gamification:points:edit'" link type="primary" @click="saveRule(row as RuleRow)">
              {{ $t('admin.common.save') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 兑换项（只读） -->
    <el-card v-if="exchangeRules.length" class="mt-4" shadow="never">
      <template #header>
        <span>{{ $t('admin.gamification.points.exchangeTitle') }}</span>
      </template>
      <el-table :data="exchangeRules" border stripe>
        <el-table-column :label="$t('admin.gamification.points.action')" min-width="160" prop="action"/>
        <el-table-column :label="$t('admin.gamification.points.cost')" prop="cost" width="120"/>
        <el-table-column :label="$t('admin.gamification.points.description')" min-width="200" prop="description"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.common.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? $t('admin.common.enabled') : $t('admin.common.disabled') }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 榜首 -->
    <el-card v-if="topHolders.length" class="mt-4" shadow="never">
      <template #header>
        <span>{{ $t('admin.gamification.points.topHolders') }}</span>
      </template>
      <el-table :data="topHolders" border stripe>
        <el-table-column :label="$t('admin.gamification.points.rank')" prop="rank" width="80"/>
        <el-table-column :label="$t('admin.gamification.points.user')" min-width="160">
          <template #default="{ row }">{{ row.username || `#${row.user_id}` }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.gamification.points.balance')" prop="balance" width="140"/>
      </el-table>
    </el-card>

    <!-- 手动奖励（award；需权限 + 二次确认） -->
    <el-card class="mt-4" shadow="never">
      <template #header>
        <span>{{ $t('admin.gamification.points.awardTitle') }}</span>
      </template>
      <el-form :inline="true" @submit.prevent="submitAward()">
        <el-form-item :label="$t('admin.gamification.points.userId')">
          <el-input v-model="award.user_id" :placeholder="$t('admin.gamification.points.userIdPlaceholder')"
                    style="width: 140px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.gamification.points.amount')">
          <el-input v-model="award.amount" style="width: 120px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.gamification.points.reason')">
          <el-input v-model="award.reason" style="width: 220px"/>
        </el-form-item>
        <el-form-item>
          <el-button v-auth="'module_gamification:points:edit'" :loading="awarding" type="primary"
                     @click="submitAward()">
            {{ $t('admin.gamification.points.awardSubmit') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 我的积分账户（me：余额 + 等级 + 最近流水） -->
    <el-card class="mt-4" shadow="never">
      <template #header>
        <span>{{ $t('admin.gamification.points.meTitle') }}</span>
      </template>

      <AdminTableSkeleton v-if="auxLoading && !me" :rows="2"/>
      <AdminEmpty
        v-else-if="!me"
        :title="auxFailed ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
        :variant="auxFailed ? 'error' : 'default'"
      >
        <el-button v-if="auxFailed" :icon="Refresh" @click="loadAuxiliary()">
          {{ $t('admin.common.retry') }}
        </el-button>
      </AdminEmpty>
      <template v-else>
        <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <el-card shadow="never">
            <p class="text-xs text-fg-muted">{{ $t('admin.gamification.points.balance') }}</p>
            <p class="mt-1 text-xl font-semibold">{{ me?.account.balance ?? 0 }}</p>
          </el-card>
          <el-card shadow="never">
            <p class="text-xs text-fg-muted">{{ $t('admin.gamification.points.totalEarned') }}</p>
            <p class="mt-1 text-xl font-semibold">{{ me?.account.total_earned ?? 0 }}</p>
          </el-card>
          <el-card shadow="never">
            <p class="text-xs text-fg-muted">{{ $t('admin.gamification.points.totalSpent') }}</p>
            <p class="mt-1 text-xl font-semibold">{{ me?.account.total_spent ?? 0 }}</p>
          </el-card>
          <el-card shadow="never">
            <p class="text-xs text-fg-muted">{{ $t('admin.gamification.points.meLevel') }}</p>
            <p class="mt-1 text-xl font-semibold">
              {{
                me ? $t('admin.gamification.points.meLevelValue', {name: me.level.name, level: me.level.level}) : '-'
              }}
            </p>
          </el-card>
        </div>

        <div class="mt-4">
          <div class="mb-2 flex items-center justify-between text-xs text-fg-muted">
            <span>{{ $t('admin.gamification.points.meProgress') }}</span>
            <span v-if="me?.level.next_level === null">
              {{ $t('admin.gamification.points.meMaxLevel') }}
            </span>
            <span v-else>
              {{ $t('admin.gamification.points.mePointsToNext', {points: me?.level.points_to_next}) }}
            </span>
          </div>
          <el-progress :percentage="Math.round((me?.level.progress ?? 0) * 100)"/>
        </div>

        <div class="mt-4">
          <p class="mb-2 text-sm font-medium text-fg">{{ $t('admin.gamification.points.meRecent') }}</p>
          <el-table :data="me?.recent_transactions ?? []" border stripe>
            <el-table-column :label="$t('admin.gamification.points.action')" min-width="140" prop="action"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.gamification.points.description')" min-width="200" prop="description"
                             show-overflow-tooltip/>
            <el-table-column :label="$t('admin.gamification.points.amount')" prop="amount" width="110"/>
            <el-table-column :label="$t('admin.gamification.points.balance')" prop="balance_after" width="110"/>
          </el-table>
        </div>
      </template>
    </el-card>

    <!-- 排行榜（ranking） -->
    <el-card class="mt-4" shadow="never">
      <template #header>
        <span>{{ $t('admin.gamification.points.rankingTitle') }}</span>
      </template>
      <el-table v-loading="auxLoading" :data="ranking" border stripe>
        <el-table-column :label="$t('admin.gamification.points.rank')" prop="rank" width="80"/>
        <el-table-column :label="$t('admin.gamification.points.user')" min-width="160">
          <template #default="{ row }">{{ row.username || `#${row.user_id}` }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.gamification.points.balance')" prop="balance" width="140"/>
      </el-table>
    </el-card>

    <!-- 等级详情（level 纯函数查询） -->
    <el-card class="mt-4" shadow="never">
      <template #header>
        <span>{{ $t('admin.gamification.points.levelTitle') }}</span>
      </template>
      <el-form :inline="true" @submit.prevent="queryLevel()">
        <el-form-item :label="$t('admin.gamification.points.levelScore')">
          <el-input-number v-model="levelScore" :max="1000000" :min="0" controls-position="right" size="small"/>
        </el-form-item>
        <el-form-item>
          <el-button :loading="levelBusy" @click="queryLevel()">
            {{ $t('admin.gamification.points.levelQuery') }}
          </el-button>
        </el-form-item>
      </el-form>
      <div v-if="levelResult" class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.gamification.points.levelName') }}</p>
          <p class="mt-1 text-xl font-semibold">
            {{ $t('admin.gamification.points.meLevelValue', {name: levelResult?.name, level: levelResult?.level}) }}
          </p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.gamification.points.levelRange') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ levelResult?.min_score }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.gamification.points.levelNext') }}</p>
          <p class="mt-1 text-xl font-semibold">
            {{
              levelResult?.next_level === null
                ? $t('admin.gamification.points.levelNoNext')
                : $t('admin.gamification.points.meLevelValue', {
                  name: levelResult?.next_level_name ?? '',
                  level: levelResult?.next_level,
                })
            }}
          </p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-fg-muted">{{ $t('admin.gamification.points.levelProgress') }}</p>
          <el-progress :percentage="Math.round((levelResult?.progress ?? 0) * 100)" class="mt-2"/>
          <p class="mt-1 text-xs text-fg-subtle">
            {{
              levelResult?.next_level === null
                ? $t('admin.gamification.points.meMaxLevel')
                : $t('admin.gamification.points.mePointsToNext', {points: levelResult?.points_to_next})
            }}
          </p>
        </el-card>
      </div>
    </el-card>
  </div>
</template>
