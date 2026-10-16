/** 权限组接口（/api/v3/system/group）
 *
 * 权限组是**数据范围（data_scope）**的载体：角色决定「能做什么」，权限组决定「能看谁的数据」
 * （配合 `roles.data_scope = 5` 使用）。组之间可以有父子层级，成员与角色绑定都是**全量覆盖**语义。
 */

import http from '../request'
import type {PageQuery} from '../types'

export interface GroupItem {
  id: number
  name?: string | null
  code?: string | null
  description?: string | null
  parent_id?: number | null
  sort_order: number
  owner_id?: number | null
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
  member_count: number
  children: GroupItem[]
}

export interface GroupPayload {
  name: string
  code: string
  description?: string
  parent_id?: number | null
  sort_order?: number
  owner_id?: number | null
  is_active?: boolean
}

export interface GroupMemberItem {
  id: number
  username?: string | null
  email?: string | null
  is_active: boolean
}

export interface GroupRoleItem {
  id: number
  name?: string | null
  slug?: string | null
  data_scope?: number | null
}

export const groupApi = {
  /** 平铺列表（后端一次性返回，不分页） */
  list: (params?: { is_active?: boolean; keyword?: string }) =>
    http.page<GroupItem>('/system/group', params),
  /** 树形结构（含 children） */
  tree: (is_active?: boolean) => http.get<GroupItem[]>('/system/group/tree', {is_active}),
  detail: (id: number) => http.get<GroupItem>(`/system/group/${id}`),
  create: (data: GroupPayload) => http.post<GroupItem>('/system/group', data),
  update: (id: number, data: Partial<GroupPayload>) =>
    http.put<GroupItem>(`/system/group/${id}`, data),
  remove: (id: number) => http.delete<null>(`/system/group/${id}`),
  /** 组成员（全量返回） */
  members: (id: number) => http.page<GroupMemberItem>(`/system/group/${id}/members`),
  /** 全量覆盖组成员 */
  setMembers: (id: number, userIds: number[]) =>
    http.post<null>(`/system/group/${id}/members`, {user_ids: userIds}),
  removeMember: (id: number, userId: number) =>
    http.delete<null>(`/system/group/${id}/members/${userId}`),
  /** 组绑定的角色（全量返回） */
  roles: (id: number) => http.get<GroupRoleItem[]>(`/system/group/${id}/roles`),
  /** 全量覆盖组绑定的角色 */
  setRoles: (id: number, roleIds: number[]) =>
    http.put<null>(`/system/group/${id}/roles`, {role_ids: roleIds}),
}

export type GroupQuery = PageQuery & { is_active?: boolean; keyword?: string }
