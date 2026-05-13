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

# ---------- Django 初始化 ----------
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_blog.settings')
import django

if not hasattr(django, '_setup_complete') or not django.apps.apps.ready:
    try:
        django.setup()
        django._setup_complete = True
    except RuntimeError as e:
        if "populate() isn't reentrant" not in str(e):
            raise


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


async def safe_run_async(func_name: str, coro_or_func, *args, **kwargs):
    """安全执行异步初始化"""
    print(f"\n{'=' * 60}\n[{func_name}] 开始初始化...")
    try:
        if hasattr(coro_or_func, '__await__'):
            result = await coro_or_func(*args, **kwargs)
        else:
            result = coro_or_func(*args, **kwargs)
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
    ("src.api.v1.users", "/api/v1/users", ["users"], True),
    ("src.api.v1.user_management", "/api/v1", ["user-management"], True),
    ("src.api.v1", "", [], True),  # api_v1_router 内部自带前缀
    ("src.api.v1.category_management", "/api/v1/categories", ["categories"], True),
    ("src.api.v1.dashboard", "/api/v1/dashboard", ["dashboard"], True),
    ("src.api.v1.home", "/api/v1", ["home"], True),
    # 功能模块（可选加载，失败仅警告）
    ("src.api.v1.batch_seo", "/api/v1/seo", ["batch-seo"], False),
    ("src.api.v1.seo_optimization", "/api/v1", ["seo-optimization"], False),
    ("src.api.v1.block_editor", "/api/v1", ["block-editor"], False),
    ("src.api.v1.graphql", "/graphql", ["graphql"], False),
    ("src.api.v1.article_search", "/api/v1", ["search"], False),
    ("src.api.v1.fulltext_search", "/api/v1", ["fulltext-search"], False),
    ("src.api.v1.resource_transfer", "/api/v1", ["resource-transfer"], False),
    ("src.api.v1.ai_recommendations", "/api/v1", ["ai"], False),
    ("src.api.v1.translations", "/api/v1", ["translations"], False),
    ("src.api.v1.localization", "/api/v1", ["localization"], False),
    ("src.api.v1.analytics", "/api/v1", ["analytics"], False),
    ("src.api.v1.user_profile", "/api/v1", ["user-profile"], False),
    ("src.api.v1.batch_operations", "/api/v1", ["batch"], False),
    ("src.api.v1.membership", "/api/v1", ["membership"], False),
    ("src.api.v1.websocket", "", [], False),  # WebSocket 无前缀
    ("src.api.v1.chat_groups", "/api/v1", ["chat-groups"], False),
    ("src.api.v1.collaboration", "/api/v1", [], False),
    ("src.api.v1.collaboration_invites", "/api/v1", [], False),
    ("src.api.v1.collaboration_save", "/api/v1", [], False),
    ("src.api.v1.yjs_collaboration", "/api/v1", [], False),
    ("src.api.v1.ecommerce_products", "/api/v1", [], False),
    ("src.api.v1.ecommerce_cart_orders", "/api/v1", [], False),
    ("src.api.v1.edge_functions", "/api/v1", ["edge-functions"], False),
    ("src.api.v1.scheduled_publish", "/api/v1", ["scheduled-publish"], False),
    ("src.api.v1.draft_preview", "/api/v1", ["draft-preview"], False),
    ("src.api.v1.custom_blocks", "/api/v1", ["custom-blocks"], False),
    ("src.api.v1.nft", "/api/v1", ["nft"], False),
    ("src.api.v1.audit_log", "/api/v1/audit-log", ["audit-log"], False),
    ("src.api.v1.query_optimization", "/api/v1/query-optimization", ["query-optimization"], False),
    ("src.api.v1.page_cache", "/api/v1/page-cache", ["page-cache"], False),
    ("src.api.v1.object_cache", "/api/v1/object-cache", ["object-cache"], False),
    ("src.api.v1.resource_optimization", "/api/v1/resource-optimization", ["resource-optimization"], False),
    ("src.api.v1.image_lazy_load", "/api/v1/image-lazy-load", ["image-lazy-load"], False),
    ("src.api.v1.performance_monitor", "/api/v1/performance-monitor", ["performance-monitor"], False),
    ("src.api.v1.slow_query_log", "/api/v1/slow-query", ["slow-query"], False),
    ("src.api.v1.http2_config", "/api/v1/http2", ["http2"], False),
    ("src.api.v1.translation_progress", "/api/v1/translation", ["translation"], False),
    ("src.api.v1.anomaly_detection", "/api/v1/anomaly-detection", ["anomaly-detection"], False),
    ("src.api.v1.security_alert", "/api/v1/security-alert", ["security-alert"], False),
    ("src.api.v1.tipping_system", "/api/v1", ["tips"], False),
    ("src.api.v1.advertisement_system", "/api/v1", ["advertisements"], False),
    ("src.api.v1.security_report", "/api/v1/security-report", ["security-report"], False),
    ("src.api.v1.content_approval", "/api/v1/approval", ["approval"], False),
    ("src.api.v1.workflow", "/api/v1", ["workflows"], False),
    ("src.api.v1.backup_management", "/api/v1/backup", ["backup"], False),
    ("src.api.v1.load_balancer", "/api/v1", ["load-balancer"], False),
    ("src.api.v1.team_collaboration", "/api/v1", ["collaboration"], False),
    ("src.api.v1.rbac", "/api/v1", ["rbac"], False),
    ("src.api.v1.i18n", "/api/v1", ["i18n"], False),
    ("src.api.v1.multisite", "/api/v1", ["multisite"], False),
    ("src.api.v1.sso", "/api/v1", ["sso"], False),
    ("src.api.v1.team_comments", "/api/v1/team-comments", ["team-comments"], False),
    ("src.api.v1.rate_limit", "/api/v1/rate-limit", ["rate-limit"], False),
    ("src.api.v1.performance_tracking", "/api/v1/performance-tracking", ["performance-tracking"], False),
    ("src.api.v1.translation_io", "/api/v1/translation-io", ["translation-io"], False),
    ("src.api.v1.seo_management", "/api/v1/seo", ["seo"], False),
    ("src.api.v1.seo_tracking", "/api/v1", ["seo-tracking"], False),
    ("src.api.v1.report_management", "/api/v1", ["reports"], False),
    ("src.api.v1.incremental_backup", "/api/v1", ["incremental-backup"], False),
    ("src.api.v1.database_migration", "/api/v1", ["database-migration"], False),
    ("src.api.v1.gdpr_compliance", "/api/v1/gdpr", ["gdpr"], False),
    ("src.api.v1.accessibility_audit", "/api/v1/accessibility", ["accessibility"], False),
    ("src.api.v1.cdn_management", "/api/v1/cdn", ["cdn"], False),
    ("src.api.v1.ipfs", "/api/v1", ["ipfs"], False),
    ("src.api.v1.google_analytics", "/api/v1", ["google-analytics"], False),
    ("src.api.v1.baidu_analytics", "/api/v1", ["baidu-analytics"], False),
    ("src.api.v1.notification_integration", "/api/v1", ["notifications"], False),
    ("src.api.v1.email_service", "/api/v1", ["email-service"], False),
    ("src.api.v1.enterprise_auth", "/api/v1", ["enterprise-auth"], False),
]


