<script lang="ts" setup>
/**
 * CDN 配置（T5-11 批次 4；远端动作批次 18）
 *
 * 对齐 v3 `/ops/cdn/config`（GET/PUT，单配置）与 `/ops/cdn/purge`、`/ops/cdn/preheat`。
 *
 * 凭据只有一个密文槽 `api_token`（只写不读，响应只给 `has_api_token`，留空保持原值），
 * 它在不同 provider 下语义不同 —— 页面按 provider 切换 label 与配套的标识字段
 * （非敏感标识存 `settings`：AWS 的 access_key_id / distribution_id / region，
 * 阿里云的 access_key_id，腾讯云的 secret_id / region，以及可选的 endpoint）。
 *
 * **远端动作是真实调用**：cloudflare 走官方 purge_cache，aws_cloudfront 走 SigV4 签名的
 * CreateInvalidation（XML），aliyun_cdn / tencent_cdn 走各自的 RPC / TC3 签名接口，
 * custom 调自建网关。Cloudflare 与 CloudFront **没有预热接口**、阿里/腾讯**不支持一键
 * 全量刷新** —— 这些都被后端明确拒绝，页面如实显示原因，不显示任何"看起来成功"的结果。
 */
import {ElMessage} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {cdnApi, type CdnConfig} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ops.cdn.title',
  permission: 'module_ops:cdn:view',
})

const {t} = useI18n()

const loading = ref(false)
const saving = ref(false)
const hasApiToken = ref(false)

/**
 * 厂商非敏感标识的存放位置：`settings`。
 * 敏感密钥统一走 `api_token` 单槽（按 provider 语义不同：Cloudflare API Token /
 * AWS Secret Access Key / 阿里云 AccessKey Secret / 腾讯云 SecretKey），落库前加密。
 */
const VENDOR_SETTING_KEYS = ['access_key_id', 'secret_id', 'distribution_id', 'region', 'endpoint']

const form = reactive<{
  provider: string;
  domain: string;
  cdn_url: string;
  api_token: string;
  zone_id: string;
  access_key_id: string;
  secret_id: string;
  distribution_id: string;
  region: string;
  endpoint: string;
  settings_text: string;
  is_active: boolean
}>({
  provider: 'cloudflare',
  domain: '',
  cdn_url: '',
  api_token: '',
  zone_id: '',
  access_key_id: '',
  secret_id: '',
  distribution_id: '',
  region: '',
  endpoint: '',
  settings_text: '',
  is_active: false,
})

/** 同一个凭据槽在不同 provider 下的语义完全不同 → label 随 provider 变 */
const TOKEN_LABEL_KEYS: Record<string, string> = {
  cloudflare: 'admin.ops.cdn.tokenLabelCloudflare',
  aws_cloudfront: 'admin.ops.cdn.tokenLabelAws',
  aliyun_cdn: 'admin.ops.cdn.tokenLabelAliyun',
  tencent_cdn: 'admin.ops.cdn.tokenLabelTencent',
  custom: 'admin.ops.cdn.tokenLabelCustom',
}

const tokenLabel = computed(() => t(TOKEN_LABEL_KEYS[form.provider] || 'admin.ops.cdn.apiToken'))
const usesAccessKeyId = computed(() =>
  ['aws_cloudfront', 'aliyun_cdn'].includes(form.provider),
)
const usesRegion = computed(() => ['aws_cloudfront', 'tencent_cdn'].includes(form.provider))
const regionPlaceholder = computed(() =>
  form.provider === 'tencent_cdn' ? 'ap-guangzhou' : 'us-east-1',
)

