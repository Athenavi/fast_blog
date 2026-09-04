"""
FastBlog API v2 路由规范配置

v2 版本采用以下原则：
1. 所有路径使用 kebab-case 命名
2. 避免通用路径冲突（如 /stats、/config）
3. 资源路径清晰分层，不使用根级参数
4. 合并重复模块功能
5. 统一领域前缀

内置插件化：非核心功能模块（电商/企业/广告等）作为内置插件管理，
默认启用，可通过环境变量 DISABLED_MODULES 关闭（逗号分隔模块名或短名），不删除代码。
"""
import os

# v2 路由注册表：(模块路径, v2前缀, 标签列表, 是否必需)
ROUTE_REGISTRY_V2 = [
    # ==================== 核心模块（必需）====================
    ("src.api.v2.home", "/api/v2/home", ["home"], True),
    # ==================== 仪表板（V2 聚合路由器）====================
    # V2 Dashboard 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.dashboard", "/api/v2/dashboard", ["dashboard-v2"], True),
    # core.system 已迁移：health/info 路由现已直接内联在 v2.system 聚合器中

    # ==================== 文章核心（V2 聚合路由器）====================
    # V2 Articles 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.articles", "/api/v2/articles", ["articles-v2"], True),

    # ==================== 分类管理（已迁移到 /api/v2/cms/categories）====================
    # 移除理由：V2 content_management 聚合器已在 /api/v2/cms 下以 /categories 前缀注册了 category_management 路由

    # ==================== 标签管理（V2 聚合路由器）====================
    ("src.api.v2.tags", "/api/v2/tags", ["tags"], False),

    # ==================== 搜索（V2 聚合路由器）====================
    # V2 Search 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.search", "/api/v2/search", ["search-v2"], True),

    # ==================== 评论系统（V2 聚合路由器）====================
    # V2 Comments 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.comments", "/api/v2/comments", ["comments-v2"], True),
    # V1 comments 各子模块已废弃，功能已迁移到 V2 聚合路由器

    # ==================== 聊天与消息（V2 聚合路由器）====================
    # V2 Chat 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.chat", "/api/v2/chats", ["chat-v2"], True),
    # ==================== 通知消息（V2 聚合路由器）====================
    # V2 Notifications 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.notifications", "/api/v2/notifications", ["notifications-v2"], True),
    # ==================== 协作功能（V2 聚合路由器）====================
    # V2 Collaboration 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.collaboration", "/api/v2/collaboration", ["collaboration-v2"], True),

    # ==================== CMS 内容管理（V2 聚合路由器）====================
    # V2 Content Management 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.content_management", "/api/v2/cms", ["cms-v2"], True),
    # V1 content_management 各子模块已废弃，功能已迁移到 V2 聚合路由器

    # ==================== 块模式库（已迁移到 /api/v2/cms/block-patterns）====================
    # 移除理由：V2 content_management 聚合器已在 /api/v2/cms 下以 /block-patterns 前缀注册了 block_patterns 路由

    # ==================== 全局样式（已迁移到 /api/v2/cms/global-styles）====================
    # 移除理由：V2 content_management 聚合器已在 /api/v2/cms 下以 /global-styles 前缀注册了 global_styles 路由

    # ==================== 电商功能（V2 聚合路由器）====================
    # V2 Ecommerce 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.ecommerce", "/api/v2/shop", ["ecommerce-v2"], True),
    # V1 ecommerce 各子模块已废弃，功能已迁移到 V2 聚合路由器

    # ==================== 媒体管理（V2 聚合路由器）====================
    ("src.api.v2.media", "/api/v2/media", ["media"], False),

    # ==================== SEO 优化（V2 聚合路由器）====================
    # V2 SEO 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.seo", "/api/v2/seo", ["seo-v2"], True),

    # ==================== 安全与权限（V2 聚合路由器）====================
    # V2 Security 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.security", "/api/v2/security", ["security-v2"], True),
    # V1 security 各子模块已废弃，功能已迁移到 V2 聚合路由器

    # ==================== 认证模块（V2 聚合路由器）====================
    ("src.api.v2.auth", "/api/v2/auth", ["auth"], False),
    ("src.api.v2.qr_login", "/api/v2/auth/qr", ["qr-login"], False),

    # ==================== 用户管理（V2 聚合路由器）====================
    # V2 Users 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.users", "/api/v2", ["users-v2"], True),
    # ==================== 性能监控与优化（V2 聚合路由器）====================
    # V2 Performance 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.performance", "/api/v2/performance", ["performance-v2"], True),
    # V1 performance 各子模块已废弃，功能已迁移到 V2 聚合路由器

    # ==================== 系统管理（V2 聚合路由器）====================
    # V2 System 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.system", "/api/v2/system", ["system-v2"], True),

    # ==================== 安装向导（已迁移到 /api/v2/system/install）====================
    # 移除理由：V2 system 聚合器已在 /api/v2/system 下以 /install 前缀注册了 installation 路由

    # ==================== GDPR 合规（V2 完整版）====================
    # V1 gdpr_compliance 已废弃，功能已整合到 V2 compliance_api
    # ("src.api.v1.compliance.gdpr_compliance", "/api/v2/gdpr", ["gdpr-compliance"], False),
    ("src.api.v2.compliance.compliance_api", "/api/v2", ["compliance-management-v2"], True),

    # ==================== 主题管理（移除） ====================

    # ==================== 插件管理（V2 聚合路由器）====================
    # V2 Plugins 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.plugins", "/api/v2/plugins", ["plugins-v2"], True),

    # ==================== 主题管理（V2 独立路由，主题以 category="theme" 插件形式存在）====================
    ("src.api.v2.plugins.theme_routes", "/api/v2/themes", ["themes-v2"], False),

    # ==================== 翻译（V2 聚合路由器）====================
    # V2 Translation 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.translation", "/api/v2", ["translation-v2"], True),
    # V1 translation 各子模块已废弃，功能已迁移到 V2 聚合路由器

    # ==================== 第三方集成（V2 聚合路由器）====================
    # V2 Integrations 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.integrations", "/api/v2/integrations", ["integrations-v2"], True),
    # V1 integrations 各子模块已废弃，功能已迁移到 V2 聚合路由器

    # ==================== 广告管理（V2 聚合路由器）====================
    # V2 Marketing 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.marketing", "/api/v2/ads", ["marketing-v2"], True),
    # V1 marketing 各子模块已废弃，功能已迁移到 V2 聚合路由器
    # ("src.api.v1.marketing.advertisement_system", "/api/v2/ads", ["advertisement-system"], False),

    # ==================== 静态生成（V2 聚合路由器）====================
    # V2 Static Generation 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.static_generation", "/api/v2/static-site", ["static-generation-v2"], True),
    # V1 static_generation 各子模块已废弃，功能已迁移到 V2 聚合路由器
    # ("src.api.v1.static_generation.static_site_generation", "/api/v2/static-site", ["static-site-generation"], False),

    # ==================== 支付（已迁移到 /api/v2/shop/payment + /api/v2/shop/admin）====================
    # 移除理由：utils.payment 和 payment_management 已加入 v2.ecommerce 聚合器

    # ==================== 迁移系统管理（已迁移到 /api/v2/system/migration-management）====================
    # 移除理由：migration_management 已加入 v2.system 聚合器

    # ==================== 内容管理扩展（已整合到 /api/v2/cms/management）====================
    # 移除理由：content_management_ext 已加入 v2.content_management 聚合器

    # ==================== 用户安全管理（已整合到 /api/v2/users/security）====================
    # 移除理由：user_security_management 已加入 v2.users 聚合器

    # ==================== 搜索与媒体管理（已整合到 /api/v2/search/management）====================
    # 移除理由：search_media_management 已加入 v2.search 聚合器

    # ==================== 可访问性（V2 聚合路由器）====================
    # V2 Accessibility 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.accessibility", "/api/v2/accessibility", ["accessibility-v2"], True),
    # V1 accessibility 各子模块已废弃，功能已迁移到 V2 聚合路由器

    # ==================== 高级扩展功能（V2 聚合路由器）====================
    # V2 Advanced Features 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.advanced_features", "/api/v2/ext", ["advanced-features-v2"], True),
    # AI 配置管理
    ("src.api.v2.ai", "/api/v2", ["ai-config"], False),
    # V1 advanced_features 各子模块已废弃，功能已迁移到 V2 聚合路由器

    # ==================== 其他系统模块（V2 聚合路由器）====================
    ("src.api.v2.analytics", "/api/v2/analytics", ["analytics-v2"], False),
    # ("src.api.v1.articles.anomaly_detection", "/api/v2/system/anomaly-detection", ["anomaly-detection"], False),  # 模块不存在，已禁用
    # ==================== 社交（V2 聚合路由器）====================
    # V2 Social 模块采用包级别聚合模式，所有子模块通过 __init__.py 统一注册
    ("src.api.v2.social", "/api/v2/social", ["social-v2"], True),
    # V1 social 各子模块已废弃，功能已迁移到 V2 聚合路由器
    # ("src.api.v1.social.share_stats", "/api/v2/social/share-stats", ["share-stats"], False),

    # ==================== 示例和工具端点（集中管理）====================
    # 已移除：examples_tools 模块，已转换为 docs/API_EXAMPLES.md 文档

    # ==================== 企业管理（V2 聚合路由器）====================
    # V2 Enterprise 模块整合许可证、工单、部署脚本、监控告警
    ("src.api.v2.enterprise", "/api/v2/enterprise", ["enterprise-v2"], False),

    # ==================== 缓存管理（V2 独立路由）====================
    ("src.api.v2.admin.cache_management", "/api/v2/admin/caches", ["cache-admin"], False),

    # ==================== MCP AI 代理（V2 独立路由）====================
    # 提供 MCP 代理 API，供 AI Chat 前端调用
    ("src.api.v2.mcp", "/api/v2", ["mcp-proxy-v2"], False),
]


