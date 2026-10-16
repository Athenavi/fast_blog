/** 访问埋点与统计接口（/api/v3/analytics/tracking）
 *
 * 分两类（对应后端 `src/api/v3/modules/analytics/tracking/controller.py`）：
 *
 *  - **上报**（page-view / event / search / ad-impression / ad-click）：**可选登录**，供前台访客页面
 *    调用；后端写入 `page_views` / `user_activities` / `search_history` / `ad_impressions` / `ad_clicks`
 *    四张表（v3 里原本无写入点，本模块补齐），埋点失败不阻断业务。
 *  - **报表**（traffic-sources / devices / popular-pages / sessions / articles/{id} / searches / ads）：
 *    需权限码 `module_analytics:dashboard:view`（`codes.DASHBOARD_VIEW`），返回对真表的聚合结果。
 */

import http from '../request'

// ---------------------------------------------------------------- 上报入参（字段来源：schema.py）

/** 页面浏览上报 —— 对应 `schema.PageViewTrackRequest`（page_url 必填，其余可选） */
export interface PageViewTrackPayload {
  /** 页面 URL（建议相对路径），必填，1–500 字符 */
  page_url: string
  /** 页面标题，可选，≤500 字符 */
  page_title?: string | null
  /** 来源页；空表示直接访问，可选，≤500 字符 */
  referrer?: string | null
  /** 前端生成的会话 ID（同一会话复用，用于会话统计），可选，≤255 字符 */
  session_id?: string | null
}

/** 行为事件上报 —— 对应 `schema.EventTrackRequest`（activity_type 必填）。
 *  activity_type 稳定枚举：view / like / unlike / share / bookmark / comment / click / scroll / search / follow / purchase… */
export interface EventTrackPayload {
  /** 事件类型（稳定枚举），必填，1–100 字符 */
  activity_type: string
  /** 目标类型，如 article，可选，≤50 字符 */
  target_type?: string | null
  /** 目标 ID，如文章 ID，可选，≥1 */
  target_id?: number | null
  /** 附加说明，可选，≤255 字符 */
  details?: string | null
}

/** 搜索记录上报 —— 对应 `schema.SearchTrackRequest`（keyword 必填） */
export interface SearchTrackPayload {
  /** 搜索关键词，必填，1–255 字符 */
  keyword: string
  /** 本次搜索命中结果数，可选，默认 0，0–1000000 */
  results_count?: number
}

/** 广告曝光上报 —— 对应 `schema.AdImpressionTrackRequest`（ad_id 必填） */
export interface AdImpressionTrackPayload {
  /** 广告 ID，必填，≥1（后端要求广告存在，否则 404） */
  ad_id: number
  /** 曝光所在页面 URL，可选，≤500 字符 */
  page_url?: string | null
}

/** 广告点击上报 —— 对应 `schema.AdClickTrackRequest`（ad_id 必填） */
export interface AdClickTrackPayload {
  /** 广告 ID，必填，≥1（后端要求广告存在，否则 404） */
  ad_id: number
  /** 来源页，可选，≤500 字符 */
  referrer?: string | null
}

// ---------------------------------------------------------------- 上报返回（字段来源：service.py 各 record_* 返回 dict）

/** 页面浏览上报返回 —— `service.record_page_view()`：`{id, device_type, browser, platform}` */
export interface PageViewTrackResult {
  /** 新写入的 page_views 记录 ID */
  id: number
  /** 后端按 UA 轻量解析出的设备类型（desktop/mobile/tablet），识别不到为 null */
  device_type: string | null
  /** 解析出的浏览器名，识别不到为 null */
  browser: string | null
  /** 解析出的操作系统，识别不到为 null */
  platform: string | null
}

/** 行为事件上报返回 —— `service.record_event()`：`{id, activity_type}` */
export interface EventTrackResult {
  /** 新写入的 user_activities 记录 ID */
  id: number
  /** 回写的事件类型 */
  activity_type: string
}