async function load(): Promise<void> {
  loading.value = true
  try {
    const config: CdnConfig = await cdnApi.getConfig()
    hasApiToken.value = config.has_api_token
    form.provider = config.provider || 'cloudflare'
    form.domain = config.domain || ''
    form.cdn_url = config.cdn_url || ''
    form.api_token = ''
    form.zone_id = config.zone_id || ''
    // 厂商标识从 settings 里读出来单独编辑，textarea 只留"其它扩展设置"
    const settings: Record<string, unknown> = {...(config.settings || {})}
    form.access_key_id = String(settings.access_key_id ?? '')
    form.secret_id = String(settings.secret_id ?? '')
    form.distribution_id = String(settings.distribution_id ?? '')
    form.region = String(settings.region ?? '')
    form.endpoint = String(settings.endpoint ?? '')
    for (const key of VENDOR_SETTING_KEYS) delete settings[key]
    form.settings_text = Object.keys(settings).length ? JSON.stringify(settings, null, 2) : ''
    form.is_active = config.is_active
  } finally {
    loading.value = false
  }
}

onMounted(load)

/** 只写当前 provider 用得到的标识，避免切 provider 后残留旧厂商字段 */
function vendorSettings(): Record<string, string> {
  const vendor: Record<string, string> = {}
  if (form.provider === 'aws_cloudfront') {
    vendor.access_key_id = form.access_key_id.trim()
    vendor.distribution_id = form.distribution_id.trim()
    vendor.region = form.region.trim()
  } else if (form.provider === 'aliyun_cdn') {
    vendor.access_key_id = form.access_key_id.trim()
  } else if (form.provider === 'tencent_cdn') {
    vendor.secret_id = form.secret_id.trim()
    vendor.region = form.region.trim()
  }
  const endpoint = form.endpoint.trim()
  if (endpoint) vendor.endpoint = endpoint
  return Object.fromEntries(Object.entries(vendor).filter(([, value]) => value))
}

