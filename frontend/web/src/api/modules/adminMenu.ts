/** 后台菜单与角色菜单授权接口（`/api/v3/system/admin-menu`，system 域）
 *
 * 对齐后端 `src/api/v3/modules/system/admin_menu/{controller.py,schema.py,service.py}`。
 *
 * 本模块是**后台管理菜单定义（admin_menus）+ 角色菜单授权（role_admin_menus）**，
 * 与既有 `/api/v3/system/menu`（前台导航菜单 + 菜单项）是两个不同模块，二者互不复用。
 *
 * 端点（完整路径省略 `/api/v3` 前缀）：
 *   - GET    /system/admin-menu                 菜单列表（**分页信封**：resp.success_page）
 *   - GET    /system/admin-menu/tree            菜单树（普通 data：树形数组）
 *   - GET    /system/admin-menu/my              当前用户可见菜单标识（普通 data）
 *   - POST   /system/admin-menu                 新建菜单
 *   - GET    /system/admin-menu/role/{role_id}  角色已授权菜单 id（普通 data：number[]）
 *   - PUT    /system/admin-menu/role/{role_id}  全量覆盖角色菜单授权
 *   - GET    /system/admin-menu/{menu_id}       菜单详情
 *   - PUT    /system/admin-menu/{menu_id}       更新菜单
 *   - DELETE /system/admin-menu/{menu_id}       删除菜单
 *
 * 权限码（`controller.py` 的 `AuthControl(...)`，反查 `core/permission/codes.py`）：
 *   - 查看：`module_system:menu:view`（`MENU_VIEW`）
 *   - 新建：`module_system:menu:create`（`MENU_CREATE`）
 *   - 更新：`module_system:menu:edit`（`MENU_EDIT`）
 *   - 删除：`module_system:menu:delete`（`MENU_DELETE`）
 *   - 授权：`module_system:menu:grant`（`MENU_GRANT`）
 *   - `/my` 端点无 `AuthControl`，仅需登录用户（CurrentUser）。
 *
 * 说明：`/list`、`/create`、`/delete`、`/detail/{id}`、`/update/{id}` 是
 * FastApiAdmin **兼容别名**（`include_in_schema=False`），本模块**刻意不接线**。
 */

import http from '../request'
import type {PageQuery} from '../types'

/** 菜单类型（对齐 `schema.py`：1 目录 / 2 菜单 / 3 按钮） */
export const MENU_TYPE_DIR = 1
export const MENU_TYPE_MENU = 2
export const MENU_TYPE_BUTTON = 3

/** 后台菜单节点（响应体，字段逐项对齐 `service._menu_out`） */
export interface AdminMenu {
  id: number
  /** 菜单稳定标识（与前端路由 name / meta.menuCode 一致） */
  code?: string | null
  /** 菜单名称 */
  title?: string | null
  parent_id?: number | null
  /** 1 目录 / 2 菜单 / 3 按钮 */
  menu_type: number
  /** 关联权限码（与 capabilities.code 同构） */
  permission_code?: string | null
  sort_order: number
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
  /** 子菜单（`/tree` 时填充；列表接口恒为空数组） */
  children: AdminMenu[]
}

/** 列表查询参数（`GET /system/admin-menu` 的查询串） */
export interface AdminMenuQuery extends PageQuery {
  is_active?: boolean
  keyword?: string
}

/** 新建请求体（`schema.AdminMenuCreate`） */
export interface AdminMenuCreatePayload {
  /** 菜单稳定标识，长度 1..100 */
  code: string
  /** 菜单名称，长度 1..100 */
  title: string
  parent_id?: number | null
  /** 1 目录 / 2 菜单 / 3 按钮，默认 2 */
  menu_type?: number
  /** 关联权限码，最长 100 */
  permission_code?: string | null
  sort_order?: number
  is_active?: boolean
}

/** 更新请求体（`schema.AdminMenuUpdate`，字段全部可选） */
export interface AdminMenuUpdatePayload {
  code?: string
  title?: string
  parent_id?: number | null
  menu_type?: number
  permission_code?: string | null
  sort_order?: number
  is_active?: boolean
}

/** 角色菜单授权请求体（`schema.RoleMenuAssign`） */
export interface RoleMenuAssignPayload {
  /** 全量覆盖该角色已授权的菜单 id */
  menu_ids: number[]
}

/** 当前用户可见菜单（`GET /system/admin-menu/my`，`service.menu_codes_with_ancestors`） */
export interface MyAdminMenus {
  /** 可见菜单标识（已补齐祖先目录） */
  menu_codes: string[]
  is_superuser: boolean
}

export const adminMenuApi = {
  /** 菜单列表（**分页信封**：`resp.success_page`，data 为数组、分页信息在 pagination） */
  list: (params?: AdminMenuQuery) => http.page<AdminMenu>('/system/admin-menu', params),

  /** 菜单树（普通 data：按 `sort_order`、`id` 排序的树形数组） */
  tree: (params?: { is_active?: boolean }) =>
    http.get<AdminMenu[]>('/system/admin-menu/tree', params),

  /** 当前用户可见菜单标识（普通 data：`{menu_codes, is_superuser}`） */
  my: () => http.get<MyAdminMenus>('/system/admin-menu/my'),

  /** 新建菜单 */
  create: (data: AdminMenuCreatePayload) =>
    http.post<AdminMenu>('/system/admin-menu', data),

  /** 菜单详情 */
  detail: (menuId: number) => http.get<AdminMenu>(`/system/admin-menu/${menuId}`),

  /** 更新菜单 */
  update: (menuId: number, data: AdminMenuUpdatePayload) =>
    http.put<AdminMenu>(`/system/admin-menu/${menuId}`, data),

  /** 删除菜单（存在子菜单时后端返回 409） */
  remove: (menuId: number) => http.delete<null>(`/system/admin-menu/${menuId}`),

  /** 角色已授权的菜单 id（普通 data：升序 number[]） */
  roleMenuIds: (roleId: number) => http.get<number[]>(`/system/admin-menu/role/${roleId}`),

  /** 全量覆盖角色菜单授权，返回覆盖后的已授权 id 列表 */
  setRoleMenus: (roleId: number, menuIds: number[]) =>
    http.put<number[]>(`/system/admin-menu/role/${roleId}`, {menu_ids: menuIds}),
}
