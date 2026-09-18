/**
 * 权限/菜单状态
 *
 * 与旧版（Vue Router 动态注册）的区别：Nuxt 使用文件路由，页面**始终存在**，
 * 因此这里只负责按权限码与后端菜单授权过滤侧边栏；越权访问由
 * `middleware/auth.ts` 依据 `definePageMeta({permission})` 拦截。
 */

import {defineStore} from 'pinia'

import {ADMIN_MENUS, type AdminMenuItem} from '@/utils/menus'

export const usePermissionStore = defineStore('permission', {
  state: () => ({
    /** 过滤后的侧边栏菜单 */
    menus: [] as AdminMenuItem[],
    built: false,
  }),

  actions: {
    build(permissions: string[], menuCodes: string[], isSuperuser: boolean): void {
      const owned = new Set(permissions)
      const ownedMenus = new Set(menuCodes)
      // 菜单门可降级：后端未下发任何菜单授权时不启用菜单过滤，
      // 避免"已迁移但未跑 seed"时菜单整片消失。菜单与权限码是 AND 语义。
      const menuGate = ownedMenus.size > 0

      const allowed = (item: AdminMenuItem): boolean => {
        if (isSuperuser) return true
        const permissionOk = !item.permission || owned.has(item.permission)
        const menuOk = !menuGate || ownedMenus.has(item.name)
        return permissionOk && menuOk
      }

      const filter = (items: AdminMenuItem[]): AdminMenuItem[] =>
        items
          .filter(allowed)
          .map((item) => ({...item, children: item.children ? filter(item.children) : undefined}))
          // 父菜单过滤后没有子项则整条移除（避免空目录）
          .filter((item) => !item.children || item.children.length > 0)

      this.menus = filter(ADMIN_MENUS).sort((a, b) => (a.order ?? 999) - (b.order ?? 999))
      this.built = true
    },

    reset(): void {
      this.menus = []
      this.built = false
    },
  },
})
