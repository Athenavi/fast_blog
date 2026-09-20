<script lang="ts" setup>
/**
 * 打赏弹窗（文章详情页与专家页共用）
 *
 * 走 v3 `POST /commerce/tipping/tip`：先落 `pending` 订单 → 调批次 7 的 payment-gateway
 * 插件下单，返回的 `payment` 就是插件给的调起参数（支付宝 / Stripe 是 `payment_url`，
 * 微信是 `prepay_id`）。
 *
 * **刻意不做「假装已支付」**：打赏只有在网关回调经插件验签后才变成 `paid`，
 * 所以这里只如实展示订单号与支付入口，成功文案也是「订单已创建，完成支付后到账」。
 */
import {type PaymentLaunchInfo, type TipConfig, type TipItem, tippingApi} from '@/api'
import {useUserStore} from '@/store/modules/user'

const props = defineProps<{
  modelValue: boolean
  authorId: number
  authorName?: string | null
  articleId?: number | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const {t} = useI18n()
const userStore = useUserStore()

const config = ref<TipConfig | null>(null)
const amountCents = ref(0)
const customYuan = ref('')
const message = ref('')

const loading = ref(false)
const submitting = ref(false)
const error = ref('')

/** 下单成功后的结果（订单号 + 插件调起参数） */
const placed = ref<TipItem | null>(null)
const payUrl = ref('')

function close(): void {
  emit('update:modelValue', false)
}

function yuanToCents(value: string): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed <= 0) return 0
  return Math.round(parsed * 100)
}

/** 选了预设就用预设，填了自定义金额则以自定义为准（后端按「分」校验范围） */
const effectiveCents = computed(() =>
  customYuan.value.trim() ? yuanToCents(customYuan.value) : amountCents.value,
)

/** 预设金额展示（分 → 元，去掉多余的 .00） */
function showYuan(cents: number): string {
  const yuan = cents / 100
  return Number.isInteger(yuan) ? String(yuan) : yuan.toFixed(2)
}

const invalidHint = computed(() => {
  const cents = effectiveCents.value
  if (!cents) return t('tipping.amountRequired')
  if (config.value && cents < config.value.min_amount) {
    return t('tipping.amountTooSmall', {min: showYuan(config.value.min_amount)})
  }
  if (config.value && cents > config.value.max_amount) {
    return t('tipping.amountTooLarge', {max: showYuan(config.value.max_amount)})
  }
  return ''
})

function reset(): void {
  amountCents.value = config.value?.presets[0] ?? 0
  customYuan.value = ''
  message.value = ''
  error.value = ''
  placed.value = null
  payUrl.value = ''
}

async function loadConfig(): Promise<void> {
  loading.value = true
  try {
    config.value = await tippingApi.config()
    amountCents.value = config.value.presets[0] ?? config.value.min_amount
  } catch {
    error.value = t('tipping.configFailed')
  } finally {
    loading.value = false
  }
}

async function submit(): Promise<void> {
  error.value = ''
  if (!userStore.isLoggedIn) {
    close()
    await navigateTo('/login')
    return
  }
  if (invalidHint.value) {
    error.value = invalidHint.value
    return
  }
  submitting.value = true
  try {
    const result = await tippingApi.tip({
      author_id: props.authorId,
      amount: effectiveCents.value,
      article_id: props.articleId ?? null,
      message: message.value.trim() || null,
      return_url: import.meta.client ? window.location.href : null,
    })
    placed.value = result.tip
    const payment: PaymentLaunchInfo = result.payment ?? {}
    const url = typeof payment.payment_url === 'string' ? payment.payment_url : ''
    payUrl.value = url
    if (url && import.meta.client) {
      window.open(url, '_blank', 'noopener,noreferrer')
    }
  } catch (thrown) {
    error.value = thrown instanceof Error ? thrown.message : t('common.networkError')
  } finally {
    submitting.value = false
  }
}

