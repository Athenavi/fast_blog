<script lang="ts" setup>
/**
 * 关注流（personalized feed，批次 17）
 *
 * 数据源：v3 `/api/v3/mobile/feed`（**仅需认证**）—— 按当前登录用户的真实关注关系
 * 聚合**已发布**文章（后端复用公开列表的排序：置顶 → sort_order → 发布时间倒序）。
 * 关注为空时后端返回空页，本页据此展示引导文案 + 去发现作者。
 *
 * 需登录：`middleware: 'auth'`；`/feed` 在 nuxt.config.ts 里配置为 `ssr: false`，纯 CSR。
 *
 * 追加（批次 19 · content/feed 动态流）：本页在原有「关注流文章」之外，接入同域
 * `content/feed` 模块的「关注时间线」（事件流）与「我的流概览」——见下方各区块。
 */
import {contentFeedApi, feedApi, type FeedEvent, type FeedStats} from '@/api'
import type {ArticleItem} from '@/types/content'
import {formatDateTime} from '@/utils/format'

definePageMeta({layout: 'default', middleware: 'auth', title: 'feed.title'})

const {t} = useI18n()
const site = await useSiteInfo()

/** 每页条数（后端上限 50） */
const PAGE_SIZE = 20
const articles = ref<ArticleItem[]>([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const loading = ref(false)
const failed = ref(false)

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    const result = await feedApi.list({page: page.value, page_size: PAGE_SIZE})
    articles.value = result.items ?? []
    total.value = result.total ?? 0
    pages.value = result.pages ?? 0
  } catch {
    failed.value = true
    articles.value = []
    total.value = 0
    pages.value = 0
  } finally {
    loading.value = false
  }
}

function onPage(next: number): void {
  page.value = next
  void load()
}

// ---- 我的流概览（content/feed/stats，仅登录）----
const stats = ref<FeedStats | null>(null)

async function loadStats(): Promise<void> {
  try {
    stats.value = await contentFeedApi.stats()
  } catch {
    /* 概览拉取失败不阻塞页面：保留原有文章列表与时间线 */
    stats.value = null
  }
}

// ---- 关注时间线 · 事件流（content/feed/timeline，仅登录）----
type FeedEventType = FeedEvent['type']
const eventTypeOptions: FeedEventType[] = ['article', 'like', 'comment']
const activeType = ref<FeedEventType | ''>('')
const events = ref<FeedEvent[]>([])
const eventTotal = ref(0)
const eventPages = ref(0)
const eventPage = ref(1)
const eventLoading = ref(false)
const eventFailed = ref(false)

async function loadEvents(): Promise<void> {
  eventLoading.value = true
  eventFailed.value = false
  try {
    const result = await contentFeedApi.timeline({
      page: eventPage.value,
      page_size: PAGE_SIZE,
      event_types: activeType.value || undefined,
    })
    events.value = result.items ?? []
    eventTotal.value = result.total ?? 0
    eventPages.value = result.pages ?? 0
  } catch {
    eventFailed.value = true
    events.value = []
    eventTotal.value = 0
    eventPages.value = 0
  } finally {
    eventLoading.value = false
  }
}

function filterByType(value: FeedEventType | ''): void {
  activeType.value = value
  eventPage.value = 1
  void loadEvents()
}

function onEventPage(next: number): void {
  eventPage.value = next
  void loadEvents()
}

function eventTypeLabel(type: FeedEventType): string {
  if (type === 'like') return t('contentFeed.typeLike')
  if (type === 'comment') return t('contentFeed.typeComment')
  return t('contentFeed.typeArticle')
}

function eventArticleLink(event: FeedEvent): string {
  const article = event.article
  if (!article) return '/articles'
  return article.slug ? `/articles/${article.slug}` : `/articles/id/${article.id}`
}

useSeoMeta({
  title: () => t('feed.seoTitle', {name: site.value.site_name || 'FastBlog'}),
  description: () => t('feed.subtitle'),
})

onMounted(load)
onMounted(() => {
  void loadStats()
  void loadEvents()
})
</script>