def register_all_routes(app: FastAPI, worker_info: str):
    """根据配置表自动注册所有路由"""
    for module_path, prefix, tags, required in ROUTE_REGISTRY:
        try:
            mod = importlib.import_module(module_path)
            router = getattr(mod, "router", None)
            if router is None:
                raise AttributeError("No 'router' found")
            if prefix:
                app.include_router(router, prefix=prefix, tags=tags if tags else [])
            else:
                app.include_router(router)
            print(f"{worker_info} [OK] {module_path.split('.')[-1]} 已加载")
        except ImportError as e:
            if required:
                print(f"{worker_info} [ERROR] 必需模块加载失败: {module_path} - {e}")
                raise
            else:
                print(f"{worker_info} [Warning] {module_path} 未能加载: {e}")
        except Exception as e:
            if required:
                raise
            print(f"{worker_info} [Warning] {module_path} 注册异常: {e}")


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
    safe_run("扩展初始化", lambda: __import__('src.extensions').init_extensions(app))
    safe_run("调度器初始化", lambda: __import__('src.scheduler').init_scheduler(app))

    if is_installed:
        await safe_run_async("定时发布调度器", _start_scheduled_publisher)

    # 4. 插件系统
    safe_run("插件系统", _init_plugins)

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
    from shared.services.plugins.plugin_manager import initialize_plugins
    return initialize_plugins()


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
                        body = await request.body()
                        print(f"[DEBUG] Body: {body.decode('utf-8')}")
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
