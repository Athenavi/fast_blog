"""
FastBlog 应用入口
"""
import asyncio
import importlib
import os
import time as _time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

from src.unified_logger import logger


# ---------- 工具函数 ----------
def safe_run(func_name: str, func, *args, **kwargs):
    """安全执行同步/异步初始化，统一日志输出"""
    logger.info(f"[{func_name}] 开始初始化...")
    try:
        result = func(*args, **kwargs)
        logger.info(f"[{func_name}] 完成")
        return result
    except Exception as e:
        logger.error(f"[{func_name}] 失败: {e}")
        logger.exception(f"[{func_name}] 详细错误")
        return None


async def safe_run_async(func_name: str, func, *args, **kwargs):
    """安全执行异步初始化"""
    logger.info(f"[{func_name}] 开始初始化...")
    try:
        # 直接调用函数，如果是协程函数会自动返回协程对象
        result = func(*args, **kwargs)
        # 如果结果是协程，则等待它
        if hasattr(result, '__await__'):
            await result
        logger.info(f"[{func_name}] 完成")
        return result
    except Exception as e:
        logger.error(f"[{func_name}] 失败: {e}")
        logger.exception(f"[{func_name}] 详细错误")
        return None


def check_installation() -> bool:
    """检查系统是否已安装"""
    try:
        from shared.services.install.install_manager import installation_wizard_service
        installed = installation_wizard_service.is_installed()
        if not installed:
            logger.info("系统尚未安装，请启动前端进程后访问 http://localhost:4321/install 完成安装向导")
        return installed
    except Exception as e:
        logger.warning(f"检查安装状态失败: {e}")
        return False


# ---------- 路由注册 ----------


def register_all_routes(app: FastAPI, worker_info: str):
    """注册 v3 路由（唯一权威 API 层；v2 已于 T5-12 下线移除）"""

    # 注册 v3 路由
    # fail-fast：模块导入失败或路由冲突都会中止启动，避免"半成品 router 继续提供服务"
    # （对应 FastApiAdmin core/discover.py 的两条工程原则）
    logger.info(f"{worker_info} {'=' * 60}")
    logger.info(f"{worker_info} 开始注册 API v3 路由...")
    routes_start = _time.monotonic()
    from src.api.v3 import register_v3_routes

    v3_summary = register_v3_routes(app)
    logger.info(
        f"{worker_info} API v3 路由注册完成 (路由: {v3_summary['routes']}, "
        f"域: {len(v3_summary['domains'])}, 耗时: {_time.monotonic() - routes_start:.2f}s)"
    )

    # P4：启动期权限审计
    #   1) 写操作端点必须声明权限码，否则须在 EXEMPT_WRITE_ENDPOINTS 中显式承认
    #   2) 端点用到的权限码必须已登记在 codes.CODE_LABELS
    # 默认只告警（便于渐进修复）；设 PERMISSION_AUDIT_STRICT=1 则问题即拒绝启动
    try:
        from src.api.v3.core.permission.audit import audit_permissions

        strict = os.getenv("PERMISSION_AUDIT_STRICT", "").strip().lower() in {"1", "true", "yes"}
        audit_permissions(app, strict=strict)
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"{worker_info} 权限审计执行失败（不影响启动）：{exc}")


