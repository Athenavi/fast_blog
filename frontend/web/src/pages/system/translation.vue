<script lang="ts" setup>
/**
 * 翻译管理（`/system/translation`，system 域）
 *
 * 对齐后端 27 个端点（`modules/system/translation/controller.py`），按 el-tabs 分 6 组：
 *   1. 语言与区域   languages / languages/detect / locales / localize / languages(POST)
 *   2. 词条与语言包 entry / bundle(GET) / bundle(PUT) / entry(POST)
 *   3. 统计与进度   stats / progress / progress/{locale} / report / missing / template / progress(POST)
 *   4. 翻译记忆库   memory / memory/suggest / memory(POST) / memory(DELETE) / memory/import / memory/export
 *   5. 机器翻译     mt/providers / mt/translate / mt/batch
 *   6. 导入导出     export / import
 *
 * 权限：本模块无专用权限码，主权限取 `module_system:setting:view`，写操作用
 * `module_system:setting:edit`（controller docstring 已说明）。按钮级权限用 `v-auth`。
 *
 * 诚实降级：机器翻译未配置密钥时后端返回 `available=false` + 所需环境变量名、
 * `translated_text=null`，页面**如实提示未配置**，绝不伪装成功。
 *
 * 只读加载一律用 `Promise.allSettled`，避免多请求并发时出现未处理拒绝。
 */
import {Delete, Download, Plus, Refresh, Upload} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {
  type BundleResult,
  type DetectResult,
  type EntryResult,
  type LanguageItem,
  type LanguageProgress,
  type LocaleInfo,
  type LocalizeResult,
  type MemoryStats,
  type MemorySuggestResult,
  type MissingResult,
  type MTBatchResult,
  type MTProviderStatus,
  type MTTranslateResult,
  type ReportResult,
  type StatsResult,
  type TemplateResult,
  type TextDirection,
  translationApi,
  type TranslationFormat,
} from '@/api'
import {formatDateTime} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.translation.title',
  permission: 'module_system:setting:view',
})

const {t} = useI18n()

const STATUSES = ['translated', 'pending', 'reviewed'] as const
const FORMATS: TranslationFormat[] = ['json', 'csv', 'po', 'xliff', 'yaml']

function statusLabel(status: string): string {
  if (status === 'translated') return t('admin.system.translation.entries.statusTranslated')
  if (status === 'reviewed') return t('admin.system.translation.entries.statusReviewed')
  return t('admin.system.translation.entries.statusPending')
}

function statusTagType(status: string): 'success' | 'primary' | 'warning' {
  if (status === 'translated') return 'success'
  if (status === 'reviewed') return 'primary'
  return 'warning'
}

// ================================================================ 标签页懒加载
const activeTab = ref('languages')
const loadedTabs = reactive<Record<string, boolean>>({})

onMounted(() => {
  void openTab('languages')
})

async function openTab(name: string | number): Promise<void> {
  const key = String(name)
  activeTab.value = key
  if (loadedTabs[key]) return
  loadedTabs[key] = true
  switch (key) {
    case 'languages':
      await loadLanguagesTab()
      break
    case 'entries':
      await Promise.allSettled([ensureLanguages()])
      break
    case 'progress':
      await loadProgressTab()
      break
    case 'memory':
      await loadMemoryStats()
      break
    case 'mt':
      await loadProviders()
      break
    case 'io':
      await ensureLanguages()
      break
  }
}

// ================================================================ 1. 语言与区域
const langLoading = ref(false)
const langFailed = ref(false)
const languageList = ref<LanguageItem[]>([])
const localeList = ref<LocaleInfo[]>([])

async function loadLanguagesTab(): Promise<void> {
  langLoading.value = true
  langFailed.value = false
  const [langs, locs] = await Promise.allSettled([
    translationApi.languages(),
    translationApi.locales(),
  ])
  if (langs.status === 'fulfilled') languageList.value = langs.value
  if (locs.status === 'fulfilled') localeList.value = locs.value
  if (langs.status === 'rejected' || locs.status === 'rejected') langFailed.value = true
  langLoading.value = false
}

async function ensureLanguages(): Promise<void> {
  if (languageList.value.length) return
  const [langs] = await Promise.allSettled([translationApi.languages()])
  if (langs.status === 'fulfilled') languageList.value = langs.value
}

// ---- 语言识别
const detectLoading = ref(false)
const detectInput = ref('')
const detectResult = ref<DetectResult | null>(null)

async function runDetect(): Promise<void> {
  if (!detectInput.value.trim()) {
    ElMessage.warning(t('admin.system.translation.languages.detectRequired'))
    return
  }
  detectLoading.value = true
  try {
    detectResult.value = await translationApi.detectLanguage(detectInput.value.trim())
  } finally {
    detectLoading.value = false
  }
}

