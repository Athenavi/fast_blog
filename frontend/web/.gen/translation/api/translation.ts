/** 翻译管理接口（`/api/v3/system/translation`，system 域）
 *
 * 本模块**没有专用权限码**（`core/permission/codes.py` 里不存在 `translation:*`），
 * 后端取语义最近的 `module_system:setting:view` / `module_system:setting:edit`：
 * 语言包/词条本质是系统级 key/value 配置。
 *
 * 契约要点（逐条对齐 `modules/system/translation/controller.py`）：
 *  - 只读端点（languages / detect / locales / localize / entry / bundle / stats / missing /
 *    template / export / mt/providers）**公开**（无权限装饰器）；
 *  - 进度（progress / report）与记忆库读（memory / suggest / export）需 `setting:view`；
 *  - 所有写端点（bundle PUT、entry POST、import、languages POST、progress POST、
 *    memory POST/DELETE/import、mt/translate、mt/batch）需 `setting:edit`。
 *
 * 文件下载：`export` 与 `memory/export` 返回**真实文件**（服务端带 `Content-Disposition`），
 * `@/api/request` 的 axios 实例只认 `code === 200` 的 JSON envelope，无法承载二进制流；
 * 因此与 `modules/report.ts` 同法，绕开 axios 用 `$fetch` + `responseType: 'blob'` 落盘。
 *
 * 搬运：本文件应放到 `src/api/modules/translation.ts`；若要在 `@/api` 聚合入口暴露，
 * 需在 `src/api/index.ts` 追加导出（本次**未**改动该文件，见 REPORT.md「未接线项」）。
 */

import http from '../request'
import {API_BASE_URL, STORAGE_TOKEN} from '@/constants'
import {storage} from '@/utils/storage'

// ================================================================ 语言 / 区域
export type TextDirection = 'ltr' | 'rtl'

/** 一个受支持语言（内置 + 自定义，`is_default` 为模块默认语言） */
export interface LanguageItem {
  code: string
  name: string
  native_name: string
  direction: TextDirection
  is_default: boolean
}

export interface DetectResult {
  accept_language: string
  language: string
  default_language: string
}

export interface CurrencyInfo {
  symbol: string
  code: string
  position: string
}

export interface NumberFormat {
  thousands: string
  decimal: string
}

export interface LocaleInfo {
  locale: string
  timezone: string
  first_day_of_week: number
  currency: CurrencyInfo
  formats: {
    date: string
    datetime: string
    time: string
    number: NumberFormat
  }
}

/** `localize` 的返回：日期/时间/日期时间/相对时间 + 区域信息 */
export interface LocalizeResult {
  locale: string
  timezone: string
  date: string
  time: string
  datetime: string
  relative: string
  first_day_of_week: number
  currency: CurrencyInfo
  number_format: NumberFormat
}

// ================================================================ 词条 / 语言包
/** 单条词条的回退链结果，`source` ∈ {language, default_language, default} */
export interface EntryResult {
  key: string
  locale: string
  value: string
  source: string
}

export interface BundleResult {
  locale: string
  count: number
  status_counts: Record<string, number>
  entries: Record<string, string>
}

export interface BundleReplacePayload {
  /** {词条键: 译文} */
  data: Record<string, string>
  /** true 合并（默认），false 覆盖 */
  merge?: boolean
  /** 写入词条的状态：translated / pending / reviewed */
  status?: string
}

export interface BundleReplaceResult {
  locale: string
  merge: boolean
  written: number
  total: number
}

export interface EntryUpsertPayload {
  locale: string
  key: string
  value?: string
  status?: string
  translator_id?: number
  translator_name?: string
}

export interface EntryUpsertResult {
  locale: string
  key: string
  entry: Record<string, unknown>
}

export interface LanguageUpsertPayload {
  code: string
  name?: string
  native_name?: string
  direction?: TextDirection
}

export interface LanguageUpsertResult {
  code: string
  action: 'created' | 'updated'
  overrides_builtin: boolean
}

// ================================================================ 统计 / 缺失 / 模板
export interface LanguageStat {
  total_keys: number
  translated_keys: number
  missing_keys: number
  completion_rate: number
}

export interface StatsResult {
  source_language: string
  source_keys: number
  languages: Record<string, LanguageStat>
}

export interface MissingResult {
  locale: string
  source_locale: string
  missing_count: number
  untranslated_count: number
  missing_keys: string[]
  untranslated_keys: string[]
}

export interface TemplateResult {
  locale: string
  default_language: string
  count: number
  template: Record<string, string>
}

// ================================================================ 导入导出
export type TranslationFormat = 'json' | 'csv' | 'po' | 'xliff' | 'yaml'

