<script lang="ts" setup>
/**
 * 翻译管理 · 统计与进度面板
 *
 * 从 `pages/system/translation.vue` 的「统计与进度」标签页抽出：各语言完成度统计、
 * 所有语言进度、单语言进度、缺失 / 未翻译清单、生成模板、登记翻译状态、进度报告。
 *
 * ## 加载时机与原实现保持一致
 *
 * 原页面在 `@tab-change` 里**切到本标签才加载**，触发 `loadProgressTab()`（并发拉
 * 统计 / 进度 / 报告），并保留原 `loadedTabs` 去重。这里用 `active` 属性 +
 * `watch(immediate)` 还原。
 *
 * `languageList` 由页面持有（跨标签共享），本组件只 `:languages` 读它用于下拉选择；
 * 原 'progress' 分支并不做语言列表兜底加载，这里同样不做。
 */
import {Refresh} from '@element-plus/icons-vue'
import {computed, reactive, ref, watch} from 'vue'

import {
  type LanguageItem,
  type LanguageProgress,
  type MissingResult,
  type ReportResult,
  type StatsResult,
  type TemplateResult,
  translationApi,
} from '@/api'
import {ElMessage} from '@/utils/feedback'
import {formatDateTime} from '@/utils/format'

const props = defineProps<{
  /** 本标签页是否激活 */
  active: boolean
  /** 语言列表（跨标签共享，由页面持有） */
  languages: LanguageItem[]
}>()

const {t} = useI18n()

const STATUSES = ['translated', 'pending', 'reviewed'] as const

function statusLabel(status: string): string {
  if (status === 'translated') return t('admin.system.translation.entries.statusTranslated')
  if (status === 'reviewed') return t('admin.system.translation.entries.statusReviewed')
  return t('admin.system.translation.entries.statusPending')
}

const progLoading = ref(false)
const progFailed = ref(false)
const stats = ref<StatsResult | null>(null)
const progressList = ref<LanguageProgress[]>([])
const report = ref<ReportResult | null>(null)

const statsRows = computed(() =>
  Object.entries(stats.value?.languages ?? {}).map(([code, stat]) => ({code, ...stat})),
)

async function loadProgressTab(): Promise<void> {
  progLoading.value = true
  progFailed.value = false
  const [st, pr, rp] = await Promise.allSettled([
    translationApi.stats(),
    translationApi.allProgress(),
    translationApi.report(),
  ])
  if (st.status === 'fulfilled') stats.value = st.value
  if (pr.status === 'fulfilled') progressList.value = pr.value.languages
  if (rp.status === 'fulfilled') report.value = rp.value
  if (st.status === 'rejected' || pr.status === 'rejected' || rp.status === 'rejected') {
    progFailed.value = true
  }
  progLoading.value = false
}

// ---- 单语言进度
const oneLoading = ref(false)
const oneLocale = ref('')
const oneProgress = ref<LanguageProgress | null>(null)

async function loadOneProgress(): Promise<void> {
  if (!oneLocale.value) {
    ElMessage.warning(t('admin.system.translation.progress.oneRequired'))
    return
  }
  oneLoading.value = true
  try {
    oneProgress.value = await translationApi.oneProgress(oneLocale.value)
  } finally {
    oneLoading.value = false
  }
}

// ---- 缺失 / 未翻译清单
const missingLoading = ref(false)
const missingLocale = ref('')
const missingLimit = ref(100)
const missingResult = ref<MissingResult | null>(null)

async function loadMissing(): Promise<void> {
  if (!missingLocale.value) {
    ElMessage.warning(t('admin.system.translation.progress.missingRequired'))
    return
  }
  missingLoading.value = true
  try {
    missingResult.value = await translationApi.missing(missingLocale.value, missingLimit.value)
  } finally {
    missingLoading.value = false
  }
}

// ---- 生成模板
const templateLoading = ref(false)
const templateLocale = ref('')
const templateResult = ref<TemplateResult | null>(null)
const templatePreview = computed(() =>
  templateResult.value ? JSON.stringify(templateResult.value.template, null, 2) : '',
)

