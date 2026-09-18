/** 权限/菜单状态：把路由表按用户权限过滤，生成可访问路由与侧边栏菜单 */

import {defineStore} from 'pinia'
import type {RouteRecordRaw} from 'vue-router'

import {type AppRouteMeta, asyncRoutes} from '@/router/routes'

export interface SidebarMenuItem {
  path: string
  title: string
  icon?: string
  order?: number
  children: SidebarMenuItem[]
}

function metaOf(route: RouteRecordRaw): AppRouteMeta | undefined {
  return route.meta as AppRouteMeta | undefined
}

/** 计算子路由的完整路径（子路由 path 是相对的） */
function joinPath(parent: string, child: string): string {
  if (child.startsWith('/')) return child
  return `${parent.replace(/\/$/, '')}/${child}`
}

export const usePermissionStore = defineStore('permission', {
  state: () => ({
    /** 过滤后的可访问路由 */
    routes: [] as RouteRecordRaw[],
    /** 过滤后的侧边栏菜单 */
    menus: [] as SidebarMenuItem[],
    built: false,
  }),

  actions: {
    buildRoutes(permissions: string[], menuCodes: string[], isSuperuser: boolean): void {
      const owned = new Set(permissions)
      const ownedMenus = new Set(menuCodes)
      // 菜单级授权门：后端尚未下发任何菜单授权时不启用，
      // 避免"已迁移但未跑 seed_admin_menus"时菜单整片消失。
      const menuGate = ownedMenus.size > 0

      const allowed = (route: RouteRecordRaw): boolean => {
        if (isSuperuser) return true
        const meta = metaOf(route)
        const permissionOk = !meta?.permission || owned.has(meta.permission)
        // 菜单授权取路由 name，与后端 admin_menus.code 一一对应；两者是 AND 语义
        const menuOk = !menuGate || (route.name != null && ownedMenus.has(String(route.name)))
        return permissionOk && menuOk
      }

      const filter = (routes: RouteRecordRaw[]): RouteRecordRaw[] =>
        routes
          .filter((route) => allowed(route))
          .map((route) =>
            route.children ? {...route, children: filter(route.children)} : {...route},
          )
          // 父路由若过滤后没有子路由，则整条移除（避免空目录）
          .filter((route) => !route.children || route.children.length > 0)

      this.routes = filter(asyncRoutes)
      this.menus = this.toMenus(this.routes, '')
      this.built = true
    },

    toMenus(routes: RouteRecordRaw[], parentPath: string): SidebarMenuItem[] {
      return routes
        .filter((route) => !metaOf(route)?.hidden)
        .map((route) => {
          const meta = metaOf(route)
          const fullPath = joinPath(parentPath, route.path)
          return {
            path: fullPath,
            title: meta?.title ?? route.name?.toString() ?? fullPath,
            icon: meta?.icon,
            order: meta?.order,
            children: route.children ? this.toMenus(route.children, fullPath) : [],
          }
        })
        .sort((a, b) => (a.order ?? 999) - (b.order ?? 999))
    },

    reset(): void {
      this.routes = []
      this.menus = []
      this.built = false
    },
  },
})
