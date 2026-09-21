<script lang="ts" setup>
/**
 * 勋章中心（`/badges`）
 *
 * - 我的勋章：来自 `badgeApi.mine()`；
 * - 全部勋章 + 进度：进度是**真实统计**对比阈值（v2 的统计函数恒返回 0，所以那时进度永远是 0%）；
 * - 「检查并授予」：幂等，`is_manual` 的勋章**不会**被自动授予（服务端会单独回报 skipped_manual）。
 *
 * 管理操作（定义列表 / 手工授予 / 统计）已移到后台独立页 `/gamification/badges`。
 */
import {badgeApi, type BadgeDefinition, type BadgeProgress, type UserBadge,} from '@/api'
import {formatDateTime} from '@/utils/format'

definePageMeta({layout: 'default', middleware: 'auth', title: 'badges.title'})

const {t} = useI18n()

const mine = ref<UserBadge[]>([])
const available = ref<BadgeDefinition[]>([])
const progressMap = ref<Record<string, BadgeProgress>>({})

const loading = ref(false)
const failed = ref(false)
const busy = ref(false)
const notice = ref('')
const error = ref('')

const ownedKeys = computed(() => new Set(mine.value.map((item) => item.badge_key)))

/** 自动授予的条件名 → 文案 key（与后端 CONDITION_TYPES 对应） */
const CONDITION_LABELS: Record<string, string> = {
  article_count: 'badges.conditionArticleCount',
  max_article_likes: 'badges.conditionMaxLikes',
  follower_count: 'badges.conditionFollowerCount',
  comment_count: 'badges.conditionCommentCount',
  like_received: 'badges.conditionLikeReceived',
}

function conditionText(badge: BadgeDefinition): string {
  if (badge.is_manual) return t('badges.manualOnly')
  const key = CONDITION_LABELS[badge.condition_type ?? '']
  if (!key) return t('badges.conditionUnknown')
  return t(key, {value: badge.condition_value})
}

interface BadgeRow {
  badge: BadgeDefinition
  owned: boolean
  progress: BadgeProgress | null
}

/** 已获得的排在最前；进度一并算好（模板里不用再索引查表，避免可空下标） */
const rows = computed<BadgeRow[]>(() =>
  [...available.value]
    .sort((a, b) => {
      const aOwned = ownedKeys.value.has(a.badge_key ?? '')
      const bOwned = ownedKeys.value.has(b.badge_key ?? '')
      if (aOwned !== bOwned) return aOwned ? -1 : 1
      return (a.sort_order ?? 0) - (b.sort_order ?? 0)
    })
    .map((badge) => ({
      badge,
      owned: ownedKeys.value.has(badge.badge_key ?? ''),
      progress: progressMap.value[badge.badge_key ?? ''] ?? null,
    })),
)

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    const [mineRows, rows] = await Promise.all([badgeApi.mine(), badgeApi.available()])
    mine.value = mineRows ?? []
    available.value = rows ?? []
    void loadProgress()
  } catch {
    failed.value = true
    mine.value = []
    available.value = []
  } finally {
    loading.value = false
  }
}

/** 逐个拉未获得勋章的进度（并行；失败静默，不影响列表） */
async function loadProgress(): Promise<void> {
  const targets = available.value.filter(
    (badge) => !badge.is_manual && badge.badge_key && !ownedKeys.value.has(badge.badge_key),
  )
  const results = await Promise.all(
    targets.map((badge) => badgeApi.progress(badge.badge_key as string).catch(() => null)),
  )
  const next: Record<string, BadgeProgress> = {}
  for (const item of results) {
    if (item) next[item.badge_key] = item
  }
  progressMap.value = next
}