/** 搜索上报返回 —— `service.record_search()`：`{id, keyword}` */
export interface SearchTrackResult {
  /** 新写入的 search_history 记录 ID */
  id: number
  /** 回写的关键词 */
  keyword: string
}

/** 广告曝光上报返回 —— `service.record_ad_impression()`：`{id, ad_id}` */
export interface AdImpressionTrackResult {
  /** 新写入的 ad_impressions 记录 ID */
  id: number
  /** 对应广告 ID */
  ad_id: number
}

/** 广告点击上报返回 —— `service.record_ad_click()`：`{id, ad_id}` */
export interface AdClickTrackResult {
  /** 新写入的 ad_clicks 记录 ID */
  id: number
  /** 对应广告 ID */
  ad_id: number
}

// ---------------------------------------------------------------- 报表返回（字段来源：service.py 各聚合方法）

/** 流量来源单行 —— `service.traffic_sources()` 的 `items[]` 元素 */
export interface TrafficSourceItem {
  /** 来源 referrer；空 referrer 被后端归为 "(direct)" */
  source: string
  /** 该来源浏览量 */
  views: number
  /** 占比（0–1 小数，后端 round(...,4)） */
  share: number
}

/** 流量来源 —— `service.traffic_sources()`：`{period_days, total, items[]}` */
export interface TrafficSourcesResult {
  /** 统计周期天数 */
  period_days: number
  /** 周期内总浏览量 */
  total: number
  /** 按 referrer 聚合的来源列表（降序） */
  items: TrafficSourceItem[]
}

/** 设备/浏览器/系统单项 —— `service.device_breakdown()` 各组元素 */
export interface DeviceCountItem {
  /** 维度取值（如 desktop / Chrome / Windows），识别不到为 "unknown" */
  name: string
  /** 该取值浏览量 */
  views: number
}

/** 设备/浏览器/系统分布 —— `service.device_breakdown()`：`{period_days, device_type, browser, platform}`
 *  三组均为 `{name, views}[]`（来自 page_views 的 UA 解析结果） */
export interface DeviceBreakdownResult {
  /** 统计周期天数 */
  period_days: number
  /** 设备类型分布 */
  device_type: DeviceCountItem[]
  /** 浏览器分布 */
  browser: DeviceCountItem[]
  /** 操作系统分布 */
  platform: DeviceCountItem[]
}

/** 热门页面单行 —— `service.popular_pages()` 的 `items[]` 元素 */
export interface PopularPageItem {
  /** 页面 URL */
  page_url: string
  /** 浏览量 */
  views: number
  /** 独立会话数（distinct session_id） */
  sessions: number
}

/** 热门页面 —— `service.popular_pages()`：`{period_days, items[]}` */
export interface PopularPagesResult {
  /** 统计周期天数 */
  period_days: number
  /** 按 URL 聚合的热门页面（降序） */
  items: PopularPageItem[]
}

/** 会话统计 —— `service.session_stats()`：`{period_days, sessions, avg_views_per_session, max_views_in_session}` */
export interface SessionStatsResult {
  /** 统计周期天数 */
  period_days: number
  /** 会话数（distinct session_id） */
  sessions: number
  /** 人均浏览（avg_views_per_session，后端 round(...,2)） */
  avg_views_per_session: number
  /** 单会话最大浏览数 */
  max_views_in_session: number
}

/** 单篇文章行为事件统计 —— `service.article_events()`：
 *  `{article_id, period_days, by_type, total}` */
export interface ArticleEventsResult {
  /** 文章 ID */
  article_id: number
  /** 统计周期天数 */
  period_days: number
  /** 事件类型 → 次数（activity_type 可能为 "unknown"） */
  by_type: Record<string, number>
  /** 事件总数 */
  total: number
}

/** 搜索统计单行 —— `service.search_stats()` 的 `items[]` 元素 */
export interface SearchStatItem {
  /** 关键词 */
  keyword: string
  /** 搜索次数 */
  count: number
  /** 平均结果数（后端 round(...,2)） */
  avg_results: number
}

