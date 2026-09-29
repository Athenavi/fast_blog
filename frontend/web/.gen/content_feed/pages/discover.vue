<script lang="ts" setup>
/**
 * 发现流（content/feed，公开）
 *
 * 数据源：v3 `GET /api/v3/content/feed/discover`（**公开**，匿名可访问）——
 * 全站已发布文章聚合成事件流（`UNION ALL` 排序分页）；打开
 * `include_interactions` 后额外纳入全站最新的点赞与评论。
 *
 * `content/feed` 与 `mobile/feed`（关注流）**不是同一个模块**：后者只列登录
 * 用户关注的人发布的文章，本页是无门槛的全站发现。
 *
 * 加载：纯客户端（走 `contentFeedApi`，与前台动态流一致），首屏渲染骨架，
 * 数据在 `onMounted` 拉取。
 */
import {contentFeedApi, type FeedEvent} from '@/api'
import {formatDateTime} from '@/utils/format'

definePageMeta({layout: 'default', title: 'contentFeed.discoverTitle'})

const {t} = useI18n()
const site = await useSiteInfo()

const PAGE_SIZE = 20
const includeInteractions = ref(false)
const events = ref<FeedEvent[]>([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const loading = ref(false)
const failed = ref(false)

type FeedEventType = FeedEvent['type']

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    const result = await contentFeedApi.discover({
      page: page.value,
      page_size: PAGE_SIZE,
      include_interactions: includeInteractions.value,
    })
    events.value = result.items ?? []
    total.value = result.total ?? 0
    pages.value = result.pages ?? 0
  } catch {
    failed.value = true
    events.value = []
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

function toggleInteractions(): void {
  includeInteractions.value = !includeInteractions.value
  page.value = 1
  void load()
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
  title: () => t('contentFeed.seoTitle', {name: site.value.site_name || 'FastBlog'}),
  description: () => t('contentFeed.seoDescription'),
})

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-wide px-4 py-10">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('contentFeed.discoverTitle') }}</h1>
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('contentFeed.discoverSubtitle') }}</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <Button
          :variant="includeInteractions ? 'default' : 'outline'"
          size="sm"
          @click="toggleInteractions"
        >
          {{ $t('contentFeed.includeInteractions') }}
        </Button>
        <Button :disabled="loading" size="sm" variant="outline" @click="load()">
          <Icon class="h-4 w-4" name="refresh-cw"/>
          {{ $t('common.refresh') }}
        </Button>
      </div>
    </div>

    <p v-if="total" class="mt-4 text-sm text-fg-muted">{{ $t('contentFeed.total', {n: total}) }}</p>

    <div v-if="loading" class="mt-6 space-y-3">
      <Skeleton v-for="i in 6" :key="i" class="h-20 w-full"/>
    </div>

    <ErrorState
      v-else-if="failed"
      :description="$t('common.networkError')"
      :title="$t('contentFeed.loadFailed')"
      class="mt-6"
      @retry="load()"
    />

    <EmptyState
      v-else-if="!events.length"
      :description="$t('contentFeed.emptyDesc')"
      :title="$t('contentFeed.empty')"
      class="mt-6"
    />

    <ul v-else class="mt-6 space-y-3">
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

    <PaginationBar :page="page" :pages="pages" @change="onPage"/>
  </div>
</template>
