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
  if (!userStore.userInfo) {
    try {
      await userStore.fetchUserInfo()
    } catch {
      await userStore.logout()
      return navigateTo({path: '/login', query: {redirect: to.fullPath}})
    }
    usePermissionStore().build(userStore.permissions, userStore.menuCodes, userStore.isSuperuser)
  }

  // 页面级权限：meta.permission 存在但用户不具备 → 403
  const required = to.meta.permission as string | undefined
  if (required && !userStore.hasPermission(required)) {
    return navigateTo('/403')
  }
})
