/** 插件市场接口（/api/v3/extension/plugin/market/*）
 *
 * 后端只做**只读市场**（目录 / 详情 / 更新检查）+ 一次**显式确认**的安装；
 * 上传与发布不在本侧（市场服务端 `plugin-market-server/` 的 API.md 里为预留，一律 403）。
 */

import http from '../request'

/** 市场目录条目 */
export interface MarketPluginItem {
  slug: string
  name?: string
  version?: string
  summary?: string
  description?: string
  category?: string
  author?: string
  icon?: string
  tags?: string[]
  rating?: number
  installs?: number
  updated_at?: string
  download_url?: string
  sha256?: string
  readme?: string
  changelog?: string
  license?: string
  screenshots?: string[]
  versions?: MarketPluginVersion[]

  [key: string]: unknown
}

export interface MarketPluginVersion {
  version: string
  published_at?: string
  changelog?: string
  download_url?: string
  sha256?: string
  size?: number

  [key: string]: unknown
}

export interface MarketPluginList {
  items: MarketPluginItem[]
  total?: number
  page?: number
  page_size?: number
}

/** 更新检查条目（后端只返回确实有更新的） */
export interface MarketUpdateItem {
  slug: string
  current?: string
  latest?: string
  changelog?: string
  sha256?: string

  [key: string]: unknown
}

/** 目录查询参数。
 *
 * 用 `type` 而非 `interface`：TS 只给对象类型**字面量**（type alias）隐式索引签名，
 * 因此 `type` 才能直接传给 `http.get(url, params: Record<string, unknown>)`。
 */
export type MarketPluginQuery = {
  keyword?: string
  category?: string
  page?: number
  page_size?: number
}

export interface MarketInstallPayload {
  slug: string
  version: string
  /** 市场声明的校验和（可选，后端会二次校验） */
  sha256?: string
  /** 二次确认：危险操作必须显式传 true，否则后端拒绝 */
  confirm: boolean
}

export const pluginMarketApi = {
  list: (params: MarketPluginQuery = {}) =>
    http.get<MarketPluginList>('/extension/plugin/market/plugins', params),
  detail: (slug: string) => http.get<MarketPluginItem>(`/extension/plugin/market/plugins/${slug}`),
  updates: () => http.get<{ updates: MarketUpdateItem[] }>('/extension/plugin/market/updates'),
  install: (payload: MarketInstallPayload) =>
    http.post<Record<string, unknown>>('/extension/plugin/market/install', payload),
}
