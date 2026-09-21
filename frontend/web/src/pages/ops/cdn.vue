<script lang="ts" setup>
/**
 * CDN 配置（T5-11 批次 4；远端动作批次 18）
 *
 * 对齐 v3 `/ops/cdn/config`（GET/PUT，单配置）与 `/ops/cdn/purge`、`/ops/cdn/preheat`。
 * api_token 只写不读（响应只有 has_api_token），留空保持原值。
 *
 * **远端动作是真实调用**：cloudflare 走官方 purge_cache API、custom 调自建网关；
 * 厂商签名未接入的 provider（aws/aliyun/tencent）与 cloudflare 的预热都会被后端
 * 明确拒绝 —— 页面如实显示错误原因，不显示任何"看起来成功"的结果。
 */
import {ElMessage} from '@/utils/feedback'
import {onMounted, reactive, ref} from 'vue'

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

const form = reactive<{
  provider: string;
  domain: string;
  cdn_url: string;
  api_token: string;
  zone_id: string;
  settings_text: string;
  is_active: boolean
}>({
  provider: 'cloudflare',
  domain: '',
  cdn_url: '',
  api_token: '',
  zone_id: '',
  settings_text: '',
  is_active: false,
})

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
    form.settings_text = config.settings ? JSON.stringify(config.settings, null, 2) : ''
    form.is_active = config.is_active
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function submit(): Promise<void> {
  let settings: Record<string, unknown> | null = null
  if (form.settings_text.trim()) {
    try {
      settings = JSON.parse(form.settings_text)
    } catch {
      ElMessage.warning(t('admin.ops.cdn.invalidJson'))
      return
    }
  }
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
        <el-form-item :label="$t('admin.ops.cdn.apiToken')">
          <el-input
            v-model="form.api_token"
            :placeholder="hasApiToken ? $t('admin.ops.cdn.tokenKeepHint') : $t('admin.ops.cdn.tokenPlaceholder')"
            show-password
            type="password"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.ops.cdn.zoneId')">
          <el-input v-model="form.zone_id"/>
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
</style>
