/**
 * 后台鉴权中间件
 *
 * 后台路由在 `nuxt.config.ts` 中配置为 `ssr: false`（保持与原 Vite 版一致的 SPA 行为），
 * 因此这里运行在客户端，可直接读取本地存储中的 token。
 *
 * 页面通过 `definePageMeta({middleware: 'auth', permission: '...'})` 声明所需权限码。
 */
import {usePermissionStore} from '@/store/modules/permission'
import {useUserStore} from '@/store/modules/user'

export default defineNuxtRouteMiddleware(async (to) => {
  if (import.meta.server) return

  const userStore = useUserStore()

  if (!userStore.isLoggedIn) {
    return navigateTo({path: '/login', query: {redirect: to.fullPath}})
  }

  // 首次进入或刷新后：拉取用户信息并构建侧边栏菜单
  // 注意：`userInfo` 是从 localStorage 恢复的（且 `login()` 里已 fetch 过一次），
  // 所以只用 `!userInfo` 判断会让 `refresh` 后永远跳过下面两步 —— 侧边栏因此变空。
  // 这里额外把"缓存记录里缺 `menu_codes` 字段"（旧版本缓存的用户信息）视为需要刷新。
  if (!userStore.userInfo || userStore.userInfo.menu_codes === undefined) {
    try {
      await userStore.fetchUserInfo()
    } catch {
      await userStore.logout()
      return navigateTo({path: '/login', query: {redirect: to.fullPath}})
    }
  }

  // permission store 不持久化，刷新后必须重建；同一次 SPA 会话内不重复构建
  const permissionStore = usePermissionStore()
  if (!permissionStore.built) {
    permissionStore.build(userStore.permissions, userStore.menuCodes, userStore.isSuperuser)
  }

  // 页面级权限：meta.permission 存在但用户不具备 → 403
  const required = to.meta.permission as string | undefined
  if (required && !userStore.hasPermission(required)) {
    return navigateTo('/403')
  }
})
