<script lang="ts" setup>
/**
 * 勋章管理（后台独立页，`/gamification/badges`）
 *
 * 数据源：v3 `/api/v3/gamification/badge`
 *  - 定义与统计：`available` / `stats`（分类分布、授予总数、热门勋章）
 *  - 手工授予 `award`（幂等；`is_manual` 的勋章**只能**手工授予 ——
 *    没有统计源的条件不会被假装成"能自动判定"）
 *
 * 自动授予（文章数 / 获赞 / 粉丝 / 评论数）由前台 `/badges` 的「检查并授予」触发，
 * 那里展示的是**真实进度**（v2 的统计函数恒返回 0，进度永远是 0%）。
 */
import {Refresh, Search} from '@element-plus/icons-vue'
import {ElMessage} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {badgeApi, type BadgeDefinition, type BadgeStats} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.gamification.badges.title',
  permission: 'module_gamification:badge:view',
})

const {t} = useI18n()

const CONDITION_LABELS: Record<string, string> = {
  article_count: 'admin.gamification.badges.conditionArticleCount',
  max_article_likes: 'admin.gamification.badges.conditionMaxLikes',
  follower_count: 'admin.gamification.badges.conditionFollowerCount',
  comment_count: 'admin.gamification.badges.conditionCommentCount',
  like_received: 'admin.gamification.badges.conditionLikeReceived',
}

const loading = ref(false)
const awarding = ref(false)
const stats = ref<BadgeStats | null>(null)
const definitions = ref<BadgeDefinition[]>([])
const keyword = ref('')

const dialogVisible = ref(false)
const target = ref<BadgeDefinition | null>(null)
const awardForm = reactive<{ user_id: string }>({user_id: ''})

const filtered = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return definitions.value
  return definitions.value.filter((item) =>
    [item.badge_key, item.name, item.description, item.category]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(text)),
  )
})

function conditionText(badge: BadgeDefinition): string {
  if (badge.is_manual) return t('admin.gamification.badges.manualOnly')
  const key = CONDITION_LABELS[badge.condition_type ?? '']
  if (!key) return t('admin.gamification.badges.conditionUnknown')
  return t(key, {value: badge.condition_value})
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const [items, summary] = await Promise.all([
      badgeApi.available(),
      badgeApi.stats().catch(() => null),
    ])
    definitions.value = items ?? []
    stats.value = summary
  } finally {
    loading.value = false
  }
}

function openAward(badge: BadgeDefinition): void {
  target.value = badge
  awardForm.user_id = ''
  dialogVisible.value = true
}

async function submitAward(): Promise<void> {
  const userId = Number(awardForm.user_id)
  if (!userId || !target.value?.badge_key) {
    ElMessage.warning(t('admin.gamification.badges.userRequired'))
    return
  }
  awarding.value = true
  try {
    const result = await badgeApi.award(userId, target.value.badge_key)
    ElMessage.success(
      result.already_awarded
        ? t('admin.gamification.badges.alreadyAwarded')
        : t('admin.gamification.badges.awarded'),
    )
    dialogVisible.value = false
    await load()
  } finally {
    awarding.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="table-toolbar">
        <span class="table-toolbar__total">{{ $t('admin.gamification.badges.statsTitle') }}</span>
        <el-button :icon="Refresh" @click="load()">{{ $t('admin.common.refresh') }}</el-button>
      </div>

      <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <el-card shadow="never">
          <p class="text-xs text-gray-500">{{ $t('admin.gamification.badges.totalDefinitions') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.total_definitions ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-gray-500">{{ $t('admin.gamification.badges.activeDefinitions') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.active_definitions ?? 0 }}</p>
        </el-card>
        <el-card shadow="never">
          <p class="text-xs text-gray-500">{{ $t('admin.gamification.badges.totalAwarded') }}</p>
          <p class="mt-1 text-xl font-semibold">{{ stats?.total_awarded ?? 0 }}</p>
        </el-card>
      </div>
    </el-card>

    <el-card class="mt-4" shadow="never">
      <template #header>
        <div class="flex items-center justify-between">
          <span>{{ $t('admin.gamification.badges.definitionsTitle') }}</span>
          <el-input v-model="keyword" :placeholder="$t('admin.gamification.badges.searchPlaceholder')" clearable
                    style="width: 260px">
            <template #prefix>
              <el-icon>
                <Search/>
              </el-icon>
            </template>
          </el-input>
        </div>
      </template>

      <AdminTableSkeleton v-if="loading && !filtered.length" :rows="5"/>
      <AdminEmpty v-else-if="!loading && !filtered.length" :title="$t('admin.common.empty')"/>
      <el-table v-else v-loading="loading" :data="filtered" border stripe>
        <el-table-column :label="$t('admin.gamification.badges.key')" min-width="140" prop="badge_key"
                         show-overflow-tooltip/>
        <el-table-column :label="$t('admin.common.name')" min-width="140" prop="name" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.gamification.badges.category')" prop="category" width="120"/>
        <el-table-column :label="$t('admin.gamification.badges.condition')" min-width="200">
          <template #default="{ row }">{{ conditionText(row as BadgeDefinition) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.gamification.badges.pointsReward')" prop="points_reward"
                         width="120"/>
        <el-table-column :label="$t('admin.common.status')" width="110">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? $t('admin.common.enabled') : $t('admin.common.disabled') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="110">
          <template #default="{ row }">
            <el-button v-auth="'module_gamification:badge:edit'" link type="primary"
                       @click="openAward(row as BadgeDefinition)">
              {{ $t('admin.gamification.badges.award') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="stats?.top_badges?.length" class="mt-4" shadow="never">
      <template #header>
        <span>{{ $t('admin.gamification.badges.topBadges') }}</span>
      </template>
      <el-table :data="stats?.top_badges ?? []" border stripe>
        <el-table-column :label="$t('admin.gamification.badges.key')" min-width="180">
          <template #default="{ row }">{{ row.name || row.badge_key }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.gamification.badges.awardedCount')" prop="count" width="140"/>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="$t('admin.gamification.badges.awardTitle')" width="440px">
      <el-form label-width="110px">
        <el-form-item :label="$t('admin.gamification.badges.badge')">
          <span>{{ target?.name || target?.badge_key }}</span>
        </el-form-item>
        <el-form-item :label="$t('admin.gamification.points.userId')" required>
          <el-input v-model="awardForm.user_id"
                    :placeholder="$t('admin.gamification.points.userIdPlaceholder')"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="awarding" type="primary" @click="submitAward()">
          {{ $t('admin.gamification.badges.award') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
