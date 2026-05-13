"""
FastBlog 应用入口
"""
import importlib
import logging
import os
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.staticfiles import StaticFiles


# ---------- 工具函数 ----------
def safe_run(func_name: str, func, *args, **kwargs):
    """安全执行同步/异步初始化，统一日志输出"""
    print(f"\n{'=' * 60}\n[{func_name}] 开始初始化...")
    try:
        result = func(*args, **kwargs)
        print(f"[{func_name}] ✅ 完成")
        return result
    except Exception as e:
        print(f"[{func_name}] ❌ 失败: {e}")
        traceback.print_exc()
        return None


async def safe_run_async(func_name: str, func, *args, **kwargs):
    """安全执行异步初始化"""
    print(f"\n{'=' * 60}\n[{func_name}] 开始初始化...")
    try:
        # 直接调用函数，如果是协程函数会自动返回协程对象
        result = func(*args, **kwargs)
        # 如果结果是协程，则等待它
        if hasattr(result, '__await__'):
            await result
        print(f"[{func_name}] ✅ 完成")
        return result
    except Exception as e:
        print(f"[{func_name}] ❌ 失败: {e}")
        traceback.print_exc()
        return None


def check_installation() -> bool:
    """检查系统是否已安装"""
    try:
        from shared.services.install.install_manager import installation_wizard_service
        installed = installation_wizard_service.is_installed()
        if not installed:
            print("\n" + "=" * 60)
            print("⚠️  系统尚未安装")
            print("👉 请启动前端进程后访问 http://localhost:3000/install 完成安装向导")
            print("=" * 60 + "\n")
        return installed
    except Exception as e:
        print(f"Warning: Failed to check installation status: {e}")
        return False