<template>
  <div class="mx-auto max-w-wide px-4 py-10">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('feed.title') }}</h1>
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('feed.subtitle') }}</p>
      </div>
      <Button :disabled="loading" size="sm" variant="outline" @click="load()">
        <Icon class="h-4 w-4" name="refresh-cw"/>
        {{ $t('common.refresh') }}
      </Button>
    </div>

    <!-- 我的流概览（content/feed/stats） -->
    <div v-if="stats" class="mt-6 grid gap-3 sm:grid-cols-3">
      <div class="rounded-card border border-line bg-surface p-4 text-center">
        <p class="text-xs text-fg-muted">{{ $t('contentFeed.statsFollowing') }}</p>
        <p class="mt-1 text-lg font-semibold text-fg">{{ stats.following }}</p>
      </div>
      <div class="rounded-card border border-line bg-surface p-4 text-center">
        <p class="text-xs text-fg-muted">{{ $t('contentFeed.statsTimelineEvents') }}</p>
        <p class="mt-1 text-lg font-semibold text-fg">{{ stats.timeline_events }}</p>
      </div>
      <div class="rounded-card border border-line bg-surface p-4 text-center">
        <p class="text-xs text-fg-muted">{{ $t('contentFeed.statsByType') }}</p>
        <p class="mt-1 text-sm text-fg">
          {{ $t('contentFeed.statArticle') }} {{ stats.by_type.article || 0 }} ·
          {{ $t('contentFeed.statLike') }} {{ stats.by_type.like || 0 }} ·
          {{ $t('contentFeed.statComment') }} {{ stats.by_type.comment || 0 }}
        </p>
      </div>
    </div>

    <p v-if="stats?.hint" class="mt-3 text-sm text-fg-muted">{{ stats.hint }}</p>

    <p v-if="total" class="mt-4 text-sm text-fg-muted">{{ $t('feed.total', {n: total}) }}</p>

    <ArticleListSection
      v-if="loading || articles.length"
      :articles="articles"
      :empty-description="$t('feed.emptyDesc')"
      :empty-title="$t('feed.empty')"
      :loading="loading"
      :page="page"
      :pages="pages"
      class="mt-6"
      @change="onPage"
    />

    <ErrorState
      v-else-if="failed"
      :description="$t('common.networkError')"
      :title="$t('feed.loadFailed')"
      class="mt-6"
      @retry="load()"
    />

    <EmptyState v-else :description="$t('feed.emptyDesc')" :title="$t('feed.empty')" class="mt-6">
      <NuxtLink class="mt-3" to="/experts">
        <Button size="sm">{{ $t('feed.goDiscover') }}</Button>
      </NuxtLink>
    </EmptyState>

    <!-- 关注动态 · 事件时间线（content/feed/timeline） -->
    <section class="mt-12 border-t border-line pt-10">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 class="text-lg font-semibold tracking-tight text-fg">{{ $t('contentFeed.timelineTitle') }}</h2>
          <p class="mt-1 text-sm text-fg-muted">{{ $t('contentFeed.timelineSubtitle') }}</p>
        </div>
        <div class="flex flex-wrap items-center gap-1.5">
          <Button
            :variant="activeType === '' ? 'default' : 'outline'"
            size="sm"
            @click="filterByType('')"
          >
            {{ $t('contentFeed.filterAll') }}
          </Button>
          <Button
            v-for="option in eventTypeOptions"
            :key="option"
            :variant="activeType === option ? 'default' : 'outline'"
            size="sm"
            @click="filterByType(option)"
          >
            {{ eventTypeLabel(option) }}
          </Button>
        </div>
      </div>

      <p class="mt-2 text-xs text-fg-subtle">{{ $t('contentFeed.filterTypesHint') }}</p>

      <p v-if="eventTotal" class="mt-3 text-sm text-fg-muted">{{ $t('contentFeed.total', {n: eventTotal}) }}</p>

      <div v-if="eventLoading" class="mt-4 space-y-3">
        <Skeleton v-for="i in 4" :key="i" class="h-20 w-full"/>
      </div>

      <ErrorState
        v-else-if="eventFailed"
        :description="$t('common.networkError')"
        :title="$t('contentFeed.loadFailed')"
        class="mt-4"
        @retry="loadEvents()"
      />

      <EmptyState
        v-else-if="!events.length"
        :description="$t('contentFeed.emptyDesc')"
        :title="$t('contentFeed.empty')"
        class="mt-4"
      />

      <ul v-else class="mt-4 space-y-3">
        <li
          v-for="(event, index) in events"
          :key="`${event.type}-${event.article?.id ?? 'x'}-${index}`"
          class="rounded-card border border-line bg-surface p-4"
        >
          <div class="flex flex-wrap items-center gap-2 text-xs text-fg-subtle">
            <Badge variant="secondary">{{ eventTypeLabel(event.type) }}</Badge>
            <span v-if="event.actor_id">{{ $t('contentFeed.actorLabel', {id: event.actor_id}) }}</span>
            <span>{{ formatDateTime(event.at) }}</span>
          </div>

          <template v-if="event.article">
            <NuxtLink
              :to="eventArticleLink(event)"
              class="mt-2 block text-base font-semibold leading-snug text-fg transition-colors hover:text-primary"
            >
              {{ event.article.title }}
            </NuxtLink>
            <p v-if="event.article.excerpt" class="mt-1 line-clamp-2 text-sm leading-relaxed text-fg-muted">
              {{ event.article.excerpt }}
            </p>
            <div class="mt-2 flex items-center gap-4 text-xs text-fg-subtle">
              <span class="inline-flex items-center gap-1">
                <Icon class="h-3.5 w-3.5" name="eye"/>
                {{ $t('contentFeed.views', {n: event.article.views}) }}
              </span>
              <span class="inline-flex items-center gap-1">
                <Icon class="h-3.5 w-3.5" name="heart"/>
                {{ $t('contentFeed.likes', {n: event.article.likes}) }}
              </span>
            </div>
          </template>

          <p v-else-if="event.extra" class="mt-2 text-sm leading-relaxed text-fg-muted">
            {{ event.extra }}
          </p>
        </li>
      </ul>

      <PaginationBar :page="eventPage" :pages="eventPages" @change="onEventPage"/>
    </section>
  </div>
</template>