async function submit(): Promise<void> {
  let settings: Record<string, unknown> = {}
  if (form.settings_text.trim()) {
    try {
      const parsed = JSON.parse(form.settings_text)
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        ElMessage.warning(t('admin.ops.cdn.invalidJson'))
        return
      }
      settings = parsed as Record<string, unknown>
    } catch {
      ElMessage.warning(t('admin.ops.cdn.invalidJson'))
      return
    }
  }
  Object.assign(settings, vendorSettings())
  saving.value = true
  try {
    await cdnApi.saveConfig({
      provider: form.provider,
      domain: form.domain || null,
      cdn_url: form.cdn_url || null,
      api_token: form.api_token || undefined,
      zone_id: form.zone_id || null,
      settings,
      is_active: form.is_active,
    })
    ElMessage.success(t('admin.common.save'))
    await load()
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------- 远端动作
const purgeUrlsText = ref('')
const purgeEverything = ref(false)
const purging = ref(false)
const preheating = ref(false)

/** URL 支持换行或逗号分隔 */
function parsePurgeUrls(): string[] {
  return purgeUrlsText.value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

async function runPurge(): Promise<void> {
  const urls = parsePurgeUrls()
  if (!purgeEverything.value && !urls.length) {
    ElMessage.warning(t('admin.ops.cdn.remote.urlsRequired'))
    return
  }
  purging.value = true
  try {
    const result = await cdnApi.purge({urls, purge_everything: purgeEverything.value})
    ElMessage.success(result.message || t('admin.ops.cdn.remote.purgeOk'))
  } finally {
    purging.value = false
  }
}

async function runPreheat(): Promise<void> {
  const urls = parsePurgeUrls()
  if (!urls.length) {
    ElMessage.warning(t('admin.ops.cdn.remote.urlsRequired'))
    return
  }
  preheating.value = true
  try {
    const result = await cdnApi.preheat({urls})
    ElMessage.success(result.message || t('admin.ops.cdn.remote.preheatOk'))
  } finally {
    preheating.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <el-card v-loading="loading" shadow="never">
      <template #header>
        <span>{{ $t('admin.ops.cdn.title') }}</span>
      </template>

      <el-form :model="form" label-width="130px" style="max-width: 640px">
        <el-form-item :label="$t('admin.ops.cdn.provider')" required>
          <el-select v-model="form.provider" style="width: 100%">
            <el-option label="Cloudflare" value="cloudflare"/>
            <el-option label="AWS CloudFront" value="aws_cloudfront"/>
            <el-option label="阿里云 CDN" value="aliyun_cdn"/>
            <el-option label="腾讯云 CDN" value="tencent_cdn"/>
            <el-option label="Custom" value="custom"/>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.cdn.domain')">
          <el-input v-model="form.domain" placeholder="cdn.example.com"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.cdn.cdnUrl')">
          <el-input v-model="form.cdn_url" placeholder="https://cdn.example.com"/>
        </el-form-item>
        <el-form-item v-if="form.provider === 'cloudflare'" :label="$t('admin.ops.cdn.zoneId')">
          <el-input v-model="form.zone_id"/>
        </el-form-item>
        <el-form-item v-if="usesAccessKeyId" :label="$t('admin.ops.cdn.accessKeyId')">
          <el-input v-model="form.access_key_id" placeholder="AKIA..."/>
        </el-form-item>
        <el-form-item v-if="form.provider === 'tencent_cdn'" :label="$t('admin.ops.cdn.secretId')">
          <el-input v-model="form.secret_id" placeholder="AKID..."/>
        </el-form-item>
        <el-form-item v-if="form.provider === 'aws_cloudfront'" :label="$t('admin.ops.cdn.distributionId')">
          <el-input v-model="form.distribution_id" placeholder="E2ABCDEFGHIJK"/>
        </el-form-item>
        <el-form-item v-if="usesRegion" :label="$t('admin.ops.cdn.region')">
          <el-input v-model="form.region" :placeholder="regionPlaceholder"/>
        </el-form-item>
        <el-form-item v-if="form.provider !== 'custom'" :label="$t('admin.ops.cdn.endpoint')">
          <el-input v-model="form.endpoint" :placeholder="$t('admin.ops.cdn.endpointPlaceholder')"/>
          <div class="form-hint">{{ $t('admin.ops.cdn.endpointHint') }}</div>
        </el-form-item>
        <el-form-item :label="tokenLabel">
          <el-input
            v-model="form.api_token"
            :placeholder="hasApiToken ? $t('admin.ops.cdn.tokenKeepHint') : $t('admin.ops.cdn.tokenPlaceholder')"
            show-password
            type="password"
          />
          <div class="form-hint">{{ $t('admin.ops.cdn.tokenHint') }}</div>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.cdn.settings')">
          <el-input
            v-model="form.settings_text"
            :autosize="{minRows: 5, maxRows: 14}"
            :placeholder="$t('admin.ops.cdn.settingsPlaceholder')"
            type="textarea"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.ops.cdn.active')">
          <el-switch v-model="form.is_active"/>
        </el-form-item>
        <el-form-item>
          <el-button v-auth="'module_ops:cdn:edit'" :loading="saving" type="primary" @click="submit">
            {{ $t('admin.common.save') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 远端动作：真实调用厂商接口；未接入/未配置时后端会带原因拒绝 -->
    <el-card class="remote-card" shadow="never">
      <template #header>
        <span>{{ $t('admin.ops.cdn.remote.title') }}</span>
      </template>

      <el-form label-width="130px" style="max-width: 640px">
        <el-form-item :label="$t('admin.ops.cdn.remote.urls')">
          <el-input
            v-model="purgeUrlsText"
            :autosize="{minRows: 3, maxRows: 8}"
            :placeholder="$t('admin.ops.cdn.remote.urlsPlaceholder')"
            type="textarea"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.ops.cdn.remote.purgeEverything')">
          <el-switch v-model="purgeEverything"/>
          <span class="remote-hint">{{ $t('admin.ops.cdn.remote.purgeEverythingHint') }}</span>
        </el-form-item>
        <el-form-item>
          <el-button
            v-auth="'module_ops:cdn:execute'"
            :loading="purging"
            type="primary"
            @click="runPurge"
          >
            {{ $t('admin.ops.cdn.remote.purge') }}
          </el-button>
          <el-button
            v-auth="'module_ops:cdn:execute'"
            :loading="preheating"
            @click="runPreheat"
          >
            {{ $t('admin.ops.cdn.remote.preheat') }}
          </el-button>
        </el-form-item>
        <p class="remote-hint">{{ $t('admin.ops.cdn.remote.hint') }}</p>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.remote-card {
  margin-top: 16px;
}

.remote-hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.form-hint {
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-secondary);
}
</style>
