/** 关注关系接口（/api/v3/mobile/follow，mobile 域）
 *
 * 「我的」两个列表与关注 / 取关**仅需认证**；「某人的」三个只读端点**公开**
 * （登录时会额外带上 `is_following` / `is_mutual` 标记，匿名恒 false）。
 */

import http from '../request'
import type {PageQuery} from '../types'

export interface FollowUserBrief {
  id: number
  username?: string | null
  email?: string | null
  is_active: boolean
  created_at?: string | null
  /** 当前登录者是否关注了 TA */
  is_following: boolean
  /** 是否互相关注 */
  is_mutual: boolean
}

export interface FollowItem {
  user: FollowUserBrief
  created_at?: string | null
}

export interface FollowStats {
  user_id: number
  follower_count: number
  following_count: number
  is_following: boolean
  is_mutual: boolean
}

export const followApi = {
  /** 我的粉丝 */
  myFollowers: (params?: PageQuery) => http.page<FollowItem>('/mobile/follow/follower', params),

  /** 我的关注 */
  myFollowing: (params?: PageQuery) => http.page<FollowItem>('/mobile/follow/following', params),

  /** 某人的关注概览（公开） */
  status: (userId: number) => http.get<FollowStats>(`/mobile/follow/${userId}/status`),

  /** 某人的粉丝（公开） */
  userFollowers: (userId: number, params?: PageQuery) =>
    http.page<FollowItem>(`/mobile/follow/${userId}/follower`, params),

  /** 某人的关注（公开） */
  userFollowing: (userId: number, params?: PageQuery) =>
    http.page<FollowItem>(`/mobile/follow/${userId}/following`, params),

  /** 关注（幂等；不能关注自己；对方拉黑我时后端返回 409） */
  follow: (userId: number) => http.post<FollowStats>(`/mobile/follow/${userId}`),

  /** 取消关注（幂等） */
  unfollow: (userId: number) => http.delete<FollowStats>(`/mobile/follow/${userId}`),
}
