<script lang="ts" setup>
/**
 * 翻译管理 · 机器翻译面板
 *
 * 从 `pages/system/translation.vue` 的「机器翻译」标签页抽出：提供商可用状态、单条翻译、
 * 批量翻译。
 *
 * ## 加载时机与原实现保持一致
 *
 * 原页面在 `@tab-change` 里**切到本标签才加载**，触发 `loadProviders()`，并靠原
 * `loadedTabs` 去重。这里用 `active` 属性 + `watch(immediate)` 还原。
 *
 * 诚实降级：未配置密钥时后端返回 `available=false`，页面**如实提示未配置**，
 * 绝不伪装成功（`translateUnavailable` / `batchUnavailable`）。
 */
import {Refresh} from '@element-plus/icons-vue'
import {computed, reactive, ref, watch} from 'vue'

import {type MTBatchResult, type MTProviderStatus, type MTTranslateResult, translationApi,} from '@/api'
import {ElMessage} from '@/utils/feedback'

const props = defineProps<{
  /** 本标签页是否激活 */
  active: boolean
}>()

const {t} = useI18n()

const mtLoading = ref(false)
const providers = ref<MTProviderStatus[]>([])

async function loadProviders(): Promise<void> {
  mtLoading.value = true
  const [res] = await Promise.allSettled([translationApi.mtProviders()])
  if (res.status === 'fulfilled') providers.value = res.value
  mtLoading.value = false
}

const translateLoading = ref(false)
const translateForm = reactive({text: '', source_lang: 'auto', target_lang: '', provider: 'baidu'})
const translateResult = ref<MTTranslateResult | null>(null)

const translateUnavailable = computed(
  () => translateResult.value !== null && !translateResult.value.available,
)

async function runTranslate(): Promise<void> {
  if (!translateForm.text.trim()) {
    ElMessage.warning(t('admin.system.translation.mt.textRequired'))
    return
  }
  if (!translateForm.target_lang.trim()) {
    ElMessage.warning(t('admin.system.translation.mt.targetRequired'))
    return
  }
  translateLoading.value = true
  try {
    translateResult.value = await translationApi.mtTranslate({
      text: translateForm.text,
      source_lang: translateForm.source_lang,
      target_lang: translateForm.target_lang.trim(),
      provider: translateForm.provider,
    })
  } finally {
    translateLoading.value = false
  }
}

const batchLoading = ref(false)
const batchForm = reactive({
  textsText: '',
  source_lang: 'auto',
  target_lang: '',
  provider: 'baidu',
  delay: 0.2,
})
const batchResult = ref<MTBatchResult | null>(null)

const batchUnavailable = computed(
  () => batchResult.value !== null && !batchResult.value.available,
)

async function runBatch(): Promise<void> {
  const texts = batchForm.textsText
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
  if (!texts.length) {
    ElMessage.warning(t('admin.system.translation.mt.batchRequired'))
    return
  }
  if (!batchForm.target_lang.trim()) {
    ElMessage.warning(t('admin.system.translation.mt.targetRequired'))
    return
  }
  batchLoading.value = true
  try {
    batchResult.value = await translationApi.mtBatch({
      texts,
      source_lang: batchForm.source_lang,
      target_lang: batchForm.target_lang.trim(),
      provider: batchForm.provider,
      delay: batchForm.delay,
    })
  } finally {
    batchLoading.value = false
  }
}

// ---- 加载时机：切到本标签才触发（对应原 openTab 的 'mt' 分支），只触发一次
let loaded = false
watch(
  () => props.active,
  (isActive) => {
    if (!isActive || loaded) return
    loaded = true
    void loadProviders()
  },
  {immediate: true},
)
</script>

