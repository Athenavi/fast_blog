"""
FastBlog 应用入口
"""
import asyncio
import importlib
import os
import time as _time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
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
            print("👉 请启动前端进程后访问 http://localhost:4321/install 完成安装向导")
            print("=" * 60 + "\n")
        return installed
    except Exception as e:
        print(f"Warning: Failed to check installation status: {e}")
        return False


# ---------- 路由自动发现 ----------
# 注意：为了更好的兼容性保留 旧的 V1 路由注册表，已废弃，新功能请在V2中开发


def _load_single_module(module_path: str, required: bool):
    """并行加载单个模块并获取其 router（线程安全）"""
    mod_start = _time.monotonic()
    mod = importlib.import_module(module_path)
    router = getattr(mod, "router", None)
    mod_elapsed = _time.monotonic() - mod_start
    return module_path, router, mod_elapsed, required, None


def _load_single_module_safe(module_path: str, required: bool):
    """安全版本：捕获异常并返回错误信息"""
    try:
        return _load_single_module(module_path, required, )
    except Exception as e:
        return module_path, None, 0.0, required, e


def register_all_routes(app: FastAPI, worker_info: str):
    """注册 API v2 和 v3 路由（已移除 v1）"""

    # 注册 v2 路由（新规范）— 并行加载 + 顺序注册
    print(f"\n{worker_info} {'=' * 60}")
    print(f"{worker_info} 开始注册 API v2 路由...")
    routes_start = _time.monotonic()
    try:
        from src.api.v2 import ROUTE_REGISTRY_V2
        loaded_count = 0
        failed_count = 0

        # Phase 0: 预热 shared.models 子包，避免并行导入时 _DeadlockError
        # Python 的 import 系统对包 __init__.py 使用模块锁，
        # 多线程同时触发同一子包导入会产生死锁（如 collaboration/__init__.py）
        _prewarm_start = _time.monotonic()
        try:
            _shared_subpkgs = [
                'shared.models',
                'shared.models.article',
                'shared.models.collaboration',
                'shared.models.media',
                'shared.models.enterprise',
                'shared.models.security',
                'shared.models.user',
                'shared.models.comment',
                'shared.models.category',
                'shared.models.notification',
                'shared.models.chat',
                'shared.models.search',
                'shared.models.ecommerce',
                'shared.models.payment',
                'shared.models.revenue',
                'shared.models.rbac',
                'shared.models.system',
                'shared.models.analytics',
                'shared.models.integration',
                'shared.models.monitoring',
                'shared.models.migration',
                'shared.models.form',
                'shared.models.menu',
                'shared.models.page',
                'shared.models.theme',
                'shared.models.plugin',
                'shared.models.widget',
                'shared.models.vip',
                'shared.models.webhook',
                'shared.models.multisite',
                'shared.models.report',
                'shared.models.content',
                'shared.models.social',
                'shared.models.ad',
                'shared.models.ai',
                # 预热 auth_deps 避免并行加载时死锁
                'src.auth',
                'src.auth.auth_deps',
            ]
            for _pkg in _shared_subpkgs:
                importlib.import_module(_pkg)

            # 预热最常用的模型文件（不仅仅是包 __init__），避免并行加载时死锁
            _model_files = [
                'shared.models.user.user',
                'shared.models.article.article',
                'shared.models.category.category',
                'shared.models.comment.comment',
                'shared.models.media.media',
            ]
            for _mod in _model_files:
                try:
                    importlib.import_module(_mod)
                except Exception:
                    pass
            _prewarm_elapsed = _time.monotonic() - _prewarm_start
            print(f"{worker_info} 🔥 shared.models 预热完成 ({_prewarm_elapsed:.2f}s)")
        except Exception as _pw_err:
            print(f"{worker_info} [Warning] shared.models 预热失败: {_pw_err}")

        # Phase 1: 并行加载所有模块和路由器（ThreadPoolExecutor）
        # importlib + getattr(mod, "router") 触发 _build_router() 是 CPU/IO 密集操作，可并行
        load_start = _time.monotonic()
        load_results = []

        # 根据核心数自适应线程池大小，最少 4 最多 16
        max_workers = min(max(4, (os.cpu_count() or 4)), 16, len(ROUTE_REGISTRY_V2))

        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="route_loader") as executor:
            future_map = {
                executor.submit(_load_single_module_safe, module_path, required): module_path
                for module_path, prefix, tags, required in ROUTE_REGISTRY_V2
            }
            # 保持结果顺序与 ROUTE_REGISTRY_V2 一致
            result_by_path = {}
            for future in as_completed(future_map):
                result = future.result()
                result_by_path[result[0]] = result

            for module_path, prefix, tags, required in ROUTE_REGISTRY_V2:
                load_results.append((module_path, prefix, tags, result_by_path.get(module_path)))

        load_elapsed = _time.monotonic() - load_start
        print(f"{worker_info} 📦 模块并行加载完成 (线程池: {max_workers}, 耗时: {load_elapsed:.2f}s)")

        # Phase 2: 顺序注册路由器到 app（FastAPI include_router 非线程安全）
        register_start = _time.monotonic()
        for module_path, prefix, tags, result in load_results:
            if result is None:
                failed_count += 1
                print(f"{worker_info} [Warning] v2/{module_path} 未找到加载结果")
                continue

            _, router, mod_elapsed, req, error = result

            if error is not None:
                if req:
                    print(f"{worker_info} [ERROR] v2 必需模块加载失败: {module_path} - {error}")
                    raise error
                else:
                    failed_count += 1
                    print(f"{worker_info} [Warning] v2/{module_path} 未能加载: {error}")
                    continue

            if router is None:
                failed_count += 1
                print(f"{worker_info} [Warning] v2/{module_path} 未找到 router 属性")
                continue

            try:
                if prefix:
                    app.include_router(router, prefix=prefix, tags=tags if tags else [])
                else:
                    app.include_router(router)
                loaded_count += 1
                short_name = module_path.split('.')[-1]
                if mod_elapsed > 1.0:
                    print(f"{worker_info} [SLOW] v2/{short_name} 已加载 ({mod_elapsed:.2f}s)")
                else:
                    print(f"{worker_info} [OK] v2/{short_name} 已加载 ({mod_elapsed:.2f}s)")
            except Exception as e:
                if req:
                    raise
                failed_count += 1
                print(f"{worker_info} [Warning] v2/{module_path} 注册异常: {e}")

        routes_elapsed = _time.monotonic() - routes_start
        register_elapsed = _time.monotonic() - register_start
        print(f"{worker_info} ✅ API v2 路由注册完成 (成功: {loaded_count}, 失败: {failed_count}, "
              f"加载: {load_elapsed:.2f}s, 注册: {register_elapsed:.2f}s, 总耗时: {routes_elapsed:.2f}s)\n")
    except ImportError as e:
        print(f"{worker_info} [ERROR] API v2 模块未找到: {e}\n")
        raise

    # 注册 v3 路由（移动端专用）
    print(f"\n{worker_info} {'=' * 60}")
    print(f"{worker_info} 开始注册 API v3 路由（移动端）...")
    try:
        from src.api.v3 import register_v3_routes
        register_v3_routes(app)
        print(f"{worker_info} ✅ API v3 路由注册完成\n")
    except ImportError as e:
        print(f"{worker_info} [Warning] API v3 模块未找到，跳过: {e}\n")
    except Exception as e:
        print(f"{worker_info} [Warning] API v3 路由注册失败: {e}\n")


