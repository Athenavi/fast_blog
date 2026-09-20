"""权限码常量（**单一真相**）—— 官方三段式

格式：``module_{域}:{模块}:{动作}``

命名规则：

  - **域** = v3 路由域（``src/api/v3/modules/{域}``）：content / system / analytics / extension / ops
  - **模块** = v3 模块目录名（单数）
  - **动作** = ``view`` / ``create`` / ``edit`` / ``delete`` + 模块特有动作（``publish`` / ``approve`` / ``upload`` …）

与 ``scripts/seed_rbac.py`` 写入 ``capabilities.code`` 的格式**严格一致**；比较时不做任何分隔符转换。

### P4 迁移中修正的三处历史问题

  - ``content/tag`` 原先借用 ``article:*`` → 独立为 ``module_content:tag:*``
  - ``system/role`` 原先借用 ``user:manage_roles`` → 独立为 ``module_system:role:*``
  - ``settings:view`` / ``settings:edit`` 原先是"万能码"（43 处共用）→ 按模块拆分为
    setting / log / permission / widget / webhook / seo / search / dashboard 等各自独立的码
  - ``system/menu``（**前台导航菜单**）改用 ``module_system:navmenu:*``，
    ``module_system:menu:*`` 交给**后台菜单**（``admin_menus``）

### 过渡期兼容

``LEGACY_ALIASES`` 提供"新码 → 旧码"的映射，``AuthPermission`` 在过渡期会**同时接受**旧码，
避免已发放的角色在小范围内失效。**只覆盖"纯改名"的模块**；上面那三类"语义修正"不提供别名，
因为让旧码继续放行恰恰违背拆分的目的。P6 会移除该兼容与映射。
"""

# ============================================================ content 域
ARTICLE_VIEW = "module_content:article:view"
ARTICLE_CREATE = "module_content:article:create"
ARTICLE_EDIT = "module_content:article:edit"
ARTICLE_DELETE = "module_content:article:delete"
ARTICLE_PUBLISH = "module_content:article:publish"
ARTICLE_EDIT_OTHERS = "module_content:article:edit_others"
ARTICLE_DELETE_OTHERS = "module_content:article:delete_others"

CATEGORY_VIEW = "module_content:category:view"
CATEGORY_CREATE = "module_content:category:create"
CATEGORY_EDIT = "module_content:category:edit"
CATEGORY_DELETE = "module_content:category:delete"

TAG_VIEW = "module_content:tag:view"
TAG_EDIT = "module_content:tag:edit"

COMMENT_VIEW = "module_content:comment:view"
COMMENT_APPROVE = "module_content:comment:approve"
COMMENT_EDIT = "module_content:comment:edit"
COMMENT_DELETE = "module_content:comment:delete"

MEDIA_VIEW = "module_content:media:view"
MEDIA_UPLOAD = "module_content:media:upload"
MEDIA_DELETE = "module_content:media:delete"

CPT_VIEW = "module_content:custom_post_type:view"

APPROVAL_VIEW = "module_content:approval:view"
APPROVAL_ACT = "module_content:approval:act"
APPROVAL_DELETE = "module_content:approval:delete"
CPT_CREATE = "module_content:custom_post_type:create"
CPT_EDIT = "module_content:custom_post_type:edit"
CPT_DELETE = "module_content:custom_post_type:delete"

PAGE_VIEW = "module_content:page:view"
PAGE_CREATE = "module_content:page:create"
PAGE_EDIT = "module_content:page:edit"
PAGE_DELETE = "module_content:page:delete"
PAGE_PUBLISH = "module_content:page:publish"

# ============================================================ system 域
USER_VIEW = "module_system:user:view"
USER_CREATE = "module_system:user:create"
USER_EDIT = "module_system:user:edit"
USER_DELETE = "module_system:user:delete"
USER_MANAGE_ROLES = "module_system:user:manage_roles"

ROLE_VIEW = "module_system:role:view"
ROLE_EDIT = "module_system:role:edit"

# 前台导航菜单（表 menus / menu_items）—— 原名 menu:*，为与后台菜单区分而改名
NAVMENU_VIEW = "module_system:navmenu:view"
NAVMENU_CREATE = "module_system:navmenu:create"
NAVMENU_EDIT = "module_system:navmenu:edit"
NAVMENU_DELETE = "module_system:navmenu:delete"

