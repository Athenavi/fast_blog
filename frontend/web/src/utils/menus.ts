/**
 * 后台菜单结构
 *
 * 权威划分（与后端约定一致）：
 *  - **结构**由本文件定义（路径、标题、图标、所需权限码）；
 *  - **授权**由后端 `admin_menus` + `role_admin_menus` 下发（`/system/permission/my` 的 `menu_codes`）；
 *  - 两者是 **AND** 语义：既要权限码匹配，也要菜单被授权。
 *
 * `name` 必须与后端 `admin_menus.code` 一一对应（例如 `UserList`），
 * 同时它也是前端路由名，侧边栏与面包屑都复用它。
 */

export interface AdminMenuItem {
  /** 路由名，与后端 admin_menus.code 对应 */
  name: string
  path: string
  title: string
  icon?: string
  /** 页面级权限码；缺省表示仅需登录 */
  permission?: string
  order?: number
  /** 不在侧边栏展示（如个人中心） */
  hidden?: boolean
  children?: AdminMenuItem[]
}

export const ADMIN_MENUS: AdminMenuItem[] = [
  {
    name: 'Dashboard',
    path: '/dashboard',
    title: '仪表盘',
    icon: 'Odometer',
    permission: 'module_analytics:dashboard:view',
    order: 1,
  },
  {
    name: 'Content',
    path: '/content',
    title: '内容管理',
    icon: 'Document',
    order: 2,
    children: [
      {name: 'ArticleList', path: '/content/article', title: '文章', permission: 'module_content:article:view'},
      {name: 'CategoryList', path: '/content/category', title: '分类', permission: 'module_content:category:view'},
      {name: 'TagList', path: '/content/tag', title: '标签', permission: 'module_content:tag:view'},
      {name: 'CommentList', path: '/content/comment', title: '评论', permission: 'module_content:comment:view'},
      {name: 'MediaLibrary', path: '/content/media', title: '媒体库', permission: 'module_content:media:view'},
      {name: 'PageList', path: '/content/page', title: '页面', permission: 'module_content:page:view'},
    ],
  },
  {
    name: 'System',
    path: '/system',
    title: '系统管理',
    icon: 'Setting',
    order: 3,
    children: [
      {name: 'UserList', path: '/system/user', title: '用户', permission: 'module_system:user:view'},
      {name: 'RoleList', path: '/system/role', title: '角色', permission: 'module_system:role:view'},
      {name: 'MenuList', path: '/system/menu', title: '菜单', permission: 'module_system:navmenu:view'},
      {
        name: 'PermissionList',
        path: '/system/permission',
        title: '权限码',
        permission: 'module_system:permission:view'
      },
      {name: 'SettingList', path: '/system/setting', title: '系统设置', permission: 'module_system:setting:view'},
      {name: 'LogList', path: '/system/log', title: '日志', permission: 'module_system:log:view'},
    ],
  },
  {
    name: 'Analytics',
    path: '/analytics',
    title: '数据与 SEO',
    icon: 'DataLine',
    order: 4,
    children: [
      {name: 'SeoAnalysis', path: '/analytics/seo', title: 'SEO 分析', permission: 'module_analytics:seo:view'},
      {
        name: 'SearchAnalytics',
        path: '/analytics/search',
        title: '搜索分析',
        permission: 'module_analytics:search:view'
      },
    ],
  },
  {
    name: 'Extension',
    path: '/extension',
    title: '扩展',
    icon: 'Grid',
    order: 5,
    children: [
      {name: 'PluginList', path: '/extension/plugin', title: '插件', permission: 'module_extension:plugin:view'},
      {name: 'ThemeList', path: '/extension/theme', title: '主题', permission: 'module_extension:theme:view'},
      {name: 'WidgetList', path: '/extension/widget', title: '小部件', permission: 'module_extension:widget:view'},
    ],
  },
  {
    name: 'Ops',
    path: '/ops',
    title: '运维',
    icon: 'Tools',
    order: 6,
    children: [
      {name: 'NotificationList', path: '/ops/notification', title: '通知'},
      {name: 'BackupList', path: '/ops/backup', title: '备份', permission: 'module_ops:backup:view'},
      {name: 'WebhookList', path: '/ops/webhook', title: 'Webhook', permission: 'module_ops:webhook:view'},
    ],
  },
]

/** 菜单里出现的权限码集合（便于前端自检与文档化） */
export const ADMIN_MENU_PERMISSIONS: string[] = ADMIN_MENUS.flatMap(function collect(
  item: AdminMenuItem,
): string[] {
  const self = item.permission ? [item.permission] : []
  return [...self, ...(item.children ?? []).flatMap(collect)]
})