# ---------- 路由自动发现 ----------
# 配置表：(模块路径, 前缀, 标签列表, 是否必需)
ROUTE_REGISTRY = [
    # 核心模块（必需）
    ("src.api.v1.articles.article_password", "/api/v1", ["article-password"], True),
    ("src.api.v1.articles.article_revisions", "/api/v1", ["article-revisions"], True),
    ("src.api.v1.users.users", "/api/v1/users", ["users"], True),
    ("src.api.v1.__init__", "", [], True),  # api_v1_router 内部自带前缀
    ("src.api.v1.content_management.category_management", "/api/v1/categories", ["categories"], True),
    ("src.api.v1.dashboard.dashboard", "/api/v1/dashboard", ["dashboard"], True),
    ("src.api.v1.core.home", "/api/v1", ["home"], True),
    ("src.api.v1.advanced_features.membership", "/api/v1/membership", ["membership"], True),
    ("src.api.v1.articles.anomaly_detection", "/api/v1/sys", ["anomaly-detection"], True),
    # misc 模块已完全清理并删除，功能已迁移到对应模块
    ("src.api.v1.core.system", "/api/v1/system", ["system"], True),
    # 功能模块（可选加载，失败仅警告）
    ("src.api.v1.articles.article_analytics", "/api/v1/analytics", ["article-analytics"], False),
    ("src.api.v1.articles.article_annotations", "/api/v1/article-annotations", ["article-annotations"], False),
    ("src.api.v1.articles.article_search", "/api/v1/search", ["article-search"], False),
    ("src.api.v1.articles.article_stats", "/api/v1/views", ["article-stats"], False),
    ("src.api.v1.articles.draft_preview", "/api/v1/draft", ["draft-preview"], False),
    ("src.api.v1.articles.scheduled_publish", "/api/v1/scheduler", ["scheduled-publish"], False),
    ("src.api.v1.chat.chat", "/api/v1/chats", ["chat"], False),
    ("src.api.v1.chat.chat_groups", "/api/v1/chats/groups", ["chat-groups"], False),
    ("src.api.v1.chat.private_messages", "/api/v1/messages/private", ["private-messages"], False),
    ("src.api.v1.collaboration.collaboration_invites", "/api/v1/collaboration-invites", ["collaboration-invites"],
     False),
    ("src.api.v1.collaboration.collaboration_save", "/api/v1/collaboration", ["collaboration-save"], False),
    ("src.api.v1.collaboration.team_collaboration", "/api/v1/admin/team", ["team-collaboration"], False),
    ("src.api.v1.collaboration.team_comments", "/api/v1/team/comments", ["team-comments"], False),
    ("src.api.v1.collaboration.yjs_collaboration", "/api/v1", ["yjs-collaboration"], False),
    ("src.api.v1.comments.comment_config", "/api/v1", ["comment-config"], False),
    ("src.api.v1.comments.comment_subscriptions", "/api/v1", ["comment-subscriptions"], False),
    ("src.api.v1.comments.comments", "/api/v1/comments", ["comments"], False),
    ("src.api.v1.comments.comments_enhanced", "/api/v1/comment-plus", ["comments-enhanced"], False),
    ("src.api.v1.compliance.gdpr_compliance", "/api/v1", ["gdpr-compliance"], False),
    ("src.api.v1.content_management.block_editor", "/api/v1", ["block-editor"], False),
    ("src.api.v1.content_management.custom_block_patterns", "/api/v1/pattern", ["custom-block-patterns"], False),
    ("src.api.v1.content_management.custom_post_types", "/api/v1", ["custom-post-types"], False),
    ("src.api.v1.content_management.feed", "/api/v1", ["feed"], False),
    ("src.api.v1.content_management.form_builder", "/api/v1/admin/form", ["form-builder"], False),
    ("src.api.v1.content_management.menu_management", "/api/v1/admin/menu", ["menu-management"], False),
    ("src.api.v1.content_management.shortcode", "/api/v1", ["shortcode"], False),
    ("src.api.v1.content_management.widgets", "/api/v1", ["widgets"], False),
    ("src.api.v1.dashboard.analytics", "/api/v1", ["analytics"], False),
    ("src.api.v1.dashboard.realtime_monitor", "/api/v1", ["realtime-monitor"], False),
    # Ecommerce
    ("src.api.v1.ecommerce.ecommerce", "/api/v1/shop", ["ecommerce"], False),
    ("src.api.v1.ecommerce.ecommerce_cart", "/api/v1/shop", ["ecommerce-cart"], False),
    ("src.api.v1.ecommerce.ecommerce_cart_orders", "/api/v1/shop", ["ecommerce-cart-orders"], False),
    ("src.api.v1.ecommerce.ecommerce_products", "/api/v1/shop", ["ecommerce-products"], False),
    ("src.api.v1.ecommerce.inventory_management", "/api/v1/admin/shop", ["inventory-management"], False),
    ("src.api.v1.ecommerce.revenue_sharing", "/api/v1/shop", ["revenue-sharing"], False),
    ("src.api.v1.integrations.baidu_analytics", "/api/v1/analytics/baidu", ["baidu-analytics"], False),
    ("src.api.v1.integrations.ipfs", "/api/v1/ipfs", ["ipfs"], False),
    ("src.api.v1.integrations.oauth_login", "/api/v1/oauth", ["oauth-login"], False),
    ("src.api.v1.integrations.sso", "/api/v1", ["sso"], False),
    ("src.api.v1.integrations.wordpress_import", "/api/v1/wordpress", ["wordpress-import"], False),
    ("src.api.v1.marketing.ad_management", "/api/v1/admin/ad", ["ad-management"], False),
    ("src.api.v1.marketing.advertisement_system", "/api/v1/ads", ["advertisement-system"], False),
    ("src.api.v1.media", "/api/v1", ["media"], False),
    ("src.api.v1.notifications.email_service", "/api/v1", ["email-service"], False),
    ("src.api.v1.notifications.notifications", "/api/v1/notifications", ["notifications"], False),
    ("src.api.v1.notifications.push_notifications", "/api/v1", ["push-notifications"], False),
    ("src.api.v1.performance.cache_management", "/api/v1/admin/caches", ["cache-management"], False),
    ("src.api.v1.performance.cdn_management", "/api/v1/admin/cdn", ["cdn-management"], False),
    ("src.api.v1.performance.code_splitting_optimization", "/api/v1", ["code-splitting-optimization"], False),
    ("src.api.v1.performance.css_optimizer", "/api/v1", ["css-optimizer"], False),
    ("src.api.v1.performance.http2_config", "/api/v1", ["http2-config"], False),
    ("src.api.v1.performance.image_lazy_load", "/api/v1", ["image-lazy-load"], False),
    ("src.api.v1.performance.lazy_load_optimization", "/api/v1", ["lazy-load-optimization"], False),
    ("src.api.v1.performance.load_balancer", "/api/v1", ["load-balancer"], False),
    ("src.api.v1.performance.localization", "/api/v1", ["localization"], False),
    ("src.api.v1.performance.object_cache", "/api/v1", ["object-cache"], False),
    ("src.api.v1.performance.performance_monitor", "/api/v1/performance-monitor", ["performance-monitor"], False),
    ("src.api.v1.performance.performance_tracking", "/api/v1/performance-tracking", ["performance-tracking"], False),
    ("src.api.v1.performance.query_monitor", "/api/v1", ["query-monitor"], False),
    ("src.api.v1.performance.query_optimization", "/api/v1", ["query-optimization"], False),
    ("src.api.v1.performance.resource_optimization", "/api/v1", ["resource-optimization"], False),
    ("src.api.v1.search.fulltext_search", "/api/v1", ["fulltext-search"], False),
    ("src.api.v1.security.audit_log", "/api/v1", ["audit-log"], False),
    ("src.api.v1.security.content_approval", "/api/v1/content-approval", ["content-approval"], False),
    ("src.api.v1.security.login_security", "/api/v1", ["login-security"], False),
    ("src.api.v1.security.rate_limit", "/api/v1", ["rate-limit"], False),
    ("src.api.v1.security.rbac", "/api/v1", ["rbac"], False),
    ("src.api.v1.security.security_alert", "/api/v1", ["security-alert"], False),
    ("src.api.v1.security.security_report", "/api/v1", ["security-report"], False),
    ("src.api.v1.security.sensitive_words", "/api/v1/sensitive-words", ["sensitive-words"], False),
    ("src.api.v1.security.session_management", "/api/v1/admin/session", ["session-management"], False),
    ("src.api.v1.security.two_factor_auth", "/api/v1/2fa", ["2fa"], False),
    ("src.api.v1.seo.batch_seo", "/api/v1", ["batch-seo"], False),
    ("src.api.v1.seo.breadcrumbs", "/api/v1/breadcrumbs", ["breadcrumbs"], False),
    ("src.api.v1.seo.hreflang_api", "/api/v1", ["hreflang-api"], False),
    ("src.api.v1.seo.internal_links", "/api/v1", ["internal-links"], False),
    ("src.api.v1.seo.redirect_management", "/api/v1/redirect", ["redirect-management"], False),
    ("src.api.v1.seo.seo", "/api/v1/seo", ["seo"], False),
    ("src.api.v1.seo.seo_management", "/api/v1/admin/seo", ["seo-management"], False),
    ("src.api.v1.seo.seo_optimization", "/api/v1/seo", ["seo-optimization"], False),
    ("src.api.v1.seo.seo_tracking", "/api/v1/seo-tracking", ["seo-tracking"], False),
    ("src.api.v1.seo.sitemap", "/api/v1", ["sitemap"], False),
    ("src.api.v1.social.share_stats", "/api/v1", ["share-stats"], False),
    ("src.api.v1.static_generation.page_cache", "/api/v1", ["page-cache"], False),
    ("src.api.v1.static_generation.static_site_generation", "/api/v1", ["static-site-generation"], False),
    ("src.api.v1.system.admin_settings", "/api/v1/admin-settings", ["admin-settings"], False),
    ("src.api.v1.system.backup_management", "/api/v1/admin/backup", ["backup-management"], False),
    ("src.api.v1.system.batch_operations", "/api/v1", ["batch-operations"], False),
    ("src.api.v1.system.data_export", "/api/v1", ["data-export"], False),
    ("src.api.v1.system.database_migration", "/api/v1/admin/db/database-migration", ["database-migration"], False),
    ("src.api.v1.system.incremental_backup", "/api/v1/backup-plus", ["incremental-backup"], False),
    ("src.api.v1.system.installation", "/api/v1", ["installation"], False),
    ("src.api.v1.system.maintenance", "/api/v1", ["maintenance"], False),
    ("src.api.v1.system.migrations", "/api/v1", ["migrations"], False),
    ("src.api.v1.system.multisite", "/api/v1", ["multisite"], False),
    ("src.api.v1.system.report_management", "/api/v1/admin/report", ["report-management"], False),
    ("src.api.v1.system.resource_transfer", "/api/v1", ["resource-transfer"], False),
    ("src.api.v1.system.screen_options", "/api/v1", ["screen-options"], False),
    ("src.api.v1.system.slow_query_log", "/api/v1/admin/slow-query-log", ["slow-query-log"], False),
    ("src.api.v1.system.webhook_management", "/api/v1/admin/webhook", ["webhook-management"], False),
    ("src.api.v1.system.workflow", "/api/v1", ["workflow"], False),

    ("src.api.v1.themes.page_templates", "/api/v1/pages", ["page-templates"], False),
    # themes
    ("src.api.v1.themes.full_site_editor", "/api/v1/theme", ["full-site-editor"], False),
    ("src.api.v1.themes.template_hierarchy", "/api/v1/theme", ["template-hierarchy"], False),
    ("src.api.v1.themes.theme_customizer", "/api/v1/theme", ["theme-customizer"], False),
    ("src.api.v1.themes.theme_management", "/api/v1/admin/theme", ["theme-management"], False),
    # translation_io, translation_progress, translation_service moved after user_management
    # due to wildcard routes /{locale}/{key}
    ("src.api.v1.user_utils", "/api/v1", ["user-utils"], False),
    ("src.api.v1.user_utils.vip", "/api/v1", ["vip"], False),
    ("src.api.v1.users.user_blocks", "/api/v1/user-blocks", ["user-blocks"], False),
    ("src.api.v1.users.user_management", "/api/v1/admin/user", ["user-management"], False),
    ("src.api.v1.users.user_profile", "/api/v1/users", ["user-profile"], False),
    ("src.api.v1.users.user_relations", "/api/v1", ["user-relations"], False),
    ("src.api.v1.users.user_settings", "/api/v1", ["user-settings"], False),
    ("src.api.v1.utils.payment", "/api/v1", ["payment"], False),
    # Wildcard route modules must be registered last
    ("src.api.v1.advanced_features.edge_functions", "/api/v1/edge—func", ["edge-functions"], False),
    # Translation modules with wildcard routes /{locale}/{key}
    ("src.api.v1.translation.i18n", "/api/v1/i18n", ["i18n"], False),
    ("src.api.v1.translation.translation_io", "/api/v1/i18n", ["translation-io"], False),
    ("src.api.v1.translation.translation_progress", "/api/v1/i18n", ["translation-progress"], False),
    ("src.api.v1.translation.translation_service", "/api/v1/i18n", ["translation-service"], False),
    ("src.api.v1.translation.translations", "/api/v1/i18n", ["translations"], False),
    ("src.api.v1.accessibility.accessibility_audit", "/api/v1/accessibility-audit", ["accessibility-audit"], False),
    ("src.api.v1.accessibility.amp", "/api/v1/amp", ["amp"], False),
    ("src.api.v1.advanced_features.achievement_badges", "/api/v1/ext/badges", ["achievement-badges"], False),
    ("src.api.v1.advanced_features.ai_recommendations", "/api/v1/ext/ai-recommendations", ["ai-recommendations"],
     False),
    ("src.api.v1.advanced_features.expert_certification", "/api/v1/ext/expert-certification", ["expert-certification"],
     False),
    ("src.api.v1.advanced_features.nft", "/api/v1/ext/nft", ["nft"], False),
    ("src.api.v1.advanced_features.personalized_feed", "/api/v1/ext/personalized-feed", ["personalized-feed"], False),
    ("src.api.v1.advanced_features.points_system", "/api/v1/ext/point-system", ["points-system"], False),
    ("src.api.v1.advanced_features.recommendations", "/api/v1/ext/recommendations", ["recommendations"], False),
    ("src.api.v1.advanced_features.tipping_system", "/api/v1/ext/tipping-system", ["tipping-system"], False),
    ("src.api.v1.advanced_features.websocket", "/api/v1/ext/ws", ["websocket"], False),
]