# 后台菜单（表 admin_menus）—— P3 的菜单级授权载体
MENU_VIEW = "module_system:menu:view"
MENU_CREATE = "module_system:menu:create"
MENU_EDIT = "module_system:menu:edit"
MENU_DELETE = "module_system:menu:delete"
MENU_GRANT = "module_system:menu:grant"

# 权限组（数据范围载体）
GROUP_VIEW = "module_system:group:view"
GROUP_CREATE = "module_system:group:create"
GROUP_EDIT = "module_system:group:edit"
GROUP_DELETE = "module_system:group:delete"
GROUP_MANAGE_MEMBERS = "module_system:group:manage_members"
GROUP_MANAGE_ROLES = "module_system:group:manage_roles"

PERMISSION_VIEW = "module_system:permission:view"
PERMISSION_EDIT = "module_system:permission:edit"

SETTING_VIEW = "module_system:setting:view"
SETTING_EDIT = "module_system:setting:edit"

LOG_VIEW = "module_system:log:view"
LOG_EDIT = "module_system:log:edit"

CACHE_VIEW = "module_system:cache:view"
CACHE_CLEAR = "module_system:cache:clear"
CACHE_WARMUP = "module_system:cache:warmup"
CACHE_WRITE = "module_system:cache:write"

SENSITIVE_WORD_VIEW = "module_system:sensitive_word:view"
SENSITIVE_WORD_CREATE = "module_system:sensitive_word:create"
SENSITIVE_WORD_EDIT = "module_system:sensitive_word:edit"
SENSITIVE_WORD_DELETE = "module_system:sensitive_word:delete"

MONITOR_VIEW = "module_system:monitor:view"
MONITOR_KICK = "module_system:monitor:kick"
MONITOR_MANAGE = "module_system:monitor:manage"

# ============================================================ analytics 域
DASHBOARD_VIEW = "module_analytics:dashboard:view"
SEO_VIEW = "module_analytics:seo:view"
SEO_EDIT = "module_analytics:seo:edit"
SEARCH_VIEW = "module_analytics:search:view"

# ============================================================ extension 域
PLUGIN_VIEW = "module_extension:plugin:view"
PLUGIN_INSTALL = "module_extension:plugin:install"
PLUGIN_ACTIVATE = "module_extension:plugin:activate"
PLUGIN_DELETE = "module_extension:plugin:delete"
PLUGIN_CONFIGURE = "module_extension:plugin:configure"

THEME_VIEW = "module_extension:theme:view"
THEME_INSTALL = "module_extension:theme:install"
THEME_ACTIVATE = "module_extension:theme:activate"
THEME_DELETE = "module_extension:theme:delete"
THEME_CUSTOMIZE = "module_extension:theme:customize"

WIDGET_VIEW = "module_extension:widget:view"
WIDGET_EDIT = "module_extension:widget:edit"

BLOCK_PATTERN_VIEW = "module_extension:block_pattern:view"
BLOCK_PATTERN_CREATE = "module_extension:block_pattern:create"
BLOCK_PATTERN_EDIT = "module_extension:block_pattern:edit"
BLOCK_PATTERN_DELETE = "module_extension:block_pattern:delete"

# ============================================================ marketing 域
AD_VIEW = "module_marketing:ad:view"
AD_CREATE = "module_marketing:ad:create"
AD_EDIT = "module_marketing:ad:edit"
AD_DELETE = "module_marketing:ad:delete"

VIP_VIEW = "module_marketing:vip:view"
VIP_CREATE = "module_marketing:vip:create"
VIP_EDIT = "module_marketing:vip:edit"
VIP_DELETE = "module_marketing:vip:delete"

FORM_VIEW = "module_marketing:form:view"
FORM_CREATE = "module_marketing:form:create"
FORM_EDIT = "module_marketing:form:edit"
FORM_DELETE = "module_marketing:form:delete"

# ============================================================ ops 域
MIGRATION_VIEW = "module_ops:migration:view"
MIGRATION_CREATE = "module_ops:migration:create"
MIGRATION_EDIT = "module_ops:migration:edit"
MIGRATION_DELETE = "module_ops:migration:delete"

EMAIL_VIEW = "module_ops:email:view"
EMAIL_EDIT = "module_ops:email:edit"
EMAIL_DELETE = "module_ops:email:delete"