export interface ImportPayload {
  /** 文件内容（字符串） */
  content: string
  /** json / csv / po / xliff / yaml，默认 json */
  format?: TranslationFormat
  /** 目标语言；缺省时取内容里的 language */
  locale?: string
  merge?: boolean
  status?: string
}

export interface ImportResult {
  locale: string
  format: string
  merge: boolean
  imported: number
  total: number
}

// ================================================================ 进度
export interface LanguageProgress {
  locale: string
  total_keys: number
  present_keys: number
  translated: number
  pending: number
  reviewed: number
  missing_keys: string[]
  missing_count: number
  untranslated_keys: string[]
  untranslated_count: number
  completion_rate: number
  last_updated: string | null
}

export interface ProgressResult {
  source_locale: string
  languages: LanguageProgress[]
}

export interface ProgressContributor {
  user_id: number
  name: string | null
  translations_count: number
  last_contribution: string | null
}

export interface ReportResult {
  summary: {
    total_languages: number
    completed_languages: number
    average_progress: number
    generated_at: string
  }
  languages: LanguageProgress[]
  top_contributors: ProgressContributor[]
}

export interface ProgressRegisterPayload {
  key: string
  value?: string
  status?: string
  is_translated?: boolean
  translator_id?: number
  translator_name?: string
}

// ================================================================ 翻译记忆库
export interface MemoryPair {
  pair: string
  source_lang: string
  target_lang: string
  entry_count: number
}

export interface MemoryStats {
  total_entries: number
  language_pairs: number
  pairs_detail: MemoryPair[]
}

export interface MemoryMatch {
  source: string
  target: string
  similarity: number
  match_type: 'exact' | 'fuzzy'
  context: string
  usage_count: number
}

export interface MemorySuggestResult {
  pair: string
  source_text: string
  threshold: number
  total_entries: number
  matches: MemoryMatch[]
}

export interface MemoryAddPayload {
  source_text: string
  target_text?: string
  source_lang: string
  target_lang: string
  context?: string
}

export interface MemoryAddResult {
  pair: string
  action: 'created' | 'updated'
  entry: Record<string, unknown>
}

export interface MemoryImportPayload {
  /** JSON 字符串或已解析的对象 */
  content: string | Record<string, unknown>
  merge?: boolean
}

export interface MemoryImportResult {
  merge: boolean
  total_entries: number
}

// ================================================================ 机器翻译
export interface MTProviderStatus {
  provider: string
  name: string
  available: boolean
  /** 各环境变量是否已设置（true/false，**不含明文**） */
  env: Record<string, boolean>
  required_env: string[]
  url: string
}

export interface MTTranslatePayload {
  text: string
  source_lang?: string
  target_lang: string
  provider?: string
}

export interface MTTranslateResult {
  provider: string
  provider_name: string
  source_lang: string
  target_lang: string
  available: boolean
  success: boolean
  translated_text: string | null
  reason: string | null
}

export interface MTBatchResultItem {
  original: string
  translated: string | null
  success: boolean
  reason: string | null
}

export interface MTBatchPayload {
  texts: string[]
  source_lang?: string
  target_lang: string
  provider?: string
  /** 请求间隔秒数（防限流） */
  delay?: number
}

export interface MTBatchResult {
  provider: string
  provider_name: string
  available: boolean
  success: boolean
  total: number
  success_count: number
  failed_count: number
  reason: string | null
  results: MTBatchResultItem[]
}

// ================================================================ 文件下载
function triggerDownload(blob: Blob, filename: string): void {
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(href)
}

/** GET 二进制下载：绕开 axios envelope，用 `$fetch` + `responseType: 'blob'` 落盘 */
async function downloadGet(
  url: string,
  query: Record<string, unknown>,
  filename: string,
): Promise<void> {
  const token = storage.get<string>(STORAGE_TOKEN)
  const blob = await $fetch<Blob>(url, {
    method: 'GET',
    query,
    headers: token ? {Authorization: `Bearer ${token}`} : {},
    responseType: 'blob',
  })
  triggerDownload(blob, filename)
}

