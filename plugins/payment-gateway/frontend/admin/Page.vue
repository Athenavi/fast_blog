<script lang="ts" setup>
import {onMounted, ref} from 'vue'

import {pluginAction} from '@/utils/pluginAction'

/**
 * 支付网关（payment-gateway 插件后台页）
 *
 * 对应 `plugins/payment-gateway/frontend/admin/Page.tsx`：
 * 展示当前支付配置（提供商 / 货币 / 沙箱）+ 发起一笔测试支付 + 显示已配置的凭据。
 */
interface Settings {
  provider?: string | null
  currency?: string | null
  alipay_sandbox?: boolean | null
  alipay_app_id?: string | null
  wechat_app_id?: string | null
  stripe_secret_key?: string | null
}

const settings = ref<Settings>({})
const loading = ref(true)
const error = ref('')

const orderId = ref('')
const amount = ref('')
const paying = ref(false)
const result = ref<unknown>(null)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const response = await pluginAction<Settings>('payment-gateway', 'get_settings')
    settings.value = response.data ?? {}
    if (!response.success) error.value = response.error || '加载配置失败'
  } finally {
    loading.value = false
  }
}

async function testPayment(): Promise<void> {
  paying.value = true
  try {
    const response = await pluginAction('payment-gateway', 'create_payment', {
      order_id: orderId.value || `test_${Date.now()}`,
      amount: Number.parseInt(amount.value, 10) || 100,
      subject: '测试支付',
    })
    result.value = response.data
  } finally {
    paying.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="p-4">
    <div class="mb-3 flex justify-end">
      <el-button :loading="loading" size="small" @click="load">
        <Icon class="mr-1 h-3.5 w-3.5" name="refresh-cw"/>
        刷新
      </el-button>
    </div>

    <p v-if="error" class="mb-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

    <!-- 配置卡片 -->
    <div class="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
      <div class="rounded-card border border-line bg-surface p-5">
        <div class="mb-3 flex items-center gap-3">
          <span class="flex h-10 w-10 items-center justify-center rounded-control bg-primary-soft">
            <Icon class="h-5 w-5 text-primary" name="credit-card"/>
          </span>
          <div>
            <p class="text-sm text-fg-muted">当前提供商</p>
            <p class="text-lg font-semibold text-fg">{{ settings.provider || '未配置' }}</p>
          </div>
        </div>
      </div>

      <div class="rounded-card border border-line bg-surface p-5">
        <div class="mb-3 flex items-center gap-3">
          <span class="flex h-10 w-10 items-center justify-center rounded-control bg-success-soft">
            <Icon class="h-5 w-5 text-success" name="dollar-sign"/>
          </span>
          <div>
            <p class="text-sm text-fg-muted">货币</p>
            <p class="text-lg font-semibold uppercase text-fg">{{ settings.currency || 'cny' }}</p>
          </div>
        </div>
      </div>

      <div class="rounded-card border border-line bg-surface p-5">
        <div class="mb-3 flex items-center gap-3">
          <span class="flex h-10 w-10 items-center justify-center rounded-control bg-primary-soft">
            <Icon class="h-5 w-5 text-primary" name="circle-check"/>
          </span>
          <div>
            <p class="text-sm text-fg-muted">沙箱模式</p>
            <p class="text-lg font-semibold text-fg">{{ settings.alipay_sandbox ? '开启' : '关闭' }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 测试支付 -->
    <div class="mb-6 rounded-card border border-line bg-surface p-5">
      <h3 class="mb-4 text-sm font-semibold text-fg">测试支付</h3>
      <div class="flex flex-wrap gap-3">
        <el-input v-model="orderId" class="min-w-[200px] flex-1" placeholder="订单号（可选，自动生成）"/>
        <el-input v-model="amount" class="w-32" placeholder="金额（分）" type="number"/>
        <el-button :loading="paying" type="primary" @click="testPayment">
          <Icon class="mr-1 h-4 w-4" name="arrow-right"/>
          发起测试
        </el-button>
      </div>
      <pre
        v-if="result"
        class="mt-3 overflow-auto rounded-control bg-surface-soft p-3 text-xs text-fg-muted"
      >{{ JSON.stringify(result, null, 2) }}</pre>
    </div>

    <!-- 凭据 -->
    <div class="rounded-card border border-line bg-surface p-5">
      <h3 class="mb-3 text-sm font-semibold text-fg">支付配置</h3>

      <div v-if="loading" class="space-y-3">
        <Skeleton class="h-5 w-64"/>
        <Skeleton class="h-5 w-48"/>
      </div>

      <div v-else class="space-y-2 text-sm text-fg-muted">
        <p v-if="settings.alipay_app_id">
          支付宝 AppID：<code class="text-fg">{{ settings.alipay_app_id }}</code>
        </p>
        <p v-if="settings.wechat_app_id">
          微信 AppID：<code class="text-fg">{{ settings.wechat_app_id }}</code>
        </p>
        <p v-if="settings.stripe_secret_key">Stripe：<code class="text-fg">已配置</code></p>
        <p v-if="!settings.alipay_app_id && !settings.wechat_app_id && !settings.stripe_secret_key">
          暂未配置支付参数，请在插件设置中配置
        </p>
      </div>
    </div>
  </div>
</template>
