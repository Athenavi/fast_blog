/** 多站点管理接口（/api/v3/system/site，system 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface SiteItem {
  id: number
  name?: string | null
  slug?: string | null
  domain?: string | null
  additional_domains?: string[] | null
  description?: string | null
  logo_url?: string | null
  favicon_url?: string | null
  theme?: string | null
  language?: string | null
  timezone?: string | null
  settings?: Record<string, unknown> | null
  is_active: boolean
  is_default: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface SiteQuery extends PageQuery {
  is_active?: boolean
}

export interface SitePayload {
  name: string
  slug?: string
  domain?: string
  additional_domains?: string[] | null
  description?: string | null
  logo_url?: string | null
  favicon_url?: string | null
  theme?: string
  language?: string
  timezone?: string
  settings?: Record<string, unknown> | null
  is_active?: boolean
  is_default?: boolean
}

export const siteApi = {
  list: (params?: SiteQuery) => http.page<SiteItem>('/system/site', params),

  create: (data: SitePayload) => http.post<SiteItem>('/system/site', data),

  update: (id: number, data: Partial<SitePayload>) =>
    http.put<SiteItem>(`/system/site/${id}`, data),

  remove: (id: number) => http.delete<null>(`/system/site/${id}`),

  // ───────────────── 以下为追加（多站点：域名解析 + 用户归属 + 站点成员） ─────────────────

  /** 当前用户所属站点（GET /system/site/mine） */
  mine: () => http.get<MySitesResult>('/system/site/mine'),

  /** 按域名解析站点（GET /system/site/resolve，公开端点） */
  resolve: (domain: string) =>
    http.get<SiteResolveResult>('/system/site/resolve', {domain}),

  /** 设为默认站点（POST /system/site/{site_id}/default） */
  setDefault: (id: number) => http.post<SiteBrief>(`/system/site/${id}/default`),

  /** 设置站点域名（PUT /system/site/{site_id}/domains） */
  setDomains: (id: number, data: SiteDomainsPayload) =>
    http.put<SiteDomainsResult>(`/system/site/${id}/domains`, data),

  /** 站点成员列表（GET /system/site/{site_id}/members，分页） */
  members: (id: number, params?: PageQuery) =>
    http.page<SiteMemberItem>(`/system/site/${id}/members`, params),

  /** 添加 / 更新站点成员（POST /system/site/{site_id}/members） */
  addMember: (id: number, data: SiteMemberPayload) =>
    http.post<SiteMemberAddResult>(`/system/site/${id}/members`, data),

  /** 移除站点成员（DELETE /system/site/{site_id}/members/{user_id}） */
  removeMember: (id: number, userId: number) =>
    http.delete<null>(`/system/site/${id}/members/${userId}`),
}

// ───────────────── 追加类型（逐条对照后端 multisite_service / controller 返回体） ─────────────────

/** 站点概要（后端 multisite `_site_out`；resolve / default 返回值） */
export interface SiteBrief {
  id: number
  name?: string | null
  slug?: string | null
  domain?: string | null
  theme?: string | null
  language?: string | null
  timezone?: string | null
  logo_url?: string | null
  favicon_url?: string | null
  is_active: boolean
  is_default: boolean
}

/** 域名设置返回值（`_site_out(..., with_domains=True)`，含 additional_domains） */
export interface SiteDomainsResult extends SiteBrief {
  additional_domains: string[]
}

/** `PUT /{site_id}/domains` 请求体（SiteDomainsUpdate） */
export interface SiteDomainsPayload {
  domain?: string
  additional_domains?: string[]
}

/** `GET /resolve` 返回值（matched=false 表示回退到默认站点） */
export interface SiteResolveResult extends SiteBrief {
  matched: boolean
  match: 'primary' | 'additional' | 'default'
}

/** 站点成员（后端 multisite `_member_out`） */
export interface SiteMemberItem {
  id: number
  site_id: number
  user_id: number
  role: string
  is_active: boolean
  joined_at?: string | null
}

/** `POST /{site_id}/members` 请求体（SiteMemberCreate） */
export interface SiteMemberPayload {
  user_id: number
  role?: string
  is_active?: boolean
}

/** 添加 / 更新成员的返回值（`created` 区分新增与更新） */
export interface SiteMemberAddResult extends SiteMemberItem {
  created: boolean
}

/** 「我的站点」单项（`user_sites` 的 items 元素） */
export interface MySiteItem extends SiteBrief {
  role: string
  joined_at?: string | null
}

/** `GET /mine` 返回值 */
export interface MySitesResult {
  user_id: number
  items: MySiteItem[]
}
