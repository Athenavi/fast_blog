<script lang="ts" setup>
import {computed, onMounted, ref} from 'vue'

import {pluginAction} from '@/utils/pluginAction'

/**
 * 短信服务（sms-provider 插件后台页）
 *
 * 对应 `plugins/sms-provider/frontend/admin/Page.tsx`：
 * 服务商 / 签名 / 配置状态三张卡 + 测试发送 + 已配置凭据列表。
 */
interface Settings {
  provider?: string | null
  aliyun_sign_name?: string | null
  tencent_sign_name?: string | null
  aliyun_access_key_id?: string | null
  tencent_secret_id?: string | null
  twilio_account_sid?: string | null
}

const settings = ref<Settings>({})
const loading = ref(true)
const error = ref('')

const phone = ref('')
const code = ref('')
const sending = ref(false)
const sendResult = ref<{ success?: boolean; error?: string } | null>(null)

const providerLabel = computed(() => {
  switch (settings.value.provider) {
    case 'aliyun':
      return '阿里云'
    case 'tencent':
      return '腾讯云'
    case 'twilio':
      return 'Twilio'
    default:
      return '未配置'
  }
})

const signName = computed(
  () => settings.value.aliyun_sign_name || settings.value.tencent_sign_name || '—',
)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const response = await pluginAction<Settings>('sms-provider', 'get_settings')
    settings.value = response.data ?? {}
    if (!response.success) error.value = response.error || '加载配置失败'
  } finally {
    loading.value = false
  }
}

async function sendTest(): Promise<void> {
  if (!phone.value) return
  sending.value = true
  sendResult.value = null
  try {
    const response = await pluginAction<{ success?: boolean; error?: string }>('sms-provider', 'send_sms', {
      phone: phone.value,
      code: code.value || '123456',
    })
    sendResult.value = response.data ?? {success: response.success, error: response.error}
  } finally {
    sending.value = false
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

    <!-- 状态卡片 -->
    <div class="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
      <div class="rounded-card border border-line bg-surface p-5">
        <div class="flex items-center gap-3">
          <span class="flex h-10 w-10 items-center justify-center rounded-control bg-primary-soft">
            <Icon class="h-5 w-5 text-primary" name="message-square"/>
          </span>
          <div>
            <p class="text-sm text-fg-muted">当前服务商</p>
            <p class="text-lg font-semibold text-fg">{{ providerLabel }}</p>
          </div>
        </div>
      </div>

      <div class="rounded-card border border-line bg-surface p-5">
        <div class="flex items-center gap-3">
          <span class="flex h-10 w-10 items-center justify-center rounded-control bg-success-soft">
            <Icon class="h-5 w-5 text-success" name="smartphone"/>
          </span>
          <div>
            <p class="text-sm text-fg-muted">签名</p>
            <p class="text-lg font-semibold text-fg">{{ signName }}</p>
          </div>
        </div>
      </div>

      <div class="rounded-card border border-line bg-surface p-5">
        <div class="flex items-center gap-3">
          <span class="flex h-10 w-10 items-center justify-center rounded-control bg-surface-soft">
            <Icon
              :class="settings.provider ? 'text-success' : 'text-fg-subtle'"
              :name="settings.provider ? 'circle-check' : 'circle-x'"
              class="h-5 w-5"
            />
          </span>
          <div>
            <p class="text-sm text-fg-muted">状态</p>
            <p class="text-lg font-semibold text-fg">{{ settings.provider ? '已配置' : '未配置' }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 测试发送 -->
    <div class="mb-6 rounded-card border border-line bg-surface p-5">
      <h3 class="mb-4 text-sm font-semibold text-fg">测试短信发送</h3>
      <div class="flex flex-wrap gap-3">
        <el-input v-model="phone" class="min-w-[200px] flex-1" placeholder="手机号"/>
        <el-input v-model="code" class="w-40" placeholder="验证码（默认 123456）"/>
        <el-button :disabled="!phone" :loading="sending" type="primary" @click="sendTest">
          <Icon class="mr-1 h-4 w-4" name="send"/>
          发送测试
        </el-button>
      </div>

      <p
        v-if="sendResult"
        :class="sendResult.success ? 'bg-success-soft text-success' : 'bg-danger-soft text-danger'"
        class="mt-3 rounded-control p-3 text-xs"
      >
        {{ sendResult.success ? '✓ 发送成功' : `✗ 发送失败：${sendResult.error || '未知错误'}` }}
      </p>
    </div>

    <!-- 配置信息 -->
    <div class="rounded-card border border-line bg-surface p-5">
      <h3 class="mb-3 text-sm font-semibold text-fg">短信配置</h3>

      <div v-if="loading" class="space-y-3">
        <Skeleton class="h-5 w-52"/>
        <Skeleton class="h-5 w-40"/>
      </div>

      <div v-else class="space-y-2 text-sm text-fg-muted">
        <p v-if="settings.aliyun_access_key_id">阿里云：<code class="text-fg">已配置</code></p>
        <p v-if="settings.tencent_secret_id">腾讯云：<code class="text-fg">已配置</code></p>
        <p v-if="settings.twilio_account_sid">Twilio：<code class="text-fg">已配置</code></p>
        <p v-if="!settings.aliyun_access_key_id && !settings.tencent_secret_id && !settings.twilio_account_sid">
          暂未配置短信参数，请在插件设置中配置
        </p>
      </div>
    </div>
  </div>
</template>
