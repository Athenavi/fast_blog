/** 路由守卫：登录态校验、权限过滤、动态路由注册 */

import NProgress from 'nprogress'
import type {Router} from 'vue-router'

import {HOME_PATH, WHITE_LIST} from '@/constants'
import {usePermissionStore} from '@/store/modules/permission'
import {useUserStore} from '@/store/modules/user'

import {registerCatchAll, registerDynamicRoutes} from './index'

NProgress.configure({showSpinner: false})

export function setupRouterGuard(router: Router): void {
  router.beforeEach(async (to) => {
    NProgress.start()

    const userStore = useUserStore()

    if (WHITE_LIST.includes(to.path)) {
      return true
    }

    if (!userStore.isLoggedIn) {
      return {path: '/login', query: {redirect: to.fullPath}}
    }

    // 首次进入或刷新后：拉取用户信息并注册动态路由
    if (!userStore.userInfo) {
      try {
        await userStore.fetchUserInfo()
      } catch {
        await userStore.logout()
        return {path: '/login', query: {redirect: to.fullPath}}
      }

      const permissionStore = usePermissionStore()
      permissionStore.buildRoutes(userStore.permissions, userStore.isSuperuser)
      registerDynamicRoutes(permissionStore.routes)
      registerCatchAll()

      // 动态路由注册后重新进入目标地址，确保能命中
      return {...to, replace: true}
    }

    // 页面级权限：meta.permission 存在但用户没有 → 跳 403
    const required = to.meta?.permission as string | undefined
    if (required && !userStore.hasPermission(required)) {
      return {path: '/403'}
    }

    return true
  })

  router.afterEach((to) => {
    const title = (to.meta?.title as string | undefined) || ''
    document.title = title ? `${title} - FastBlog 管理后台` : 'FastBlog 管理后台'
    NProgress.done()
  })

  router.onError(() => {
    NProgress.done()
  })
}

export {HOME_PATH}
