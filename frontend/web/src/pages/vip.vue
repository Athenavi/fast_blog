<script lang="ts" setup>
const {t} = useI18n()
/**
 * VIP 会员页（前台 SSR）
 *
 * 数据源：`GET /api/v3/marketing/vip/public/plans`（公开接口，无需登录）。
 * 接口未部署 / 请求失败 / 套餐为空时统一降级为空态，保证页面不白屏。
 *
 * 订阅入口：登录态存于本地存储（`fastblog.token`），SSR 期间读不到，
 * 因此只在客户端点击时判断，据此跳转登录页或个人中心。
 */
import {STORAGE_TOKEN} from '@/constants'

/** 套餐数据契约（/marketing/vip/public/plans 的 data.plans 元素） */
interface VipPlan {
  id: number
  name: string
  description: string | null
  price: number
  original_price: number | null
  duration_days: number
  level: number
  features: string[]
}

const site = await useSiteInfo()

const {data: payload} = await useAsyncData('vip-plans', () =>
  apiGet<{ plans: VipPlan[] }>('/marketing/vip/public/plans'),
)

/** 请求失败时 apiGet 返回 null，与「后台未配置套餐」一样走空态 */
const plans = computed<VipPlan[]>(() => payload.value?.plans ?? [])

/** 订阅按钮：客户端按本地登录态分流（SSR 渲染期间不涉及该逻辑） */
async function handleSubscribe(): Promise<void> {
  let loggedIn = false
  if (import.meta.client) {
    try {
      loggedIn = Boolean(localStorage.getItem(STORAGE_TOKEN))
    } catch {
      loggedIn = false
    }
  }
  await navigateTo(loggedIn ? '/profile' : '/login')
}

useSeoMeta({
  title: () => `${t('vip.title')} - ${site.value.site_name || 'FastBlog'}`,
  description: () => t('vip.subtitle'),
})
</script>

<template>
  <div class="mx-auto max-w-wide px-4 py-10">
    <!-- 页头 -->
    <header class="max-w-read">
      <h1 class="text-2xl font-bold tracking-tight text-fg sm:text-3xl">{{ $t('vip.title') }}</h1>
      <p class="mt-3 text-base leading-relaxed text-fg-muted">{{ $t('vip.subtitle') }}</p>
    </header>

    <!-- 套餐网格 -->
    <div v-if="plans.length" class="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      <article
        v-for="plan in plans"
        :key="plan.id"
        class="flex flex-col rounded-card border border-line bg-surface p-6"
      >
        <div class="flex items-start justify-between gap-2">
          <h2 class="text-lg font-semibold text-fg">{{ plan.name }}</h2>
          <Badge v-if="plan.level" class="shrink-0" variant="outline">
            {{ $t('vip.level') }} {{ plan.level }}
          </Badge>
        </div>

        <p v-if="plan.description" class="mt-2 text-sm leading-relaxed text-fg-muted">
          {{ plan.description }}
        </p>

        <div class="mt-5 flex items-baseline gap-2">
          <span class="text-3xl font-bold tracking-tight text-fg">
            <span class="text-base font-medium text-fg-muted">{{ $t('vip.currency') }}</span>
            {{ plan.price }}
          </span>
          <span v-if="plan.original_price" class="text-sm text-fg-subtle line-through">
            {{ $t('vip.currency') }}{{ plan.original_price }}
          </span>
        </div>
        <p class="mt-1 text-sm text-fg-subtle">
          {{ $t('vip.durationDays', {days: plan.duration_days}) }}
        </p>

        <ul v-if="plan.features?.length" class="mt-5 space-y-2 text-sm">
          <li v-for="feature in plan.features" :key="feature" class="flex items-start gap-2 text-fg-muted">
            <Icon class="mt-0.5 h-4 w-4 shrink-0 text-primary" name="check"/>
            <span>{{ feature }}</span>
          </li>
        </ul>

        <div class="mt-auto pt-6">
          <Button class="w-full" @click="handleSubscribe">
            {{ $t('vip.subscribe') }}
            <Icon class="h-4 w-4" name="arrow-right"/>
          </Button>
        </div>
      </article>
    </div>

    <!-- 空态：接口未部署 / 请求失败 / 后台未配置套餐 -->
    <EmptyState
      v-else
      :description="$t('vip.contactAdmin')"
      :title="$t('vip.noPlans')"
      class="mt-10"
    />

    <!-- 底部说明 -->
    <p class="mt-10 text-sm leading-relaxed text-fg-subtle">{{ $t('vip.footerNote') }}</p>
  </div>
</template>