def register_all_routes(app: FastAPI, worker_info: str):
    """注册 API v2 路由（已移除 v1）"""

    # 注册 v2 路由（新规范）
    print(f"\n{worker_info} {'=' * 60}")
    print(f"{worker_info} 开始注册 API v2 路由...")
    try:
        from src.api.v2 import ROUTE_REGISTRY_V2
        loaded_count = 0
        failed_count = 0

        for module_path, prefix, tags, required in ROUTE_REGISTRY_V2:
            try:
                mod = importlib.import_module(module_path)
                router = getattr(mod, "router", None)
                if router is None:
                    raise AttributeError("No 'router' found")
                if prefix:
                    app.include_router(router, prefix=prefix, tags=tags if tags else [])
                else:
                    app.include_router(router)
                loaded_count += 1
                print(f"{worker_info} [OK] v2/{module_path.split('.')[-1]} 已加载")
            except ImportError as e:
                if required:
                    print(f"{worker_info} [ERROR] v2 必需模块加载失败: {module_path} - {e}")
                    raise
                else:
                    failed_count += 1
                    print(f"{worker_info} [Warning] v2/{module_path} 未能加载: {e}")
            except Exception as e:
                if required:
                    raise
                failed_count += 1
                print(f"{worker_info} [Warning] v2/{module_path} 注册异常: {e}")

        print(f"{worker_info} ✅ API v2 路由注册完成 (成功: {loaded_count}, 失败: {failed_count})\n")
    except ImportError as e:
        print(f"{worker_info} [ERROR] API v2 模块未找到: {e}\n")
        raise