GDPR_VIEW = "module_system:gdpr:view"
GDPR_DELETE = "module_system:gdpr:delete"
INTEGRATION_VIEW = "module_system:integration:view"
INTEGRATION_CREATE = "module_system:integration:create"
INTEGRATION_EDIT = "module_system:integration:edit"
INTEGRATION_DELETE = "module_system:integration:delete"
SOCIAL_VIEW = "module_system:social:view"
SOCIAL_DELETE = "module_system:social:delete"
SECURITY_VIEW = "module_system:security:view"
SECURITY_DELETE = "module_system:security:delete"

BACKUP_VIEW = "module_ops:backup:view"
BACKUP_CREATE = "module_ops:backup:create"
BACKUP_RESTORE = "module_ops:backup:restore"
BACKUP_DELETE = "module_ops:backup:delete"

WEBHOOK_VIEW = "module_ops:webhook:view"
WEBHOOK_EDIT = "module_ops:webhook:edit"

NOTIFICATION_VIEW = "module_ops:notification:view"
NOTIFICATION_EDIT = "module_ops:notification:edit"

CDN_VIEW = "module_ops:cdn:view"
CDN_EDIT = "module_ops:cdn:edit"

# ============================================================ T5-11 批次 5（可做项）
UPGRADE_VIEW = "module_ops:upgrade:view"
UPGRADE_EXECUTE = "module_ops:upgrade:execute"

SHORTCODE_VIEW = "module_content:shortcode:view"
SHORTCODE_CREATE = "module_content:shortcode:create"
SHORTCODE_EDIT = "module_content:shortcode:edit"
SHORTCODE_DELETE = "module_content:shortcode:delete"

ENTERPRISE_VIEW = "module_ops:enterprise:view"
ENTERPRISE_EDIT = "module_ops:enterprise:edit"

DEPLOYMENT_VIEW = "module_ops:deployment:view"
DEPLOYMENT_EDIT = "module_ops:deployment:edit"

PAGE_BUILDER_VIEW = "module_content:page_builder:view"
PAGE_BUILDER_CREATE = "module_content:page_builder:create"
PAGE_BUILDER_EDIT = "module_content:page_builder:edit"
PAGE_BUILDER_DELETE = "module_content:page_builder:delete"

# ============================================================ T5-11 批次 7（commerce 域）
PAYMENT_VIEW = "module_commerce:payment:view"
PAYMENT_CREATE = "module_commerce:payment:create"
PAYMENT_EDIT = "module_commerce:payment:edit"
PAYMENT_DELETE = "module_commerce:payment:delete"

REVENUE_VIEW = "module_commerce:revenue:view"
REVENUE_CREATE = "module_commerce:revenue:create"
REVENUE_EDIT = "module_commerce:revenue:edit"
REVENUE_DELETE = "module_commerce:revenue:delete"

# ============================================================ T5-11 批次 8（analytics 报表域）
REPORT_VIEW = "module_analytics:report:view"
REPORT_CREATE = "module_analytics:report:create"
REPORT_EDIT = "module_analytics:report:edit"
REPORT_DELETE = "module_analytics:report:delete"

# ============================================================ T5-11 批次 12（gamification 域：积分 / 勋章 / 认证）
POINTS_VIEW = "module_gamification:points:view"
POINTS_EDIT = "module_gamification:points:edit"

BADGE_VIEW = "module_gamification:badge:view"
BADGE_EDIT = "module_gamification:badge:edit"

CERTIFICATION_VIEW = "module_gamification:certification:view"
CERTIFICATION_REVIEW = "module_gamification:certification:review"

# ---- commerce 域：打赏（批次 12，并入商务域）----
TIPPING_VIEW = "module_commerce:tipping:view"
TIPPING_EDIT = "module_commerce:tipping:edit"

# ============================================================ T5-11 批次 9（content 协作域）
COLLABORATION_VIEW = "module_content:collaboration:view"
COLLABORATION_CREATE = "module_content:collaboration:create"
COLLABORATION_EDIT = "module_content:collaboration:edit"
COLLABORATION_DELETE = "module_content:collaboration:delete"

# ============================================================ ai 域（T5-11 批次 4）
AI_CONFIG_VIEW = "module_ai:config:view"
AI_CONFIG_CREATE = "module_ai:config:create"
AI_CONFIG_EDIT = "module_ai:config:edit"
AI_CONFIG_DELETE = "module_ai:config:delete"

AI_WORKFLOW_VIEW = "module_ai:workflow:view"
AI_WORKFLOW_DELETE = "module_ai:workflow:delete"

