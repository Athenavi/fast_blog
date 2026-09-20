<script lang="ts" setup>
/**
 * 认证专家列表（公开）
 *
 * 数据源：v3 `/api/v3/gamification/certification/experts` —— 只列**已通过且未过期**的认证
 * （后端按 `expires_at` 现算，不是内存里的一个布尔位）。这页不需要登录，SSR 直出。
 */
import type {CertificationItem, CertTypeItem} from '@/api'
import {formatDate} from '@/utils/format'

const PAGE_SIZE = 12

const route = useRoute()
const router = useRouter()
const {t} = useI18n()
const site = await useSiteInfo()

const page = computed(() => Number(route.query.page || 1))
const certType = computed(() => (route.query.type ? String(route.query.type) : undefined))

const {data: pageData, pending} = await useAsyncData(
  () => `experts-${page.value}-${certType.value ?? 'all'}`,
  () =>
    apiPage<CertificationItem>('/gamification/certification/experts', {
      page: page.value,
      page_size: PAGE_SIZE,
      cert_type: certType.value,
    }),
  {watch: [page, certType]},
)

const {data: types} = await useAsyncData('certification-types', () =>
  apiGet<CertTypeItem[]>('/gamification/certification/types'),
)

const experts = computed(() => pageData.value?.items ?? [])

function selectType(code?: string): void {
  router.push({query: code ? {type: code} : {}})
}

function changePage(next: number): void {
  router.push({query: {...route.query, page: next}})
}

function displayName(item: CertificationItem): string {
  return item.username || t('experts.userFallback', {id: item.user_id})
}

/** 机构 / 职位 / 部门拼一行，空值不占位 */
function affiliation(item: CertificationItem): string {
  return [item.organization, item.position, item.department].filter(Boolean).join(' · ')
}

useSeoMeta({
  title: () => t('experts.seoTitle', {name: site.value.site_name || 'FastBlog'}),
  description: () => t('experts.seoDescription'),
})
</script>

<template>
  <div class="mx-auto max-w-wide px-4 py-10">
    <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('experts.title') }}</h1>
    <p class="mt-1.5 text-sm text-fg-muted">{{ $t('experts.subtitle') }}</p>

    <div v-if="(types || []).length" class="mt-6 flex flex-wrap gap-2">
      <button @click="selectType()">
        <Badge :variant="certType ? 'outline' : 'default'" class="cursor-pointer px-3 py-1 text-sm">
          {{ $t('experts.allTypes') }}
        </Badge>
      </button>
      <button v-for="item in types || []" :key="item.code" @click="selectType(item.code)">
        <Badge
          :variant="certType === item.code ? 'default' : 'outline'"
          class="cursor-pointer px-3 py-1 text-sm"
        >
          {{ item.name }}
        </Badge>
      </button>
    </div>

    <div v-if="pending" class="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <Skeleton v-for="i in 6" :key="i" class="h-32 w-full"/>
    </div>

    <EmptyState v-else-if="!experts.length" :description="$t('experts.emptyDesc')" :title="$t('experts.empty')"/>

    <ul v-else class="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <li v-for="item in experts" :key="item.id" class="rounded-card border border-line bg-surface p-4">
        <div class="flex items-start gap-3">
          <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-pill bg-primary-soft text-primary">
            <Icon class="h-5 w-5" name="badge-check"/>
          </span>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <NuxtLink
                :to="`/experts/${item.user_id}`"
                class="truncate text-sm font-semibold text-fg transition-colors hover:text-primary"
              >
                {{ displayName(item) }}
              </NuxtLink>
              <Badge variant="secondary">{{ item.cert_type_name || item.cert_type }}</Badge>
            </div>

            <p v-if="affiliation(item)" class="mt-1 truncate text-xs text-fg-muted">{{ affiliation(item) }}</p>
            <p v-if="item.intro" class="mt-2 line-clamp-2 text-sm text-fg-muted">{{ item.intro }}</p>

            <p class="mt-2 text-xs text-fg-subtle">
              {{ $t('experts.validUntil', {date: formatDate(item.expires_at)}) }}
            </p>

            <NuxtLink
              :to="`/experts/${item.user_id}`"
              class="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
            >
              {{ $t('experts.viewDetail') }}
              <Icon class="h-3.5 w-3.5" name="arrow-right"/>
            </NuxtLink>
          </div>
        </div>
      </li>
    </ul>

    <PaginationBar :page="page" :pages="pageData?.pages ?? 0" @change="changePage"/>
  </div>
</template>