# ---------- 生命周期 ----------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理（结构化）"""
    lifespan_start = _time.monotonic()

    # 1. 安装状态检查
    step_start = _time.monotonic()
    is_installed = check_installation()
    logger.info(f"[lifespan] 安装检查耗时: {_time.monotonic() - step_start:.2f}s")

    # 2. 数据库管理器（仅安装后）
    if is_installed:
        step_start = _time.monotonic()
        await safe_run_async("数据库管理器", _init_database)
        logger.info(f"[lifespan] 数据库初始化耗时: {_time.monotonic() - step_start:.2f}s")

    # 3. 扩展、调度器
    try:
        from src.extensions import init_extensions
        step_start = _time.monotonic()
        safe_run("扩展初始化", lambda: init_extensions(app))
        logger.info(f"[lifespan] 扩展初始化耗时: {_time.monotonic() - step_start:.2f}s")
    except ImportError as e:
        logger.warning(f"[扩展初始化] 跳过: {e}")

    try:
        from src.scheduler import init_scheduler
        step_start = _time.monotonic()
        safe_run("调度器初始化", lambda: init_scheduler(app))
        logger.info(f"[lifespan] 调度器初始化耗时: {_time.monotonic() - step_start:.2f}s")
    except ImportError as e:
        logger.warning(f"[调度器初始化] 跳过: {e}")

    if is_installed:
        # 定时发布由 SessionScheduler（src/scheduler.py，每 5 分钟）统一处理，
        # 已移除独立的 shared.services.core.scheduler 60s 循环，避免双触发竞态。
        pass

    # 4. 插件系统
    try:
        step_start = _time.monotonic()
        safe_run("插件系统", _init_plugins)
        logger.info(f"[lifespan] 插件系统耗时: {_time.monotonic() - step_start:.2f}s")
    except ImportError as e:
        logger.warning(f"[插件系统] 跳过: {e}")

    # 4.5 审计日志订阅者（依赖 EventBus，需在插件之后）
    try:
        step_start = _time.monotonic()
        from shared.services.security.audit_subscriber import register_audit_subscriber
        register_audit_subscriber()
        logger.info(f"[lifespan] 审计日志订阅者注册耗时: {_time.monotonic() - step_start:.2f}s")
    except ImportError as e:
        logger.warning(f"[审计日志订阅者] 跳过: {e}")

    # 5. 下载队列处理器
    if is_installed:
        step_start = _time.monotonic()
        await safe_run_async("下载队列处理器", _init_download_processor)
        logger.info(f"[lifespan] 下载队列处理器耗时: {_time.monotonic() - step_start:.2f}s")

    # 6. 权限缓存预热 + 广播订阅
    if is_installed:
        step_start = _time.monotonic()
        await safe_run_async("权限缓存预热", _warm_permission_cache)
        logger.info(f"[lifespan] 权限缓存预热耗时: {_time.monotonic() - step_start:.2f}s")
        # 启动 Redis 广播订阅（后台任务）
        asyncio.ensure_future(_start_redis_subscriber())
        logger.info("[lifespan] Redis 广播订阅已启动")

    total_elapsed = _time.monotonic() - lifespan_start
    logger.info(f"[lifespan] 应用启动完成，总耗时: {total_elapsed:.2f}s")

    yield

    # ---------- 关闭清理 ----------
    await safe_run_async("调度器停止", lambda: __import__('src.scheduler').session_scheduler.scheduler.shutdown())

    if is_installed:
        await safe_run_async("下载队列停止", _shutdown_download_processor)
    await safe_run_async("数据库连接关闭", _close_database)


async def _init_database():
    from src.utils.database.unified_manager import db_manager
    db_manager.initialize()


def _init_plugins():
    try:
        from shared.services.plugins.plugin_manager.init import initialize_plugins
        return initialize_plugins()
    except ImportError as e:
        logger.warning(f"[插件系统] 导入失败: {e}")
        return None


async def _init_download_processor():
    from shared.services.media.download_queue_processor import init_download_processor
    await init_download_processor()


async def _warm_permission_cache():
    """预热超级管理员的权限缓存，避免首请求冷启动 DB 查询"""
    try:
        from sqlalchemy import select
        from shared.models.user import User
        from shared.models.rbac import Capability
        from src.api.v3.core.permission import memory_cache
        from src.utils.database.unified_manager import db_manager

        async with db_manager.get_session() as db:
            # 找出所有 superuser
            result = await db.execute(
                select(User.id).where(User.is_superuser, User.is_active)
            )
            superadmin_ids = [row[0] for row in result.all()]

            if not superadmin_ids:
                return

            # 加载所有 capability codes
            caps_result = await db.execute(select(Capability.code))
            all_codes = {row[0] for row in caps_result.all() if row[0]}

            # 预写入内存缓存
            for uid in superadmin_ids:
                await memory_cache.set(uid, frozenset(all_codes))

        logger.info(f"[lifespan] 权限缓存预热: {len(superadmin_ids)} 个超级管理员, {len(all_codes)} 个权限代码")
    except Exception as e:
        logger.info(f"[lifespan] 权限缓存预热跳过: {e}")


