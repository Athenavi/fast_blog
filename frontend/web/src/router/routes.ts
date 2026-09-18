/**
 * 路由表
 *
 * 设计说明：**后台菜单由前端路由表 + 用户权限码过滤生成**，而不是由后端菜单表驱动。
 * 原因：fast_blog 的 `menus` / `menu_items` 是**前台导航菜单**（`menu_location` 用于主题渲染），
 * 不具备后台「菜单 ↔ 权限码」语义；后台权限的权威来源是 `capabilities.code`
 * （`resource:action`）。因此后台菜单以前端路由表为准，用 `/system/permission/my`
 * 返回的权限码做过滤 —— 这与 FastApiAdmin 的 `sys_menu` 单表模型不同，属于有意取舍。
 *
 * 每个业务路由的 `meta.permission` 对应一个权限码；置空表示"仅需登录"。
 */

import type {RouteRecordRaw} from 'vue-router'

const Placeholder = () => import('@/views/placeholder/index.vue')

export interface AppRouteMeta {
  title: string
  icon?: string
  /** 需要的权限码（resource:action）；缺省表示仅需登录 */
  permission?: string
  /** 侧边栏排序 */
  order?: number
  /** 是否在侧边栏隐藏 */
  hidden?: boolean
}

/** 无需鉴权的常量路由 */
export const constantRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: {title: '登录', hidden: true},
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('@/views/error/403.vue'),
    meta: {title: '无权限', hidden: true},
  },
]

/** 业务路由（登录后按权限动态注册） */
export const asyncRoutes: RouteRecordRaw[] = [
  {
    path: 'dashboard',
    name: 'Dashboard',
    component: () => import('@/views/dashboard/index.vue'),
    meta: {title: '仪表盘', icon: 'Odometer', permission: 'settings:view', order: 1},
  },
  {
    path: 'content',
    name: 'Content',
    redirect: '/content/article',
    meta: {title: '内容管理', icon: 'Document', order: 2},
    children: [
      {
        path: 'article',
        name: 'ArticleList',
        component: Placeholder,
        meta: {title: '文章', permission: 'article:view'},
      },
      {
        path: 'category',
        name: 'CategoryList',
        component: Placeholder,
        meta: {title: '分类', permission: 'category:view'},
      },
      {
        path: 'tag',
        name: 'TagList',
        component: Placeholder,
        meta: {title: '标签', permission: 'article:view'},
      },
      {
        path: 'comment',
        name: 'CommentList',
        component: Placeholder,
        meta: {title: '评论', permission: 'comment:view'},
      },
      {
        path: 'media',
        name: 'MediaLibrary',
        component: Placeholder,
        meta: {title: '媒体库', permission: 'media:view'},
      },
      {
        path: 'page',
        name: 'PageList',
        component: Placeholder,
        meta: {title: '页面', permission: 'page:view'},
      },
    ],
  },
  {
    path: 'system',
    name: 'System',
    redirect: '/system/user',
    meta: {title: '系统管理', icon: 'Setting', order: 3},
    children: [
      {
        path: 'user',
        name: 'UserList',
        component: () => import('@/views/system/user/index.vue'),
        meta: {title: '用户', permission: 'user:view'},
      },
      {
        path: 'role',
        name: 'RoleList',
        component: () => import('@/views/system/role/index.vue'),
        meta: {title: '角色', permission: 'user:manage_roles'},
      },
      {
        path: 'menu',
        name: 'MenuList',
        component: Placeholder,
        meta: {title: '菜单', permission: 'menu:view'},
      },
      {
        path: 'permission',
        name: 'PermissionList',
        component: Placeholder,
        meta: {title: '权限码', permission: 'user:view'},
      },
      {
        path: 'setting',
        name: 'SettingList',
        component: Placeholder,
        meta: {title: '系统设置', permission: 'settings:view'},
      },
      {
        path: 'log',
        name: 'LogList',
        component: Placeholder,
        meta: {title: '日志', permission: 'settings:view'},
      },
    ],
  },
  {
    path: 'analytics',
    name: 'Analytics',
    redirect: '/analytics/seo',
    meta: {title: '数据与 SEO', icon: 'DataLine', order: 4},
    children: [
      {
        path: 'seo',
        name: 'SeoAnalysis',
        component: Placeholder,
        meta: {title: 'SEO 分析', permission: 'settings:view'},
      },
      {
        path: 'search',
        name: 'SearchAnalytics',
        component: Placeholder,
        meta: {title: '搜索分析', permission: 'settings:view'},
      },
    ],
  },
  {
    path: 'extension',
    name: 'Extension',
    redirect: '/extension/plugin',
    meta: {title: '扩展', icon: 'Grid', order: 5},
    children: [
      {
        path: 'plugin',
        name: 'PluginList',
        component: Placeholder,
        meta: {title: '插件', permission: 'plugin:view'},
      },
      {
        path: 'theme',
        name: 'ThemeList',
        component: Placeholder,
        meta: {title: '主题', permission: 'theme:view'},
      },
      {
        path: 'widget',
        name: 'WidgetList',
        component: Placeholder,
        meta: {title: '小部件', permission: 'settings:view'},
      },
    ],
  },
  {
    path: 'ops',
    name: 'Ops',
    redirect: '/ops/notification',
    meta: {title: '运维', icon: 'Tools', order: 6},
    children: [
      {
        path: 'notification',
        name: 'NotificationList',
        component: Placeholder,
        meta: {title: '通知', permission: ''},
      },
      {
        path: 'backup',
        name: 'BackupList',
        component: Placeholder,
        meta: {title: '备份', permission: 'settings:view'},
      },
      {
        path: 'webhook',
        name: 'WebhookList',
        component: Placeholder,
        meta: {title: 'Webhook', permission: 'settings:view'},
      },
    ],
  },
  {
    path: 'profile',
    name: 'Profile',
    component: Placeholder,
    meta: {title: '个人中心', icon: 'User', hidden: true},
  },
]

/** 前端路由表里的权限码集合（用于「页面是否可达」的本地判断） */
export const routePermissions: string[] = asyncRoutes.flatMap((route) => {
  const codes: string[] = []
  const collect = (item: RouteRecordRaw) => {
    const permission = (item.meta as AppRouteMeta | undefined)?.permission
    if (permission) codes.push(permission)
    item.children?.forEach(collect)
  }
  collect(route)
  return codes
})
