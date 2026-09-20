/**
 * 前台内容类型
 *
 * 字段与后端 v3 内容域的公开端点返回体对齐
 * （见 src/api/v3/modules/content 下各模块的 schema.py）。
 */

export interface ArticleItem {
  id: number
  title: string
  slug?: string | null
  summary?: string | null
  cover_image?: string | null
  category_id?: number | null
  tags?: string[]
  status?: number
  views?: number
  likes?: number
  is_top?: boolean
  /** 仅 VIP 可见（批次 16）：正文由带授权的正文端点下发 */
  is_vip_only?: boolean
  /** 所需 VIP 等级 */
  required_vip_level?: number
  /** 服务端判定"当前请求者读不到正文"（未登录 / 等级不足） */
  locked?: boolean
  created_at?: string | null
  updated_at?: string | null
  published_at?: string | null
}

export interface ArticleDetail extends ArticleItem {
  content?: string | null
  author_id?: number | null
  author_name?: string | null
}

export interface CategoryItem {
  id: number
  name: string
  slug?: string | null
  description?: string | null
  parent_id?: number | null
  article_count?: number
  sort_order?: number
  children?: CategoryItem[]
}

export interface PageItem {
  id: number
  title: string
  slug: string
  content?: string | null
  summary?: string | null
  created_at?: string | null
}

/** 站点公开设置（`/system/setting/public`） */
export interface SiteSettings {
  site_name?: string
  site_description?: string
  site_keywords?: string
  site_logo?: string
  site_footer?: string
  icp?: string
}