export const translationApi = {
  // ---- 语言 / 区域（公开） ----
  languages: () => http.get<LanguageItem[]>('/system/translation/languages'),

  detectLanguage: (acceptLanguage: string) =>
    http.get<DetectResult>('/system/translation/languages/detect', {
      accept_language: acceptLanguage || undefined,
    }),

  locales: () => http.get<LocaleInfo[]>('/system/translation/locales'),

  localize: (params: { dt: string; locale?: string; timezone?: string }) =>
    http.get<LocalizeResult>('/system/translation/localize', {
      dt: params.dt,
      locale: params.locale,
      timezone: params.timezone || undefined,
    }),

  /** 新增 / 覆盖一个自定义语言（setting:edit） */
  upsertLanguage: (data: LanguageUpsertPayload) =>
    http.post<LanguageUpsertResult>('/system/translation/languages', data),

  // ---- 词条 / 语言包 ----
  getEntry: (params: { key: string; locale?: string; default?: string }) =>
    http.get<EntryResult>('/system/translation/entry', {
      key: params.key,
      locale: params.locale,
      default: params.default,
    }),

  /** 整包词条（公开）：entries 为 {键: 译文}，status_counts 为状态聚合 */
  getBundle: (locale: string) =>
    http.get<BundleResult>(`/system/translation/bundle/${encodeURIComponent(locale)}`),

  /** 覆盖 / 合并语言包（setting:edit）：只接受 data / merge / status */
  replaceBundle: (locale: string, data: BundleReplacePayload) =>
    http.put<BundleReplaceResult>(
      `/system/translation/bundle/${encodeURIComponent(locale)}`,
      data,
    ),

  /** 写单条词条（setting:edit）：只接受 locale / key / value / status / translator_id / translator_name */
  setEntry: (data: EntryUpsertPayload) =>
    http.post<EntryUpsertResult>('/system/translation/entry', data),

  // ---- 统计 / 缺失 / 模板（公开） ----
  stats: () => http.get<StatsResult>('/system/translation/stats'),

  missing: (locale: string, limit = 100) =>
    http.get<MissingResult>('/system/translation/missing', {locale, limit}),

  template: (locale: string) =>
    http.get<TemplateResult>(`/system/translation/template/${encodeURIComponent(locale)}`),

  // ---- 导入导出 ----
  /** 导出词条为**真实文件下载**（公开）；文件名 `translation-<locale>.<format>` */
  exportTranslations: (locale: string, format: TranslationFormat = 'json') =>
    downloadGet(
      `${API_BASE_URL}/system/translation/export`,
      {locale, format},
      `translation-${locale}.${format}`,
    ),

  /** 解析导入内容并落库（setting:edit）：只接受 content / format / locale / merge / status */
  importTranslations: (data: ImportPayload) =>
    http.post<ImportResult>('/system/translation/import', data),

  // ---- 进度 ----
  allProgress: () => http.get<ProgressResult>('/system/translation/progress'),

  oneProgress: (locale: string) =>
    http.get<LanguageProgress>(`/system/translation/progress/${encodeURIComponent(locale)}`),

  report: () => http.get<ReportResult>('/system/translation/report'),

  /** 登记某条词条的翻译状态（setting:edit） */
  registerProgress: (locale: string, data: ProgressRegisterPayload) =>
    http.post<EntryUpsertResult>(
      `/system/translation/progress/${encodeURIComponent(locale)}`,
      data,
    ),

  // ---- 翻译记忆库 ----
  memoryStats: () => http.get<MemoryStats>('/system/translation/memory'),

  memorySuggest: (params: {
    source_text: string
    source_lang: string
    target_lang: string
    threshold?: number
    limit?: number
  }) =>
    http.get<MemorySuggestResult>('/system/translation/memory/suggest', {
      source_text: params.source_text,
      source_lang: params.source_lang,
      target_lang: params.target_lang,
      threshold: params.threshold,
      limit: params.limit,
    }),

  /** 导出记忆库为**真实文件下载**：`translation-memory.json` */
  exportMemory: () =>
    downloadGet(`${API_BASE_URL}/system/translation/memory/export`, {}, 'translation-memory.json'),

  /** 新增 / 更新记忆（setting:edit） */
  addMemory: (data: MemoryAddPayload) =>
    http.post<MemoryAddResult>('/system/translation/memory', data),

  /** 清空记忆（setting:edit）；带 language_pair 时只清空该语言对 */
  clearMemory: (languagePair?: string) =>
    http.delete<Record<string, unknown>>('/system/translation/memory', {
      language_pair: languagePair || undefined,
    }),

  /** 导入记忆（setting:edit）：只接受 content / merge */
  importMemory: (data: MemoryImportPayload) =>
    http.post<MemoryImportResult>('/system/translation/memory/import', data),

  // ---- 机器翻译 ----
  /** 提供商可用性（公开，只读环境变量，不返回明文） */
  mtProviders: () => http.get<MTProviderStatus[]>('/system/translation/mt/providers'),

  mtTranslate: (data: MTTranslatePayload) =>
    http.post<MTTranslateResult>('/system/translation/mt/translate', data),

  mtBatch: (data: MTBatchPayload) =>
    http.post<MTBatchResult>('/system/translation/mt/batch', data),
}

export default translationApi