// ---- 时间本地化
const localizeLoading = ref(false)
const localizeForm = reactive({dt: '', locale: '', timezone: ''})
const localizeResult = ref<LocalizeResult | null>(null)

async function runLocalize(): Promise<void> {
  if (!localizeForm.dt) {
    ElMessage.warning(t('admin.system.translation.languages.localizeRequired'))
    return
  }
  localizeLoading.value = true
  try {
    localizeResult.value = await translationApi.localize({
      dt: localizeForm.dt,
      locale: localizeForm.locale || undefined,
      timezone: localizeForm.timezone || undefined,
    })
  } finally {
    localizeLoading.value = false
  }
}

// ---- 新增 / 覆盖自定义语言
const langFormVisible = ref(false)
const langSaving = ref(false)
const langForm = reactive<{
  code: string
  name: string
  native_name: string
  direction: TextDirection
}>({code: '', name: '', native_name: '', direction: 'ltr'})

function openLangCreate(): void {
  Object.assign(langForm, {code: '', name: '', native_name: '', direction: 'ltr'})
  langFormVisible.value = true
}

async function saveLanguage(): Promise<void> {
  if (!langForm.code.trim()) {
    ElMessage.warning(t('admin.system.translation.languages.codeRequired'))
    return
  }
  langSaving.value = true
  try {
    await translationApi.upsertLanguage({
      code: langForm.code.trim(),
      name: langForm.name.trim() || undefined,
      native_name: langForm.native_name.trim() || undefined,
      direction: langForm.direction,
    })
    ElMessage.success(t('admin.system.translation.languages.saved'))
    langFormVisible.value = false
    loadedTabs.languages = false
    await loadLanguagesTab()
    loadedTabs.languages = true
  } finally {
    langSaving.value = false
  }
}

// ================================================================ 2. 词条与语言包
const entryLocale = ref('')
const bundleLoading = ref(false)
const bundleFailed = ref(false)
const bundle = ref<BundleResult | null>(null)

const bundleRows = computed(() =>
  Object.entries(bundle.value?.entries ?? {}).map(([key, value]) => ({key, value})),
)

async function loadBundle(): Promise<void> {
  if (!entryLocale.value) return
  bundleLoading.value = true
  bundleFailed.value = false
  try {
    bundle.value = await translationApi.getBundle(entryLocale.value)
  } catch {
    bundle.value = null
    bundleFailed.value = true
  } finally {
    bundleLoading.value = false
  }
}

// ---- 取单条词条
const entryLookupLoading = ref(false)
const entryLookup = reactive({key: '', locale: '', default: ''})
const entryLookupResult = ref<EntryResult | null>(null)

async function fetchEntry(): Promise<void> {
  if (!entryLookup.key.trim()) {
    ElMessage.warning(t('admin.system.translation.entries.keyRequired'))
    return
  }
  entryLookupLoading.value = true
  try {
    entryLookupResult.value = await translationApi.getEntry({
      key: entryLookup.key.trim(),
      locale: entryLookup.locale || undefined,
      default: entryLookup.default || undefined,
    })
  } finally {
    entryLookupLoading.value = false
  }
}

// ---- 写单条词条
const entrySaving = ref(false)
const entryForm = reactive({locale: '', key: '', value: '', status: ''})

async function saveEntry(): Promise<void> {
  if (!entryForm.locale.trim()) {
    ElMessage.warning(t('admin.system.translation.entries.localeRequired'))
    return
  }
  if (!entryForm.key.trim()) {
    ElMessage.warning(t('admin.system.translation.entries.keyRequired'))
    return
  }
  entrySaving.value = true
  try {
    await translationApi.setEntry({
      locale: entryForm.locale.trim(),
      key: entryForm.key.trim(),
      value: entryForm.value,
      status: entryForm.status || undefined,
    })
    ElMessage.success(t('admin.system.translation.entries.entrySaved'))
    if (entryLocale.value === entryForm.locale.trim()) await loadBundle()
  } finally {
    entrySaving.value = false
  }
}

// ---- 覆盖 / 合并语言包
const replaceSaving = ref(false)
const replaceForm = reactive<{ locale: string; merge: boolean; status: string; dataText: string }>({
  locale: '',
  merge: true,
  status: '',
  dataText: '',
})

async function replaceBundle(): Promise<void> {
  if (!replaceForm.locale.trim()) {
    ElMessage.warning(t('admin.system.translation.entries.localeRequired'))
    return
  }
  let data: Record<string, string>
  try {
    const parsed: unknown = JSON.parse(replaceForm.dataText || '{}')
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      throw new Error('not-object')
    }
    data = parsed as Record<string, string>
  } catch {
    ElMessage.warning(t('admin.system.translation.entries.badJson'))
    return
  }
  replaceSaving.value = true
  try {
    await translationApi.replaceBundle(replaceForm.locale.trim(), {
      data,
      merge: replaceForm.merge,
      status: replaceForm.status || undefined,
    })
    ElMessage.success(t('admin.system.translation.entries.replaced'))
    if (entryLocale.value === replaceForm.locale.trim()) await loadBundle()
  } finally {
    replaceSaving.value = false
  }
}