def _enable_redis_caches():
    """多 worker 场景：将全局缓存后端切换到 Redis（失败静默降级内存）"""
    try:
        from shared.config.settings import settings as _st
        import redis as _redis

        host = getattr(_st, 'REDIS_HOST', 'localhost') or 'localhost'
        port = int(getattr(_st, 'REDIS_PORT', 6379) or 6379)
        db = int(getattr(_st, 'REDIS_DB', 0) or 0)
        password = getattr(_st, 'REDIS_PASSWORD', None) or None

        from shared.services.core.cache_service import cache_service
        cache_service.use_redis = True
        cache_service.key_prefix = 'fastblog:'
        cache_service.redis_client = _redis.Redis(
            host=host, port=port, db=db, password=password,
            decode_responses=True, socket_connect_timeout=3, socket_timeout=3,
        )

        from shared.services.core.multi_level_cache import multi_level_cache
        multi_level_cache.redis_enabled = True

        logger.info("[CacheService] 已启用 Redis 共享缓存后端（多 worker）")
    except Exception as e:
        logger.warning(f"[CacheService] 启用 Redis 缓存后端失败，继续使用内存缓存: {e}")


async def _start_redis_subscriber():
    """启动 Redis 缓存广播订阅（后台任务，失败不阻塞）"""
    # 1. 先建立共享 Redis 连接，再启动各订阅者（订阅依赖已连接的客户端）
    try:
        from src.services.redis_service import redis_service
        if redis_service._redis is None:
            await redis_service.connect()
        await redis_service.start_cache_invalidation_listener()
        _enable_redis_caches()
        logger.info("[lifespan] Redis cache:invalidate 监听已启动")
    except Exception as e:
        logger.info(f"[lifespan] Redis cache:invalidate 监听启动失败: {e}")

    # 2. 连接就绪后再启动权限缓存广播订阅（后台常驻任务，不能直接 await）
    try:
        from src.api.v3.core.permission import start_invalidate_subscriber
        start_invalidate_subscriber()
    except Exception as e:
        logger.info(f"[lifespan] Redis 广播订阅启动失败: {e}")


async def _shutdown_download_processor():
    from shared.services.media.download_queue_processor import shutdown_download_processor
    await shutdown_download_processor()


async def _close_database():
    from src.utils.database.unified_manager import db_manager
    await db_manager.close()


# ---------- 中间件注册 ----------
def _make_lazy_middleware(module_path: str, class_name: str):
    """创建惰性中间件代理类：首次实例化时才导入目标模块（避免启动时加载 psutil 等重依赖）"""
    _cache = {}

    class _LazyProxy:

        def __init__(self, app, **kwargs):
            if 'cls' not in _cache:
                mod = importlib.import_module(module_path)
                _cache['cls'] = getattr(mod, class_name)
            self._impl = _cache['cls'](app=app, **kwargs)

        async def __call__(self, scope, receive, send):
            return await self._impl(scope, receive, send)

    _LazyProxy.__name__ = f"Lazy_{class_name}"
    _LazyProxy.__qualname__ = f"_make_lazy_middleware.<locals>.Lazy_{class_name}"
    return _LazyProxy