# ---------- 生命周期 ----------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理（结构化）"""
    lifespan_start = _time.monotonic()

    # 1. 安装状态检查
    step_start = _time.monotonic()
    is_installed = check_installation()
    print(f"[lifespan] 安装检查耗时: {_time.monotonic() - step_start:.2f}s")

    # 2. 数据库管理器（仅安装后）
    if is_installed:
        step_start = _time.monotonic()
        await safe_run_async("数据库管理器", _init_database)
        print(f"[lifespan] 数据库初始化耗时: {_time.monotonic() - step_start:.2f}s")

    # 2.5 懒加载系统初始化
    try:
        from src.utils.lazy_loader import init_lazy_loading
        step_start = _time.monotonic()
        safe_run("懒加载系统", init_lazy_loading)
        print(f"[lifespan] 懒加载系统耗时: {_time.monotonic() - step_start:.2f}s")
    except ImportError as e:
        print(f"[懒加载系统] ⚠️ 跳过: {e}")

    # 3. 扩展、调度器
    try:
        from src.extensions import init_extensions
        step_start = _time.monotonic()
        safe_run("扩展初始化", lambda: init_extensions(app))
        print(f"[lifespan] 扩展初始化耗时: {_time.monotonic() - step_start:.2f}s")
    except ImportError as e:
        print(f"[扩展初始化] ⚠️ 跳过: {e}")

    try:
        from src.scheduler import init_scheduler
        step_start = _time.monotonic()
        safe_run("调度器初始化", lambda: init_scheduler(app))
        print(f"[lifespan] 调度器初始化耗时: {_time.monotonic() - step_start:.2f}s")
    except ImportError as e:
        print(f"[调度器初始化] ⚠️ 跳过: {e}")

    if is_installed:
        step_start = _time.monotonic()
        await safe_run_async("定时发布调度器", _start_scheduled_publisher)
        print(f"[lifespan] 定时发布调度器耗时: {_time.monotonic() - step_start:.2f}s")

    # 4. 插件系统
    try:
        step_start = _time.monotonic()
        safe_run("插件系统", _init_plugins)
        print(f"[lifespan] 插件系统耗时: {_time.monotonic() - step_start:.2f}s")
    except ImportError as e:
        print(f"[插件系统] ⚠️ 跳过: {e}")

    # 4.5 审计日志订阅者（依赖 EventBus，需在插件之后）
    try:
        step_start = _time.monotonic()
        from shared.services.security.audit_subscriber import register_audit_subscriber
        register_audit_subscriber()
        print(f"[lifespan] 审计日志订阅者注册耗时: {_time.monotonic() - step_start:.2f}s")
    except ImportError as e:
        print(f"[审计日志订阅者] ⚠️ 跳过: {e}")

    # 5. 下载队列处理器
    if is_installed:
        step_start = _time.monotonic()
        await safe_run_async("下载队列处理器", _init_download_processor)
        print(f"[lifespan] 下载队列处理器耗时: {_time.monotonic() - step_start:.2f}s")

    # 6. 权限缓存预热 + 广播订阅
    if is_installed:
        step_start = _time.monotonic()
        await safe_run_async("权限缓存预热", _warm_permission_cache)
        print(f"[lifespan] 权限缓存预热耗时: {_time.monotonic() - step_start:.2f}s")
        # 启动 Redis 广播订阅（后台任务）
        asyncio.ensure_future(_start_redis_subscriber())
        print(f"[lifespan] Redis 广播订阅已启动")

    total_elapsed = _time.monotonic() - lifespan_start
    print(f"\n{'=' * 60}")
    print(f"[lifespan] 🚀 应用启动完成，总耗时: {total_elapsed:.2f}s")
    print(f"{'=' * 60}\n")

    yield

    # ---------- 关闭清理 ----------
    await safe_run_async("调度器停止", lambda: __import__('src.scheduler').session_scheduler.scheduler.shutdown())

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
        from shared.services.plugins.plugin_manager.init import initialize_plugins
        return initialize_plugins()
    except ImportError as e:
        print(f"[插件系统] 导入失败: {e}")
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
        from src.api.v3._permission import _memory_cache
        from src.utils.database.unified_manager import db_manager

        async with db_manager.get_async_session() as db:
            # 找出所有 superuser
            result = await db.execute(
                select(User.id).where(User.is_superuser == True, User.is_active == True)
            )
            superadmin_ids = [row[0] for row in result.all()]

            if not superadmin_ids:
                return

            # 加载所有 capability codes
            caps_result = await db.execute(select(Capability.code))
            all_codes = {row[0] for row in caps_result.all() if row[0]}

            # 预写入内存缓存
            for uid in superadmin_ids:
                await _memory_cache.set(uid, all_codes)

            print(f"[lifespan] 权限缓存预热: {len(superadmin_ids)} 个超级管理员, {len(all_codes)} 个权限代码")
    except Exception as e:
        print(f"[lifespan] 权限缓存预热跳过: {e}")


