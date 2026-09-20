<script lang="ts" setup>
/**
 * VIP 会员页（前台）
 *
 * 三段内容：
 *  1. **公开套餐**（SSR + SEO）：`GET /marketing/vip/public/plans`；
 *  2. **我的订阅**（客户端，仅登录时拉取）：`GET /mobile/vip/my-subscription`；
 *  3. **付费内容**（同上）：`GET /mobile/vip/premium-content`。
 *
 * 「开通 / 续费」走真实支付：`POST /mobile/vip/create-payment` → payment-gateway 插件下单 →
 * 返回的 `payment.payment_url` 存在就打开支付页；**付款后要等网关回调经插件验签通过才真正开通**，
 * 所以这里只如实展示订单号与支付入口，不写"已开通"。
 *
 * 登录态存于本地存储（SSR 期间读不到），因此订阅区放在 `ClientOnly` 里、
 * 未登录时不发请求（避免 401 触发跳登录），公开套餐部分照常 SSR。
 */
import {storeToRefs} from 'pinia'

import {type MyVipInfo, type PremiumContentItem, vipSelfApi} from '@/api'
import {useUserStore} from '@/store/modules/user'
import {formatDate, formatDateTime} from '@/utils/format'

const {t} = useI18n()
const userStore = useUserStore()
const {isLoggedIn} = storeToRefs(userStore)
const site = await useSiteInfo()

/** 套餐数据契约（/marketing/vip/public/plans 的 data.plans 元素） */
interface PublicPlan {
  id: number
  name: string
  description: string | null
  price: number
  original_price: number | null
  duration_days: number
  level: number
  features: string[]
}

const {data: payload} = await useAsyncData('vip-plans', () =>
  apiGet<{ plans: PublicPlan[] }>('/marketing/vip/public/plans'),
)

const plans = computed<PublicPlan[]>(() => payload.value?.plans ?? [])

// ---------------------------------------------------------------- 我的订阅
const mine = ref<MyVipInfo | null>(null)
const premium = ref<PremiumContentItem[]>([])
const loadingMine = ref(false)
const busyPlan = ref<number | null>(null)
const cancelling = ref(false)
const notice = ref('')
const error = ref('')

const SUBSCRIPTION_STATUS: Record<number, string> = {
  0: 'vip.statusActive',
  1: 'vip.statusExpired',
  2: 'vip.statusCancelled',
}

const ORDER_STATUS: Record<string, string> = {
  pending: 'vip.orderStatusPending',
  paid: 'vip.orderStatusPaid',
  failed: 'vip.orderStatusFailed',
}

function subscriptionLabel(status?: number): string {
  return t(SUBSCRIPTION_STATUS[status ?? 0] ?? 'vip.statusExpired')
}

function orderLabel(status?: string | null): string {
  return t(ORDER_STATUS[String(status)] ?? 'vip.orderStatusFailed')
}

async function loadMine(): Promise<void> {
  if (!userStore.isLoggedIn) return
  loadingMine.value = true
  try {
    const [info, content] = await Promise.all([
      vipSelfApi.my(),
      vipSelfApi.premiumContent({page: 1, page_size: 6}).catch(() => null),
    ])
    mine.value = info
    premium.value = content?.items ?? []
  } catch {
    /* 错误提示由 request 拦截器统一处理，这里只保证界面不炸 */
  } finally {
    loadingMine.value = false
  }
}

/** 开通 / 续费：真实下单（金额由服务端按套餐取） */
async function subscribe(plan: PublicPlan): Promise<void> {
  notice.value = ''
  error.value = ''
  if (!userStore.isLoggedIn) {
    await navigateTo('/login')
    return
  }
  busyPlan.value = plan.id
  try {
    const result = await vipSelfApi.createPayment(plan.id)
    const url = typeof result.payment?.payment_url === 'string' ? result.payment.payment_url : ''
    notice.value = t('vip.orderCreated', {order: result.order.order_no})
    if (url && import.meta.client) {
      window.open(url, '_blank', 'noopener,noreferrer')
    }
    await loadMine()
  } catch (thrown) {
    error.value = thrown instanceof Error ? thrown.message : t('common.networkError')
  } finally {
    busyPlan.value = null
  }
}

async function cancelSubscription(): Promise<void> {
  notice.value = ''
  error.value = ''
  cancelling.value = true
  try {
    await vipSelfApi.cancel()
    notice.value = t('vip.cancelSuccess')
    await loadMine()
  } catch (thrown) {
    error.value = thrown instanceof Error ? thrown.message : t('common.networkError')
  } finally {
    cancelling.value = false
  }
}