# ---------- 生命周期 ----------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理（结构化）"""
    # 1. 安装状态检查
    is_installed = check_installation()

    # 2. 数据库管理器（仅安装后）
    if is_installed:
        await safe_run_async("数据库管理器", _init_database)

    # 3. 扩展、调度器
    try:
        from src.extensions import init_extensions
        safe_run("扩展初始化", lambda: init_extensions(app))
    except ImportError as e:
        print(f"[扩展初始化] ⚠️ 跳过: {e}")

    try:
        from src.scheduler import init_scheduler
        safe_run("调度器初始化", lambda: init_scheduler(app))
    except ImportError as e:
        print(f"[调度器初始化] ⚠️ 跳过: {e}")

    if is_installed:
        await safe_run_async("定时发布调度器", _start_scheduled_publisher)

    # 4. 插件系统
    try:
        safe_run("插件系统", _init_plugins)
    except ImportError as e:
        print(f"[插件系统] ⚠️ 跳过: {e}")

    # 5. 下载队列处理器
    if is_installed:
        await safe_run_async("下载队列处理器", _init_download_processor)

    yield

    # ---------- 关闭清理 ----------
    await safe_run_async("调度器停止", lambda: __import__('src.scheduler').session_scheduler.scheduler.stop())

    if is_installed:
        await safe_run_async("下载队列停止", _shutdown_download_processor)
        await safe_run_async("数据库连接关闭", _close_database)


