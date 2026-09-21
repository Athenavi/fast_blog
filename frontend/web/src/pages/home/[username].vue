<script lang="ts" setup>
/**
 * 用户主页（公开）— `/home/{username}`
 *
 * 数据源：v3 `GET /api/v3/mobile/user/public/{username}`（公开，匿名可访问；
 * 登录时额外带 `is_following` / `is_mutual` 标记）。
 *
 *  - 首屏资料走 `apiGet`（SSR 直出，SEO 友好）；取不到即 404；
 *  - TA 的公开文章走公开列表 `/content/article/public/list`（`user_id` 过滤）；
 *  - 关注 / 取关与打赏是登录态交互，包在 `<ClientOnly>` 里；
 *  - 私密资料（`is_private`）后端只回 id / username / profile_picture，
 *    这里不渲染简介与统计，仅给提示。
 */
import {followApi, mobileApi, type MobilePublicProfile} from '@/api'
import {useUserStore} from '@/store/modules/user'
import type {ArticleItem} from '@/types/content'
import {formatDate} from '@/utils/format'

const PAGE_SIZE = 10

const route = useRoute()
const {t} = useI18n()
const site = await useSiteInfo()

const username = computed(() => String(route.params.username))
const page = computed(() => Math.max(1, Number(route.query.page || 1)))

const {data: profile} = await useAsyncData(
  () => `home-profile-${username.value}`,
  () => apiGet<MobilePublicProfile>(`/mobile/user/public/${encodeURIComponent(username.value)}`),
)

if (!profile.value) {
  throw createError({statusCode: 404, statusMessage: t('home.notFound')})
}

const {data: articlePage, pending, error, refresh} = await useAsyncData(
  () => `home-articles-${username.value}-${page.value}`,
  () =>
    apiPage<ArticleItem>('/content/article/public/list', {
      user_id: profile.value?.id,
      // VIP 文章不列进公开清单（点进去才需权限）；后端 public_list 的 exclude_vip
      exclude_vip: true,
      page: page.value,
      page_size: PAGE_SIZE,
    }),
  {watch: [page]},
)

const articles = computed(() => articlePage.value?.items ?? [])
const displayName = computed(() => profile.value?.username || username.value)

// ---- 关注（仅客户端、登录态）----
const userStore = useUserStore()
const following = ref(profile.value?.is_following ?? false)
const mutual = ref(profile.value?.is_mutual ?? false)
const acting = ref(false)

/** SSR 的公开请求不带凭据（apiGet 用 credentials:'omit'），登录用户进来后补拉一次真实标记 */
onMounted(async () => {
  if (!userStore.isLoggedIn) return
  try {
    const fresh = await mobileApi.publicProfile(username.value)
    following.value = fresh.is_following
    mutual.value = fresh.is_mutual
  } catch {
    /* 拉取失败不阻塞，保留 SSR 值 */
  }
})

async function toggleFollow(): Promise<void> {
  if (acting.value) return
  if (!userStore.isLoggedIn) {
    await navigateTo('/login')
    return
  }
  const targetId = profile.value?.id
  if (!targetId) return
  acting.value = true
  try {
    const stats = following.value
      ? await followApi.unfollow(targetId)
      : await followApi.follow(targetId)
    following.value = stats.is_following
    mutual.value = stats.is_mutual
  } catch {
    /* 失败静默：标记以服务端下一次为准 */
  } finally {
    acting.value = false
  }
}

// ---- 打赏（仅客户端）----
const rewardOpen = ref(false)

function changePage(next: number): void {
  void navigateTo({query: {...route.query, page: next}})
}

useSeoMeta({
  title: () =>
    t('home.seoTitle', {name: displayName.value, site: site.value.site_name || 'FastBlog'}),
  description: () => profile.value?.bio || undefined,
})
</script>