function openPayUrl(): void {
  if (payUrl.value && import.meta.client) {
    window.open(payUrl.value, '_blank', 'noopener,noreferrer')
  }
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') close()
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) {
      window.removeEventListener('keydown', onKeydown)
      return
    }
    window.addEventListener('keydown', onKeydown)
    reset()
    if (!config.value) void loadConfig()
  },
)

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-[60] flex items-center justify-center bg-canvas/80 p-4 backdrop-blur-sm"
      @click.self="close"
    >
      <div class="w-full max-w-md overflow-hidden rounded-card border border-line bg-surface">
        <div class="flex items-center justify-between border-b border-line px-4 py-3">
          <h2 class="text-sm font-semibold text-fg">{{ $t('tipping.dialogTitle') }}</h2>
          <button
            class="inline-flex h-7 w-7 items-center justify-center rounded-control text-fg-muted transition-colors hover:bg-surface-soft hover:text-fg"
            type="button"
            @click="close"
          >
            <Icon class="h-4 w-4" name="x"/>
          </button>
        </div>

        <div class="space-y-4 px-4 py-4">
          <div
            v-if="!userStore.isLoggedIn"
            class="rounded-card border border-line bg-surface-soft px-3 py-6 text-center text-sm text-fg-muted"
          >
            {{ $t('tipping.loginHint') }}
            <NuxtLink class="ml-1 text-primary hover:underline" to="/login" @click="close">
              {{ $t('site.goLogin') }}
            </NuxtLink>
          </div>

          <template v-else-if="placed">
            <div class="rounded-card border border-line bg-surface-soft p-3 text-sm">
              <p class="font-medium text-fg">{{ $t('tipping.placedTitle') }}</p>
              <p class="mt-1 text-xs text-fg-muted">{{ $t('tipping.placedHint') }}</p>
              <dl class="mt-2 space-y-0.5 text-xs text-fg-subtle">
                <div class="flex justify-between gap-3">
                  <dt>{{ $t('tipping.orderNo') }}</dt>
                  <dd class="truncate text-fg-muted">{{ placed.order_no }}</dd>
                </div>
                <div class="flex justify-between gap-3">
                  <dt>{{ $t('tipping.amountLabel') }}</dt>
                  <dd class="text-fg-muted">¥{{ placed.amount_yuan }}</dd>
                </div>
              </dl>
            </div>

            <Button v-if="payUrl" class="w-full" type="button" @click="openPayUrl">
              <Icon class="h-4 w-4" name="credit-card"/>
              {{ $t('tipping.openPayPage') }}
            </Button>
            <p v-else class="text-xs text-fg-muted">{{ $t('tipping.payOfflineHint') }}</p>
          </template>

          <template v-else>
            <p class="text-sm text-fg-muted">
              {{ $t('tipping.dialogTo', {name: authorName || $t('tipping.authorFallback', {id: authorId})}) }}
            </p>

            <div v-if="loading" class="space-y-2">
              <Skeleton class="h-9 w-full"/>
              <Skeleton class="h-9 w-full"/>
            </div>

            <template v-else>
              <div>
                <p class="mb-2 text-xs font-medium text-fg-muted">{{ $t('tipping.amountLabel') }}</p>
                <div class="grid grid-cols-3 gap-2">
                  <button
                    v-for="preset in config?.presets ?? []"
                    :key="preset"
                    :class="!customYuan.trim() && amountCents === preset
                      ? 'border-primary bg-primary-soft text-primary'
                      : 'border-line text-fg-muted hover:border-primary hover:text-primary'"
                    class="rounded-control border px-2 py-2 text-sm font-medium transition-colors"
                    type="button"
                    @click="amountCents = preset; customYuan = ''"
                  >
                    ¥{{ showYuan(preset) }}
                  </button>
                </div>
                <Input
                  v-model="customYuan"
                  :placeholder="$t('tipping.customAmountPlaceholder', {
                    min: showYuan(config?.min_amount ?? 0),
                    max: showYuan(config?.max_amount ?? 0),
                  })"
                  class="mt-2"
                  inputmode="decimal"
                />
              </div>

              <div>
                <p class="mb-2 text-xs font-medium text-fg-muted">{{ $t('tipping.messageLabel') }}</p>
                <textarea
                  v-model="message"
                  :placeholder="$t('tipping.messagePlaceholder')"
                  class="w-full rounded-control border border-line px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                  maxlength="255"
                  rows="2"
                />
              </div>

              <p v-if="error" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

              <div class="flex items-center justify-between pt-1">
                <span class="text-xs text-fg-subtle">
                  {{ $t('tipping.payHint') }}
                </span>
                <Button :disabled="submitting" type="button" @click="submit">
                  <Icon v-if="submitting" class="h-4 w-4 animate-spin" name="loader-circle"/>
                  <Icon v-else class="h-4 w-4" name="gift"/>
                  {{ $t('tipping.submit') }}
                </Button>
              </div>
            </template>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>