async def _init_database():
    from src.utils.database.unified_manager import db_manager
    db_manager.initialize()


async def _start_scheduled_publisher():
    from src.utils.database.unified_manager import db_manager
    from shared.services.core.scheduler import start_scheduler, init_scheduler
    init_scheduler(db_manager.async_session_factory, check_interval=60)
    await start_scheduler()


def _init_plugins():
    try:
        from shared.services.plugins.plugin_manager import initialize_plugins
        return initialize_plugins()
    except ImportError as e:
        print(f"[插件系统] 导入失败: {e}")
        return None


async def _init_download_processor():
    from shared.services.media.download_queue_processor import init_download_processor
    await init_download_processor()


async def _shutdown_download_processor():
    from shared.services.media.download_queue_processor import shutdown_download_processor
    await shutdown_download_processor()


async def _close_database():
    from src.utils.database.unified_manager import db_manager
    await db_manager.close()


# ---------- 中间件注册 ----------
def register_middleware(app: FastAPI):
    """统一注册所有中间件（调试、安全、缓存等）"""
    # 获取 worker 信息（用于日志）
    from src.setting import _get_worker_info
    worker_info = _get_worker_info()
    
    # CORS（从环境变量或默认值）
    from fastapi.middleware.cors import CORSMiddleware
    origins_env = os.environ.get('CORS_ORIGINS', '')
    if origins_env:
        allow_origins = [o.strip() for o in origins_env.replace(';', ',').split(',') if o.strip()]
    else:
        allow_origins = ["http://localhost:3000", "http://127.0.0.1:3000",
                         "http://localhost:9421", "http://127.0.0.1:9421"]
    if "*" in allow_origins:
        allow_origins = [o for o in allow_origins if o != "*"] or ["http://localhost:3000"]

    print(f"[CORS] 允许源: {allow_origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "Cookie", "X-Requested-With"],
        expose_headers=["Content-Length", "X-Total-Count"],
    )

    # 统一调试中间件
    class DebugMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            url = str(request.url)
            if "/sensitive-words" in url:
                print(f"\n[DEBUG] 请求: {request.method} {url}")
                print(f"[DEBUG] Headers: {dict(request.headers)}")
                if request.method == "POST":
                    try:
                        # 先读取 body
                        body = await request.body()
                        print(f"[DEBUG] Body: {body.decode('utf-8')}")

                        # 重要：将 body 重新设置回 request，以便后续 endpoint 可以读取
                        async def receive():
                            return {"type": "http.request", "body": body}

                        request._receive = receive
                    except Exception as e:
                        print(f"[DEBUG] 无法读取 body: {e}")
            response = await call_next(request)
            if "/sensitive-words" in url and response.status_code == 422:
                print(f"[DEBUG] 422 响应: {response.status_code}")
            return response

    app.add_middleware(DebugMiddleware)

    # WebSocket 调试（简化）
    class WSDebugMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.headers.get("upgrade", "").lower() == "websocket" and "/collaboration/ws/" in str(request.url):
                print(f"[WS DEBUG] 连接尝试: {request.url}")
            return await call_next(request)

    app.add_middleware(WSDebugMiddleware)

    # HTTP 缓存
    try:
        from src.middleware.http_cache_middleware import HttpCacheMiddleware
        app.add_middleware(HttpCacheMiddleware, enable_etag=True, enable_last_modified=True,
                           default_cache_ttl=300, skip_methods=['POST', 'PUT', 'DELETE', 'PATCH'])
        print("[HTTP Cache] 已添加")
    except ImportError:
        pass

    # 安全中间件
    try:
        from src.auth.security_middleware import create_security_middleware_stack
        create_security_middleware_stack(app, rate_limit_requests=100, rate_limit_window=60)
    except ImportError:
        pass

    # 速率限制
    try:
        from src.middleware.rate_limit_middleware import RateLimitMiddleware
        app.add_middleware(RateLimitMiddleware)
    except ImportError:
        pass

    # 多站点
    try:
        from src.middleware.multisite_middleware import MultiSiteMiddleware
        app.add_middleware(MultiSiteMiddleware)
    except ImportError:
        pass


