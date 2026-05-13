"""
FastBlog API v2 路由规范配置

根据 TODO.md 中的建议，v2 版本采用以下原则：
1. 所有路径使用 kebab-case 命名
2. 避免通用路径冲突（如 /stats、/config）
3. 资源路径清晰分层，不使用根级参数
4. 合并重复模块功能
5. 统一领域前缀

领域映射表：
- users: 用户认证与资料
- articles: 文章核心功能
- categories: 分类管理
- search: 搜索功能
- cms: CMS 内容管理
- shop: 电商功能
- monitoring: 性能监控
- backup: 备份管理
- cache: 缓存管理
- translations: 国际化与翻译
- ads: 广告管理
- integrations: 第三方集成
- seo: SEO 优化
- gdpr: GDPR 合规
- analytics: 统计分析
- notifications: 通知消息
- security: 安全管理
- themes: 主题管理
- ext: 扩展功能
"""

# v2 路由注册表：(模块路径, v2前缀, 标签列表, 是否必需)
ROUTE_REGISTRY_V2 = [
    # ==================== 核心模块（必需）====================
    ("src.api.v1.core.home", "/api/v2/home", ["home"], True),
    ("src.api.v1.dashboard.dashboard", "/api/v2/dashboard", ["dashboard"], True),
    ("src.api.v1.core.system", "/api/v2/system", ["system"], True),

    # ==================== 文章核心 ====================
    ("src.api.v1.articles.article_password", "/api/v2/articles", ["article-password"], False),
    ("src.api.v1.articles.article_revisions", "/api/v2/articles", ["article-revisions"], False),
    ("src.api.v1.articles.article_analytics", "/api/v2/analytics/articles", ["article-analytics"], False),
    ("src.api.v1.articles.article_annotations", "/api/v2/articles/annotations", ["article-annotations"], False),
    ("src.api.v1.articles.article_interactions", "/api/v2/articles", ["article-interactions"], False),
    ("src.api.v1.articles.article_stats", "/api/v2/analytics/articles/stats", ["article-stats"], False),
    ("src.api.v1.articles.draft_preview", "/api/v2/articles/drafts", ["draft-preview"], False),
    ("src.api.v1.articles.scheduled_publish", "/api/v2/articles/scheduler", ["scheduled-publish"], False),

    # ==================== 分类管理 ====================
    ("src.api.v1.content_management.category_management", "/api/v2/categories", ["categories"], True),

    # ==================== 标签管理（新增）====================
    ("src.api.v1.articles.tags", "/api/v2/tags", ["tags"], False),

    # ==================== 搜索 ====================
    ("src.api.v1.search.fulltext_search", "/api/v2/search", ["fulltext-search"], False),
    ("src.api.v1.search.search_history", "/api/v2/search", ["search-history"], False),

    # ==================== 评论系统 ====================
    ("src.api.v1.comments.comments", "/api/v2/comments", ["comments"], False),
    ("src.api.v1.comments.comments_enhanced", "/api/v2/comments/enhanced", ["comments-enhanced"], False),
    ("src.api.v1.comments.comment_config", "/api/v2/comments/config", ["comment-config"], False),
    ("src.api.v1.comments.comment_subscriptions", "/api/v2/comments/subscriptions", ["comment-subscriptions"], False),

    # ==================== 聊天与消息 ====================
    ("src.api.v1.chat.chat", "/api/v2/chats", ["chat"], False),
    ("src.api.v1.chat.chat_groups", "/api/v2/chats/groups", ["chat-groups"], False),
    ("src.api.v1.chat.private_messages", "/api/v2/messages/private", ["private-messages"], False),
    ("src.api.v1.notifications.notifications", "/api/v2/notifications", ["notifications"], False),
    ("src.api.v1.notifications.email_service", "/api/v2/notifications/email", ["email-service"], False),
    ("src.api.v1.notifications.push_notifications", "/api/v2/notifications/push", ["push-notifications"], False),

    # ==================== 协作功能 ====================
    ("src.api.v1.collaboration.collaboration_invites", "/api/v2/collaboration/invites", ["collaboration-invites"],
     False),
    ("src.api.v1.collaboration.collaboration_save", "/api/v2/collaboration", ["collaboration-save"], False),
    ("src.api.v1.collaboration.team_collaboration", "/api/v2/collaboration/team", ["team-collaboration"], False),
    ("src.api.v1.collaboration.team_comments", "/api/v2/collaboration/comments", ["team-comments"], False),
    ("src.api.v1.collaboration.yjs_collaboration", "/api/v2/collaboration/yjs", ["yjs-collaboration"], False),

    # ==================== CMS 内容管理 ====================
    ("src.api.v1.content_management.block_editor", "/api/v2/cms/blocks", ["block-editor"], False),
    ("src.api.v1.content_management.custom_block_patterns", "/api/v2/cms/patterns", ["custom-block-patterns"], False),
    ("src.api.v1.content_management.custom_post_types", "/api/v2/cms/post-types", ["custom-post-types"], False),
    ("src.api.v1.content_management.form_builder", "/api/v2/cms/forms", ["form-builder"], False),
    ("src.api.v1.content_management.menu_management", "/api/v2/cms/menus", ["menu-management"], False),
    ("src.api.v1.content_management.shortcode", "/api/v2/cms/shortcodes", ["shortcode"], False),
    ("src.api.v1.content_management.widgets", "/api/v2/cms/widgets", ["widgets"], False),
    ("src.api.v1.content_management.feed", "/api/v2/feed", ["feed"], False),

    # ==================== 电商功能（已重构，删除重复端点）====================
    ("src.api.v1.ecommerce.ecommerce", "/api/v2/shop", ["ecommerce"], False),
    ("src.api.v1.ecommerce.ecommerce_cart", "/api/v2/shop/cart", ["ecommerce-cart"], False),
    ("src.api.v1.ecommerce.ecommerce_orders", "/api/v2/shop/orders", ["ecommerce-orders"], False),
    # ecommerce_products 已废弃，功能合并到 ecommerce.py
    # ("src.api.v1.ecommerce.ecommerce_products", "/api/v2/shop/products", ["ecommerce-products"], False),
    ("src.api.v1.ecommerce.inventory_management", "/api/v2/shop/inventory", ["inventory-management"], False),
    ("src.api.v1.ecommerce.revenue_sharing", "/api/v2/shop/revenue", ["revenue-sharing"], False),

    # ==================== 媒体管理 ====================
    ("src.api.v1.media", "/api/v2/media", ["media"], False),
    ("src.api.v1.media.cover_upload", "/api/v2/media", ["cover-upload"], False),

    # ==================== SEO 优化（已合并为统一模块）====================
    # 所有 SEO 功能已整合到 seo.py 中，通过子路由统一管理
    ("src.api.v1.seo.seo", "/api/v2/seo", ["seo"], False),
    # 以下独立模块已废弃，功能已合并到 seo.py
    # ("src.api.v1.seo.seo_management", "/api/v2/seo/management", ["seo-management"], False),
    # ("src.api.v1.seo.seo_optimization", "/api/v2/seo/optimization", ["seo-optimization"], False),
    # ("src.api.v1.seo.seo_tracking", "/api/v2/seo/tracking", ["seo-tracking"], False),
    # ("src.api.v1.seo.breadcrumbs", "/api/v2/seo/breadcrumbs", ["breadcrumbs"], False),
    # ("src.api.v1.seo.hreflang_api", "/api/v2/seo/hreflang", ["hreflang-api"], False),
    # ("src.api.v1.seo.internal_links", "/api/v2/seo/internal-links", ["internal-links"], False),
    # ("src.api.v1.seo.redirect_management", "/api/v2/seo/redirects", ["redirect-management"], False),
    # ("src.api.v1.seo.batch_seo", "/api/v2/seo/batch", ["batch-seo"], False),
    # ("src.api.v1.seo.sitemap", "/api/v2/seo/sitemap", ["sitemap"], False),

    # ==================== 安全与权限 ====================
    ("src.api.v1.security.audit_log", "/api/v2/security/audit-log", ["audit-log"], False),
    ("src.api.v1.security.content_approval", "/api/v2/security/approval", ["content-approval"], False),
    ("src.api.v1.security.login_security", "/api/v2/security/login", ["login-security"], False),
    ("src.api.v1.security.rate_limit", "/api/v2/security/rate-limit", ["rate-limit"], False),
    ("src.api.v1.security.rbac", "/api/v2/security/rbac", ["rbac"], False),
    ("src.api.v1.security.security_alert", "/api/v2/security/alerts", ["security-alert"], False),
    ("src.api.v1.security.security_report", "/api/v2/security/reports", ["security-report"], False),
    ("src.api.v1.security.sensitive_words", "/api/v2/security/sensitive-words", ["sensitive-words"], False),
    ("src.api.v1.security.session_management", "/api/v2/security/sessions", ["session-management"], False),
    ("src.api.v1.security.two_factor_auth", "/api/v2/security/2fa", ["2fa"], False),

    # ==================== 认证模块（新增）====================
    ("src.api.v1.auth", "/api/v2/auth", ["auth"], False),

    # ==================== 用户管理（已合并，删除重复的关注端点）====================
    # 所有用户功能已整合到 users/__init__.py 中，通过子路由统一管理
    ("src.api.v1.users", "/api/v2/users", ["users"], False),
    # user_management 保留管理员功能，路径为 /api/v2/admin/users
    ("src.api.v1.users.user_management", "/api/v2/admin/users", ["user-management"], False),
    # 以下独立模块已废弃，功能已合并到 users/__init__.py
    # ("src.api.v1.users.user_blocks", "/api/v2/users/blocks", ["user-blocks"], False),
    # ("src.api.v1.users.user_profile", "/api/v2/users/profiles", ["user-profile"], False),
    # ("src.api.v1.users.user_relations", "/api/v2/users/relations", ["user-relations"], False),
    # ("src.api.v1.users.user_settings", "/api/v2/users/settings", ["user-settings"], False),
    # ("src.api.v1.users.user_utils", "/api/v2/users", ["user-utils"], False),

    # ==================== 会员与积分（已统一，VIP功能已合并到membership）====================
    ("src.api.v1.advanced_features.membership", "/api/v2/membership", ["membership"], True),
    # VIP 模块已废弃，功能已合并到 membership 模块
    # ("src.api.v1.user_utils.vip", "/api/v2/users/vip", ["vip"], False),
    ("src.api.v1.advanced_features.points_system", "/api/v2/ext/points", ["points-system"], False),
    ("src.api.v1.advanced_features.tipping_system", "/api/v2/ext/tipping", ["tipping-system"], False),

    # ==================== 性能监控（合并）====================
    ("src.api.v1.performance.performance_monitor", "/api/v2/monitoring/performance", ["performance-monitor"], False),
    ("src.api.v1.performance.query_monitor", "/api/v2/monitoring/queries", ["query-monitor"], False),
    ("src.api.v1.performance.query_optimization", "/api/v2/monitoring/queries/optimization", ["query-optimization"],
     False),
    ("src.api.v1.performance.slow_query_log", "/api/v2/monitoring/queries/slow", ["slow-query-log"], False),

    # ==================== 缓存管理（合并）====================
    ("src.api.v1.performance.cache_management", "/api/v2/cache", ["cache-management"], False),
    ("src.api.v1.performance.object_cache", "/api/v2/cache/object", ["object-cache"], False),
    ("src.api.v1.performance.page_cache", "/api/v2/cache/page", ["page-cache"], False),

    # ==================== CDN 与优化 ====================
    ("src.api.v1.performance.cdn_management", "/api/v2/cdn", ["cdn-management"], False),
    ("src.api.v1.performance.code_splitting_optimization", "/api/v2/optimization/code-splitting", ["code-splitting"],
     False),
    ("src.api.v1.performance.css_optimizer", "/api/v2/optimization/css", ["css-optimizer"], False),
    ("src.api.v1.performance.http2_config", "/api/v2/cdn/http2", ["http2-config"], False),
    ("src.api.v1.performance.image_lazy_load", "/api/v2/optimization/lazy-load", ["image-lazy-load"], False),
    ("src.api.v1.performance.lazy_load_optimization", "/api/v2/optimization/lazy-load", ["lazy-load-optimization"],
     False),
    ("src.api.v1.performance.load_balancer", "/api/v2/cdn/load-balancer", ["load-balancer"], False),
    ("src.api.v1.performance.resource_optimization", "/api/v2/optimization/resources", ["resource-optimization"],
     False),

    # ==================== 备份管理（合并）====================
    ("src.api.v1.system.backup_management", "/api/v2/backup", ["backup-management"], False),

    # ==================== 系统管理 ====================
    ("src.api.v1.system.admin_settings", "/api/v2/admin/settings", ["admin-settings"], False),
    ("src.api.v1.system.batch_operations", "/api/v2/admin/batch", ["batch-operations"], False),
    ("src.api.v1.system.data_export", "/api/v2/gdpr/export", ["data-export"], False),
    ("src.api.v1.system.database_migration", "/api/v2/admin/database/migrations", ["database-migration"], False),
    ("src.api.v1.system.installation", "/api/v2/install", ["installation"], False),
    ("src.api.v1.system.maintenance", "/api/v2/admin/maintenance", ["maintenance"], False),
    ("src.api.v1.system.migrations", "/api/v2/admin/migrations", ["migrations"], False),
    ("src.api.v1.system.multisite", "/api/v2/sites", ["multisite"], False),
    ("src.api.v1.system.report_management", "/api/v2/admin/reports", ["report-management"], False),
    ("src.api.v1.system.resource_transfer", "/api/v2/admin/resource-transfer", ["resource-transfer"], False),
    ("src.api.v1.system.screen_options", "/api/v2/admin/screen-options", ["screen-options"], False),
    ("src.api.v1.system.version", "/api/v2/system/version", ["system-version"], False),
    ("src.api.v1.system.webhook_management", "/api/v2/admin/webhooks", ["webhook-management"], False),
    ("src.api.v1.system.workflow", "/api/v2/workflow", ["workflow"], False),

    # ==================== GDPR 合规（路径已优化为 RESTful 风格）====================
    ("src.api.v1.compliance.gdpr_compliance", "/api/v2/gdpr", ["gdpr-compliance"], False),

    # ==================== 主题管理 ====================
    ("src.api.v1.themes.page_templates", "/api/v2/themes/templates", ["page-templates"], False),
    ("src.api.v1.themes.full_site_editor", "/api/v2/themes/editor", ["full-site-editor"], False),
    ("src.api.v1.themes.template_hierarchy", "/api/v2/themes/hierarchy", ["template-hierarchy"], False),
    ("src.api.v1.themes.theme_customizer", "/api/v2/themes/customizer", ["theme-customizer"], False),
    ("src.api.v1.themes.theme_management", "/api/v2/admin/themes", ["theme-management"], False),

    # ==================== 国际化与翻译（合并）====================
    ("src.api.v1.translation.translations", "/api/v2/translations", ["translations"], False),

    # ==================== 第三方集成 ====================
    ("src.api.v1.integrations.baidu_analytics", "/api/v2/integrations/baidu-analytics", ["baidu-analytics"], False),
    ("src.api.v1.integrations.ipfs", "/api/v2/integrations/ipfs", ["ipfs"], False),
    ("src.api.v1.integrations.oauth_login", "/api/v2/integrations/oauth", ["oauth-login"], False),
    ("src.api.v1.integrations.sso", "/api/v2/integrations/sso", ["sso"], False),
    ("src.api.v1.integrations.wordpress_import", "/api/v2/integrations/wordpress-import", ["wordpress-import"], False),

    # ==================== 广告管理（合并）====================
    ("src.api.v1.marketing.advertisement_system", "/api/v2/ads", ["advertisement-system"], False),

    # ==================== 静态生成 ====================
    ("src.api.v1.static_generation.static_site_generation", "/api/v2/static-site", ["static-site-generation"], False),

    # ==================== 支付工具 ====================
    ("src.api.v1.utils.payment", "/api/v2/payments", ["payment"], False),

    # ==================== 可访问性 ====================
    ("src.api.v1.accessibility.accessibility_audit", "/api/v2/accessibility/audit", ["accessibility-audit"], False),
    ("src.api.v1.accessibility.amp", "/api/v2/amp", ["amp"], False),

    # ==================== 高级扩展功能（已删除 personalized_feed 中的重复关注端点）====================
    ("src.api.v1.advanced_features.achievement_badges", "/api/v2/ext/badges", ["achievement-badges"], False),
    ("src.api.v1.advanced_features.ai_recommendations", "/api/v2/ext/ai-recommendations", ["ai-recommendations"],
     False),
    ("src.api.v1.advanced_features.edge_functions", "/api/v2/ext/edge-functions", ["edge-functions"], False),
    ("src.api.v1.advanced_features.expert_certification", "/api/v2/ext/expert-certification", ["expert-certification"],
     False),
    ("src.api.v1.advanced_features.nft", "/api/v2/ext/nft", ["nft"], False),
    # personalized_feed 仅保留 feed 生成功能，关注功能已统一到 user_relations
    ("src.api.v1.advanced_features.personalized_feed", "/api/v2/ext/personalized-feed", ["personalized-feed"], False),
    ("src.api.v1.advanced_features.recommendations", "/api/v2/ext/recommendations", ["recommendations"], False),
    ("src.api.v1.advanced_features.websocket", "/api/v2/ext/websocket", ["websocket"], False),

    # ==================== 其他系统模块（misc 模块已完全清理并删除）====================
    ("src.api.v1.articles.anomaly_detection", "/api/v2/system/anomaly-detection", ["anomaly-detection"], False),
    ("src.api.v1.dashboard.analytics", "/api/v2/dashboard/analytics", ["analytics"], False),
    ("src.api.v1.dashboard.realtime_monitor", "/api/v2/dashboard/realtime", ["realtime-monitor"], False),
    ("src.api.v1.social.share_stats", "/api/v2/social/share-stats", ["share-stats"], False),
]