async function loadTemplate(): Promise<void> {
  if (!templateLocale.value) {
    ElMessage.warning(t('admin.system.translation.progress.templateRequired'))
    return
  }
  templateLoading.value = true
  try {
    templateResult.value = await translationApi.template(templateLocale.value)
  } finally {
    templateLoading.value = false
  }
}

// ---- 登记翻译状态
const regSaving = ref(false)
const regForm = reactive<{
  locale: string
  key: string
  value: string
  status: string
  isTranslated: boolean | undefined
}>({locale: '', key: '', value: '', status: '', isTranslated: undefined})

async function registerProgress(): Promise<void> {
  if (!regForm.locale.trim()) {
    ElMessage.warning(t('admin.system.translation.entries.localeRequired'))
    return
  }
  if (!regForm.key.trim()) {
    ElMessage.warning(t('admin.system.translation.progress.registerKeyRequired'))
    return
  }
  regSaving.value = true
  try {
    await translationApi.registerProgress(regForm.locale.trim(), {
      key: regForm.key.trim(),
      value: regForm.value || undefined,
      status: regForm.status || undefined,
      is_translated: regForm.isTranslated,
    })
    ElMessage.success(t('admin.system.translation.progress.registered'))
  } finally {
    regSaving.value = false
  }
}

// ---- 加载时机：切到本标签才触发（对应原 openTab 的 'progress' 分支），只触发一次
let loaded = false
watch(
  () => props.active,
  (isActive) => {
    if (!isActive || loaded) return
    loaded = true
    void loadProgressTab()
  },
  {immediate: true},
)
</script>