<template>
  <div v-if="profile" class="mx-auto max-w-read px-4 py-10">
    <header class="flex flex-wrap items-center gap-4">
      <span
        class="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-pill bg-surface-soft text-fg-muted"
      >
        <img
          v-if="profile.profile_picture"
          :alt="displayName"
          :src="profile.profile_picture"
          class="h-full w-full object-cover" decoding="async" loading="lazy"
        >
        <Icon v-else class="h-7 w-7" name="user"/>
      </span>

      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-2">
          <h1 class="text-2xl font-bold tracking-tight text-fg">{{ displayName }}</h1>
          <Badge v-if="profile.is_certified" variant="success">{{ $t('home.certified') }}</Badge>
          <Badge v-if="following && mutual" variant="secondary">{{ $t('fans.mutual') }}</Badge>
          <Badge v-if="profile.vip_level > 0" variant="secondary">
            {{ $t('home.vipBadge', {level: profile.vip_level}) }}
          </Badge>
        </div>
        <p v-if="profile.date_joined" class="mt-1 text-sm text-fg-muted">
          {{ $t('home.joinedAt', {date: formatDate(profile.date_joined)}) }}
        </p>
      </div>

      <ClientOnly>
        <div class="flex items-center gap-2">
          <Button
            :disabled="acting"
            :variant="following ? 'outline' : 'default'"
            @click="toggleFollow"
          >
            <Icon :name="following ? 'user-check' : 'user-plus'" class="h-4 w-4"/>
            {{ following ? $t('fans.unfollow') : $t('fans.follow') }}
          </Button>
          <Button size="sm" variant="outline" @click="rewardOpen = true">
            <Icon class="h-4 w-4" name="gift"/>
            {{ $t('tipping.rewardAuthor') }}
          </Button>
        </div>
      </ClientOnly>
    </header>

    <!-- 私密资料：不展示简介与统计 -->
    <p
      v-if="profile.is_private"
      class="mt-6 rounded-card border border-line bg-surface-soft px-4 py-6 text-center text-sm text-fg-muted"
    >
      {{ $t('home.privateHint') }}
    </p>

    <template v-else>
      <p v-if="profile.bio" class="mt-4 whitespace-pre-line text-sm leading-relaxed text-fg-muted">
        {{ profile.bio }}
      </p>

      <dl class="mt-6 grid grid-cols-3 gap-3">
        <div class="rounded-card border border-line bg-surface p-4 text-center">
          <dt class="text-xs text-fg-muted">{{ $t('home.posts') }}</dt>
          <dd class="mt-1 text-lg font-semibold text-fg">{{ profile.stats.articles }}</dd>
        </div>
        <div class="rounded-card border border-line bg-surface p-4 text-center">
          <dt class="text-xs text-fg-muted">{{ $t('home.followers') }}</dt>
          <dd class="mt-1 text-lg font-semibold text-fg">{{ profile.stats.followers }}</dd>
        </div>
        <div class="rounded-card border border-line bg-surface p-4 text-center">
          <dt class="text-xs text-fg-muted">{{ $t('home.following') }}</dt>
          <dd class="mt-1 text-lg font-semibold text-fg">{{ profile.stats.following }}</dd>
        </div>
      </dl>

      <section class="mt-10">
        <h2 class="text-lg font-semibold tracking-tight text-fg">{{ $t('home.postsTitle') }}</h2>

        <div v-if="pending" class="mt-4 grid gap-6 sm:grid-cols-2">
          <div v-for="i in 4" :key="i" class="space-y-2.5">
            <Skeleton class="h-40 w-full"/>
            <Skeleton class="h-5 w-3/4"/>
          </div>
        </div>

        <EmptyState
          v-else-if="error"
          :description="$t('common.networkError')"
          :title="$t('home.loadFailed')"
        >
          <Button class="mt-3" size="sm" variant="outline" @click="refresh()">
            {{ $t('common.retry') }}
          </Button>
        </EmptyState>

        <EmptyState v-else-if="!articles.length" :title="$t('home.emptyPosts')"/>

        <div v-else class="mt-4 grid gap-8 sm:grid-cols-2">
          <ThemeArticleCard v-for="article in articles" :key="article.id" :article="article"/>
        </div>

        <PaginationBar
          :page="page"
          :pages="articlePage?.pages ?? 0"
          @change="changePage"
        />
      </section>
    </template>

    <ClientOnly>
      <RewardDialog
        v-model="rewardOpen"
        :author-id="profile.id"
        :author-name="profile.username"/>
    </ClientOnly>
  </div>
</template>