# v1 到 v2 的路径映射表（用于自动重定向）
V1_TO_V2_REDIRECT_MAP = {
    # 通用冲突路径
    "/api/v1/stats": "/api/v2/monitoring/stats",
    "/api/v1/config": "/api/v2/admin/config",
    "/api/v1/delete": "/api/v2/gdpr/data-deletion",
    "/api/v1/export": "/api/v2/gdpr/data-export",
    "/api/v1/rights": "/api/v2/gdpr/user-rights",
    "/api/v1/generate": "/api/v2/seo/hreflang/generate",
    "/api/v1/sync": "/api/v2/sites/sync",
    "/api/v1/process-queue": "/api/v2/downloads/queue/process",

    # 文章相关
    "/api/v1/revisions": "/api/v2/articles/revisions",
    "/api/v1/{article_id}/access": "/api/v2/articles/{article_id}/access-check",

    # 用户相关 - 需要特殊处理动态路径
    "/api/v1/users/profile": "/api/v2/users/me",
    "/api/v1/admin/user/me/profile": "/api/v2/users/me",
    "/api/v1/profiles": "/api/v2/users/settings",

    # SEO 相关
    "/api/v1/admin/seo": "/api/v2/seo/management",
    "/api/v1/breadcrumbs": "/api/v2/seo/breadcrumbs",
    "/api/v1/redirect": "/api/v2/seo/redirects",
    "/api/v1/seo-tracking": "/api/v2/seo/tracking",

    # 缓存相关
    "/api/v1/admin/caches": "/api/v2/cache",
    "/api/v1/clear-all": "/api/v2/cache/clear-all",

    # 备份相关
    "/api/v1/admin/backup": "/api/v2/backup",
    "/api/v1/backup-plus": "/api/v2/backup/incremental",

    # 性能监控相关
    "/api/v1/performance-monitor": "/api/v2/monitoring/performance",
    "/api/v1/performance-tracking": "/api/v2/monitoring/performance",

    # 广告相关
    "/api/v1/admin/ad": "/api/v2/ads/management",

    # 翻译相关
    "/api/v1/i18n": "/api/v2/translations",

    # misc 模块迁移重定向
    "/api/v1/misc/tags/suggest": "/api/v2/tags/suggest",
    "/api/v1/misc/search/history": "/api/v2/search/history",
    "/api/v1/misc/upload/cover": "/api/v2/media/cover",
    "/api/v1/misc/check-email": "/api/v2/auth/check-email",
    "/api/v1/misc/check-username": "/api/v2/auth/check-username",
    "/api/v1/misc/email-exists": "/api/v2/auth/check-email",
    "/api/v1/misc/username-exists/{username}": "/api/v2/auth/check-username/{username}",
    "/api/v1/misc/version/info": "/api/v2/system/version/full",
    "/api/v1/misc/version/frontend": "/api/v2/system/version/frontend",
    "/api/v1/misc/version/backend": "/api/v2/system/version/backend",
}
