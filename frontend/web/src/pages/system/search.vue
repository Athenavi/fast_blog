<script lang="ts" setup>
/**
 * 搜索设置：Meilisearch 连接配置（后台可改）
 *
 * 配置存后端 `system_settings` 的 `search.meilisearch` 键；保存后**立即生效** ——
 * 后端会把新值推给服务单例，不需要重启（否则"改了没反应"就是假实现）。
 *
 * 密钥只入不出：读取时只回 `has_api_key`。因此这里 `api_key` 留空表示
 * **保持原值**，要清空必须显式勾选 —— 把"没改"和"要清空"区分开，
 * 避免一次误提交静默丢掉凭据。
 */
import {onMounted, reactive, ref} from 'vue'

import {searchSettingsApi, type SearchStats} from '@/api'
import {ElMessage} from '@/utils/feedback'

const {t} = useI18n()

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const reindexing = ref(false)
/** 后端是否已保存过密钥（决定输入框的占位文案） */
const hasApiKey = ref(false)
/** 环境变量侧配置的地址（用于排查"为什么没生效"） */
const envHost = ref<string | null>(null)
const testResult = ref('')
const stats = ref<SearchStats | null>(null)

const form = reactive({
  enabled: true,
  host: '',
  index_name: 'articles',
  api_key: '',
  clear_api_key: false,
})

async function load(): Promise<void> {
  loading.value = true
  try {
    const config = await searchSettingsApi.getConfig()
    form.enabled = config.enabled
    form.host = config.host
    form.index_name = config.index_name
    // 密钥不回显，每次进页面都从空白开始填
    form.api_key = ''
    form.clear_api_key = false
    hasApiKey.value = config.has_api_key
    envHost.value = config.env_host ?? null
  } catch {
    ElMessage.warning(String(t('admin.system.search.loadFailed')))
  } finally {
    loading.value = false
  }
}

async function loadStats(): Promise<void> {
  try {
    stats.value = await searchSettingsApi.stats()
  } catch {
    // 统计失败不影响配置编辑，静默置空
    stats.value = null
  }
}

async function save(): Promise<void> {
  saving.value = true
  try {
    const config = await searchSettingsApi.updateConfig({...form})
    hasApiKey.value = config.has_api_key
    form.api_key = ''
    form.clear_api_key = false
    ElMessage.success(String(t('admin.system.search.saved')))
  } catch {
    ElMessage.warning(String(t('common.operationFailed')))
  } finally {
    saving.value = false
  }
}

async function test(): Promise<void> {
  testing.value = true
  testResult.value = ''
  try {
    const result = await searchSettingsApi.test()
    // 连不上时如实展示后端给的原因，而不是显示一个笼统的"失败"
    testResult.value = result.ok
      ? String(t('admin.system.search.testOk', {version: result.version ?? '', ms: result.latency_ms ?? 0}))
      : result.message
    if (!result.ok) ElMessage.warning(result.message)
  } catch {
    ElMessage.warning(String(t('common.operationFailed')))
  } finally {
    testing.value = false
  }
}

async function reindex(): Promise<void> {
  reindexing.value = true
  try {
    const result = await searchSettingsApi.reindex()
    ElMessage.success(result.message)
    await loadStats()
  } catch {
    ElMessage.warning(String(t('common.operationFailed')))
  } finally {
    reindexing.value = false
  }
}

onMounted(async () => {
  await load()
  await loadStats()
})
</script>

<template>
  <AdminPage :desc="t('admin.system.search.desc')" :title="t('admin.system.search.title')">
    <el-card v-loading="loading" shadow="never">
      <el-form label-position="top">
        <el-form-item :label="t('admin.system.search.enabled')">
          <el-switch v-model="form.enabled"/>
          <p class="form-hint">{{ t('admin.system.search.enabledHint') }}</p>
        </el-form-item>

        <el-form-item :label="t('admin.system.search.host')">
          <el-input v-model="form.host" placeholder="http://127.0.0.1:7700"/>
          <p v-if="envHost" class="form-hint">
            {{ t('admin.system.search.envHint', {host: envHost}) }}
          </p>
        </el-form-item>

        <el-form-item :label="t('admin.system.search.indexName')">
          <el-input v-model="form.index_name"/>
        </el-form-item>

        <el-form-item :label="t('admin.system.search.apiKey')">
          <el-input
            v-model="form.api_key"
            :placeholder="
              hasApiKey
                ? t('admin.system.search.apiKeyKeep')
                : t('admin.system.search.apiKeyEmpty')
            "
            show-password
            type="password"
          />
          <el-checkbox v-if="hasApiKey" v-model="form.clear_api_key">
            {{ t('admin.system.search.clearApiKey') }}
          </el-checkbox>
        </el-form-item>
      </el-form>

      <div class="search-actions">
        <el-button :loading="saving" type="primary" @click="save">
          {{ t('common.save') }}
        </el-button>
        <el-button :loading="testing" @click="test">
          {{ t('admin.system.search.test') }}
        </el-button>
        <el-button :loading="reindexing" @click="reindex">
          {{ t('admin.system.search.reindex') }}
        </el-button>
      </div>

      <el-alert v-if="testResult" :closable="false" :title="testResult" type="info"/>

      <el-descriptions v-if="stats" :column="3" border class="search-stats">
        <el-descriptions-item :label="t('admin.system.search.available')">
          {{ stats.available ? t('common.yes') : t('common.no') }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('admin.system.search.documents')">
          {{ stats.documents }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('admin.system.search.indexing')">
          {{ stats.is_indexing ? t('common.yes') : t('common.no') }}
        </el-descriptions-item>
      </el-descriptions>
      <el-alert
        v-if="stats && !stats.available && stats.message"
        :closable="false"
        :title="stats.message"
        type="warning"
      />
    </el-card>
  </AdminPage>
</template>

<style scoped>
.search-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.search-stats {
  margin-top: 12px;
}
</style>
