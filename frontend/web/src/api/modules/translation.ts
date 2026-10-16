/** 翻译管理接口（`/api/v3/system/translation`，system 域）
 *
 * 本模块**没有专用权限码**（`src/api/v3/core/permission/codes.py` 里不存在 `translation:*`），
 * 后端取语义最近的 `module_system:setting:view` / `module_system:setting:edit`：
 * 语言包 / 词条本质是系统级 key/value 配置。
 *
 * 契约要点（逐条对齐 `src/api/v3/modules/system/translation/controller.py`，共 27 个端点）：
 *  - 公开只读端点（无权限装饰器）：languages / languages/detect / locales / localize /
 *    entry / bundle/{locale} / stats / missing / template/{locale} / export / mt/providers；
 *  - 进度读（progress / progress/{locale} / report）与记忆库读（memory / memory/suggest /
 *    memory/export）需 `setting:view`；
 *  - 全部写端点（languages POST、bundle PUT、entry POST、import、progress POST、
 *    memory POST/DELETE/import、mt/translate、mt/batch）需 `setting:edit`。
 *
 * 文件下载：`GET /export` 与 `GET /memory/export` 返回**真实文件流**（服务端带
 * `Content-Disposition: attachment`），不是 `{code,msg,data}` JSON 信封，`http.get`
 * （只认 `code === 200` 的信封）无法承载二进制，故用同一 axios 实例 `http.raw`
 * 以 `responseType: 'blob'` 拉取，再从 `content-disposition` 解析文件名落盘。
 *
 * 机器翻译诚实降级：未配置提供商密钥时返回 `available=false` + 所需环境变量名、
 * `translated_text=null`，**绝不伪造译文**；页面据此如实提示。
 *
 * 搬运：本文件应放到 `src/api/modules/translation.ts`；`import http from '../request'`
 * 在迁入后即指向 `src/api/request.ts`。若要在 `@/api` 聚合入口暴露 `translationApi`
 * 与类型，需父代理在 `src/api/index.ts` 追加导出（本次**未**改动该文件）。
 */

import http from '../request'

// ================================================================ 语言 / 区域
export type TextDirection = 'ltr' | 'rtl'

/** 一个受支持语言（内置 + 自定义合并；自定义同 `code` 覆盖内置）；`is_default` 为模块默认语言 */
export interface LanguageItem {
  code: string
  name: string
  native_name: string
  direction: TextDirection
  is_default: boolean
}

/** `GET /languages/detect` 的语言识别结果（真实回退链） */
export interface DetectResult {
  accept_language: string
  language: string
  default_language: string
}

export interface CurrencyInfo {
  symbol: string
  code: string
  /** before / after */
  position: string
}

export interface NumberFormat {
  thousands: string
  decimal: string
}

/** `GET /locales` 单条区域信息 */
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

/** `GET /localize` 的返回：按区域格式化后的日期 / 时间 / 相对时间 + 区域信息 */
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

/** `POST /languages` 请求体（后端只接受 code / name / native_name / direction，未知字段直接 400） */
export interface LanguageUpsertPayload {
  code: string
  name?: string
  native_name?: string
  direction?: TextDirection
}

export interface LanguageUpsertResult {
  code: string
  action: 'created' | 'updated' | string
  overrides_builtin: boolean
}

// ================================================================ 词条 / 语言包
/** `GET /entry` 词条回退链结果，`source` ∈ {language, default_language, default} */
export interface EntryResult {
  key: string
  locale: string
  value: string
  source: string
}

/** `GET /bundle/{locale}` 整包词条：entries 为 `{键: 译文}`，status_counts 为状态聚合 */
export interface BundleResult {
  locale: string
  count: number
  status_counts: Record<string, number>
  entries: Record<string, string>
}

