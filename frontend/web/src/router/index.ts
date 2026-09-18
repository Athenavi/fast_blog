/** 路由实例：静态路由 + 登录后动态注册业务路由 */

import {createRouter, createWebHistory, type RouteRecordRaw} from 'vue-router'

import {HOME_PATH} from '@/constants'

import {setupRouterGuard} from './guard'
import {constantRoutes} from './routes'

/** 布局路由名（业务路由作为它的子路由动态注册） */
export const LAYOUT_ROUTE_NAME = 'Layout'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...constantRoutes,
    {
      path: '/',
      name: LAYOUT_ROUTE_NAME,
      component: () => import('@/layouts/DefaultLayout.vue'),
      redirect: HOME_PATH,
      children: [],
    },
  ],
  scrollBehavior: () => ({top: 0}),
})

/** 动态注册业务路由（幂等：重复注册同名路由会覆盖） */
export function registerDynamicRoutes(routes: RouteRecordRaw[]): void {
  routes.forEach((route) => router.addRoute(LAYOUT_ROUTE_NAME, route))
}

/** 兜底 404 必须在动态路由注册之后再添加，否则会抢先匹配 */
export function registerCatchAll(): void {
  if (!router.hasRoute('NotFound')) {
    router.addRoute({
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/error/404.vue'),
      meta: {title: '页面不存在', hidden: true},
    })
  }
}

/** 登出时重置：移除所有动态注册的路由 */
export function resetDynamicRoutes(): void {
  router.getRoutes().forEach((route) => {
    if (route.name && route.name !== LAYOUT_ROUTE_NAME && !constantRoutes.some((c) => c.name === route.name)) {
      router.removeRoute(route.name)
    }
  })
}

setupRouterGuard(router)

export default router