def register_middleware(app: FastAPI):
    """统一注册所有中间件（调试、安全、缓存等）"""
    # 获取 worker 信息（用于日志）
    from starlette.middleware.base import BaseHTTPMiddleware

    # CORS（从环境变量或默认值）
    from fastapi.middleware.cors import CORSMiddleware
    origins_env = os.environ.get('CORS_ORIGINS', '')
    if origins_env:
        allow_origins = [o.strip() for o in origins_env.replace(';', ',').split(',') if o.strip()]
    else:
        allow_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:4321",
            "http://127.0.0.1:4321",
            "http://localhost:9421",
            "http://127.0.0.1:9421",
            "http://localhost"  # Capacitor Android 模拟器
        ]
        if "*" in allow_origins:
            allow_origins = [o for o in allow_origins if o != "*"] or ["http://localhost:3000"]

    logger.info(f"[CORS] 允许源: {allow_origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "Cookie", "X-Requested-With"],
        expose_headers=["Content-Length", "X-Total-Count"],
    )

    # 统一调试中间件（仅 DEBUG 环境启用，避免生产环境打印敏感请求头/请求体）
    from shared.config.settings import app_config as _app_cfg
    _debug_enabled = bool(getattr(_app_cfg, 'DEBUG', False))

    if _debug_enabled:
        class DebugMiddleware(BaseHTTPMiddleware):

            async def dispatch(self, request, call_next):
                url = str(request.url)
                if "/sensitive-words" in url:
                    logger.debug(f"请求: {request.method} {url}")
                    logger.debug(f"Headers: {dict(request.headers)}")
                    if request.method == "POST":
                        try:
                            # 先读取 body
                            body = await request.body()
                            logger.debug(f"Body: {body.decode('utf-8')}")

                            # 重要：将 body 重新设置回 request，以便后续 endpoint 可以读取
                            async def receive():
                                return {"type": "http.request", "body": body}

                            request._receive = receive
                        except Exception as e:
                            logger.debug(f"无法读取 body: {e}")
                response = await call_next(request)
                if "/sensitive-words" in url and response.status_code == 422:
                    logger.debug(f"422 响应: {response.status_code}")
                return response

        app.add_middleware(DebugMiddleware)

        # WebSocket 调试（简化）
        class WSDebugMiddleware(BaseHTTPMiddleware):

            async def dispatch(self, request, call_next):
                if request.headers.get("upgrade", "").lower() == "websocket" and "/collaboration/ws/" in str(request.url):
                    logger.debug(f"WS 连接尝试: {request.url}")
                return await call_next(request)

        app.add_middleware(WSDebugMiddleware)

    # HTTP 缓存
    try:
        from src.middleware.http_cache_middleware import HttpCacheMiddleware
        app.add_middleware(HttpCacheMiddleware, enable_etag=True, enable_last_modified=True,
                           default_cache_ttl=300, skip_methods=['POST', 'PUT', 'DELETE', 'PATCH'])
        logger.info("[HTTP Cache] 已添加")
    except ImportError:
        pass

    # 速率限制中间件（基于 shared/services/security/rate_limiter.py）
    try:
        from shared.services.security.rate_limiter import rate_limit_middleware as _rate_limit_fn
        from starlette.middleware.base import BaseHTTPMiddleware

        class RateLimitMiddleware(BaseHTTPMiddleware):

            async def dispatch(self, request, call_next):
                return await _rate_limit_fn(request, call_next)

        app.add_middleware(RateLimitMiddleware)
        logger.info("[Rate Limit] 已添加")
    except ImportError as e:
        logger.warning(f"[Rate Limit] 加载失败: {e}")
    except Exception as e:
        logger.warning(f"[Rate Limit] 注册异常: {e}")

    # RBAC 路径映射中间件已移除：权限改由路由级 AuthPermission 声明，
    # 不再保留第二套“路径正则 → 权限码”机制（其 27 条路径早已失效）。

    # API 版本响应头
    class APIVersionMiddleware(BaseHTTPMiddleware):

        async def dispatch(self, request, call_next):
            response = await call_next(request)
            response.headers["API-Version"] = "v2"
            return response

    # 安全响应头中间件：X-Frame-Options / CSP / Permissions-Policy / Referrer-Policy
    class SecurityHeadersMiddleware(BaseHTTPMiddleware):

        async def dispatch(self, request, call_next):
            response = await call_next(request)
            # 非错误响应和非文件响应时添加安全头
            if response.status_code < 400:
                response.headers.setdefault("X-Frame-Options", "DENY")
                response.headers.setdefault("X-Content-Type-Options", "nosniff")
                response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
                # CSP: 防御 XSS 和注入攻击。'unsafe-inline' + 'unsafe-eval' 是
                # 给部分应用（如编辑器、Admin 面板）的最低妥协，生产环境可进一步收紧。
                response.headers.setdefault("Content-Security-Policy",
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: blob:; "
                    "font-src 'self' data:; "
                    "connect-src 'self' ws: wss:; "
                    "frame-ancestors 'none'; "
                    "form-action 'self'; "
                    "base-uri 'self'"
                )
                response.headers.setdefault("Permissions-Policy",
                    "geolocation=(), microphone=(), camera=(), payment=()"
                )
                if "X-XSS-Protection" not in response.headers:
                    response.headers["X-XSS-Protection"] = "1; mode=block"
            return response

    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("[Security Headers] X-Frame-Options / CSP / Permissions-Policy / Referrer-Policy 已添加")

    app.add_middleware(APIVersionMiddleware)
    logger.info("[API Version] 已添加版本响应头中间件")

    # 性能监控中间件（惰性加载：避免启动时 import psutil）
    try:
        app.add_middleware(
            _make_lazy_middleware("src.middleware.performance_monitor", "RequestPerformanceMiddleware")
        )
        logger.info("[Performance Monitor] 已添加性能监控中间件（惰性加载）")
    except Exception as e:
        logger.warning(f"[Performance Monitor] 加载失败: {e}")

    # 多站点（惰性加载：避免启动时导入 Site 模型）
    try:
        app.add_middleware(
            _make_lazy_middleware("src.middleware.multisite_middleware", "MultiSiteMiddleware")
        )
    except Exception:
        pass

    # Token 黑名单中间件
    try:
        from src.middleware.token_blacklist_middleware import TokenBlacklistMiddleware
        app.add_middleware(TokenBlacklistMiddleware)
        logger.info("[Token Blacklist] 已添加 Token 黑名单中间件")
    except Exception as e:
        logger.warning(f"[Token Blacklist] 加载失败: {e}")

    # 暴力破解防护中间件（阈值可用环境变量调整，默认 10 次/15 分钟每 IP、5 次/每用户名）
    try:
        from src.middleware.brute_force_protection import BruteForceProtectionMiddleware
        app.add_middleware(
            BruteForceProtectionMiddleware,
            max_attempts_per_ip=int(os.environ.get('BRUTE_FORCE_MAX_PER_IP', '10')),
            max_attempts_per_user=int(os.environ.get('BRUTE_FORCE_MAX_PER_USER', '5')),
        )
        logger.info("[Brute Force] 已添加暴力破解防护中间件")
    except Exception as e:
        logger.warning(f"[Brute Force] 加载失败: {e}")


