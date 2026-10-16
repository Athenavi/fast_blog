/** 菜单接口（/api/v3/system/menu） */

import http from '../request'

export interface MenuItemNode {
  id: number
  menu_id: number
  parent_id?: number | null
  title: string
  url?: string | null
  target?: string | null
  order_index: number
  is_active: boolean
  created_at?: string | null
  children: MenuItemNode[]
}

export interface MenuNode {
  id: number
  name: string
  slug: string
  description?: string | null
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
  items: MenuItemNode[]
}

export interface MenuCreatePayload {
  name: string
  slug: string
  description?: string
}

export interface MenuUpdatePayload {
  name?: string
  description?: string
  is_active?: boolean
}

export interface MenuItemCreatePayload {
  title: string
  url?: string
  parent_id?: number | null
  target?: string
  order_index?: number
  is_active?: boolean
}

export interface MenuItemUpdatePayload {
  title?: string
  url?: string
  parent_id?: number | null
  target?: string
  order_index?: number
  is_active?: boolean
}

export interface MenuTreeOut {
  id: number
  name: string
  slug: string
  items: MenuItemNode[]
}

export const menuApi = {
  list: (params?: { is_active?: boolean }) => http.page<MenuNode>('/system/menu', params),
  tree: (menu_id?: number) => http.get<MenuTreeOut[]>('/system/menu/tree', {menu_id}),
  detail: (id: number) => http.get<MenuNode>(`/system/menu/${id}`),
  create: (data: MenuCreatePayload) => http.post<MenuNode>('/system/menu', data),
  update: (id: number, data: MenuUpdatePayload) => http.put<MenuNode>(`/system/menu/${id}`, data),
  remove: (id: number) => http.delete<null>(`/system/menu/${id}`),
  addItem: (menu_id: number, data: MenuItemCreatePayload) =>
    http.post<MenuItemNode>(`/system/menu/${menu_id}/items`, data),
  updateItem: (item_id: number, data: MenuItemUpdatePayload) =>
    http.put<MenuItemNode>(`/system/menu/items/${item_id}`, data),
  removeItem: (item_id: number) => http.delete<null>(`/system/menu/items/${item_id}`),
  reorderItems: (menu_id: number, items: Array<{ id: number; order_index: number }>) =>
    http.put<MenuItemNode[]>(`/system/menu/${menu_id}/items/order`, {items}),
}