onMounted(loadMine)

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

    <p v-if="notice" class="mt-6 rounded-card border border-line bg-surface-soft px-4 py-2.5 text-sm text-fg">
      {{ notice }}
    </p>
    <p v-if="error" class="mt-6 rounded-card border border-danger/40 bg-surface-soft px-4 py-2.5 text-sm text-danger">
      {{ error }}
    </p>

    <!-- 我的订阅（仅客户端） -->
    <ClientOnly>
      <section class="mt-8 rounded-card border border-line bg-surface p-5">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 class="text-base font-semibold text-fg">{{ $t('vip.myTitle') }}</h2>
          <Button v-if="isLoggedIn" :disabled="loadingMine" size="sm" variant="outline" @click="loadMine()">
            <Icon class="h-4 w-4" name="refresh-cw"/>
            {{ $t('common.refresh') }}
          </Button>
        </div>

        <div v-if="!isLoggedIn" class="mt-3 text-sm text-fg-muted">
          {{ $t('vip.notLoggedIn') }}
          <NuxtLink class="ml-1 text-primary hover:underline" to="/login">{{ $t('site.goLogin') }}</NuxtLink>
        </div>

        <div v-else-if="loadingMine && !mine" class="mt-3 space-y-2">
          <Skeleton class="h-6 w-48"/>
          <Skeleton class="h-6 w-64"/>
        </div>

        <template v-else-if="mine">
          <div class="mt-3 flex flex-wrap items-center gap-3">
            <Badge :variant="mine.status.is_vip ? 'success' : 'secondary'">
              {{ mine.status.is_vip ? $t('vip.active') : $t('vip.inactive') }}
            </Badge>
            <span v-if="mine.status.is_vip" class="text-sm text-fg">
              {{ $t('vip.myPlan', {name: mine.status.plan_name || '-', level: mine.status.level}) }}
            </span>
            <span v-if="mine.status.expires_at" class="text-sm text-fg-muted">
              {{ $t('vip.expiresAt', {date: formatDate(mine.status.expires_at)}) }}
            </span>
            <span v-if="mine.status.is_vip" class="text-sm text-fg-subtle">
              {{ $t('vip.daysLeft', {n: mine.status.days_left}) }}
            </span>
            <Button
              v-if="mine.status.is_vip"
              :disabled="cancelling"
              class="ml-auto"
              size="sm"
              variant="outline"
              @click="cancelSubscription()"
            >
              <Icon v-if="cancelling" class="h-4 w-4 animate-spin" name="loader-circle"/>
              {{ $t('vip.cancel') }}
            </Button>
          </div>

          <!-- 待支付订单 -->
          <div v-if="mine.pending_orders.length" class="mt-4">
            <p class="text-sm font-medium text-fg">{{ $t('vip.pendingOrders') }}</p>
            <p class="mt-1 text-xs text-fg-subtle">{{ $t('vip.payHint') }}</p>
            <ul class="mt-2 space-y-1.5">
              <li
                v-for="order in mine.pending_orders"
                :key="order.id"
                class="flex flex-wrap items-center justify-between gap-2 rounded-card border border-line bg-surface-soft px-3 py-2 text-sm"
              >
                <span class="text-fg-muted">{{ $t('vip.orderNo', {order: order.order_no}) }}</span>
                <span class="text-fg-muted">
                  {{ order.plan_name || '-' }} · {{ $t('vip.currency') }}{{ order.amount }}
                </span>
                <Badge variant="warning">{{ $t('vip.orderStatusPending') }}</Badge>
              </li>
            </ul>
          </div>

          <!-- 订阅记录 -->
          <div v-if="mine.subscriptions.length" class="mt-4">
            <p class="text-sm font-medium text-fg">{{ $t('vip.history') }}</p>
            <ul class="mt-2 divide-y divide-line rounded-card border border-line">
              <li
                v-for="row in mine.subscriptions"
                :key="row.id"
                class="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm"
              >
                <span class="text-fg-muted">
                  {{ row.plan_name || '-' }} · {{ formatDate(row.starts_at) }} ~ {{ formatDate(row.expires_at) }}
                </span>
                <Badge :variant="row.status === 0 ? 'success' : 'secondary'">
                  {{ subscriptionLabel(row.status) }}
                </Badge>
              </li>
            </ul>
          </div>
        </template>
      </section>
    </ClientOnly>

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
          <Button :disabled="busyPlan === plan.id" class="w-full" @click="subscribe(plan)">
            <Icon v-if="busyPlan === plan.id" class="h-4 w-4 animate-spin" name="loader-circle"/>
            <Icon v-else class="h-4 w-4" name="credit-card"/>
            {{ $t('vip.subscribe') }}
          </Button>
          <p class="mt-2 text-xs text-fg-subtle">{{ $t('vip.payHint') }}</p>
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

    <!-- 付费内容（仅客户端，需登录） -->
    <ClientOnly>
      <section v-if="isLoggedIn" class="mt-12">
        <h2 class="text-base font-semibold text-fg">{{ $t('vip.premiumTitle') }}</h2>
        <p class="mt-1 text-sm text-fg-muted">{{ $t('vip.premiumHint') }}</p>

        <p v-if="!premium.length" class="mt-4 text-sm text-fg-muted">{{ $t('vip.premiumEmpty') }}</p>
        <ul v-else class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <li
            v-for="item in premium"
            :key="item.id"
            class="rounded-card border border-line bg-surface p-4"
          >
            <NuxtLink
              v-if="item.slug && item.accessible"
              :to="`/articles/${item.slug}`"
              class="text-sm font-medium text-fg hover:text-primary"
            >
              {{ item.title }}
            </NuxtLink>
            <span v-else class="text-sm font-medium text-fg">{{ item.title }}</span>

            <p v-if="item.excerpt" class="mt-1 line-clamp-2 text-xs text-fg-muted">{{ item.excerpt }}</p>
            <div class="mt-2 flex items-center gap-2">
              <Badge :variant="item.accessible ? 'success' : 'secondary'">
                {{
                  item.accessible ? $t('vip.premiumAccessible') : $t('vip.premiumLocked', {level: item.required_vip_level})
                }}
              </Badge>
              <span class="text-xs text-fg-subtle">{{ formatDateTime(item.updated_at || item.created_at) }}</span>
            </div>
          </li>
        </ul>
      </section>
    </ClientOnly>

    <!-- 底部说明 -->
    <p class="mt-10 text-sm leading-relaxed text-fg-subtle">{{ $t('vip.footerNote') }}</p>
  </div>
</template>
