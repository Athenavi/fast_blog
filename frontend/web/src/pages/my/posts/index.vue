<script lang="ts" setup>
/**
 * 我的文章
 *
 * 对应原 astro 的 `my/posts/index.astro`。接口走 `mobile/article/mine`（含草稿）。
 */

import {mobileApi, type MobileArticleItem} from '@/api'
import {articleStatusKey, formatDateTime} from '@/utils/format'

const {t} = useI18n()

definePageMeta({layout: 'default', middleware: 'auth', title: 'myPosts.title'})

const STATUS_OPTIONS = [
  {label: t('admin.common.all'), value: undefined},
  {label: t('myPosts.filterDraft'), value: 0},
  {label: t('myPosts.filterPublished'), value: 1},
]

const loading = ref(false)
const list = ref<MobileArticleItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const status = ref<number | undefined>(undefined)
const message = ref('')

async function loadList(): Promise<void> {
  loading.value = true
  try {
    const data = await mobileApi.myArticles({
      page: page.value,
      page_size: pageSize,
      ...(status.value === undefined ? {} : {status: status.value}),
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onFilterChange(): void {
  page.value = 1
  loadList()
}

async function removeOne(item: MobileArticleItem): Promise<void> {
  if (!window.confirm(t('myPosts.confirmDelete', {title: item.title}))) return
  await mobileApi.deleteMyArticle(item.id)
  message.value = t('myPosts.deleted')
  await loadList()
}

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function changePage(next: number): void {
  if (next < 1 || next > totalPages.value) return
  page.value = next
  loadList()
}

onMounted(loadList)
</script>

<template>
  <div class="mx-auto max-w-wide px-4 py-10">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('myPosts.title') }}</h1>
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('myPosts.subtitle') }}</p>
      </div>
      <NuxtLink to="/my/posts/create">
        <Button>
          <Icon class="h-4 w-4" name="plus"/>
          {{ $t('myPosts.write') }}
        </Button>
      </NuxtLink>
    </div>

    <div class="mt-6 flex flex-wrap items-center gap-2">
      <button
        v-for="option in STATUS_OPTIONS"
        :key="String(option.value)"
        type="button"
        @click="status = option.value; onFilterChange()"
      >
        <Badge :variant="status === option.value ? 'default' : 'outline'" class="cursor-pointer px-3 py-1 text-sm">
          {{ option.label }}
        </Badge>
      </button>
      <Button :icon="undefined" class="ml-auto" size="sm" variant="outline" @click="loadList">
        <Icon class="h-4 w-4" name="refresh-cw"/>
        {{ $t('common.refresh') }}
      </Button>
    </div>

    <p v-if="message" class="mt-4 rounded-control bg-success-soft px-3 py-2 text-sm text-success">{{ message }}</p>

    <div v-if="loading" class="mt-6 space-y-3">
      <Skeleton v-for="i in 4" :key="i" class="h-16 w-full"/>
    </div>

    <div v-else-if="list.length" class="mt-6 divide-y divide-line rounded-card border border-line bg-surface">
      <div v-for="item in list" :key="item.id" class="flex flex-wrap items-center gap-3 p-4">
        <div class="min-w-0 flex-1">
          <p class="truncate font-medium text-fg">{{ item.title }}</p>
          <div class="mt-1 flex flex-wrap items-center gap-3 text-xs text-fg-subtle">
            <Badge :variant="item.status === 1 ? 'success' : 'warning'" class="text-[11px]">
              {{ t(articleStatusKey(item.status)) }}
            </Badge>
            <span>{{ t('myPosts.updatedAt', {time: formatDateTime(item.updated_at)}) }}</span>
            <span v-if="item.views">{{ t('myPosts.viewsCount', {n: item.views}) }}</span>
            <span v-for="tag in (item.tags || []).slice(0, 3)" :key="tag" class="text-fg-muted">#{{ tag }}</span>
          </div>
        </div>

        <div class="flex items-center gap-2 text-sm">
          <NuxtLink :to="`/my/posts/edit/${item.id}`">
            <Button size="sm" variant="outline">{{ $t('admin.common.edit') }}</Button>
          </NuxtLink>
          <Button class="text-danger" size="sm" variant="ghost" @click="removeOne(item)">
            <Icon class="h-4 w-4" name="trash-2"/>
          </Button>
        </div>
      </div>
    </div>

    <EmptyState
      v-else
      class="mt-6"
      :description="$t('myPosts.emptyDesc')"
      :title="$t('myPosts.emptyTitle')"
    />

    <nav v-if="totalPages > 1" class="flex items-center justify-center gap-2 pt-8">
      <Button :disabled="page <= 1" size="sm" variant="outline" @click="changePage(page - 1)">{{
          $t('myPosts.prevPage')
        }}
      </Button>
      <span class="text-sm text-fg-muted">{{ page }} / {{ totalPages }}</span>
      <Button :disabled="page >= totalPages" size="sm" variant="outline" @click="changePage(page + 1)">
        {{ $t('myPosts.nextPage') }}
      </Button>
    </nav>
  </div>
</template>