async def _start_redis_subscriber():
    """启动 Redis 缓存广播订阅（后台任务，失败不阻塞）"""
    try:
        from src.api.v3._permission import _redis_subscribe_invalidate
        await _redis_subscribe_invalidate()
    except Exception as e:
        print(f"[lifespan] Redis 广播订阅启动失败: {e}")

    # 启动通用缓存失效广播监听
    try:
        from src.services.redis_service import redis_service
        await redis_service.connect()
        await redis_service.start_cache_invalidation_listener()
        print(f"[lifespan] Redis cache:invalidate 监听已启动")
    except Exception as e:
        print(f"[lifespan] Redis cache:invalidate 监听启动失败: {e}")


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
                import importlib
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
    from src.setting import _get_worker_info
    worker_info = _get_worker_info()
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
    # 速率限制中间件（基于 shared/services/security/rate_limiter.py）
    try:
        from shared.services.security.rate_limiter import rate_limit_middleware as _rate_limit_fn
        from starlette.middleware.base import BaseHTTPMiddleware

        class RateLimitMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                return await _rate_limit_fn(request, call_next)

        app.add_middleware(RateLimitMiddleware)
        print("[Rate Limit] 已添加")
    except ImportError as e:
        print(f"[Rate Limit] 加载失败: {e}")
    except Exception as e:
        print(f"[Rate Limit] 注册异常: {e}")

    # RBAC 权限中间件
    try:
        from src.middleware.rbac_middleware import RBACMiddleware
        app.add_middleware(RBACMiddleware)
        print("[RBAC Middleware] 已添加")
    except ImportError as e:
        print(f"[RBAC Middleware] 加载失败: {e}")
    except Exception as e:
        print(f"[RBAC Middleware] 注册异常: {e}")

    # API 版本响应头
    class APIVersionMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            response.headers["API-Version"] = "v2"
            return response

    app.add_middleware(APIVersionMiddleware)
    print("[API Version] 已添加版本响应头中间件")

    # 性能监控中间件（惰性加载：避免启动时 import psutil）
    try:
        app.add_middleware(
            _make_lazy_middleware("src.middleware.performance_monitor", "RequestPerformanceMiddleware")
        )
        print("[Performance Monitor] 已添加性能监控中间件（惰性加载）")
    except Exception as e:
        print(f"[Performance Monitor] 加载失败: {e}")

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
        print("[Token Blacklist] 已添加 Token 黑名单中间件")
    except Exception as e:
        print(f"[Token Blacklist] 加载失败: {e}")

    # 暴力破解防护中间件
    try:
        from src.middleware.brute_force_protection import BruteForceProtectionMiddleware
        app.add_middleware(BruteForceProtectionMiddleware)
        print("[Brute Force] 已添加暴力破解防护中间件")
    except Exception as e:
        print(f"[Brute Force] 加载失败: {e}")


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
        from src.api.v2._base import ApiResponse
        return JSONResponse(
            status_code=status_code,
            content=ApiResponse(success=False, error=message).model_dump()
        )

    @app.get("/api/v2/health", tags=["system"])
    async def health_check():
        # 原逻辑简化
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    @app.get("/api/v2/mobile-login", tags=["qr-login"])
    async def mobile_login_page(request: Request):
        """手机扫码确认页面（注册在应用顶层，绕过 API 中间件和认证）"""
        from src.api.v2.qr_login import _MOBILE_LOGIN_HTML
        from fastapi.responses import HTMLResponse

        # 动态计算前端登录页地址
        host = request.headers.get("host", "localhost:9421")
        scheme = request.url.scheme or "http"
        # 开发环境：后端 :9421 → 前端 :4321（Astro 默认端口）
        # 生产环境：同源部署时 host 不含 :9421，保持原样
        frontend_host = host.replace(":9421", ":4321")
        frontend_origin = f"{scheme}://{frontend_host}"

        html = _MOBILE_LOGIN_HTML.replace("{{FRONTEND_ORIGIN}}", frontend_origin)
        return HTMLResponse(content=html)

    @app.exception_handler(401)
    async def unauthorized_handler(request: Request, exc: HTTPException):
        if _is_api_request(request):
            return _api_error_response(401, exc.detail)
        return RedirectResponse(url=f"/login?next={request.url}")

    @app.exception_handler(403)
    async def forbidden_handler(request: Request, exc: HTTPException):
        if _is_api_request(request):
            return _api_error_response(403, exc.detail)
        from src.api.v2._base import ApiResponse
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
            print(f"[Plugin] 404 hook error: {e}")

        # 2. API 请求返回 JSON
        if _is_api_request(request):
            return _api_error_response(404, "Page Not Found")

        # 3. 非 API 路径尝试返回前端 SPA 页面
        excluded_prefixes = ['api/v2/static/', 'api/v2/assets/', 'api/v2/docs', 'api/v2/redoc', 'api/v2/openapi.json',
                             'api/v2/health']
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
        from src.unified_logger import default_logger as logger
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
        docs_url="/api/v2/docs",
        redoc_url="/api/v2/redoc",
        openapi_url="/api/v2/openapi.json",
        swagger_ui_oauth2_redirect_url="/api/v2/docs/oauth2-redirect",
    )

    # 注册中间件
    step_start = _time.monotonic()
    register_middleware(app)
    print(f"{worker_info} [create_app] 中间件注册耗时: {_time.monotonic() - step_start:.2f}s")

    # 注册所有 API 路由
    step_start = _time.monotonic()
    register_all_routes(app, worker_info)
    print(f"{worker_info} [create_app] 路由注册耗时: {_time.monotonic() - step_start:.2f}s")

    # 错误处理和 SPA 回退
    register_error_handlers(app)

    # 静态文件挂载 - 确保在所有路由注册之后挂载，避免被catch-all路由拦截
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/api/v2/static", StaticFiles(directory=static_dir), name="static")

    # 本地存储 - 使用统一前缀 /api/v2/assets/storage 避免与业务路由冲突
    try:
        from src.setting import app_config
        local_storage = getattr(app_config, 'LOCAL_STORAGE_PATH', 'storage')
    except Exception:
        local_storage = 'storage'
    os.makedirs(local_storage, exist_ok=True)
    app.mount("/api/v2/assets/storage", StaticFiles(directory=local_storage), name="local-storage")

    objects_dir = os.path.join(local_storage, 'objects')
    os.makedirs(objects_dir, exist_ok=True)
    app.mount("/api/v2/assets/storage/objects", StaticFiles(directory=objects_dir), name="storage-objects")

    themes_dir = os.path.join(os.path.dirname(__file__), "..", "themes")
    if os.path.exists(themes_dir):
        app.mount("/api/v2/assets/themes", StaticFiles(directory=themes_dir), name="themes")

    app_elapsed = _time.monotonic() - app_start
    print(f"{worker_info} [create_app] 🏭 应用工厂完成，总耗时: {app_elapsed:.2f}s")

    return app


# 全局 app 实例（供 uvicorn 直接使用）
try:
    app = create_app()
except Exception as e:
    traceback.print_exc()
    app = None
