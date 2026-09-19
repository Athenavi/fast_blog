<script lang="ts" setup>
/**
 * CDN 配置（T5-11 批次 4）
 *
 * 对齐 v3 `/ops/cdn/config`（GET/PUT，单配置）。
 * api_token 只写不读（响应只有 has_api_token），留空保持原值；
 * 实际清缓存/预热等远端动作为二期。
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
  </div>
</template>