/** 搜索统计 —— `service.search_stats()`：
 *  `{period_days, total_searches, zero_result_rate, items[]}` */
export interface SearchStatsResult {
  /** 统计周期天数 */
  period_days: number
  /** 周期内搜索总次数 */
  total_searches: number
  /** 零结果率（0–1 小数，后端 round(...,4)；无搜索时为 0.0） */
  zero_result_rate: number
  /** 热门关键词列表（降序） */
  items: SearchStatItem[]
}

/** 广告点击 Top 项 —— `service.ad_stats()` 的 `top_ads[]` 元素 */
export interface TopAdItem {
  /** 广告 ID */
  ad_id: number
  /** 点击次数 */
  clicks: number
}

/** 广告曝光/点击/CTR —— `service.ad_stats()`：
 *  `{period_days, impressions, clicks, ctr, top_ads[]}` */
export interface AdStatsResult {
  /** 统计周期天数 */
  period_days: number
  /** 曝光总数 */
  impressions: number
  /** 点击总数 */
  clicks: number
  /** 点击率（0–1 小数，后端 round(...,4)；无曝光时为 0.0） */
  ctr: number
  /** 点击最多的广告 Top 10 */
  top_ads: TopAdItem[]
}

// ---------------------------------------------------------------- API

export const trackingApi = {
  // ---- 上报（可选登录，供前台访客调用；端点见 controller.py）----
  /** 上报页面浏览。POST /analytics/tracking/page-view */
  pageView: (payload: PageViewTrackPayload) =>
    http.post<PageViewTrackResult>('/analytics/tracking/page-view', payload),
  /** 上报行为事件。POST /analytics/tracking/event */
  event: (payload: EventTrackPayload) =>
    http.post<EventTrackResult>('/analytics/tracking/event', payload),
  /** 上报搜索记录。POST /analytics/tracking/search */
  search: (payload: SearchTrackPayload) =>
    http.post<SearchTrackResult>('/analytics/tracking/search', payload),
  /** 上报广告曝光。POST /analytics/tracking/ad-impression */
  adImpression: (payload: AdImpressionTrackPayload) =>
    http.post<AdImpressionTrackResult>('/analytics/tracking/ad-impression', payload),
  /** 上报广告点击。POST /analytics/tracking/ad-click */
  adClick: (payload: AdClickTrackPayload) =>
    http.post<AdClickTrackResult>('/analytics/tracking/ad-click', payload),

  // ---- 报表（需 module_analytics:dashboard:view）----
  /** 流量来源（按 referrer 聚合）。GET /analytics/tracking/traffic-sources */
  trafficSources: (params?: { days?: number; limit?: number }) =>
    http.get<TrafficSourcesResult>('/analytics/tracking/traffic-sources', params),
  /** 设备 / 浏览器 / 系统分布。GET /analytics/tracking/devices */
  devices: (days = 7) =>
    http.get<DeviceBreakdownResult>('/analytics/tracking/devices', {days}),
  /** 热门页面。GET /analytics/tracking/popular-pages */
  popularPages: (params?: { days?: number; limit?: number }) =>
    http.get<PopularPagesResult>('/analytics/tracking/popular-pages', params),
  /** 会话统计。GET /analytics/tracking/sessions */
  sessions: (days = 7) =>
    http.get<SessionStatsResult>('/analytics/tracking/sessions', {days}),
  /** 单篇文章行为事件统计。GET /analytics/tracking/articles/{article_id} */
  articleEvents: (articleId: number, days = 30) =>
    http.get<ArticleEventsResult>(`/analytics/tracking/articles/${articleId}`, {days}),
  /** 搜索统计（热门词 / 零结果率）。GET /analytics/tracking/searches */
  searches: (params?: { days?: number; limit?: number }) =>
    http.get<SearchStatsResult>('/analytics/tracking/searches', params),
  /** 广告曝光 / 点击 / CTR。GET /analytics/tracking/ads */
  ads: (days = 30) =>
    http.get<AdStatsResult>('/analytics/tracking/ads', {days}),
}