<template>
  <el-alert
    v-if="progFailed"
    :closable="false"
    :title="$t('admin.common.loadFailed')"
    class="mb-3"
    show-icon
    type="error"
  />

  <!-- 各语言完成度统计 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.progress.statsTitle') }}</span>
      <el-button :icon="Refresh" :loading="progLoading" @click="loadProgressTab">
        {{ $t('admin.common.refresh') }}
      </el-button>
    </div>
    <p v-if="stats" class="hint mb-2">
      {{ $t('admin.system.translation.progress.sourceLanguage') }}: {{ stats.source_language }}
      · {{ $t('admin.system.translation.progress.sourceKeys') }}: {{ stats.source_keys }}
    </p>
    <el-table v-loading="progLoading" :data="statsRows" border size="small" stripe>
      <el-table-column :label="$t('admin.system.translation.progress.code')" prop="code" width="120"/>
      <el-table-column :label="$t('admin.system.translation.progress.totalKeys')" align="right"
                       prop="total_keys" width="120"/>
      <el-table-column :label="$t('admin.system.translation.progress.translatedKeys')" align="right"
                       prop="translated_keys" width="130"/>
      <el-table-column :label="$t('admin.system.translation.progress.missingKeys')" align="right"
                       prop="missing_keys" width="120"/>
      <el-table-column :label="$t('admin.system.translation.progress.completionRate')" align="right"
                       width="130">
        <template #default="{ row }">{{ (row as { completion_rate: number }).completion_rate }}%</template>
      </el-table-column>
    </el-table>
  </section>

  <!-- 所有语言进度 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.progress.progressTitle') }}</span>
    </div>
    <el-table v-loading="progLoading" :data="progressList" border size="small" stripe>
      <el-table-column :label="$t('admin.system.translation.progress.code')" prop="locale" width="110"/>
      <el-table-column :label="$t('admin.system.translation.progress.totalKeys')" align="right"
                       prop="total_keys" width="100"/>
      <el-table-column :label="$t('admin.system.translation.progress.presentKeys')" align="right"
                       prop="present_keys" width="100"/>
      <el-table-column :label="$t('admin.system.translation.progress.translated')" align="right"
                       prop="translated" width="100"/>
      <el-table-column :label="$t('admin.system.translation.progress.pending')" align="right"
                       prop="pending" width="100"/>
      <el-table-column :label="$t('admin.system.translation.progress.reviewed')" align="right"
                       prop="reviewed" width="100"/>
      <el-table-column :label="$t('admin.system.translation.progress.untranslatedCount')" align="right"
                       prop="untranslated_count" width="120"/>
      <el-table-column :label="$t('admin.system.translation.progress.completionRate')" align="right"
                       width="120">
        <template #default="{ row }">{{ (row as LanguageProgress).completion_rate }}%</template>
      </el-table-column>
      <el-table-column :label="$t('admin.system.translation.progress.lastUpdated')" min-width="170">
        <template #default="{ row }">
          {{ formatDateTime((row as LanguageProgress).last_updated) }}
        </template>
      </el-table-column>
    </el-table>
  </section>

  <!-- 单语言进度 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.progress.oneTitle') }}</span>
    </div>
    <div class="inline-form">
      <el-select v-model="oneLocale" filterable style="width: 220px">
        <el-option v-for="item in languages" :key="item.code"
                   :label="`${item.native_name} (${item.code})`" :value="item.code"/>
      </el-select>
      <el-button :loading="oneLoading" type="primary" @click="loadOneProgress">
        {{ $t('admin.system.translation.progress.view') }}
      </el-button>
    </div>
    <div v-if="oneProgress" class="mt-3">
      <div class="result-grid">
        <div class="result-item">
          <span class="result-label">{{ $t('admin.system.translation.progress.completionRate') }}</span>
          <span class="result-value">{{ oneProgress.completion_rate }}%</span>
        </div>
        <div class="result-item">
          <span class="result-label">{{ $t('admin.system.translation.progress.missingKeys') }}</span>
          <span class="result-value">{{ oneProgress.missing_count }}</span>
        </div>
        <div class="result-item">
          <span class="result-label">{{ $t('admin.system.translation.progress.untranslatedCount') }}</span>
          <span class="result-value">{{ oneProgress.untranslated_count }}</span>
        </div>
      </div>
      <p class="hint mt-2 mb-1">{{ $t('admin.system.translation.progress.missingKeysLabel') }}</p>
      <div class="tag-list">
        <el-tag v-for="key in oneProgress.missing_keys" :key="key" class="mr-1 mb-1" size="small"
                type="warning">
          {{ key }}
        </el-tag>
        <span v-if="!oneProgress.missing_keys.length" class="hint">-</span>
      </div>
      <p class="hint mt-2 mb-1">{{ $t('admin.system.translation.progress.untranslatedKeysLabel') }}</p>
      <div class="tag-list">
        <el-tag v-for="key in oneProgress.untranslated_keys" :key="key" class="mr-1 mb-1" size="small"
                type="danger">
          {{ key }}
        </el-tag>
        <span v-if="!oneProgress.untranslated_keys.length" class="hint">-</span>
      </div>
    </div>
  </section>

  <!-- 缺失 / 未翻译清单 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.progress.missingTitle') }}</span>
    </div>
    <div class="inline-form">
      <el-select v-model="missingLocale" :placeholder="$t('admin.system.translation.entries.selectLocale')" filterable
                 style="width: 220px">
        <el-option v-for="item in languages" :key="item.code" :label="item.code" :value="item.code"/>
      </el-select>
      <el-input-number v-model="missingLimit" :max="1000" :min="1" style="width: 140px"/>
      <el-button :loading="missingLoading" type="primary" @click="loadMissing">
        {{ $t('admin.system.translation.progress.loadMissing') }}
      </el-button>
    </div>
    <div v-if="missingResult" class="mt-3">
      <div class="result-grid">
        <div class="result-item">
          <span class="result-label">{{ $t('admin.system.translation.progress.missingKeys') }}</span>
          <span class="result-value">{{ missingResult.missing_count }}</span>
        </div>
        <div class="result-item">
          <span class="result-label">{{ $t('admin.system.translation.progress.untranslatedCount') }}</span>
          <span class="result-value">{{ missingResult.untranslated_count }}</span>
        </div>
      </div>
      <p class="hint mt-2 mb-1">{{ $t('admin.system.translation.progress.missingKeysLabel') }}</p>
      <div class="tag-list">
        <el-tag v-for="key in missingResult.missing_keys" :key="key" class="mr-1 mb-1" size="small"
                type="warning">
          {{ key }}
        </el-tag>
        <span v-if="!missingResult.missing_keys.length" class="hint">-</span>
      </div>
      <p class="hint mt-2 mb-1">{{ $t('admin.system.translation.progress.untranslatedKeysLabel') }}</p>
      <div class="tag-list">
        <el-tag v-for="key in missingResult.untranslated_keys" :key="key" class="mr-1 mb-1" size="small"
                type="danger">
          {{ key }}
        </el-tag>
        <span v-if="!missingResult.untranslated_keys.length" class="hint">-</span>
      </div>
    </div>
  </section>

  <!-- 生成模板 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.progress.templateTitle') }}</span>
    </div>
    <div class="inline-form">
      <el-select v-model="templateLocale" :placeholder="$t('admin.system.translation.entries.selectLocale')" filterable
                 style="width: 220px">
        <el-option v-for="item in languages" :key="item.code" :label="item.code" :value="item.code"/>
      </el-select>
      <el-button :loading="templateLoading" type="primary" @click="loadTemplate">
        {{ $t('admin.system.translation.progress.generate') }}
      </el-button>
    </div>
    <template v-if="templateResult">
      <p class="hint mt-3 mb-2">
        {{ $t('admin.system.translation.progress.templateCount', {n: templateResult.count}) }}
      </p>
      <el-input :model-value="templatePreview" :rows="8" readonly type="textarea"/>
    </template>
  </section>

  <!-- 登记翻译状态 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.progress.registerTitle') }}</span>
    </div>
    <p class="hint mb-2">{{ $t('admin.system.translation.progress.registerHint') }}</p>
    <el-form :model="regForm" label-width="120px">
      <el-form-item :label="$t('admin.system.translation.entries.selectLocale')">
        <el-input v-model="regForm.locale" placeholder="zh-CN" style="max-width: 220px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.progress.registerKey')">
        <el-input v-model="regForm.key" placeholder="home.title" style="max-width: 320px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.progress.registerValue')">
        <el-input v-model="regForm.value" :rows="2" type="textarea"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.progress.registerStatus')">
        <el-select v-model="regForm.status" clearable style="width: 200px">
          <el-option v-for="item in STATUSES" :key="item" :label="statusLabel(item)" :value="item"/>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.progress.isTranslated')">
        <el-switch v-model="regForm.isTranslated"/>
      </el-form-item>
    </el-form>
    <div class="actions-row">
      <el-button v-auth="'module_system:setting:edit'" :loading="regSaving" type="primary"
                 @click="registerProgress">
        {{ $t('admin.system.translation.progress.register') }}
      </el-button>
    </div>
  </section>

  <!-- 进度报告 -->
  <section class="tcard">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.progress.reportTitle') }}</span>
    </div>
    <template v-if="report">
      <div class="result-grid mb-3">
        <div class="result-item">
          <span class="result-label">{{ $t('admin.system.translation.progress.totalLanguages') }}</span>
          <span class="result-value">{{ report.summary.total_languages }}</span>
        </div>
        <div class="result-item">
          <span class="result-label">{{ $t('admin.system.translation.progress.completedLanguages') }}</span>
          <span class="result-value">{{ report.summary.completed_languages }}</span>
        </div>
        <div class="result-item">
          <span class="result-label">{{ $t('admin.system.translation.progress.averageProgress') }}</span>
          <span class="result-value">{{ report.summary.average_progress }}%</span>
        </div>
        <div class="result-item">
          <span class="result-label">{{ $t('admin.system.translation.progress.generatedAt') }}</span>
          <span class="result-value">{{ formatDateTime(report.summary.generated_at) }}</span>
        </div>
      </div>
      <p class="sub-title mb-2">{{ $t('admin.system.translation.progress.topContributors') }}</p>
      <el-table :data="report.top_contributors" border size="small" stripe>
        <el-table-column :label="$t('admin.system.translation.progress.contributorName')" min-width="160">
          <template #default="{ row }">{{ row.name ?? row.user_id }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.translation.progress.translationsCount')" align="right"
                         prop="translations_count" width="140"/>
        <el-table-column :label="$t('admin.system.translation.progress.lastContribution')" min-width="170">
          <template #default="{ row }">{{ formatDateTime(row.last_contribution) }}</template>
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

.sub-title {
  font-size: 13px;
  font-weight: 600;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.inline-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
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

.tag-list {
  display: flex;
  flex-wrap: wrap;
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

.mt-2 {
  margin-top: 8px;
}

.mt-3 {
  margin-top: 16px;
}

.mr-1 {
  margin-right: 4px;
}
</style>