# ---------- 错误处理与静态文件 ----------
def register_error_handlers(app: FastAPI):
    """注册全局错误处理器和 SPA 回退"""

    @app.get("/health", tags=["system"])
    async def health_check():
        # 原逻辑简化
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    @app.get('/{full_path:path}', response_class=HTMLResponse)
    async def spa_fallback(request: Request, full_path: str):
        excluded = ['api', 'static', 'local-storage', 'storage', 'shared', 'thumbnail',
                    'login', 'register', 'auth', 'health', 'docs', 'redoc', 'openapi.json',
                    'admin', 'user', 'users', 'articles', 'categories', 'media', 'profile', 'setting']
        if any(full_path.startswith(p) for p in excluded):
            return PlainTextResponse("Not Found", status_code=404)
        try:
            frontend_index = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
            if os.path.exists(frontend_index):
                with open(frontend_index, "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())
        except Exception:
            pass
        return HTMLResponse(
            content="<!DOCTYPE html><html><head><title>Blog</title></head><body><div id='app'></div></body></html>")

    # 全局路由兜底
    @app.get("/{path:path}")
    @app.post("/{path:path}")
    @app.put("/{path:path}")
    @app.delete("/{path:path}")
    async def catch_all(request: Request, path: str):
        raise HTTPException(status_code=404, detail="Not Found")

    @app.exception_handler(401)
    async def unauthorized_handler(request: Request, exc: HTTPException):
        if request.url.path.startswith('/api/') or 'application/json' in request.headers.get('accept', ''):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"detail": exc.detail})
        return RedirectResponse(url=f"/login?next={request.url}")

    @app.exception_handler(404)
    async def custom_404_handler(request: Request, exc: HTTPException):
        try:
            from shared.services.plugins.plugin_manager import plugin_hooks
            error_data = {
                'url': str(request.url),
                'ip': request.client.host if request.client else '',
                'method': request.method,
                'timestamp': datetime.now().isoformat(),
            }
            # 同步触发
            plugin_hooks.do_action_sync('response_404', error_data)
            response_data = plugin_hooks.apply_filters('response_404', error_data)
            if isinstance(response_data, dict) and response_data.get('intercepted'):
                return HTMLResponse(content=response_data.get('html_content', ''),
                                    status_code=response_data.get('status_code', 404))
        except Exception as e:
            print(f"[Plugin] 404 hook error: {e}")
        from src.error import error
        return error(404, "Page Not Found")

    @app.exception_handler(500)
    async def custom_500_handler(request: Request, exc: HTTPException):
        from src.error import error
        return error(500, "Internal Server Error")

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logging.getLogger(__name__).error(f"General error: {exc}")
        if any(kw in str(exc).lower() for kw in ["not found", "no result", "does not exist"]):
            from src.error import error
            return error(404, "Page Not Found")
        from src.error import error
        return error(500, "Internal Server Error")