// ================================================================ 3. 统计与进度
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

// ================================================================ 4. 翻译记忆库
const memLoading = ref(false)
const memStats = ref<MemoryStats | null>(null)

async function loadMemoryStats(): Promise<void> {
  memLoading.value = true
  const [res] = await Promise.allSettled([translationApi.memoryStats()])
  if (res.status === 'fulfilled') memStats.value = res.value
  memLoading.value = false
}

// ---- 相似匹配
const suggestLoading = ref(false)
const suggestForm = reactive<{
  source_text: string
  source_lang: string
  target_lang: string
  threshold: number | undefined
  limit: number
}>({source_text: '', source_lang: '', target_lang: '', threshold: undefined, limit: 10})
const suggestResult = ref<MemorySuggestResult | null>(null)

async function runSuggest(): Promise<void> {
  if (!suggestForm.source_text.trim() || !suggestForm.source_lang.trim() || !suggestForm.target_lang.trim()) {
    ElMessage.warning(t('admin.system.translation.memory.suggestRequired'))
    return
  }
  suggestLoading.value = true
  try {
    suggestResult.value = await translationApi.memorySuggest({
      source_text: suggestForm.source_text,
      source_lang: suggestForm.source_lang.trim(),
      target_lang: suggestForm.target_lang.trim(),
      threshold: suggestForm.threshold,
      limit: suggestForm.limit,
    })
  } finally {
    suggestLoading.value = false
  }
}

// ---- 新增 / 更新记忆
const addSaving = ref(false)
const addForm = reactive({source_text: '', target_text: '', source_lang: '', target_lang: '', context: ''})

async function saveMemory(): Promise<void> {
  if (!addForm.source_text.trim() || !addForm.source_lang.trim() || !addForm.target_lang.trim()) {
    ElMessage.warning(t('admin.system.translation.memory.addRequired'))
    return
  }
  addSaving.value = true
  try {
    await translationApi.addMemory({
      source_text: addForm.source_text,
      target_text: addForm.target_text,
      source_lang: addForm.source_lang.trim(),
      target_lang: addForm.target_lang.trim(),
      context: addForm.context,
    })
    ElMessage.success(t('admin.system.translation.memory.saved'))
    await loadMemoryStats()
  } finally {
    addSaving.value = false
  }
}

// ---- 清空记忆
const clearSaving = ref(false)
const clearPair = ref('')

async function clearMemory(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      clearPair.value
        ? t('admin.system.translation.memory.clearPairConfirm', {pair: clearPair.value})
        : t('admin.system.translation.memory.clearConfirm'),
      t('admin.common.notice'),
      {type: 'warning'},
    )
  } catch {
    return
  }
  clearSaving.value = true
  try {
    await translationApi.clearMemory(clearPair.value.trim() || undefined)
    ElMessage.success(t('admin.system.translation.memory.cleared'))
    clearPair.value = ''
    await loadMemoryStats()
  } finally {
    clearSaving.value = false
  }
}

// ---- 导入记忆
const memImportSaving = ref(false)
const memImportForm = reactive({content: '', merge: true})

async function importMemory(): Promise<void> {
  if (!memImportForm.content.trim()) {
    ElMessage.warning(t('admin.system.translation.memory.importRequired'))
    return
  }
  memImportSaving.value = true
  try {
    await translationApi.importMemory({content: memImportForm.content, merge: memImportForm.merge})
    ElMessage.success(t('admin.system.translation.memory.imported'))
    await loadMemoryStats()
  } finally {
    memImportSaving.value = false
  }
}

// ---- 导出记忆（真实文件下载）
const memExporting = ref(false)

async function downloadMemory(): Promise<void> {
  memExporting.value = true
  try {
    await translationApi.exportMemory()
  } finally {
    memExporting.value = false
  }
}

// ================================================================ 5. 机器翻译
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

// ================================================================ 6. 导入导出
const exportForm = reactive<{ locale: string; format: TranslationFormat }>({locale: '', format: 'json'})
const exporting = ref(false)

async function downloadExport(): Promise<void> {
  if (!exportForm.locale.trim()) {
    ElMessage.warning(t('admin.system.translation.io.exportRequired'))
    return
  }
  exporting.value = true
  try {
    await translationApi.exportTranslations(exportForm.locale.trim(), exportForm.format)
  } finally {
    exporting.value = false
  }
}

const importing = ref(false)
const importForm = reactive<{
  content: string
  format: TranslationFormat
  locale: string
  merge: boolean
  status: string
}>({content: '', format: 'json', locale: '', merge: true, status: ''})