# ==================== 内置插件开关 ====================
# 非核心功能模块（博客平台之外的扩展能力）规划为内置插件：
# - 默认启用（不破坏现有功能）
# - 可通过环境变量 DISABLED_MODULES 关闭，如 DISABLED_MODULES=ecommerce,enterprise
# - 不删除代码，按需开/关
OPTIONAL_PLUGIN_MODULES = {
    'src.api.v2.ecommerce',          # 电商（产品/购物车/订单/支付管理/分账）
    'src.api.v2.enterprise',         # 企业套件（许可证/工单/部署脚本/监控告警）
    'src.api.v2.advanced_features',  # 高级扩展（WebSocket/AI推荐等）
    'src.api.v2.marketing',          # 广告管理
    'src.api.v2.accessibility',      # 可访问性（AMP 等）
    'src.api.v2.social',             # 社交（分享统计）
    'src.api.v2.notifications',      # 通知（可独立关闭）
    'src.api.v2.ai',                 # AI 配置
}


def _match_module(module_path: str, names: set) -> bool:
    """模块名或短名匹配"""
    short = module_path.split('.')[-1]
    return module_path in names or short in names


def is_module_enabled(module_path: str) -> bool:
    """
    判断模块是否注册（内置插件开关）。

    规则：
    1. 核心模块（不在 OPTIONAL_PLUGIN_MODULES）始终启用。
    2. DISABLED_MODULES 中列出的可选模块被关闭。
    3. 可选模块默认启用。
    """
    if module_path not in OPTIONAL_PLUGIN_MODULES:
        return True
    disabled = {x.strip() for x in os.environ.get('DISABLED_MODULES', '').split(',') if x.strip()}
    if disabled and _match_module(module_path, disabled):
        return False
    return True