async function checkAndAward(): Promise<void> {
  busy.value = true
  notice.value = ''
  error.value = ''
  try {
    const result = await badgeApi.checkAndAward()
    if (result.awarded?.length) {
      notice.value = t('badges.awardedNew', {count: result.awarded.length})
    } else {
      notice.value = t('badges.nothingNew')
    }
    progressMap.value = Object.fromEntries(
      (result.progress ?? []).map((item) => [item.badge_key, item]),
    )
    await load()
  } catch (thrown) {
    error.value = thrown instanceof Error ? thrown.message : t('common.networkError')
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-wide px-4 py-10">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('badges.title') }}</h1>
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('badges.subtitle') }}</p>
      </div>
      <div class="flex items-center gap-2">
        <Button :disabled="loading" size="sm" variant="outline" @click="load()">
          <Icon class="h-4 w-4" name="refresh-cw"/>
          {{ $t('common.refresh') }}
        </Button>
        <Button :disabled="busy" size="sm" @click="checkAndAward()">
          <Icon class="h-4 w-4" name="check"/>
          {{ $t('badges.check') }}
        </Button>
      </div>
    </div>

    <p v-if="notice" class="mt-4 rounded-card border border-line bg-surface-soft px-4 py-2.5 text-sm text-fg">
      {{ notice }}
    </p>
    <p v-if="error" class="mt-4 rounded-card border border-danger/40 bg-surface-soft px-4 py-2.5 text-sm text-danger">
      {{ error }}
    </p>

    <div v-if="loading" class="mt-6 space-y-3">
      <Skeleton v-for="i in 6" :key="i" class="h-20 w-full"/>
    </div>

    <ErrorState
      v-else-if="failed"
      :description="$t('common.networkError')"
      :title="$t('badges.loadFailed')"
      @retry="load()"
    />

    <template v-else>
      <!-- 我的勋章 -->
      <section class="mt-8">
        <h2 class="text-base font-semibold text-fg">
          {{ $t('badges.mine') }}
          <span class="ml-1 text-sm font-normal text-fg-muted">({{ mine.length }})</span>
        </h2>
        <div v-if="!mine.length" class="mt-3">
          <p class="text-sm text-fg-muted">{{ $t('badges.emptyMine') }}</p>
          <NuxtLink class="mt-2 inline-block" to="/feed">
            <Button size="sm" variant="outline">{{ $t('feed.goDiscover') }}</Button>
          </NuxtLink>
        </div>
        <ul v-else class="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          <li
            v-for="item in mine"
            :key="item.badge_key"
            class="rounded-card border border-line bg-surface p-3.5"
          >
            <div class="flex items-start gap-3">
              <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-pill bg-surface-soft text-primary">
                <Icon class="h-4.5 w-4.5" name="check"/>
              </span>
              <div class="min-w-0">
                <p class="truncate text-sm font-medium text-fg">{{ item.name || item.badge_key }}</p>
                <p class="mt-0.5 line-clamp-2 text-xs text-fg-muted">{{ item.description }}</p>
                <p class="mt-1 text-xs text-fg-subtle">{{ formatDateTime(item.awarded_at) }}</p>
              </div>
            </div>
          </li>
        </ul>
      </section>

      <!-- 全部勋章 -->
      <section class="mt-10">
        <h2 class="text-base font-semibold text-fg">{{ $t('badges.all') }}</h2>
        <ul class="mt-3 divide-y divide-line rounded-card border border-line bg-surface">
          <li v-for="row in rows" :key="row.badge.badge_key || row.badge.id" class="px-4 py-3.5">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="min-w-0">
                <p class="flex items-center gap-2 text-sm font-medium text-fg">
                  {{ row.badge.name || row.badge.badge_key }}
                  <Badge v-if="row.owned" variant="success">{{ $t('badges.owned') }}</Badge>
                  <Badge v-else-if="row.badge.is_manual" variant="secondary">
                    {{ $t('badges.manual') }}
                  </Badge>
                </p>
                <p class="mt-1 text-xs text-fg-muted">{{ row.badge.description }}</p>
                <p class="mt-1 text-xs text-fg-subtle">
                  {{ conditionText(row.badge) }} ·
                  {{ $t('badges.reward', {points: row.badge.points_reward}) }}
                </p>
              </div>
              <div v-if="row.progress" class="w-full max-w-xs sm:w-48">
                <div class="flex items-center justify-between text-xs text-fg-muted">
                  <span>{{ row.progress.current_value }} / {{ row.progress.condition_value }}</span>
                  <span>{{ row.progress.progress_percent }}%</span>
                </div>
                <div class="mt-1.5 h-1.5 w-full overflow-hidden rounded-pill bg-surface-soft">
                  <div
                    :style="{width: `${Math.min(100, row.progress.progress_percent)}%`}"
                    class="h-full rounded-pill bg-primary transition-width"
                  />
                </div>
              </div>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
