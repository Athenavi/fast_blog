/** 系统工具接口（`/api/v3/system/utility`，system 域）
 *
 * 对齐后端 `src/api/v3/modules/system/utility/controller.py`，共 5 个端点：
 *   GET  /system/utility/nlp/intents            NLP 解析能力目录（**公开**）
 *   POST /system/utility/nlp/parse              解析自然语言命令（**公开**，请求字段 `command`）
 *   GET  /system/utility/user/vip-status        当前用户 VIP 状态（仅认证）
 *   GET  /system/utility/block-pattern/{id}     展开区块模式定义（`module_extension:block_pattern:view`）
 *   GET  /system/utility/article/{id}/markdown  导出文章 Markdown 附件（`module_content:article:view`）
 *
 * 字段逐条对照同目录 `schema.py` 的 `NlpIntentCatalogOut` / `NlpParseResultOut` /
 * `UserVipStatusOut` / `BlockPatternDefOut`。
 *
 * 说明：`article/{id}/markdown` 返回 **流式 Markdown 附件下载**（RFC 6266 文件名），
 * 不是统一 JSON 信封，故走 `http.raw` + `responseType: 'blob'`，由页面负责触发浏览器下载。
 */

import http from '../request'

/** NLP 解析能力目录（`GET /system/utility/nlp/intents`，字段与 `NlpIntentCatalogOut` 一致） */
export interface NlpIntentCatalog {
  /** 支持的意图类型（源 `IntentType` 枚举值） */
  intents: string[]
  /** 意图 → 触发关键词正则 */
  intent_patterns: Record<string, string[]>
  /** 可识别的实体类型 */
  entity_types: string[]
  /** 可识别的时间表达式 */
  time_ranges: string[]
}

/** `POST /system/utility/nlp/parse` 请求体（字段名即后端 `NlpParseRequest.command`） */
export interface NlpParseRequest {
  /** 自然语言命令，1 ~ 2000 字 */
  command: string
}

/** 命令解析结果（`POST /system/utility/nlp/parse`，字段与 `NlpParseResultOut` 一致） */
export interface NlpParseResult {
  /** 原始命令文本 */
  original_command: string
  /** 识别出的意图；无法识别时为 null */
  intent: string | null
  /** 识别出的实体类型 */
  entity_type: string | null
  /** 抽取到的参数 */
  parameters: Record<string, unknown>
  /** 意图置信度 0.0 ~ 1.0 */
  confidence: number
  /** 解析时间（ISO 8601） */
  timestamp: string | null
  /** 无法识别意图时的原因 */
  error: string | null
}

/** 当前用户 VIP 状态（`GET /system/utility/user/vip-status`，字段与 `UserVipStatusOut` 一致） */
export interface UserVipStatus {
  user_id: number
  /** 是否为 VIP（源 `user_defs.is_vip` 判定结果） */
  is_vip: boolean
  /** 缓存 VIP 等级字段 */
  vip_level: number | null
  /** VIP 过期时间（ISO 8601） */
  vip_expires_at: string | null
}

/** 区块模式定义展开结果（`GET /system/utility/block-pattern/{id}`，字段与 `BlockPatternDefOut` 一致） */
export interface BlockPatternDef {
  name: string | null
  title: string | null
  description: string | null
  category: string | null
  /** 解析后的块数据列表（结构取决于源 `block_pattern_defs.to_pattern_dict`） */
  blocks: unknown[]
  /** 关键词列表 */
  keywords: string[]
  thumbnail: string | null
  viewport_width: number | null
  is_public: boolean
  /** ISO 8601 字符串 */
  created_at: string | null
  /** ISO 8601 字符串 */
  updated_at: string | null
}

/** `GET /system/utility/article/{id}/markdown` 查询参数（对齐后端 Query 定义） */
export interface ArticleMarkdownParams {
  /** 语言代码，如 zh-CN；指定时按 `language_code` 精确取内容 */
  language?: string
  /** 是否在正文前加一级标题，默认 true */
  include_title?: boolean
}

export const utilityApi = {
  /** NLP 解析能力目录（**公开**，无需权限） */
  nlpIntents: () => http.get<NlpIntentCatalog>('/system/utility/nlp/intents'),

  /** 解析自然语言命令（**公开**；请求体字段为 `command`） */
  parseCommand: (command: string) => http.post<NlpParseResult>('/system/utility/nlp/parse', {command}),

  /** 当前用户 VIP 状态（仅认证） */
  userVipStatus: () => http.get<UserVipStatus>('/system/utility/user/vip-status'),

  /** 展开区块模式定义（`module_extension:block_pattern:view`） */
  blockPattern: (id: number) => http.get<BlockPatternDef>(`/system/utility/block-pattern/${id}`),

  /** 导出文章 Markdown 附件（`module_content:article:view`；返回流式附件，非 JSON 信封） */
  articleMarkdown: (id: number, params?: ArticleMarkdownParams) =>
    http.raw.get<Blob>(`/system/utility/article/${id}/markdown`, {
      params,
      responseType: 'blob',
    }),
}
