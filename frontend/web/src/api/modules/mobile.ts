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

/** 用户公开主页（`GET /mobile/user/public/{username}`，**公开**）
 *
 * 字段是**白名单**：不含 email / 权限等敏感字段。`is_private` 为真时后端只回
 * id / username / profile_picture，其余为 null/0/false（bio 与 stats 都不泄露）。
 */
export interface MobilePublicProfile {
  id: number
  username: string
  profile_picture?: string | null
  bio?: string | null
  vip_level: number
  date_joined?: string | null
  is_private: boolean
  is_following: boolean
  is_mutual: boolean
  is_certified: boolean
  stats: { articles: number; followers: number; following: number }
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
  /** 仅 VIP 可见（批次 16 起作者可自助设置） */
  is_vip_only?: boolean
  required_vip_level?: number
  created_at?: string | null
  updated_at?: string | null
  published_at?: string | null
}

export interface MobileArticleDetail extends MobileArticleItem {
  content?: string | null
  language_code?: string | null
}

/** 投稿入参：**不含** status / is_featured / is_sticky / hidden 等管理字段（后端 schema 也不接受）
 *
 * 例外：`is_vip_only` / `required_vip_level` 是**内容属性**（批次 16 放开），作者可自助设置。
 */
export interface MobileArticlePayload {
  title: string
  slug?: string
  excerpt?: string
  content?: string
  cover_image?: string
  category_id?: number | null
  tags?: string[]
  language_code?: string
  /** 仅 VIP 可见（正文由带授权的正文端点下发） */
  is_vip_only?: boolean
  /** 所需 VIP 等级（0 表示不限等级） */
  required_vip_level?: number
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

  /** 用户公开主页（公开；登录时额外带关注标记） */
  publicProfile: (username: string) =>
    http.get<MobilePublicProfile>(`/mobile/user/public/${encodeURIComponent(username)}`),

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

  /** VIP 文章的正文（仅登录；等级达标或作者本人，否则 403）
   *
   * 公开详情对 `is_vip_only` 文章只下发摘要 + `locked: true`，前台据此再调本端点取全文。
   */
  gatedContent: (id: number) =>
    http.get<{ article_id: number; is_vip_only: boolean; required_vip_level: number; content?: string | null }>(
      `/mobile/article/${id}/content`,
    ),

  // ---- 点赞（per-user 幂等切换，详见 mobile/article/service.py）----
  likeStatus: (id: number) =>
    http.get<{ article_id: number; liked: boolean; likes: number }>(
      `/mobile/article/${id}/like/status`,
    ),

  toggleLike: (id: number) =>
    http.post<{ article_id: number; liked: boolean; likes: number }>(
      `/mobile/article/${id}/like`,
    ),
}
