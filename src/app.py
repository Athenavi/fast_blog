"""
主应用文件
负责FastAPI应用工厂函数和核心配置"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import JWTStrategy, AuthenticationBackend, BearerTransport
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.staticfiles import StaticFiles

from src.auth.dependencies import get_user_manager
from src.models.user import User as UserModel
from src.setting import settings

# 全局变量，用于标记数据库是否已初始化，防止重复执行
_database_initialized = False


# 自定义中间件来处理404错误
class NotFoundMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # 检查是否是404错误且Accept头表明用户期望HTML响应
        if response.status_code == 404:
            accept_header = request.headers.get("accept", "")
            # 如果请求接受HTML响应但返回的是JSON，将其转换为HTML
            if "text/html" in accept_header or "text/plain" in accept_header:
                from src.error import error
                return error(404, "Page Not Found")
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    global _database_initialized

    # 检查是否已经执行过数据库初始化，避免重复执行
    if not _database_initialized:
        # 检查是否在uvicorn主进程中，如果不是主进程则跳过初始化
        import os
        if os.environ.get("RUN_MAIN") is None:
            print("检测到为主进程，开始执行数据库初始化...")
            # 运行数据库检查和初始化，如果数据库为空则创建测试数据
            print("运行数据库检查和初始化...")
            from src.utils.database.check_and_init_db import check_and_initialize_db
            from src.utils.database.migration_lock import run_migration_with_lock

            def _run_check_and_init():
                check_and_initialize_db()

            # 使用锁保护执行数据库初始化
            run_migration_with_lock(_run_check_and_init)
            print("数据库检查和初始化完成")

            # 启动时初始化数据库 - 使用锁机制确保多进程环境下的安全
            from src.utils.database.migration_lock import check_and_run_migrations
            check_and_run_migrations()

            # 检查是否存在超级管理员用户，如果不存在则创建
            # 放在数据库迁移和初始化之后，确保表结构已存在
            print("检查超级管理员用户...")
            from utils.database.check_superuser import ensure_superuser_exists
            # 在非交互式环境中自动创建默认超级管理员用户
            ensure_superuser_exists(auto_create=True)
            print("超级管理员用户检查完成")
        else:
            # 非主进程，跳过初始化以避免重复执行
            print("跳过初始化 - 非主进程")

            # 额外优化：在非主进程中快速返回，避免不必要的锁等待
            _database_initialized = True
            print("非主进程标识设置，跳过数据库初始化")
            # 初始化扩展（包括CORS中间件）
            from src.extensions import init_extensions
            init_extensions(app)

            # 初始化调度器
            from src.scheduler import init_scheduler
            init_scheduler(app)
            yield
            return

        # 设置标志，表明数据库初始化已完成
        _database_initialized = True
        print("数据库初始化完成")
    else:
        print("跳过数据库初始化 - 已执行过")

    # 初始化扩展（包括CORS中间件）
    from src.extensions import init_extensions
    init_extensions(app)

    # 初始化调度器
    from src.scheduler import init_scheduler
    init_scheduler(app)

    # 初始化扩展（包括CORS中间件）
    from src.extensions import init_extensions
    init_extensions(app)

    # 初始化调度器
    from src.scheduler import init_scheduler
    init_scheduler(app)

    yield

    # 关闭时的清理操作
    from src.scheduler import session_scheduler
    session_scheduler.scheduler.stop()


def create_app(config=None):
    """创建FastAPI应用实例"""
    from fastapi.middleware.cors import CORSMiddleware

    # 添加OpenAPI元数据以增强文档
    app = FastAPI(
        title="ZB FastAPI Blog - API文档",
        description="""
        # ZB FastAPI Blog API 文档

        这是一个现代化的博客系统API，提供完整的博客功能，包括文章管理、用户管理、分类管理等。

        ## 功能特点

        - 用户认证和授权
        - 文章管理（创建、编辑、删除、发布）
        - 分类管理
        - 媒体文件上传
        - 用户资料管理
        - 消息通知系统

        ## 认证

        - 使用JWT进行身份验证
        - 访问受保护的端点需要在请求头中包含Bearer Token
        """,
        version="1.0.0",
        openapi_tags=[
            {
                "name": "auth",
                "description": "认证相关接口，包括登录、注册、登出等功能"
            },
            {
                "name": "articles",
                "description": "文章管理接口，包括文章的增删改查、发布等功能"
            },
            {
                "name": "users",
                "description": "用户管理接口，包括用户信息、权限等功能"
            },
            {
                "name": "categories",
                "description": "分类管理接口，包括分类的创建、编辑、删除等功能"
            },
            {
                "name": "media",
                "description": "媒体文件管理接口，包括文件上传、删除等功能"
            },
            {
                "name": "dashboard",
                "description": "仪表板相关接口，包括统计数据、分析等功能"
            },
        ],
        lifespan=lifespan,
        # 自定义文档路径
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # Vite开发服务器
            "http://127.0.0.1:3000",
            "http://localhost:3001",  # Next.js默认端口
            "http://127.0.0.1:3001",
            "http://localhost:9421",  # 生产服务器
            "http://127.0.0.1:9421",
            "http://localhost:8000",  # 可能的其他开发服务器
            "http://127.0.0.1:8000",
            "http://localhost:8080",  # 常见的开发服务器端口
            "http://127.0.0.1:8080",
            "*"  # 在开发环境中允许所有来源，生产环境中应限制
        ],  # 在生产环境中应明确指定允许的源
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 添加404处理中间件
    app.add_middleware(NotFoundMiddleware)

    # JWT认证配置
    def get_jwt_strategy() -> JWTStrategy:
        return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=3600)

    # 导出get_jwt_strategy函数，以便在其他地方使用
    globals()['get_jwt_strategy'] = get_jwt_strategy

    # 认证后端
    auth_backend = AuthenticationBackend(
        name="jwt",
        transport=BearerTransport(tokenUrl="auth/jwt/login"),
        get_strategy=get_jwt_strategy,
    )

    # FastAPI Users配置
    from src.models.schemas import UserRead, UserUpdate
    fastapi_users = FastAPIUsers[UserModel, int](
        get_user_manager,
        [auth_backend],
    )

    app.include_router(
        fastapi_users.get_auth_router(auth_backend),
        prefix="/auth/jwt",
        tags=["auth-jwt"]
    )

    # 注意：我们使用自定义的注册路由，因此不需要包含FastAPI Users的注册路由
    # app.include_router(
    #     fastapi_users.get_register_router(UserCreate, UserRead),
    #     prefix="/auth",
    #     tags=["auth-register"]
    # )

    app.include_router(
        fastapi_users.get_reset_password_router(),
        prefix="/auth",
        tags=["auth-password-reset"]
    )

    app.include_router(
        fastapi_users.get_verify_router(UserRead),
        prefix="/auth",
        tags=["auth-verify"]
    )

    app.include_router(
        fastapi_users.get_users_router(UserRead, UserUpdate),
        prefix="/users",
        tags=["users"]
    )

    # 认证路由已整合到auth_view蓝图中

    # 主页路由已移至blog蓝图中处理

    @app.get("/health",
             summary="健康检查",
             description="检查API服务的健康状态",
             response_description="返回服务状态信息",
             tags=["system"])
    async def health_check():
        return {"status": "healthy"}

    # 添加API v1路由 - 包含所有已迁移的API功能
    try:
        from src.api.v1 import api_v1_router
        app.include_router(api_v1_router)
    except ImportError as e:
        print(f"Failed to import API v1 router: {e}")
    import os
    # 挂载静态文件目录
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    os.makedirs(static_dir, exist_ok=True)  # 确保目录存在
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # 挂载本地存储目录，用于访问本地存储的媒体文件
    try:
        from src.setting import app_config
        local_storage_path = getattr(app_config, 'LOCAL_STORAGE_PATH', 'storage')
    except Exception:
        # 如果配置获取失败，使用默认路径
        local_storage_path = 'storage'
    import os
    os.makedirs(local_storage_path, exist_ok=True)  # 确保目录存在
    app.mount("/local-storage", StaticFiles(directory=local_storage_path), name="local-storage")

    # 返回创建的应用实例
    return app


def register_routes(app: FastAPI, config_class):
    """注册应用路由 - 现在主要通过include_router实现"""

    # 为其他前端路由添加通配符处理，但要排除已知的后端路径
    @app.get('/{full_path:path}', response_class=HTMLResponse)
    async def spa_fallback(request: Request, full_path: str):
        # 排除API路径和其他已知的后端路径，这些应该返回404或正常处理
        excluded_paths = [
            'api', 'static', 'local-storage', 'shared', 'thumbnail',
            'login', 'register', 'auth', 'health', 'docs', 'redoc', 'openapi.json',
            'admin', 'user', 'users', 'articles', 'categories', 'media', 'profile', 'setting'
        ]

        # 如果路径在排除列表中，不处理为SPA路由
        for excluded_path in excluded_paths:
            if full_path.startswith(excluded_path):
                # 如果是已知的后端路径但未找到对应路由，返回404
                from fastapi.responses import PlainTextResponse
                return PlainTextResponse("Not Found", status_code=404)
        
        # 如果路径不在排除列表中，返回主页面以供前端路由处理
        # 读取前端构建的index.html或其他主页面文件
        try:
            import os
            frontend_index_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
            if os.path.exists(frontend_index_path):
                with open(frontend_index_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                return HTMLResponse(content=html_content)
            else:
                # 如果找不到前端index.html，返回一个简单的默认页面
                return HTMLResponse(content="<!DOCTYPE html><html><head><title>Blog</title></head><body><div id='app'></div></body></html>")
        except Exception:
            # 如果读取页面文件失败，返回一个简单的默认页面
            return HTMLResponse(content="<!DOCTYPE html><html><head><title>Blog</title></head><body><div id='app'></div></body></html>")

    # 错误处理
    @app.exception_handler(401)
    async def unauthorized_handler(request: Request, exc: HTTPException):
        # 检查是否是API请求，如果是则返回JSON错误
        if request.url.path.startswith('/api/') or request.headers.get('accept', '').find('application/json') != -1:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail}
            )

        # 对于非API请求，重定向到登录页面并添加next参数
        next_url = str(request.url)
        login_url = f"/login?next={next_url}"
        return RedirectResponse(url=login_url)

    @app.exception_handler(404)
    async def custom_404_handler(request: Request, exc: HTTPException):
        from src.error import error
        return error(404, "Page Not Found")

    @app.exception_handler(500)
    async def custom_500_handler(request: Request, exc: HTTPException):
        from src.error import error
        # 对于某些特定的错误，转换为404页面
        if hasattr(exc, 'status_code') and exc.status_code == 404:
            return error(404, "Page Not Found")
        return error(500, "Internal Server Error")

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        from src.error import error
        logger = logging.getLogger(__name__)
        logger.error(f"General error: {str(exc)}")
        # 某些错误类型应该显示为404页面而非500错误
        error_msg = str(exc)
        # 检查是否是常见的导致404的错误
        if "not found" in error_msg.lower() or "no result" in error_msg.lower() or "does not exist" in error_msg.lower():
            return error(404, "Page Not Found")
        return error(404, "Page Not Found")


def configure_logging(app: FastAPI):
    """配置日志"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("FastAPI应用日志已配置。")


def print_startup_info(config_class):
    """打印启动信息"""
    logger = logging.getLogger(__name__)
    logger.info(f"running at: {config_class.base_dir}")
    logger.info("sys information")
    domain = config_class.domain.rstrip('/') + '/'
    logger.info("++++++++++==========================++++++++++")
    logger.info(
        f'\n domain: {domain} \n title: {config_class.sitename} \n beian: {config_class.beian} \n')

    # 安全检查
    if config_class.SECRET_KEY == 'your-secret-key-here':
        logger.critical("CRITICAL: 应用存在严重安全风险，不能使用默认SECRET_KEY运行，请修改 SECRET_KEY 环境变量的值")
        logger.critical("CRITICAL: 请修改 SECRET_KEY 环境变量的值")
        logger.critical("CRITICAL: 请修改 SECRET_KEY 环境变量的值")
        logger.critical("CRITICAL: 请修改 SECRET_KEY 环境变量的值")

    logger.info("++++++++++==========================++++++++++")
