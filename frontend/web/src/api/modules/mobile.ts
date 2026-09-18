/**
 * 前台用户端接口（v3 的 `mobile` 域）
 *
 * 与 `system/auth` 的差异：这里面向站内读者（注册、我的资料、我的统计），
 * 需要登录的接口走浏览器 cookie / Bearer，与后台共用同一套 token 机制。
 */
import http from '../request'
import type {PageQuery} from '../types'

export interface MobileTokenData {
  access_token?: string
  refresh_token?: string
  token_type?: string
  expires_in?: number
  user_id?: number
  username?: string
  requires_2fa?: boolean
  temp_token?: string
  message?: string
}

export interface RegisterPayload {
  /** 3-30 位，仅字母/数字/下划线（与后端校验一致） */
  username: string
  email: string
  /** 至少 8 位 */
  password: string
}

export interface MobileLoginPayload {
  username?: string
  email?: string
  password: string
  remember_me?: boolean
}

export interface MobileProfile {
  id?: number
  username?: string
  email?: string
  profile_picture?: string | null
  bio?: string | null
  locale?: string | null
  is_active?: boolean
  created_at?: string | null
  updated_at?: string | null
}

/** 用户可自助修改的字段（用户名 / 邮箱 / 权限不可改） */
export interface MobileProfileUpdate {
  profile_picture?: string
  bio?: string
  locale?: string
  password?: string
}

export interface MobileUserStats {
  articles: number
  comments: number
  likes_received: number
}

// ---------------------------------------------------------------- 媒体库

export interface MobileMediaItem {
  id: number
  user_id?: number | null
  filename?: string | null
  original_filename?: string | null
  file_url?: string | null
  file_size?: number | null
  mime_type?: string | null
  file_type?: string | null
  width?: number | null
  height?: number | null
  thumbnail_url?: string | null
  description?: string | null
  alt_text?: string | null
  is_public: boolean
  category?: string | null
  tags: string[]
  folder_id?: number | null
  created_at?: string | null
}

export interface MobileMediaFolder {
  id: number
  name: string
  parent_id?: number | null
  description?: string | null
  sort_order: number
  media_count: number
  children: MobileMediaFolder[]
}

export interface MobileMediaStats {
  total: number
  total_size: number
  by_type: Record<string, number>
}

export interface MobileMediaQuery extends PageQuery {
  folder_id?: number
  mime_type?: string
  keyword?: string
}

/** 前台可自助修改的媒体字段 */
export interface MobileMediaUpdate {
  description?: string
  alt_text?: string
  category?: string
  tags?: string[]
  folder_id?: number | null
}

// ---------------------------------------------------------------- 我的投稿

export interface MobileArticleItem {
  id: number
  title?: string | null
  slug?: string | null
  excerpt?: string | null
  cover_image?: string | null
  category_id?: number | null
  tags: string[]
  status?: number | null
  views?: number
  created_at?: string | null
  updated_at?: string | null
  published_at?: string | null
}

export interface MobileArticleDetail extends MobileArticleItem {
  content?: string | null
  language_code?: string | null
}

/** 投稿入参：**不含** status / is_featured 等管理字段（后端 schema 也不接受） */
export interface MobileArticlePayload {
  title: string
  slug?: string
  excerpt?: string
  content?: string
  cover_image?: string
  category_id?: number | null
  tags?: string[]
  language_code?: string
}

export interface MobileArticleQuery extends PageQuery {
  status?: number
  keyword?: string
}

export const mobileApi = {
  // ---- 认证 ----
  register: (payload: RegisterPayload) => http.post<MobileTokenData>('/mobile/auth/register', payload),

  login: (payload: MobileLoginPayload) => http.post<MobileTokenData>('/mobile/auth/login', payload),

  // ---- 我的资料 ----
  profile: () => http.get<MobileProfile>('/mobile/user/profile'),

  updateProfile: (payload: MobileProfileUpdate) =>
    http.put<MobileProfile>('/mobile/user/profile', payload),

  stats: () => http.get<MobileUserStats>('/mobile/user/stats'),

  // ---- 前台媒体库（只操作自己的数据）----
  mediaUpload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return http.upload<MobileMediaItem>('/mobile/media/upload/image', form)
  },

  mediaList: (params?: MobileMediaQuery) =>
    http.page<MobileMediaItem>('/mobile/media/list', params),

  mediaDetail: (id: number) => http.get<MobileMediaItem>(`/mobile/media/${id}`),

  mediaUpdate: (id: number, data: MobileMediaUpdate) =>
    http.put<MobileMediaItem>(`/mobile/media/${id}`, data),

  mediaRemove: (id: number) => http.delete<null>(`/mobile/media/${id}`),

  mediaBatchDelete: (ids: number[]) =>
    http.post<{ affected: number }>('/mobile/media/batch/delete', {ids}),

  mediaStats: () => http.get<MobileMediaStats>('/mobile/media/stats'),

  mediaFolders: () => http.get<MobileMediaFolder[]>('/mobile/media/folders'),

  mediaCreateFolder: (data: { name: string; parent_id?: number | null; description?: string }) =>
    http.post<MobileMediaFolder>('/mobile/media/folders', data),

  mediaRenameFolder: (id: number, data: { name?: string; description?: string }) =>
    http.put<MobileMediaFolder>(`/mobile/media/folders/${id}`, data),

  mediaRemoveFolder: (id: number) => http.delete<null>(`/mobile/media/folders/${id}`),

  // ---- 我的投稿（只能存草稿，发布走后台）----
  myArticles: (params?: MobileArticleQuery) =>
    http.page<MobileArticleItem>('/mobile/article/mine', params),

  myArticleDetail: (id: number) =>
    http.get<MobileArticleDetail>(`/mobile/article/${id}/mine`),

  createDraft: (payload: MobileArticlePayload) =>
    http.post<MobileArticleDetail>('/mobile/article', payload),

  updateMyArticle: (id: number, payload: Partial<MobileArticlePayload>) =>
    http.put<MobileArticleDetail>(`/mobile/article/${id}`, payload),

  deleteMyArticle: (id: number) => http.delete<null>(`/mobile/article/${id}`),
}