# ============================================================ chat 域（T5-11 批次 4）
CHAT_GROUP_VIEW = "module_chat:group:view"
CHAT_GROUP_CREATE = "module_chat:group:create"
CHAT_GROUP_EDIT = "module_chat:group:edit"
CHAT_GROUP_DELETE = "module_chat:group:delete"
CHAT_GROUP_MANAGE_MEMBERS = "module_chat:group:manage_members"

# ============================================================ multisite（T5-11 批次 4）
SITE_VIEW = "module_system:site:view"
SITE_CREATE = "module_system:site:create"
SITE_EDIT = "module_system:site:edit"
SITE_DELETE = "module_system:site:delete"

# ============================================================ 过渡期兼容
#: "纯改名"的前缀映射：新码前缀 → 旧码前缀（旧码仍被接受，P6 移除）
_LEGACY_PREFIXES: dict[str, str] = {
    "module_content:article:": "article:",
    "module_content:category:": "category:",
    "module_content:comment:": "comment:",
    "module_content:media:": "media:",
    "module_content:page:": "page:",
    "module_system:user:": "user:",
    "module_system:navmenu:": "menu:",
}


def _build_legacy_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for name, value in list(globals().items()):
        if not isinstance(value, str) or not value.startswith("module_"):
            continue
        for new_prefix, old_prefix in _LEGACY_PREFIXES.items():
            if value.startswith(new_prefix):
                aliases[value] = old_prefix + value[len(new_prefix):]
                break
    return aliases


#: 新码 → 旧码（仅供过渡期"旧码也放行"使用）
LEGACY_ALIASES: dict[str, str] = _build_legacy_aliases()


def legacy_aliases_of(code: str) -> frozenset[str]:
    """返回某权限码在过渡期可接受的**全部等价写法**（含自身）"""
    alias = LEGACY_ALIASES.get(code)
    return frozenset({code, alias}) if alias else frozenset({code})


def all_codes() -> list[str]:
    """本模块定义的全部三段权限码（供启动期审计与 seed 校验）"""
    return sorted(
        value
        for value in globals().values()
        if isinstance(value, str) and value.startswith("module_")
    )