# ---------- 错误处理与静态文件 ----------
def register_error_handlers(app: FastAPI):
    """注册全局错误处理器和 SPA 回退"""

    def _is_api_request(request: Request) -> bool:
        """判断是否为 API 请求（需要 JSON 响应）"""
        path = request.url.path
        if path.startswith('/api/'):
            return True
        accept = request.headers.get('accept', '')
        return 'application/json' in accept or 'text/plain' in accept

    def _api_error_response(status_code: int, message: str) -> JSONResponse:
        """统一 API 错误响应格式"""
        from src.api.common.api_response import ApiResponse
        return JSONResponse(
            status_code=status_code,
            content=ApiResponse(success=False, error=message).model_dump()
        )

    @app.get("/api/v3/health", tags=["system"])
    async def health_check():
        # 原逻辑简化
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    @app.get("/sitemap.xml", include_in_schema=False)
    async def root_sitemap():
        """站点地图根路径 — 301 到动态 sitemap"""
        return RedirectResponse(url="/api/v3/analytics/seo/sitemap/sitemap.xml", status_code=301)

    @app.get("/sitemap-posts.xml", include_in_schema=False)
    async def root_sitemap_posts():
        return RedirectResponse(url="/api/v3/analytics/seo/sitemap/sitemap-posts.xml", status_code=301)

    @app.get("/sitemap-categories.xml", include_in_schema=False)
    async def root_sitemap_categories():
        return RedirectResponse(url="/api/v3/analytics/seo/sitemap/sitemap-categories.xml", status_code=301)

    @app.get("/sitemap-tags.xml", include_in_schema=False)
    async def root_sitemap_tags():
        return RedirectResponse(url="/api/v3/analytics/seo/sitemap/sitemap-tags.xml", status_code=301)

    @app.get("/sitemap-pages.xml", include_in_schema=False)
    async def root_sitemap_pages():
        return RedirectResponse(url="/api/v3/analytics/seo/sitemap/sitemap-pages.xml", status_code=301)

    @app.get("/sitemap-multilingual.xml", include_in_schema=False)
    async def root_sitemap_multilingual():
        return RedirectResponse(url="/api/v3/analytics/seo/sitemap/sitemap-multilingual.xml", status_code=301)

    @app.get("/sitemap-authors.xml", include_in_schema=False)
    async def root_sitemap_authors():
        return RedirectResponse(url="/api/v3/analytics/seo/sitemap/sitemap-authors.xml", status_code=301)

    @app.get("/sitemap-images.xml", include_in_schema=False)
    async def root_sitemap_images():
        return RedirectResponse(url="/api/v3/analytics/seo/sitemap/sitemap-images.xml", status_code=301)

    @app.get("/sitemap-videos.xml", include_in_schema=False)
    async def root_sitemap_videos():
        return RedirectResponse(url="/api/v3/analytics/seo/sitemap/sitemap-videos.xml", status_code=301)

    @app.get("/robots.txt", include_in_schema=False)
    async def robots_txt(request: Request):
        """robots.txt — 搜索引擎爬取规则"""
        from fastapi.responses import PlainTextResponse
        site_url = str(request.base_url).rstrip("/")
        content = f"""User-agent: *
Allow: /

Sitemap: {site_url}/sitemap.xml
"""
        return PlainTextResponse(content=content, media_type="text/plain")

    @app.exception_handler(401)
    async def unauthorized_handler(request: Request, exc: HTTPException):
        if _is_api_request(request):
            return _api_error_response(401, exc.detail)
        return RedirectResponse(url=f"/login?next={request.url}")

    @app.exception_handler(403)
    async def forbidden_handler(request: Request, exc: HTTPException):
        if _is_api_request(request):
            return _api_error_response(403, exc.detail)
        from src.api.common.api_response import ApiResponse
        return JSONResponse(
            status_code=403,
            content=ApiResponse(success=False, error=exc.detail).model_dump()
        )

    @app.exception_handler(404)
    async def custom_404_handler(request: Request, exc: HTTPException):
        # 1. 尝试 EventBus 事件拦截
        try:
            from shared.services.plugins.event_bus import event_bus
            error_data = {
                'url': str(request.url),
                'ip': request.client.host if request.client else '',
                'method': request.method,
                'timestamp': datetime.now().isoformat(),
            }
            await event_bus.emit('response.404', error_data)
            response_data = await event_bus.pipeline('response.404', error_data)
            if isinstance(response_data, dict) and response_data.get('intercepted'):
                return HTMLResponse(content=response_data.get('html_content', ''),
                                    status_code=response_data.get('status_code', 404))
        except Exception as e:
            logger.warning(f"[Plugin] 404 hook error: {e}")

        # 2. API 请求返回 JSON
        if _is_api_request(request):
            return _api_error_response(404, "Page Not Found")

        # 3. 非 API 路径尝试返回前端 SPA 页面
        excluded_prefixes = ['api/v3/static/', 'api/v3/assets/', 'api/v3/docs', 'api/v3/redoc', 'api/v3/openapi.json',
                             'api/v3/health']
        if not any(request.url.path.lstrip('/').startswith(prefix) for prefix in excluded_prefixes):
            try:
                frontend_index = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
                if os.path.exists(frontend_index):
                    with open(frontend_index, "r", encoding="utf-8") as f:
                        return HTMLResponse(content=f.read())
            except Exception:
                pass
            # 默认返回一个简单的SPA模板
            return HTMLResponse(
                content="<!DOCTYPE html><html><head><title>Blog</title></head><body><div id='app'></div></body></html>")

        from src.error import error
        return error(404, "Page Not Found")

    @app.exception_handler(422)
    async def validation_error_handler(request: Request, exc: Exception):
        """处理 FastAPI 请求验证错误"""
        if _is_api_request(request):
            from fastapi.exceptions import RequestValidationError
            if isinstance(exc, RequestValidationError):
                errors = exc.errors()
                # 提取有意义的错误消息
                first = errors[0] if errors else {}
                field = " → ".join(str(p) for p in first.get("loc", [])) if first.get("loc") else ""
                msg = first.get("msg", "Validation error") if first else "Validation error"
                detail = f"'{field}' {msg}" if field else msg
                return _api_error_response(422, detail)
            return _api_error_response(422, "Validation Error")
        raise exc

    @app.exception_handler(500)
    async def custom_500_handler(request: Request, exc: HTTPException):
        if _is_api_request(request):
            return _api_error_response(500, "Internal Server Error")
        from src.error import error
        return error(500, "Internal Server Error")

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"General error: {exc}")
        if any(kw in str(exc).lower() for kw in ["not found", "no result", "does not exist"]):
            if _is_api_request(request):
                return _api_error_response(404, "Page Not Found")
            from src.error import error
            return error(404, "Page Not Found")
        if _is_api_request(request):
            return _api_error_response(500, "Internal Server Error")
        from src.error import error
        return error(500, "Internal Server Error")