<template>
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.mt.providersTitle') }}</span>
      <el-button :icon="Refresh" :loading="mtLoading" @click="loadProviders">
        {{ $t('admin.common.refresh') }}
      </el-button>
    </div>
    <p class="hint mb-2">{{ $t('admin.system.translation.mt.notConfiguredHint') }}</p>
    <el-table v-loading="mtLoading" :data="providers" border size="small" stripe>
      <el-table-column :label="$t('admin.system.translation.mt.provider')" prop="provider" width="120"/>
      <el-table-column :label="$t('admin.system.translation.mt.providerName')" min-width="150"
                       prop="name"/>
      <el-table-column :label="$t('admin.system.translation.mt.available')" align="center" width="120">
        <template #default="{ row }">
          <el-tag :type="row.available ? 'success' : 'info'" size="small">
            {{
              row.available
                ? $t('admin.system.translation.mt.configured')
                : $t('admin.system.translation.mt.notConfigured')
            }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.system.translation.mt.requiredEnv')" min-width="240">
        <template #default="{ row }">
          <el-tag v-for="name in (row as MTProviderStatus).required_env" :key="name" class="mr-1 mb-1"
                  size="small" type="info">
            {{ name }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.system.translation.mt.envStatus')" min-width="240">
        <template #default="{ row }">
          <div v-for="(ok, name) in (row as MTProviderStatus).env" :key="name">
            {{ name }}: {{
              ok
                ? $t('admin.system.translation.mt.configured')
                : $t('admin.system.translation.mt.notConfigured')
            }}
          </div>
        </template>
      </el-table-column>
    </el-table>
  </section>

  <!-- 单条翻译 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.mt.translateTitle') }}</span>
    </div>
    <el-form :model="translateForm" label-width="120px">
      <el-form-item :label="$t('admin.system.translation.mt.text')">
        <el-input v-model="translateForm.text" :rows="2" type="textarea"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.mt.sourceLang')">
        <el-input v-model="translateForm.source_lang" style="max-width: 200px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.mt.targetLang')">
        <el-input v-model="translateForm.target_lang" placeholder="zh-CN" style="max-width: 200px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.mt.provider')">
        <el-select v-model="translateForm.provider" style="width: 200px">
          <el-option v-for="item in providers" :key="item.provider" :label="item.name"
                     :value="item.provider"/>
        </el-select>
      </el-form-item>
    </el-form>
    <div class="actions-row">
      <el-button v-auth="'module_system:setting:edit'" :loading="translateLoading" type="primary"
                 @click="runTranslate">
        {{ $t('admin.system.translation.mt.translate') }}
      </el-button>
    </div>
    <template v-if="translateResult">
      <el-alert
        v-if="translateUnavailable"
        :closable="false"
        :title="$t('admin.system.translation.mt.notConfiguredHint')"
        class="mt-3"
        show-icon
        type="warning"
      />
      <div class="result-grid mt-3">
        <div class="result-item">
          <span class="result-label">{{ $t('admin.system.translation.mt.translatedText') }}</span>
          <span class="result-value">{{ translateResult.translated_text ?? '-' }}</span>
        </div>
        <div class="result-item">
          <span class="result-label">{{ $t('admin.system.translation.mt.translateFailed') }}</span>
          <span class="result-value">{{ translateResult.reason ?? '-' }}</span>
        </div>
      </div>
    </template>
  </section>

  <!-- 批量翻译 -->
  <section class="tcard">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.mt.batchTitle') }}</span>
    </div>
    <p class="hint mb-2">{{ $t('admin.system.translation.mt.batchHint') }}</p>
    <el-form :model="batchForm" label-width="120px">
      <el-form-item :label="$t('admin.system.translation.mt.batchTexts')">
        <el-input v-model="batchForm.textsText" :autosize="{minRows: 4, maxRows: 12}" type="textarea"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.mt.sourceLang')">
        <el-input v-model="batchForm.source_lang" style="max-width: 200px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.mt.targetLang')">
        <el-input v-model="batchForm.target_lang" placeholder="zh-CN" style="max-width: 200px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.mt.provider')">
        <el-select v-model="batchForm.provider" style="width: 200px">
          <el-option v-for="item in providers" :key="item.provider" :label="item.name"
                     :value="item.provider"/>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.mt.delay')">
        <el-input-number v-model="batchForm.delay" :max="5" :min="0" :precision="1" :step="0.1"
                         style="width: 180px"/>
      </el-form-item>
    </el-form>
    <div class="actions-row">
      <el-button v-auth="'module_system:setting:edit'" :loading="batchLoading" type="primary"
                 @click="runBatch">
        {{ $t('admin.system.translation.mt.batch') }}
      </el-button>
    </div>
    <template v-if="batchResult">
      <el-alert
        v-if="batchUnavailable"
        :closable="false"
        :title="batchResult.reason ?? $t('admin.system.translation.mt.notConfiguredHint')"
        class="mt-3"
        show-icon
        type="warning"
      />
      <div class="result-grid mt-3 mb-3">
        <div class="result-item">
          <span class="result-label">{{ $t('admin.system.translation.mt.batchTotal') }}</span>
          <span class="result-value">{{ batchResult.total }}</span>
        </div>
        <div class="result-item">
          <span class="result-label">{{ $t('admin.system.translation.mt.batchSuccess') }}</span>
          <span class="result-value">{{ batchResult.success_count }}</span>
        </div>
        <div class="result-item">
          <span class="result-label">{{ $t('admin.system.translation.mt.batchFailed') }}</span>
          <span class="result-value">{{ batchResult.failed_count }}</span>
        </div>
      </div>
      <el-table v-if="batchResult.results.length" :data="batchResult.results" border size="small"
                stripe>
        <el-table-column :label="$t('admin.system.translation.mt.batchOriginal')" min-width="200"
                         prop="original" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.translation.mt.batchTranslated')" min-width="200"
                         show-overflow-tooltip>
          <template #default="{ row }">{{ row.translated ?? '-' }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.translation.mt.batchReason')" min-width="200"
                         show-overflow-tooltip>
          <template #default="{ row }">{{ row.reason ?? '-' }}</template>
        </el-table-column>
      </el-table>
    </template>
  </section>
</template>

<style scoped>
.tcard {
  padding: 16px 18px;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-line, #e5e7eb);
  border-radius: 8px;
}

.tcard__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.tcard__title {
  font-size: 15px;
  font-weight: 600;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.actions-row {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px 20px;
}

.result-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-label {
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.result-value {
  font-size: 14px;
  color: var(--color-fg, #303133);
  word-break: break-all;
}

.mb-1 {
  margin-bottom: 4px;
}

.mb-2 {
  margin-bottom: 8px;
}

.mb-3 {
  margin-bottom: 16px;
}

.mt-3 {
  margin-top: 16px;
}

.mr-1 {
  margin-right: 4px;
}
</style>