async function runImport(): Promise<void> {
  if (!importForm.content.trim()) {
    ElMessage.warning(t('admin.system.translation.io.importContentRequired'))
    return
  }
  importing.value = true
  try {
    await translationApi.importTranslations({
      content: importForm.content,
      format: importForm.format,
      locale: importForm.locale || undefined,
      merge: importForm.merge,
      status: importForm.status || undefined,
    })
    ElMessage.success(t('admin.system.translation.io.imported'))
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <AdminPage :desc="$t('admin.system.translation.desc')" :title="$t('admin.system.translation.title')">
    <el-tabs v-model="activeTab" @tab-change="openTab">
      <!-- ============================================ 1. 语言与区域 -->
      <el-tab-pane :label="$t('admin.system.translation.tabs.languages')" name="languages">
        <el-alert
          v-if="langFailed"
          :closable="false"
          :title="$t('admin.common.loadFailed')"
          class="mb-3"
          show-icon
          type="error"
        />

        <!-- 支持语言列表 -->
        <section class="tcard mb-3">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.languages.listTitle') }}</span>
            <div class="actions-row">
              <el-button :icon="Refresh" :loading="langLoading" @click="loadLanguagesTab">
                {{ $t('admin.common.refresh') }}
              </el-button>
              <el-button v-auth="'module_system:setting:edit'" :icon="Plus" type="primary" @click="openLangCreate">
                {{ $t('admin.system.translation.languages.add') }}
              </el-button>
            </div>
          </div>
          <el-table v-loading="langLoading" :data="languageList" border size="small" stripe>
            <el-table-column :label="$t('admin.system.translation.languages.code')" prop="code" width="120"/>
            <el-table-column :label="$t('admin.system.translation.languages.name')" min-width="180" prop="name"/>
            <el-table-column :label="$t('admin.system.translation.languages.nativeName')" min-width="140"
                             prop="native_name"/>
            <el-table-column :label="$t('admin.system.translation.languages.direction')" prop="direction" width="100"/>
            <el-table-column :label="$t('admin.system.translation.languages.isDefault')" align="center" width="100">
              <template #default="{ row }">
                <el-tag v-if="(row as LanguageItem).is_default" effect="dark" size="small" type="success">
                  {{ $t('admin.system.translation.languages.defaultTag') }}
                </el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
          </el-table>
        </section>

        <!-- 语言识别 -->
        <section class="tcard mb-3">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.languages.detectTitle') }}</span>
          </div>
          <div class="inline-form">
            <el-input
              v-model="detectInput"
              :placeholder="$t('admin.system.translation.languages.acceptLanguagePlaceholder')"
              style="max-width: 360px"
              @keyup.enter="runDetect"
            />
            <el-button :loading="detectLoading" type="primary" @click="runDetect">
              {{ $t('admin.system.translation.languages.detect') }}
            </el-button>
          </div>
          <div v-if="detectResult" class="result-grid mt-3">
            <div class="result-item">
              <span class="result-label">{{ $t('admin.system.translation.languages.acceptLanguage') }}</span>
              <span class="result-value">{{ detectResult.accept_language || '-' }}</span>
            </div>
            <div class="result-item">
              <span class="result-label">{{ $t('admin.system.translation.languages.detected') }}</span>
              <span class="result-value">{{ detectResult.language }}</span>
            </div>
            <div class="result-item">
              <span class="result-label">{{ $t('admin.system.translation.languages.defaultLanguage') }}</span>
              <span class="result-value">{{ detectResult.default_language }}</span>
            </div>
          </div>
        </section>

        <!-- 区域信息列表 -->
        <section class="tcard mb-3">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.languages.localesTitle') }}</span>
          </div>
          <el-table :data="localeList" border size="small" stripe>
            <el-table-column :label="$t('admin.system.translation.languages.locale')" prop="locale" width="110"/>
            <el-table-column :label="$t('admin.system.translation.languages.timezone')" min-width="150"
                             prop="timezone"/>
            <el-table-column :label="$t('admin.system.translation.languages.firstDayOfWeek')" align="center"
                             prop="first_day_of_week" width="120"/>
            <el-table-column :label="$t('admin.system.translation.languages.currency')" width="150">
              <template #default="{ row }">
                {{ (row as LocaleInfo).currency.symbol }} {{ (row as LocaleInfo).currency.code }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('admin.system.translation.languages.dateFormat')" min-width="140">
              <template #default="{ row }">{{ (row as LocaleInfo).formats.date }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.system.translation.languages.datetimeFormat')" min-width="180">
              <template #default="{ row }">{{ (row as LocaleInfo).formats.datetime }}</template>
            </el-table-column>
            <el-table-column :label="$t('admin.system.translation.languages.timeFormat')" min-width="120">
              <template #default="{ row }">{{ (row as LocaleInfo).formats.time }}</template>
            </el-table-column>
          </el-table>
        </section>

        <!-- 时间本地化 -->
        <section class="tcard">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.languages.localizeTitle') }}</span>
          </div>
          <el-form :model="localizeForm" label-width="120px">
            <el-form-item :label="$t('admin.system.translation.languages.dt')">
              <el-date-picker
                v-model="localizeForm.dt"
                :placeholder="$t('admin.system.translation.languages.dtPlaceholder')"
                style="width: 100%"
                type="datetime"
                value-format="YYYY-MM-DDTHH:mm:ss"
              />
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.languages.localizeLocale')">
              <el-select v-model="localizeForm.locale" clearable filterable style="width: 100%">
                <el-option v-for="item in localeList" :key="item.locale" :label="item.locale"
                           :value="item.locale"/>
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.languages.localizeTimezone')">
              <el-input v-model="localizeForm.timezone" placeholder="Asia/Shanghai"/>
            </el-form-item>
          </el-form>
          <div class="actions-row">
            <el-button :loading="localizeLoading" type="primary" @click="runLocalize">
              {{ $t('admin.system.translation.languages.localize') }}
            </el-button>
          </div>
          <div v-if="localizeResult" class="result-grid mt-3">
            <div class="result-item">
              <span class="result-label">{{ $t('admin.system.translation.languages.resultDate') }}</span>
              <span class="result-value">{{ localizeResult.date }}</span>
            </div>
            <div class="result-item">
              <span class="result-label">{{ $t('admin.system.translation.languages.resultTime') }}</span>
              <span class="result-value">{{ localizeResult.time }}</span>
            </div>
            <div class="result-item">
              <span class="result-label">{{ $t('admin.system.translation.languages.resultDatetime') }}</span>
              <span class="result-value">{{ localizeResult.datetime }}</span>
            </div>
            <div class="result-item">
              <span class="result-label">{{ $t('admin.system.translation.languages.resultRelative') }}</span>
              <span class="result-value">{{ localizeResult.relative }}</span>
            </div>
          </div>
        </section>
      </el-tab-pane>

      <!-- ============================================ 2. 词条与语言包 -->
      <el-tab-pane :label="$t('admin.system.translation.tabs.entries')" name="entries">
        <!-- 整包词条 -->
        <section class="tcard mb-3">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.entries.bundleTitle') }}</span>
            <div class="actions-row">
              <el-select v-model="entryLocale" :placeholder="$t('admin.system.translation.entries.selectLocale')"
                         filterable style="width: 200px">
                <el-option v-for="item in languageList" :key="item.code"
                           :label="`${item.native_name} (${item.code})`" :value="item.code"/>
              </el-select>
              <el-button :icon="Refresh" :loading="bundleLoading" @click="loadBundle">
                {{ $t('admin.system.translation.entries.load') }}
              </el-button>
            </div>
          </div>
          <el-alert
            v-if="bundleFailed"
            :closable="false"
            :title="$t('admin.common.loadFailed')"
            class="mb-3"
            show-icon
            type="error"
          />
          <p v-if="bundle" class="hint mb-2">
            {{ $t('admin.system.translation.entries.bundleCount', {n: bundle.count}) }}
          </p>
          <el-table v-if="bundleRows.length" v-loading="bundleLoading" :data="bundleRows" border size="small"
                    stripe>
            <el-table-column :label="$t('admin.system.translation.entries.key')" min-width="260" prop="key"/>
            <el-table-column :label="$t('admin.system.translation.entries.value')" min-width="260" prop="value"
                             show-overflow-tooltip/>
          </el-table>
          <el-empty v-else :description="$t('admin.system.translation.entries.empty')" :image-size="60"/>
        </section>

        <!-- 取单条词条 -->
        <section class="tcard mb-3">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.entries.entryTitle') }}</span>
          </div>
          <el-form :model="entryLookup" inline>
            <el-form-item :label="$t('admin.system.translation.entries.entryKey')">
              <el-input v-model="entryLookup.key" clearable style="width: 220px"
                        @keyup.enter="fetchEntry"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.entries.selectLocale')">
              <el-select v-model="entryLookup.locale" clearable filterable style="width: 180px">
                <el-option v-for="item in languageList" :key="item.code" :label="item.code"
                           :value="item.code"/>
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.entries.entryDefault')">
              <el-input v-model="entryLookup.default" clearable style="width: 200px"/>
            </el-form-item>
            <el-form-item>
              <el-button :loading="entryLookupLoading" type="primary" @click="fetchEntry">
                {{ $t('admin.system.translation.entries.getEntry') }}
              </el-button>
            </el-form-item>
          </el-form>
          <div v-if="entryLookupResult" class="result-grid mt-2">
            <div class="result-item">
              <span class="result-label">{{ $t('admin.system.translation.entries.entryValueResult') }}</span>
              <span class="result-value">{{ entryLookupResult.value }}</span>
            </div>
            <div class="result-item">
              <span class="result-label">{{ $t('admin.system.translation.entries.entrySource') }}</span>
              <span class="result-value">{{ entryLookupResult.source }}</span>
            </div>
          </div>
        </section>

        <!-- 写单条词条 -->
        <section class="tcard mb-3">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.entries.setTitle') }}</span>
          </div>
          <el-form :model="entryForm" label-width="110px">
            <el-form-item :label="$t('admin.system.translation.entries.selectLocale')">
              <el-input v-model="entryForm.locale" placeholder="zh-CN" style="max-width: 220px"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.entries.entryKey')">
              <el-input v-model="entryForm.key" placeholder="home.title" style="max-width: 320px"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.entries.entryValue')">
              <el-input v-model="entryForm.value" :rows="2" type="textarea"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.entries.entryStatus')">
              <el-select v-model="entryForm.status" clearable style="width: 200px">
                <el-option v-for="item in STATUSES" :key="item" :label="statusLabel(item)" :value="item"/>
              </el-select>
            </el-form-item>
          </el-form>
          <div class="actions-row">
            <el-button v-auth="'module_system:setting:edit'" :loading="entrySaving" type="primary"
                       @click="saveEntry">
              {{ $t('admin.system.translation.entries.saveEntry') }}
            </el-button>
          </div>
        </section>

        <!-- 覆盖 / 合并语言包 -->
        <section class="tcard">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.entries.replaceTitle') }}</span>
          </div>
          <p class="hint mb-2">{{ $t('admin.system.translation.entries.replaceHint') }}</p>
          <el-form :model="replaceForm" label-width="110px">
            <el-form-item :label="$t('admin.system.translation.entries.selectLocale')">
              <el-input v-model="replaceForm.locale" placeholder="zh-CN" style="max-width: 220px"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.entries.replaceMerge')">
              <el-switch v-model="replaceForm.merge"/>
              <span class="hint ml-2">
                {{
                  replaceForm.merge
                    ? $t('admin.system.translation.entries.mergeOptionMerge')
                    : $t('admin.system.translation.entries.mergeOptionReplace')
                }}
              </span>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.entries.replaceStatus')">
              <el-select v-model="replaceForm.status" clearable style="width: 200px">
                <el-option v-for="item in STATUSES" :key="item" :label="statusLabel(item)" :value="item"/>
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.entries.replaceData')">
              <el-input v-model="replaceForm.dataText" :autosize="{minRows: 4, maxRows: 12}" type="textarea"/>
            </el-form-item>
          </el-form>
          <div class="actions-row">
            <el-button v-auth="'module_system:setting:edit'" :loading="replaceSaving" type="primary"
                       @click="replaceBundle">
              {{ $t('admin.system.translation.entries.replace') }}
            </el-button>
          </div>
        </section>
      </el-tab-pane>

      <!-- ============================================ 3. 统计与进度 -->
      <el-tab-pane :label="$t('admin.system.translation.tabs.progress')" name="progress">
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
              <el-option v-for="item in languageList" :key="item.code"
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
              <el-option v-for="item in languageList" :key="item.code" :label="item.code" :value="item.code"/>
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
              <el-option v-for="item in languageList" :key="item.code" :label="item.code" :value="item.code"/>
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
      </el-tab-pane>

      <!-- ============================================ 4. 翻译记忆库 -->
      <el-tab-pane :label="$t('admin.system.translation.tabs.memory')" name="memory">
        <!-- 记忆库统计 -->
        <section class="tcard mb-3">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.memory.statsTitle') }}</span>
            <el-button :icon="Refresh" :loading="memLoading" @click="loadMemoryStats">
              {{ $t('admin.common.refresh') }}
            </el-button>
          </div>
          <div class="result-grid mb-3">
            <div class="result-item">
              <span class="result-label">{{ $t('admin.system.translation.memory.totalEntries') }}</span>
              <span class="result-value">{{ memStats?.total_entries ?? 0 }}</span>
            </div>
            <div class="result-item">
              <span class="result-label">{{ $t('admin.system.translation.memory.languagePairs') }}</span>
              <span class="result-value">{{ memStats?.language_pairs ?? 0 }}</span>
            </div>
          </div>
          <p class="sub-title mb-2">{{ $t('admin.system.translation.memory.pairsDetail') }}</p>
          <el-table :data="memStats?.pairs_detail ?? []" border size="small" stripe>
            <el-table-column :label="$t('admin.system.translation.memory.pair')" min-width="160" prop="pair"/>
            <el-table-column :label="$t('admin.system.translation.memory.sourceLang')" prop="source_lang"
                             width="130"/>
            <el-table-column :label="$t('admin.system.translation.memory.targetLang')" prop="target_lang"
                             width="130"/>
            <el-table-column :label="$t('admin.system.translation.memory.entryCount')" align="right"
                             prop="entry_count" width="120"/>
          </el-table>
        </section>

        <!-- 相似匹配 -->
        <section class="tcard mb-3">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.memory.suggestTitle') }}</span>
          </div>
          <el-form :model="suggestForm" label-width="120px">
            <el-form-item :label="$t('admin.system.translation.memory.sourceText')">
              <el-input v-model="suggestForm.source_text" :rows="2" type="textarea"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.memory.sourceLang')">
              <el-input v-model="suggestForm.source_lang" placeholder="en" style="max-width: 200px"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.memory.targetLang')">
              <el-input v-model="suggestForm.target_lang" placeholder="zh-CN" style="max-width: 200px"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.memory.threshold')">
              <el-input-number v-model="suggestForm.threshold" :max="1" :min="0" :precision="2" :step="0.1"
                               style="width: 180px"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.memory.limit')">
              <el-input-number v-model="suggestForm.limit" :max="100" :min="1" style="width: 180px"/>
            </el-form-item>
          </el-form>
          <div class="actions-row">
            <el-button :loading="suggestLoading" type="primary" @click="runSuggest">
              {{ $t('admin.system.translation.memory.suggest') }}
            </el-button>
          </div>
          <template v-if="suggestResult">
            <p class="sub-title mt-3 mb-2">{{ $t('admin.system.translation.memory.matches') }}</p>
            <el-table v-if="suggestResult.matches.length" :data="suggestResult.matches" border size="small"
                      stripe>
              <el-table-column :label="$t('admin.system.translation.memory.sourceText')" min-width="200"
                               prop="source" show-overflow-tooltip/>
              <el-table-column :label="$t('admin.system.translation.memory.targetText')" min-width="200"
                               prop="target" show-overflow-tooltip/>
              <el-table-column :label="$t('admin.system.translation.memory.similarity')" align="right"
                               prop="similarity" width="120"/>
              <el-table-column :label="$t('admin.system.translation.memory.matchType')" align="center" width="110">
                <template #default="{ row }">
                  <el-tag :type="row.match_type === 'exact' ? 'success' : 'info'" size="small">
                    {{
                      row.match_type === 'exact'
                        ? $t('admin.system.translation.memory.exact')
                        : $t('admin.system.translation.memory.fuzzy')
                    }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column :label="$t('admin.system.translation.memory.context')" min-width="140"
                               prop="context" show-overflow-tooltip/>
              <el-table-column :label="$t('admin.system.translation.memory.usageCount')" align="right"
                               prop="usage_count" width="100"/>
            </el-table>
            <el-empty v-else :description="$t('admin.system.translation.memory.noMatches')" :image-size="60"/>
          </template>
        </section>

        <!-- 新增 / 更新记忆 -->
        <section class="tcard mb-3">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.memory.addTitle') }}</span>
          </div>
          <el-form :model="addForm" label-width="120px">
            <el-form-item :label="$t('admin.system.translation.memory.sourceText')">
              <el-input v-model="addForm.source_text" :rows="2" type="textarea"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.memory.targetText')">
              <el-input v-model="addForm.target_text" :rows="2" type="textarea"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.memory.sourceLang')">
              <el-input v-model="addForm.source_lang" placeholder="en" style="max-width: 200px"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.memory.targetLang')">
              <el-input v-model="addForm.target_lang" placeholder="zh-CN" style="max-width: 200px"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.memory.context')">
              <el-input v-model="addForm.context" :maxlength="500" style="max-width: 320px"/>
            </el-form-item>
          </el-form>
          <div class="actions-row">
            <el-button v-auth="'module_system:setting:edit'" :loading="addSaving" type="primary" @click="saveMemory">
              {{ $t('admin.system.translation.memory.add') }}
            </el-button>
          </div>
        </section>

        <!-- 清空 / 导入 / 导出 -->
        <section class="tcard mb-3">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.memory.clearTitle') }}</span>
          </div>
          <p class="hint mb-2">{{ $t('admin.system.translation.memory.clearHint') }}</p>
          <div class="inline-form">
            <el-input v-model="clearPair"
                      :placeholder="$t('admin.system.translation.memory.languagePairPlaceholder')"
                      style="max-width: 260px"/>
            <el-button v-auth="'module_system:setting:edit'" :icon="Delete" :loading="clearSaving" type="danger"
                       @click="clearMemory">
              {{ $t('admin.system.translation.memory.clear') }}
            </el-button>
          </div>
        </section>

        <section class="tcard mb-3">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.memory.importTitle') }}</span>
          </div>
          <el-form :model="memImportForm" label-width="120px">
            <el-form-item :label="$t('admin.system.translation.memory.importContent')">
              <el-input v-model="memImportForm.content" :autosize="{minRows: 4, maxRows: 12}" type="textarea"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.memory.importMerge')">
              <el-switch v-model="memImportForm.merge"/>
            </el-form-item>
          </el-form>
          <div class="actions-row">
            <el-button v-auth="'module_system:setting:edit'" :icon="Upload" :loading="memImportSaving" type="primary"
                       @click="importMemory">
              {{ $t('admin.system.translation.memory.import') }}
            </el-button>
          </div>
        </section>

        <section class="tcard">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.memory.exportTitle') }}</span>
          </div>
          <p class="hint mb-2">{{ $t('admin.system.translation.memory.exportHint') }}</p>
          <el-button :icon="Download" :loading="memExporting" type="primary" @click="downloadMemory">
            {{ $t('admin.system.translation.memory.export') }}
          </el-button>
        </section>
      </el-tab-pane>

      <!-- ============================================ 5. 机器翻译 -->
      <el-tab-pane :label="$t('admin.system.translation.tabs.mt')" name="mt">
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
      </el-tab-pane>

      <!-- ============================================ 6. 导入导出 -->
      <el-tab-pane :label="$t('admin.system.translation.tabs.io')" name="io">
        <!-- 导出词条 -->
        <section class="tcard mb-3">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.io.exportTitle') }}</span>
          </div>
          <p class="hint mb-2">{{ $t('admin.system.translation.io.exportHint') }}</p>
          <div class="inline-form">
            <el-select v-model="exportForm.locale" :placeholder="$t('admin.system.translation.io.exportLocale')" filterable
                       style="width: 220px">
              <el-option v-for="item in languageList" :key="item.code"
                         :label="`${item.native_name} (${item.code})`" :value="item.code"/>
            </el-select>
            <el-select v-model="exportForm.format" style="width: 140px">
              <el-option v-for="item in FORMATS" :key="item" :label="item" :value="item"/>
            </el-select>
            <el-button :icon="Download" :loading="exporting" type="primary" @click="downloadExport">
              {{ $t('admin.system.translation.io.export') }}
            </el-button>
          </div>
        </section>

        <!-- 导入词条 -->
        <section class="tcard">
          <div class="tcard__head">
            <span class="tcard__title">{{ $t('admin.system.translation.io.importTitle') }}</span>
          </div>
          <p class="hint mb-2">{{ $t('admin.system.translation.io.importHint') }}</p>
          <el-form :model="importForm" label-width="120px">
            <el-form-item :label="$t('admin.system.translation.io.importFormat')">
              <el-select v-model="importForm.format" style="width: 200px">
                <el-option v-for="item in FORMATS" :key="item" :label="item" :value="item"/>
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.io.importLocale')">
              <el-input v-model="importForm.locale" placeholder="zh-CN" style="max-width: 200px"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.io.importMerge')">
              <el-switch v-model="importForm.merge"/>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.io.importStatus')">
              <el-select v-model="importForm.status" clearable style="width: 200px">
                <el-option v-for="item in STATUSES" :key="item" :label="statusLabel(item)" :value="item"/>
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('admin.system.translation.io.importContent')">
              <el-input v-model="importForm.content" :autosize="{minRows: 6, maxRows: 16}" type="textarea"/>
            </el-form-item>
          </el-form>
          <div class="actions-row">
            <el-button v-auth="'module_system:setting:edit'" :icon="Upload" :loading="importing" type="primary"
                       @click="runImport">
              {{ $t('admin.system.translation.io.import') }}
            </el-button>
          </div>
        </section>
      </el-tab-pane>
    </el-tabs>

    <!-- 新增 / 覆盖自定义语言 -->
    <el-drawer v-model="langFormVisible" :title="$t('admin.system.translation.languages.formTitle')"
               destroy-on-close size="440px">
      <el-form :model="langForm" label-width="120px">
        <el-form-item :label="$t('admin.system.translation.languages.formCode')" required>
          <el-input v-model="langForm.code" placeholder="pt-BR"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.translation.languages.formName')">
          <el-input v-model="langForm.name" placeholder="Portuguese (Brazil)"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.translation.languages.formNativeName')">
          <el-input v-model="langForm.native_name" placeholder="Português"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.translation.languages.formDirection')">
          <el-select v-model="langForm.direction" style="width: 100%">
            <el-option :label="$t('admin.system.translation.languages.dirLtr')" value="ltr"/>
            <el-option :label="$t('admin.system.translation.languages.dirRtl')" value="rtl"/>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="langFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="langSaving" type="primary" @click="saveLanguage">
          {{ $t('admin.system.translation.languages.save') }}
        </el-button>
      </template>
    </el-drawer>
  </AdminPage>
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

.ml-2 {
  margin-left: 8px;
}

.mr-1 {
  margin-right: 4px;
}
</style>
