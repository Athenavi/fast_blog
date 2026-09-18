/** 评论接口（/api/v3/content/comment） */

import http from '../request'
import type {PageQuery, PageResult} from '../types'

export interface CommentItem {
  id: number
  article_id: number
  parent_id?: number | null
  user_id?: number | null
  content: string
  author_name?: string | null
  author_email?: string | null
  author_url?: string | null
  author_ip?: string | null
  user_agent?: string | null
  is_approved: boolean
  likes: number
  spam_score?: number | null
  spam_reasons?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface CommentPublicItem {
  id: number
  article_id: number
  parent_id?: number | null
  user_id?: number | null
  content: string
  author_name?: string | null
  author_url?: string | null
  likes: number
  created_at?: string | null
  children: CommentPublicItem[]
}

export interface CommentQuery extends PageQuery {
  article_id?: number
  user_id?: number
  is_approved?: boolean
}

export const commentApi = {
  list: (params: CommentQuery): Promise<PageResult<CommentItem>> =>
    http.page<CommentItem>('/content/comment', params),
  pending: (params?: PageQuery): Promise<PageResult<CommentItem>> =>
    http.page<CommentItem>('/content/comment/pending', params),
  detail: (id: number) => http.get<CommentItem>(`/content/comment/${id}`),
  update: (id: number, content: string) =>
    http.put<CommentItem>(`/content/comment/${id}`, {content}),
  remove: (id: number) => http.delete<null>(`/content/comment/${id}`),
  batchDelete: (ids: number[]) =>
    http.post<{ affected: number }>('/content/comment/batch/delete', {ids}),
  approve: (id: number) => http.post<CommentItem>(`/content/comment/${id}/approve`),
  reject: (id: number) => http.post<CommentItem>(`/content/comment/${id}/reject`),
  like: (id: number) =>
    http.post<{ comment_id: number; liked: boolean; likes: number }>(
      `/content/comment/${id}/like`,
    ),
  publicTree: (article_id: number, approved_only = true) =>
    http.get<CommentPublicItem[]>(`/content/comment/public/article/${article_id}`, {
      approved_only,
    }),
}