#: 权限码 → 中文名（**顺序即后台展示与 seed 顺序**；同时是 capabilities 表的唯一真相）
CODE_LABELS: dict[str, str] = {
    # ---- content ----
    ARTICLE_VIEW: "查看文章",
    ARTICLE_CREATE: "创建文章",
    ARTICLE_EDIT: "编辑文章",
    ARTICLE_DELETE: "删除文章",
    ARTICLE_PUBLISH: "发布文章",
    ARTICLE_EDIT_OTHERS: "编辑他人文章",
    ARTICLE_DELETE_OTHERS: "删除他人文章",
    CATEGORY_VIEW: "查看分类",
    CATEGORY_CREATE: "创建分类",
    CATEGORY_EDIT: "编辑分类",
    CATEGORY_DELETE: "删除分类",
    TAG_VIEW: "查看标签",
    TAG_EDIT: "编辑标签",
    COMMENT_VIEW: "查看评论",
    COMMENT_APPROVE: "审核评论",
    COMMENT_EDIT: "编辑评论",
    COMMENT_DELETE: "删除评论",
    MEDIA_VIEW: "查看媒体",
    MEDIA_UPLOAD: "上传文件",
    MEDIA_DELETE: "删除文件",
    CPT_VIEW: "查看内容类型",
    CPT_CREATE: "创建内容类型",
    CPT_EDIT: "编辑内容类型",
    CPT_DELETE: "删除内容类型",
    APPROVAL_VIEW: "查看审批",
    APPROVAL_ACT: "处理审批",
    APPROVAL_DELETE: "删除审批单",
    GDPR_VIEW: "查看合规同意记录",
    GDPR_DELETE: "删除合规记录",
    INTEGRATION_VIEW: "查看第三方集成",
    INTEGRATION_CREATE: "创建第三方集成",
    INTEGRATION_EDIT: "编辑第三方集成",
    INTEGRATION_DELETE: "删除第三方集成",
    SOCIAL_VIEW: "查看社交绑定",
    SOCIAL_DELETE: "解除社交绑定",
    SECURITY_VIEW: "查看安全中心",
    SECURITY_DELETE: "删除安全记录",
    PAGE_VIEW: "查看页面",
    PAGE_CREATE: "创建页面",
    PAGE_EDIT: "编辑页面",
    PAGE_DELETE: "删除页面",
    PAGE_PUBLISH: "发布页面",
    # ---- system ----
    USER_VIEW: "查看用户",
    USER_CREATE: "创建用户",
    USER_EDIT: "编辑用户",
    USER_DELETE: "删除用户",
    USER_MANAGE_ROLES: "分配用户角色",
    ROLE_VIEW: "查看角色",
    ROLE_EDIT: "管理角色",
    NAVMENU_VIEW: "查看前台导航菜单",
    NAVMENU_CREATE: "创建前台导航菜单",
    NAVMENU_EDIT: "编辑前台导航菜单",
    NAVMENU_DELETE: "删除前台导航菜单",
    MENU_VIEW: "查看后台菜单",
    MENU_CREATE: "创建后台菜单",
    MENU_EDIT: "编辑后台菜单",
    MENU_DELETE: "删除后台菜单",
    MENU_GRANT: "授权角色菜单",
    GROUP_VIEW: "查看权限组",
    GROUP_CREATE: "创建权限组",
    GROUP_EDIT: "编辑权限组",
    GROUP_DELETE: "删除权限组",
    GROUP_MANAGE_MEMBERS: "管理权限组成员",
    GROUP_MANAGE_ROLES: "绑定权限组角色",
    PERMISSION_VIEW: "查看权限码",
    PERMISSION_EDIT: "刷新权限缓存",
    SETTING_VIEW: "查看系统设置",
    SETTING_EDIT: "编辑系统设置",
    LOG_VIEW: "查看操作日志",
    LOG_EDIT: "清理操作日志",
    CACHE_VIEW: "查看缓存",
    CACHE_CLEAR: "清空缓存",
    CACHE_WARMUP: "预热缓存",
    CACHE_WRITE: "读写缓存键",
    SENSITIVE_WORD_VIEW: "查看敏感词库",
    SENSITIVE_WORD_CREATE: "添加敏感词",
    SENSITIVE_WORD_EDIT: "编辑敏感词",
    SENSITIVE_WORD_DELETE: "删除敏感词",
    SITE_VIEW: "查看站点",
    SITE_CREATE: "创建站点",
    SITE_EDIT: "编辑站点",
    SITE_DELETE: "删除站点",
    MONITOR_VIEW: "查看系统状态",
    MONITOR_KICK: "强制下线",
    MONITOR_MANAGE: "管理告警 / 指标 / SLA（批次 10）",
    # ---- analytics ----
    DASHBOARD_VIEW: "查看仪表盘",
    SEO_VIEW: "查看 SEO",
    SEO_EDIT: "编辑 SEO",
    SEARCH_VIEW: "查看搜索分析",
    # ---- extension ----
    PLUGIN_VIEW: "查看插件",
    PLUGIN_INSTALL: "安装插件",
    PLUGIN_ACTIVATE: "激活插件",
    PLUGIN_DELETE: "删除插件",
    PLUGIN_CONFIGURE: "配置插件",
    THEME_VIEW: "查看主题",
    THEME_INSTALL: "安装主题",
    THEME_ACTIVATE: "激活主题",
    THEME_DELETE: "删除主题",
    THEME_CUSTOMIZE: "自定义主题",
    WIDGET_VIEW: "查看小部件",
    WIDGET_EDIT: "编辑小部件",
    BLOCK_PATTERN_VIEW: "查看区块模板",
    BLOCK_PATTERN_CREATE: "创建区块模板",
    BLOCK_PATTERN_EDIT: "编辑区块模板",
    BLOCK_PATTERN_DELETE: "删除区块模板",
    # ---- marketing ----
    AD_VIEW: "查看广告",
    AD_CREATE: "创建广告",
    AD_EDIT: "编辑广告",
    AD_DELETE: "删除广告",
    VIP_VIEW: "查看 VIP 会员",
    VIP_CREATE: "创建 VIP 套餐/订阅",
    VIP_EDIT: "编辑 VIP 套餐/订阅",
    VIP_DELETE: "删除 VIP 套餐/订阅",
    FORM_VIEW: "查看表单",
    FORM_CREATE: "创建表单",
    FORM_EDIT: "编辑表单",
    FORM_DELETE: "删除表单",
    # ---- ai ----
    AI_CONFIG_VIEW: "查看 AI 配置",
    AI_CONFIG_CREATE: "创建 AI 配置",
    AI_CONFIG_EDIT: "编辑 AI 配置",
    AI_CONFIG_DELETE: "删除 AI 配置",
    AI_WORKFLOW_VIEW: "查看 AI 工作流",
    AI_WORKFLOW_DELETE: "删除 AI 工作流记录",
    # ---- chat ----
    CHAT_GROUP_VIEW: "查看群聊",
    CHAT_GROUP_CREATE: "创建群聊",
    CHAT_GROUP_EDIT: "编辑群聊",
    CHAT_GROUP_DELETE: "删除群聊",
    CHAT_GROUP_MANAGE_MEMBERS: "管理群成员",
    # ---- shortcode ----
    SHORTCODE_VIEW: "查看短代码",
    SHORTCODE_CREATE: "创建短代码",
    SHORTCODE_EDIT: "编辑短代码",
    SHORTCODE_DELETE: "删除短代码",
    # ---- enterprise / deployment / page_builder（批次 6）----
    ENTERPRISE_VIEW: "查看企业版权限",
    ENTERPRISE_EDIT: "编辑企业版权限",
    DEPLOYMENT_VIEW: "查看部署脚本与日志",
    DEPLOYMENT_EDIT: "编辑部署脚本",
    PAGE_BUILDER_VIEW: "查看页面搭建",
    PAGE_BUILDER_CREATE: "创建搭建页面",
    PAGE_BUILDER_EDIT: "编辑搭建页面",
    PAGE_BUILDER_DELETE: "删除搭建页面",
    # ---- commerce（批次 7）----
    PAYMENT_VIEW: "查看支付网关与交易",
    PAYMENT_CREATE: "创建支付配置",
    PAYMENT_EDIT: "编辑支付配置",
    PAYMENT_DELETE: "删除支付配置",
    REVENUE_VIEW: "查看收益与提现",
    REVENUE_CREATE: "创建收益记录",
    REVENUE_EDIT: "编辑分账配置与提现",
    REVENUE_DELETE: "删除收益记录",
    # ---- analytics 报表（批次 8）----
    REPORT_VIEW: "查看报表与导出",
    REPORT_CREATE: "创建定时报表",
    REPORT_EDIT: "编辑 / 执行定时报表",
    REPORT_DELETE: "删除定时报表",
    # ---- gamification（批次 12）----
    POINTS_VIEW: "查看积分规则与统计",
    POINTS_EDIT: "调整积分与规则",
    BADGE_VIEW: "查看勋章统计",
    BADGE_EDIT: "授予勋章",
    CERTIFICATION_VIEW: "查看专家认证",
    CERTIFICATION_REVIEW: "审核专家认证",
    # ---- 打赏（批次 12，commerce 域）----
    TIPPING_VIEW: "查看打赏与提现",
    TIPPING_EDIT: "处理提现与退款",
    # ---- content 协作（批次 9）----
    COLLABORATION_VIEW: "查看工作区 / 评论 / 邀请",
    COLLABORATION_CREATE: "创建工作区 / 评论 / 邀请",
    COLLABORATION_EDIT: "编辑工作区 / 任务 / 评论",
    COLLABORATION_DELETE: "删除工作区 / 任务 / 评论",
    # ---- ops ----
    MIGRATION_VIEW: "查看迁移任务",
    MIGRATION_CREATE: "创建迁移任务",
    MIGRATION_EDIT: "编辑迁移任务",
    MIGRATION_DELETE: "删除迁移任务",
    EMAIL_VIEW: "查看邮件服务",
    EMAIL_EDIT: "编辑邮件服务",
    EMAIL_DELETE: "删除邮件服务配置",
    BACKUP_VIEW: "查看备份",
    BACKUP_CREATE: "创建备份",
    BACKUP_RESTORE: "恢复备份",
    BACKUP_DELETE: "删除备份",
    WEBHOOK_VIEW: "查看 Webhook",
    WEBHOOK_EDIT: "编辑 Webhook",
    NOTIFICATION_VIEW: "查看通知",
    NOTIFICATION_EDIT: "管理通知",
    CDN_VIEW: "查看 CDN 配置",
    CDN_EDIT: "编辑 CDN 配置",
    UPGRADE_VIEW: "查看在线升级",
    UPGRADE_EXECUTE: "执行升级操作",
}
