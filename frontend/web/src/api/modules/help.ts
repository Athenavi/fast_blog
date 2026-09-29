/** 帮助中心接口（/api/v3/system/help/*，system 域）
 *
 * 对齐后端 `src/api/v3/modules/system/help/controller.py` 的 7 个端点：
 *   - 主题概览 / 单条主题 / 相关性搜索 / 字段提示 / 视频教程：**公开读**；
 *   - 新增覆盖 / 删除自定义帮助：需 `module_system:setting:edit`。
 *
 * 字段逐条对照 `service.py`：
 *   - 概览（GET /topics）由 controller 组装，只含 page_key / title / tags / language / is_default，**不含 content**；
 *   - 单条（GET /topic/{page_key}）返回 `_normalize_topic` 的完整结构（含 content / related_links）；
 *   - 搜索（GET /search）返回 page_key / title / excerpt / score / matched_fields；
 *   - 字段提示（GET /tooltip）的 tooltip 未命中时为 null。
 */

import http from '../request'

/** 相关链接（service 中为 [{title, url}]） */
export interface HelpRelatedLink {
  title: string
  url: string
}

/** 主题概览项（GET /system/help/topics） */
export interface HelpTopicSummary {
  page_key: string
  title: string
  tags: string[]
  language: string
  /** 是否为内置默认主题（DEFAULT_TOPICS 中存在的 page_key） */
  is_default: boolean
}

/** 单条主题详情（GET /system/help/topic/{page_key}） */
export interface HelpTopicDetail {
  page_key: string
  title: string
  content: string
  tags: string[]
  language: string
  related_links: HelpRelatedLink[]
}

/** 搜索命中项（GET /system/help/search） */
export interface HelpSearchItem {
  page_key: string
  title: string
  excerpt: string
  score: number
  matched_fields: string[]
}

/** 搜索查询参数（GET /system/help/search） */
export type HelpSearchQuery = {
  q: string
  /** 默认 20，范围 1~100 */
  limit?: number
}

/** 新增 / 覆盖帮助的请求体（POST /system/help/topic）
 *
 * 后端刻意收原始 dict 并**拒绝未知字段**，因此这里只声明 TOPIC_FIELDS：
 * page_key / title / content / tags / language / related_links。
 */
export interface HelpTopicUpsertPayload {
  page_key: string
  title: string
  content: string
  tags?: string[]
  /** zh_CN / en_US */
  language?: string
  related_links?: HelpRelatedLink[]
}

/** 新增 / 覆盖结果（POST /system/help/topic） */
export interface HelpTopicUpsertResult {
  page_key: string
  action: 'created' | 'updated'
  /** 该 page_key 是否覆盖了内置默认主题 */
  overrides_default: boolean
}

/** 删除结果（DELETE /system/help/topic/{page_key}） */
export interface HelpTopicDeleteResult {
  page_key: string
  deleted: boolean
  /** 删除后是否回退到内置默认内容 */
  reverted_to_default: boolean
}

/** 字段提示查询参数（GET /system/help/tooltip） */
export type HelpTooltipQuery = {
  field: string
  /** 上下文，默认 general */
  context?: string
}

/** 字段提示结果（GET /system/help/tooltip）；tooltip 未命中时为 null */
export interface HelpTooltipResult {
  field: string
  context: string
  tooltip: string | null
}

/** 视频教程项（GET /system/help/videos） */
export interface HelpVideoItem {
  id: string
  title: string
  description: string
  duration: string
  url: string
  thumbnail: string
  topic: string
}

export const helpApi = {
  /** 全部帮助主题概览（公开） */
  listTopics: () => http.get<HelpTopicSummary[]>('/system/help/topics'),

  /** 单条帮助主题（公开）；不存在时后端 404 */
  getTopic: (pageKey: string) =>
    http.get<HelpTopicDetail>(`/system/help/topic/${encodeURIComponent(pageKey)}`),

  /** 相关性搜索（公开） */
  search: (params: HelpSearchQuery) => http.get<HelpSearchItem[]>('/system/help/search', params),

  /** 新增 / 覆盖自定义帮助（需 setting:edit） */
  upsertTopic: (data: HelpTopicUpsertPayload) =>
    http.post<HelpTopicUpsertResult>('/system/help/topic', data),

  /** 删除自定义帮助（需 setting:edit） */
  deleteTopic: (pageKey: string) =>
    http.delete<HelpTopicDeleteResult>(`/system/help/topic/${encodeURIComponent(pageKey)}`),

  /** 字段提示（公开） */
  tooltip: (params: HelpTooltipQuery) => http.get<HelpTooltipResult>('/system/help/tooltip', params),

  /** 视频教程（公开）；可选按 topic 过滤 */
  videos: (topic?: string) =>
    http.get<HelpVideoItem[]>('/system/help/videos', topic ? {topic} : undefined),
}
