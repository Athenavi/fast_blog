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
      {
        name: 'CustomPostTypes',
        path: '/content/custom-post-types',
        title: '内容类型',
        permission: 'module_content:custom_post_type:view'
      },
      {name: 'Approvals', path: '/content/approvals', title: '内容审批', permission: 'module_content:approval:view'},
      {
        name: 'ShortCodes',
        path: '/content/shortcodes',
        title: '短代码',
        permission: 'module_content:shortcode:view'
      },
      {
        name: 'PageBuilder',
        path: '/content/page-builder',
        title: '页面搭建',
        permission: 'module_content:page_builder:view'
      },
    ],
  },
  {
    name: 'System',
    path: '/system',
    title: '系统管理',
    icon: 'Setting',
    order: 3,
    children: [
      {name: 'SystemHub', path: '/system/hub', title: '系统总览', permission: 'module_system:monitor:view'},
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
      {name: 'CacheManage', path: '/system/cache', title: '缓存', permission: 'module_system:cache:view'},
      {
        name: 'SensitiveWords',
        path: '/system/sensitive-words',
        title: '敏感词库',
        permission: 'module_system:sensitive_word:view'
      },
      {name: 'GDPR', path: '/system/gdpr', title: '合规同意', permission: 'module_system:gdpr:view'},
      {
        name: 'Integrations',
        path: '/system/integrations',
        title: '第三方集成',
        permission: 'module_system:integration:view'
      },
      {
        name: 'SocialAccounts',
        path: '/system/social-accounts',
        title: '社交账号',
        permission: 'module_system:social:view'
      },
      {
        name: 'Security',
        path: '/system/security',
        title: '安全中心',
        permission: 'module_system:security:view'
      },
      {name: 'Sites', path: '/system/sites', title: '多站点', permission: 'module_system:site:view'},
    ],
  },
  {
    name: 'ChatGroups',
    path: '/chat/groups',
    title: '群聊管理',
    icon: 'ChatDotRound',
    permission: 'module_chat:group:view',
    order: 7,
  },
  {
    name: 'AI',
    path: '/ai',
    title: 'AI 能力',
    icon: 'MagicStick',
    order: 8,
    children: [
      {name: 'AIConfigs', path: '/ai/configs', title: 'AI 配置', permission: 'module_ai:config:view'},
      {name: 'AIWorkflows', path: '/ai/workflows', title: 'AI 工作流', permission: 'module_ai:workflow:view'},
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
      {
        name: 'BlockPatterns',
        path: '/extension/block-patterns',
        title: '区块模板',
        permission: 'module_extension:block_pattern:view'
      },
    ],
  },
  {
    name: 'Marketing',
    path: '/marketing',
    title: '营销',
    icon: 'Promotion',
    order: 6,
    children: [
      {name: 'AdsPage', path: '/marketing/ads', title: '广告管理', permission: 'module_marketing:ad:view'},
      {name: 'VipPage', path: '/marketing/vip', title: 'VIP 会员', permission: 'module_marketing:vip:view'},
      {name: 'FormsPage', path: '/marketing/forms', title: '表单', permission: 'module_marketing:form:view'},
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
      {name: 'Migrations', path: '/ops/migrations', title: '数据迁移', permission: 'module_ops:migration:view'},
      {name: 'EmailService', path: '/ops/email', title: '邮件服务', permission: 'module_ops:email:view'},
      {name: 'CDN', path: '/ops/cdn', title: 'CDN 配置', permission: 'module_ops:cdn:view'},
      {name: 'Upgrade', path: '/ops/upgrade', title: '在线升级', permission: 'module_ops:upgrade:view'},
      {name: 'Enterprise', path: '/ops/enterprise', title: '企业版授权', permission: 'module_ops:enterprise:view'},
      {name: 'Deployments', path: '/ops/deployments', title: '部署脚本', permission: 'module_ops:deployment:view'},
    ],
  },
  {
    name: 'Commerce',
    path: '/commerce',
    title: '商务',
    icon: 'Money',
    order: 9,
    children: [
      {name: 'Payments', path: '/commerce/payment', title: '支付管理', permission: 'module_commerce:payment:view'},
      {name: 'Revenue', path: '/commerce/revenue', title: '收益分成', permission: 'module_commerce:revenue:view'},
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
