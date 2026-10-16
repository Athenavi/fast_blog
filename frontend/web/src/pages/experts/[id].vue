<script lang="ts" setup>
/**
 * 认证专家详情（公开）
 *
 * 数据源：`GET /api/v3/gamification/certification/experts/{user_id}`
 * —— 只认「已通过且未过期」的认证；不是专家（或已过期）时后端返回 404，这里也 404。
 *
 * 页面底部提供「打赏 TA」入口：打赏走真实支付链路（见 `RewardDialog`）。
 */
import type {CertificationItem} from '@/api'
import {formatDate, formatFileSize} from '@/utils/format'

const route = useRoute()
const {t} = useI18n()
const requestUrl = useRequestURL()

const userId = Number(route.params.id)

const {data: expert} = await useAsyncData(`expert-${userId}`, () =>
  apiGet<CertificationItem>(`/gamification/certification/experts/${userId}`),
)

if (!expert.value) {
  throw createError({statusCode: 404, statusMessage: t('experts.notFound')})
}

const rewardOpen = ref(false)

const displayName = computed(
  () => expert.value?.username || t('experts.userFallback', {id: userId}),
)

const affiliation = computed(() =>
  [expert.value?.organization, expert.value?.position, expert.value?.department]
    .filter(Boolean)
    .join(' · '),
)

const breadcrumbs = computed(() => [
  {label: t('site.navHome'), to: '/'},
  {label: t('experts.title'), to: '/experts'},
  {label: displayName.value},
])

useBreadcrumbJsonLd(breadcrumbs.value, requestUrl.origin)

useSeoMeta({
  title: () => t('experts.detailSeoTitle', {name: displayName.value}),
  description: () => expert.value?.intro || t('experts.seoDescription'),
})
</script>

<template>
  <div v-if="expert" class="mx-auto max-w-read px-4 py-10">
    <Breadcrumbs :items="breadcrumbs"/>

    <header class="mt-6 flex flex-wrap items-center gap-4">
      <span class="flex h-14 w-14 items-center justify-center rounded-pill bg-primary-soft text-primary">
        <Icon class="h-7 w-7" name="badge-check"/>
      </span>
      <div class="min-w-0 flex-1">
        <h1 class="text-2xl font-bold tracking-tight text-fg">{{ displayName }}</h1>
        <div class="mt-1.5 flex flex-wrap items-center gap-2 text-sm text-fg-muted">
          <Badge variant="secondary">{{ expert.cert_type_name || expert.cert_type }}</Badge>
          <span>{{ $t('experts.validUntil', {date: formatDate(expert.expires_at)}) }}</span>
        </div>
      </div>

      <ClientOnly>
        <Button size="sm" @click="rewardOpen = true">
          <Icon class="h-4 w-4" name="gift"/>
          {{ $t('tipping.rewardAuthor') }}
        </Button>
      </ClientOnly>
    </header>

    <dl class="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div class="rounded-card border border-line bg-surface p-4">
        <dt class="text-xs text-fg-muted">{{ $t('experts.certType') }}</dt>
        <dd class="mt-1 text-sm font-medium text-fg">{{ expert.cert_type_name || expert.cert_type }}</dd>
      </div>
      <div class="rounded-card border border-line bg-surface p-4">
        <dt class="text-xs text-fg-muted">{{ $t('experts.issuedAt') }}</dt>
        <dd class="mt-1 text-sm font-medium text-fg">{{ formatDate(expert.issued_at) }}</dd>
      </div>
      <div v-if="affiliation" class="rounded-card border border-line bg-surface p-4 sm:col-span-2">
        <dt class="text-xs text-fg-muted">{{ $t('experts.affiliation') }}</dt>
        <dd class="mt-1 text-sm font-medium text-fg">{{ affiliation }}</dd>
      </div>
      <div v-if="expert.work_years" class="rounded-card border border-line bg-surface p-4">
        <dt class="text-xs text-fg-muted">{{ $t('experts.workYears') }}</dt>
        <dd class="mt-1 text-sm font-medium text-fg">
          {{ $t('experts.workYearsValue', {n: expert.work_years}) }}
        </dd>
      </div>
    </dl>

    <section v-if="expert.intro" class="mt-8">
      <h2 class="text-base font-semibold text-fg">{{ $t('experts.intro') }}</h2>
      <p class="mt-2 whitespace-pre-line text-sm leading-relaxed text-fg-muted">{{ expert.intro }}</p>
    </section>

    <section v-if="expert.achievements" class="mt-8">
      <h2 class="text-base font-semibold text-fg">{{ $t('experts.achievements') }}</h2>
      <p class="mt-2 whitespace-pre-line text-sm leading-relaxed text-fg-muted">{{ expert.achievements }}</p>
    </section>

    <section v-if="expert.portfolio_url" class="mt-8">
      <h2 class="text-base font-semibold text-fg">{{ $t('experts.portfolio') }}</h2>
      <a
        :href="expert.portfolio_url"
        class="mt-2 inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
        rel="noopener noreferrer nofollow"
        target="_blank"
      >
        <Icon class="h-4 w-4" name="link"/>
        {{ expert.portfolio_url }}
      </a>
    </section>

    <section v-if="expert.documents?.length" class="mt-8">
      <h2 class="text-base font-semibold text-fg">{{ $t('experts.documents') }}</h2>
      <ul class="mt-2 divide-y divide-line rounded-card border border-line bg-surface">
        <li v-for="doc in expert.documents" :key="doc.id" class="flex items-center justify-between gap-3 px-4 py-2.5">
          <a
            :href="doc.file_url"
            class="min-w-0 truncate text-sm text-primary hover:underline"
            rel="noopener noreferrer nofollow"
            target="_blank"
          >
            {{ doc.file_name || doc.file_url }}
          </a>
          <span class="shrink-0 text-xs text-fg-subtle">{{ formatFileSize(doc.file_size) }}</span>
        </li>
      </ul>
    </section>

    <RewardDialog
      v-model="rewardOpen"
      :author-id="expert.user_id"
      :author-name="expert.username"/>
  </div>
</template>