# ---------- 应用工厂 ----------
def create_app(config=None):
    """创建 FastAPI 应用实例"""
    if config is None:
        from src.setting import ProductionConfig
        config = ProductionConfig()

    # 获取 worker 信息（用于日志）
    from src.setting import _get_worker_info
    worker_info = _get_worker_info()

    # OpenAPI 元数据（精简但保留核心内容）
    app = FastAPI(
        title="FastBlog API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # 注册中间件
    register_middleware(app)

    # 注册所有 API 路由
    register_all_routes(app, worker_info)

    # 静态文件挂载
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # 本地存储
    try:
        from src.setting import app_config
        local_storage = getattr(app_config, 'LOCAL_STORAGE_PATH', 'storage')
    except Exception:
        local_storage = 'storage'
    os.makedirs(local_storage, exist_ok=True)
    app.mount("/local-storage", StaticFiles(directory=local_storage), name="local-storage")

    objects_dir = os.path.join(local_storage, 'objects')
    os.makedirs(objects_dir, exist_ok=True)
    app.mount("/storage/objects", StaticFiles(directory=objects_dir), name="storage-objects")

    themes_dir = os.path.join(os.path.dirname(__file__), "..", "themes")
    if os.path.exists(themes_dir):
        app.mount("/themes", StaticFiles(directory=themes_dir), name="themes")

    # 错误处理和 SPA 回退
    register_error_handlers(app)

    return app


# 全局 app 实例（供 uvicorn 直接使用）
try:
    app = create_app()
except Exception as e:
    traceback.print_exc()
    app = None