# ---------- 应用工厂 ----------
def create_app(config=None):
    """创建 FastAPI 应用实例"""
    app_start = _time.monotonic()

    if config is None:
        from shared.config.settings import ProductionConfig
        config = ProductionConfig()

    # 获取 worker 信息（用于日志）
    from shared.config.settings import _get_worker_info
    worker_info = _get_worker_info()

    # OpenAPI 元数据（精简但保留核心内容）
    # 生产环境（ENVIRONMENT=production）禁用 API 文档界面，避免泄露 API 结构信息
    _env = os.environ.get('ENVIRONMENT', 'development').lower()
    _is_production = (_env == 'production')
    app = FastAPI(
        title="FastBlog API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if _is_production else "/api/v3/docs",
        redoc_url=None if _is_production else "/api/v3/redoc",
        openapi_url=None if _is_production else "/api/v3/openapi.json",
        swagger_ui_oauth2_redirect_url=None if _is_production else "/api/v2/docs/oauth2-redirect",
    )

    # 注册中间件
    step_start = _time.monotonic()
    register_middleware(app)
    logger.info(f"{worker_info} [create_app] 中间件注册耗时: {_time.monotonic() - step_start:.2f}s")

    # 注册所有 API 路由
    step_start = _time.monotonic()
    register_all_routes(app, worker_info)
    logger.info(f"{worker_info} [create_app] 路由注册耗时: {_time.monotonic() - step_start:.2f}s")

    # 错误处理和 SPA 回退
    register_error_handlers(app)

    # 静态文件挂载 - 确保在所有路由注册之后挂载，避免被catch-all路由拦截
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/api/v3/static", StaticFiles(directory=static_dir), name="static")

    # 本地存储 - 受控文件下载（替代原先无鉴权的 StaticFiles 挂载，
    # 防止私密媒体 is_public=False 被匿名按路径下载；公开媒体仍可匿名访问）
    try:
        from shared.config.settings import app_config
        local_storage = getattr(app_config, 'LOCAL_STORAGE_PATH', 'storage')
    except Exception:
        local_storage = 'storage'
    os.makedirs(local_storage, exist_ok=True)

    import mimetypes
    import re as _re
    from pathlib import Path as _Path

    from fastapi.responses import FileResponse as _FileResponse
    from sqlalchemy import select as _select
    from src.auth import jwt_optional_dependency as _jwt_optional
    from src.utils.database.unified_manager import get_db_session as _get_async_db

    async def _serve_storage_asset(
        asset_path: str,
        current_user=Depends(_jwt_optional),
        db=Depends(_get_async_db),
    ):
        """
        受控文件服务：校验路径防止目录遍历；
        若目标文件对应数据库中的媒体且为私密(is_public=False)，则必须由登录用户本人
        访问，否则拒绝；公开媒体(匿名可访问)与其余文件保持原有行为。
        """
        storage_root = _Path(local_storage).resolve()
        target = (storage_root / asset_path).resolve()
        # 防目录遍历：解析后的路径必须仍位于 storage 根目录内
        if not str(target).startswith(str(storage_root)):
            raise HTTPException(status_code=403, detail="非法的文件路径")
        if not target.is_file():
            raise HTTPException(status_code=404, detail="文件不存在")

        # storage 内文件为内容寻址(sha256)，路径含文件哈希，据此反查媒体归属/公开状态
        m = _re.search(r'([0-9a-f]{64})', asset_path)
        if m:
            try:
                from shared.models.media import Media
                media = (await db.execute(
                    _select(Media).where(Media.hash == m.group(1))
                )).scalar_one_or_none()
                if media is not None and not getattr(media, 'is_public', True):
                    if current_user is None or getattr(current_user, 'id', None) != getattr(media, 'user', None):
                        raise HTTPException(status_code=403, detail="无权访问该媒体文件")
            except HTTPException:
                raise
            except Exception:
                logger.exception("校验媒体权限失败")
                raise HTTPException(status_code=500, detail="校验媒体权限失败")

        content_type, _ = mimetypes.guess_type(str(target))
        return _FileResponse(str(target), media_type=content_type)

    # 注册受控下载路由（媒体相关 URL 一律收敛到 /api/v3 之下）
    app.get("/api/v3/assets/storage/{asset_path:path}", name="local-storage")(_serve_storage_asset)

    themes_dir = os.path.join(os.path.dirname(__file__), "..", "themes")
    if os.path.exists(themes_dir):
        app.mount("/api/v3/assets/themes", StaticFiles(directory=themes_dir), name="themes")

    app_elapsed = _time.monotonic() - app_start
    logger.info(f"{worker_info} [create_app] 应用工厂完成，总耗时: {app_elapsed:.2f}s")

    return app


# 全局 app 实例（供 uvicorn 直接使用）
try:
    app = create_app()
except Exception as e:
    logger.error(f"Failed to create app: {e}")
    logger.exception("Failed to create app traceback")
    app = None
