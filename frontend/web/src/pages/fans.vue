<script lang="ts" setup>
/**
 * 我的关注 / 粉丝（T5-11 批次 11）
 *
 * 数据源：v3 `/api/v3/mobile/follow`。注意 v2 的同名能力读写的是**进程内内存字典**
 * （重启即丢、多 worker 各一份，且仓库里从来没有 follow 表）——v3 是真表
 * `user_follows` + 分页 + `is_following` / `is_mutual` 标记。
 *
 * 需登录：`middleware: 'auth'`；`/fans` 在 nuxt.config.ts 里配置为 `ssr: false`，纯 CSR。
 */
import {followApi, type FollowItem, type FollowStats} from '@/api'
import {formatDateTime} from '@/utils/format'

definePageMeta({layout: 'default', middleware: 'auth', title: 'fans.title'})

const {t} = useI18n()
const activeTab = ref<'following' | 'follower'>('following')

const PAGE_SIZE = 20
const items = ref<FollowItem[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const failed = ref(false)
const acting = ref<number | null>(null)

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    const params = {page: page.value, page_size: PAGE_SIZE}
    const result =
      activeTab.value === 'follower'
        ? await followApi.myFollowers(params)
        : await followApi.myFollowing(params)
    items.value = result.items ?? []
    total.value = result.total ?? 0
  } catch {
    failed.value = true
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

/** 关注 / 取关后就地更新标记（不整页刷新：在「我的关注」里取关后该项保留，符合常见交互） */
async function toggleFollow(item: FollowItem): Promise<void> {
  acting.value = item.user.id
  try {
    const stats: FollowStats = item.user.is_following
      ? await followApi.unfollow(item.user.id)
      : await followApi.follow(item.user.id)
    item.user.is_following = stats.is_following
    item.user.is_mutual = stats.is_mutual
  } finally {
    acting.value = null
  }
}

function onPage(next: number): void {
  page.value = next
  void load()
}

watch(activeTab, () => {
  page.value = 1
  void load()
})

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-wide px-4 py-10">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('fans.title') }}</h1>
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('fans.subtitle') }}</p>
      </div>
      <Button :disabled="loading" size="sm" variant="outline" @click="load()">
        <Icon class="h-4 w-4" name="refresh-cw"/>
        {{ $t('common.refresh') }}
      </Button>
    </div>

    <div class="mt-6 flex gap-2">
      <Button
        v-for="tab in (['following', 'follower'] as const)"
        :key="tab"
        :variant="activeTab === tab ? 'default' : 'outline'"
        size="sm"
        @click="activeTab = tab"
      >
        {{ tab === 'following' ? $t('fans.following') : $t('fans.follower') }}
      </Button>
    </div>

    <div class="mt-4">
      <div v-if="loading" class="space-y-3">
        <Skeleton v-for="i in 5" :key="i" class="h-16 w-full"/>
      </div>

      <ErrorState
        v-else-if="failed"
        :description="$t('common.networkError')"
        :title="$t('fans.loadFailed')"
        @retry="load()"
      />

      <EmptyState
        v-else-if="!items.length"
        :description="activeTab === 'following' ? $t('fans.emptyFollowingDesc') : $t('fans.emptyFollowerDesc')"
        :title="activeTab === 'following' ? $t('fans.emptyFollowing') : $t('fans.emptyFollower')"
      />

      <ul v-else class="divide-y divide-line rounded-card border border-line bg-surface">
        <li
          v-for="item in items"
          :key="item.user.id"
          class="flex items-center gap-3 px-4 py-3"
        >
          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-pill bg-surface-soft text-fg-muted"
          >
            <Icon class="h-4 w-4" name="user"/>
          </span>

          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="truncate text-sm font-medium text-fg">
                {{ item.user.username || $t('fans.userFallback', {id: item.user.id}) }}
              </span>
              <Badge v-if="item.user.is_mutual" variant="success">{{ $t('fans.mutual') }}</Badge>
              <Badge v-else-if="item.user.is_following" variant="default">
                {{ $t('fans.followingBadge') }}
              </Badge>
            </div>
            <p v-if="item.created_at" class="mt-0.5 text-xs text-fg-subtle">
              {{ formatDateTime(item.created_at) }}
            </p>
          </div>

          <Button
            :disabled="acting === item.user.id"
            :variant="item.user.is_following ? 'outline' : 'default'"
            size="sm"
            @click="toggleFollow(item)"
          >
            {{ item.user.is_following ? $t('fans.unfollow') : $t('fans.follow') }}
          </Button>
        </li>
      </ul>
    </div>

    <div v-if="total > PAGE_SIZE" class="mt-6 flex items-center justify-between text-sm text-fg-muted">
      <span>{{ $t('fans.total', {n: total}) }}</span>
      <div class="flex gap-2">
        <Button :disabled="page <= 1" size="sm" variant="outline" @click="onPage(page - 1)">
          {{ $t('fans.prevPage') }}
        </Button>
        <Button
          :disabled="page * PAGE_SIZE >= total"
          size="sm"
          variant="outline"
          @click="onPage(page + 1)"
        >
          {{ $t('fans.nextPage') }}
        </Button>
      </div>
    </div>
  </div>
</template>