/** `PUT /bundle/{locale}` 请求体（只接受 data / merge / status） */
export interface BundleReplacePayload {
  /** `{词条键: 译文}` */
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

/** `POST /entry` 请求体（只接受 locale / key / value / status / translator_id / translator_name） */
export interface EntryUpsertPayload {
  locale: string
  key: string
  value?: string
  status?: string
  translator_id?: number
  translator_name?: string
}

/** `POST /entry` 与 `POST /progress/{locale}` 的返回：落库后的规范化词条 */
export interface EntryUpsertResult {
  locale: string
  key: string
  entry: Record<string, unknown>
}

// ================================================================ 统计 / 缺失 / 模板
export interface LanguageStat {
  total_keys: number
  translated_keys: number
  missing_keys: number
  completion_rate: number
}

/** `GET /stats`：相对源语言的键命中率（真实计算） */
export interface StatsResult {
  source_language: string
  source_keys: number
  languages: Record<string, LanguageStat>
}

/** `GET /missing`：相对源语言的缺失键与未翻译键（真实 diff） */
export interface MissingResult {
  locale: string
  source_locale: string
  missing_count: number
  untranslated_count: number
  missing_keys: string[]
  untranslated_keys: string[]
}

/** `GET /template/{locale}`：以默认语言的键生成目标语言的空模板 */
export interface TemplateResult {
  locale: string
  default_language: string
  count: number
  template: Record<string, string>
}

// ================================================================ 导入导出
/** 后端 `service.SUPPORTED_FORMATS` */
export type TranslationFormat = 'json' | 'csv' | 'po' | 'xliff' | 'yaml'

/** `POST /import` 请求体（只接受 content / format / locale / merge / status） */
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
/** 单语言进度（后端 `service.language_progress` 的真实计算形状） */
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

/** `GET /progress` */
export interface ProgressResult {
  source_locale: string
  languages: LanguageProgress[]
}

/** 进度报告里的贡献者（由词条作者真实聚合） */
export interface ProgressContributor {
  user_id: number
  name: string | null
  translations_count: number
  last_contribution: string | null
}

/** `GET /report` */
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

/** `POST /progress/{locale}` 请求体（只接受 key / value / status / is_translated / translator_id / translator_name） */
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

/** `GET /memory` 记忆库统计 */
export interface MemoryStats {
  total_entries: number
  language_pairs: number
  pairs_detail: MemoryPair[]
}

/** `GET /memory/suggest` 的一条匹配（精确 / 模糊打分，相似度降序） */
export interface MemoryMatch {
  source: string
  target: string
  similarity: number
  match_type: 'exact' | 'fuzzy' | string
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

/** `POST /memory` 请求体（只接受 source_text / target_text / source_lang / target_lang / context） */
export interface MemoryAddPayload {
  source_text: string
  target_text?: string
  source_lang: string
  target_lang: string
  context?: string
}

export interface MemoryAddResult {
  pair: string
  action: 'created' | 'updated' | string
  entry: Record<string, unknown>
}

/** `POST /memory/import` 请求体（只接受 content / merge）——content 可为 JSON 字符串或已解析对象 */
export interface MemoryImportPayload {
  content: string | Record<string, unknown>
  merge?: boolean
}

export interface MemoryImportResult {
  merge: boolean
  total_entries: number
}

/** `DELETE /memory` 的返回：清空整个库或指定语言对 */
export interface MemoryClearResult {
  cleared: boolean
  pair?: string
  removed?: number
  pairs_removed?: number
}

// ================================================================ 机器翻译
/** `GET /mt/providers` 单条提供商可用性（只读环境变量，**不返回明文**） */
export interface MTProviderStatus {
  provider: string
  name: string
  available: boolean
  /** 各环境变量是否已设置（true/false，不含明文） */
  env: Record<string, boolean>
  required_env: string[]
  url: string
}

/** `POST /mt/translate` 请求体 */
export interface MTTranslatePayload {
  text: string
  /** 源语言，auto 表示自动检测 */
  source_lang?: string
  target_lang: string
  /** baidu / youdao / deepl / google */
  provider?: string
}

/** `POST /mt/translate` 返回：未配置密钥时 `available=false`、`translated_text=null`，**绝不伪造译文** */
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

/** `POST /mt/batch` 请求体 */
export interface MTBatchPayload {
  texts: string[]
  source_lang?: string
  target_lang: string
  provider?: string
  /** 请求间隔秒数（防限流） */
  delay?: number
}

/** `POST /mt/batch` 返回：未配置密钥时整批 `available=false` */
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
/** 触发浏览器下载：临时 `<a download>` + objectURL（用后释放） */
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

/** 从 `content-disposition` 解析文件名（优先 RFC 5987 的 `filename*`，回退 `filename`） */
function parseFilename(disposition: unknown): string | null {
  if (!disposition) return null
  const text = String(disposition)
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(text)
  if (encoded && encoded[1]) {
    try {
      return decodeURIComponent(encoded[1].trim())
    } catch {
      /* 解码失败则回退到 filename */
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(text)
  return plain && plain[1] ? plain[1].trim() : null
}

/**
 * GET 二进制下载：用同一 axios 实例（自动注入 Bearer token）以 blob 拉取，
 * 文件名从响应头解析，解析失败回退到 `fallbackName`。
 */
async function downloadGet(
  url: string,
  params: Record<string, unknown>,
  fallbackName: string,
): Promise<void> {
  const resp = await http.raw.get<Blob>(url, {params, responseType: 'blob'})
  const filename =
    parseFilename(resp.headers?.['content-disposition']) ?? fallbackName
  triggerDownload(resp.data, filename)
}

export const translationApi = {
  // ---- 语言 / 区域（languages / detect / locales / localize 公开；upsertLanguage 需 setting:edit） ----
  /** 支持语言列表（内置 + 自定义） */
  languages: () => http.get<LanguageItem[]>('/system/translation/languages'),

  /** 语言识别（按 Accept-Language 回退链） */
  detectLanguage: (acceptLanguage: string) =>
    http.get<DetectResult>('/system/translation/languages/detect', {
      accept_language: acceptLanguage || undefined,
    }),

  /** 本地化区域信息列表（13 个地区） */
  locales: () => http.get<LocaleInfo[]>('/system/translation/locales'),

  /** 按区域格式化时间点 */
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
  /** 取单条词条（回退链，公开） */
  getEntry: (params: { key: string; locale?: string; default?: string }) =>
    http.get<EntryResult>('/system/translation/entry', {
      key: params.key,
      locale: params.locale,
      default: params.default,
    }),

  /** 整包词条（公开）：entries 为 `{键: 译文}`，status_counts 为状态聚合 */
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
      '/system/translation/export',
      {locale, format},
      `translation-${locale}.${format}`,
    ),

  /** 解析导入内容并落库（setting:edit）：只接受 content / format / locale / merge / status */
  importTranslations: (data: ImportPayload) =>
    http.post<ImportResult>('/system/translation/import', data),

  // ---- 进度（读需 setting:view） ----
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
  /** 记忆库统计（setting:view） */
  memoryStats: () => http.get<MemoryStats>('/system/translation/memory'),

  /** 相似匹配（setting:view）：精确 / 模糊打分，按相似度降序 */
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

  /** 导出记忆库为**真实文件下载**（setting:view）：`translation-memory.json` */
  exportMemory: () =>
    downloadGet('/system/translation/memory/export', {}, 'translation-memory.json'),

  /** 新增 / 更新记忆（setting:edit） */
  addMemory: (data: MemoryAddPayload) =>
    http.post<MemoryAddResult>('/system/translation/memory', data),

  /** 清空记忆（setting:edit）；带 language_pair 时只清空该语言对 */
  clearMemory: (languagePair?: string) =>
    http.delete<MemoryClearResult>('/system/translation/memory', {
      language_pair: languagePair || undefined,
    }),

  /** 导入记忆（setting:edit）：只接受 content / merge */
  importMemory: (data: MemoryImportPayload) =>
    http.post<MemoryImportResult>('/system/translation/memory/import', data),

  // ---- 机器翻译 ----
  /** 提供商可用性（公开，只读环境变量，不返回明文） */
  mtProviders: () => http.get<MTProviderStatus[]>('/system/translation/mt/providers'),

  /** 单条翻译（setting:edit）：未配置密钥时如实返回 available=false，绝不伪造译文 */
  mtTranslate: (data: MTTranslatePayload) =>
    http.post<MTTranslateResult>('/system/translation/mt/translate', data),

  /** 批量翻译（setting:edit）：未配置密钥时整批如实返回 available=false */
  mtBatch: (data: MTBatchPayload) =>
    http.post<MTBatchResult>('/system/translation/mt/batch', data),
}

export default translationApi
