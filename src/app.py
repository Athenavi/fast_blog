"""
主应用文件
负责 FastAPI 应用工厂函数和核心配置"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from shared.services.plugin_manager import plugin_hooks

# 先设置 Django settings 并初始化
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_blog.settings')
import django

# 防止重复初始化 Django
if not hasattr(django, '_setup_complete') or not django.apps.apps.ready:
    try:
        django.setup()
        django._setup_complete = True
    except RuntimeError as e:
        if "populate() isn't reentrant" in str(e):
            # Django 已经初始化过了，忽略这个错误
            pass
        else:
            raise

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理 - Django 版本移除了数据库初始化代码"""
    # Django 版本：不再需要数据库初始化，Django 会自动处理

    # 检查安装状态
    try:
        from shared.services.install_manager import installation_wizard_service
        if not installation_wizard_service.is_installed():
            print("\n" + "=" * 60)
            print("⚠️  系统尚未安装")
            print("👉 请启动前端进程后访问 http://localhost:3000/install 完成安装向导")
            print("=" * 60 + "\n")
    except Exception as e:
        print(f"Warning: Failed to check installation status: {e}")

    # 初始化统一的数据库连接管理器
    try:
        from src.utils.database.unified_manager import db_manager
        print("\n" + "=" * 60)
        print("[Database] Initializing unified database manager...")
        db_manager.initialize()
        print("[Database] ✅ Unified database manager initialized successfully")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"\n[Database] ❌ Failed to initialize database manager: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60 + "\n")

    # 初始化扩展（包括 CORS 中间件）
    from src.extensions import init_extensions
    init_extensions(app)

    # 初始化调度器
    from src.scheduler import init_scheduler
    init_scheduler(app)

    # 启动定时发布调度器
    try:
        from shared.services.scheduler import init_scheduler as init_publish_scheduler, start_scheduler
        from src.utils.database.unified_manager import db_manager

        publish_scheduler = init_publish_scheduler(
            db_manager.get_async_session_factory,
            check_interval=60  # 每60秒检查一次
        )
        await start_scheduler()
        print("\n[ScheduledPublish] ✅ Scheduled publish scheduler started")
    except Exception as e:
        print(f"\n[ScheduledPublish] ⚠️ Failed to start scheduler: {e}")

    # 初始化插件系统
    try:
        print("\n" + "=" * 60)
        print("[PluginSystem] Starting plugin initialization...")
        print("=" * 60 + "\n")

        from shared.services.plugin_manager import initialize_plugins
        result = initialize_plugins()

        if result:
            print("\n[PluginSystem] ✅ Plugin system initialized successfully")
        else:
            print("\n[PluginSystem] ❌ Plugin system initialization failed")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"\n[PluginSystem] ❌ Failed to initialize plugin system: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60 + "\n")

    yield

    # 关闭时的清理操作
    from src.scheduler import session_scheduler
    session_scheduler.scheduler.stop()

    # 关闭数据库连接
    try:
        from src.utils.database.unified_manager import db_manager
        await db_manager.close()
        print("\n[Database] ✅ Database connections closed")
    except Exception as e:
        print(f"\n[Database] ⚠️ Error closing database connections: {e}")


def create_app(config=None):
    """创建FastAPI应用实例"""
    from fastapi.middleware.cors import CORSMiddleware

    # 添加OpenAPI元数据以增强文档 - AI-Friendly
    app = FastAPI(
        title="FastBlog API",
        description="""
# FastBlog API 文档

现代化的博客系统 API，提供完整的博客管理功能。

## 🚀 核心功能

### 内容管理
- **文章管理**: 创建、编辑、删除、发布文章，支持 Markdown 和富文本
- **分类管理**: 多级分类体系，支持订阅和统计
- **媒体管理**: 图片、视频等媒体文件上传和管理
- **页面管理**: 静态页面创建和管理

### 用户系统
- **用户认证**: JWT、OAuth2、WebAuthn (Passkey)
- **权限管理**: 基于角色的访问控制 (RBAC)
- **用户资料**: 个人资料管理和头像上传

### 高级功能
- **插件系统**: 可扩展的插件架构
- **主题定制**: 多主题支持和自定义
- **SEO 优化**: 自动生成 meta 标签和 sitemap
- **数据分析**: 访问统计和用户行为分析
- **定时发布**: 文章定时发布和调度

## 🔐 认证方式

API 使用 JWT (JSON Web Token) 进行身份验证：

1. 通过 `/api/v1/auth/login` 获取 token
2. 在请求头中添加: `Authorization: Bearer <token>`

## 📖 API 版本

当前版本: v1.0.0
基础路径: `/api/v1`

## 🤖 AI Agent 友好

本 API 设计遵循以下原则以支持 AI Agent 自动调用：

- **清晰的端点命名**: RESTful 风格，语义明确
- **完整的参数说明**: 每个参数都有详细描述和示例
- **标准化的响应格式**: 统一的 ApiResponse 结构
- **丰富的错误信息**: 详细的错误码和说明
- **机器可读的 Schema**: OpenAPI 3.0 规范

## 📊 主要模块

| 模块 | 前缀 | 描述 |
|------|------|------|
| Auth | `/api/v1/auth` | 用户认证和授权 |
| Articles | `/api/v1/articles` | 文章管理 |
| Users | `/api/v1/users` | 用户管理 |
| Categories | `/api/v1/categories` | 分类管理 |
| Media | `/api/v1/media` | 媒体文件管理 |
| Dashboard | `/api/v1/dashboard` | 仪表板和统计 |
| Plugins | `/api/v1/plugins` | 插件管理 |
| Settings | `/api/v1/settings` | 系统设置 |

## 💡 使用示例

### 获取文章列表
```bash
curl -X GET "http://localhost:9421/api/v1/articles?page=1&per_page=10"
```

### 创建新文章
```bash
curl -X POST "http://localhost:9421/api/v1/articles" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "我的第一篇文章",
    "content": "文章内容...",
    "category_id": 1
  }'
```

### 上传媒体文件
```bash
curl -X POST "http://localhost:9421/api/v1/media/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@image.jpg"
```

## 🔗 相关链接

- [GitHub Repository](https://github.com/fastblog/fast_blog)
- [文档中心](https://docs.fastblog.example.com)
- [插件市场](https://plugins.fastblog.example.com)
- [社区论坛](https://community.fastblog.example.com)

## 📝 更新日志

### v1.0.0 (2026-04-09)
- ✨ 初始版本发布
- 🔐 完整的用户认证系统
- 📝 文章 CRUD 操作
- 📁 分类和标签管理
- 🖼️ 媒体文件管理
- 📊 数据统计和仪表板
- 🔌 插件系统基础框架
        """,
        version="1.0.0",
        openapi_tags=[
            {
                "name": "auth",
                "description": "🔐 用户认证相关接口，包括登录、注册、登出、密码重置等功能",
                "externalDocs": {
                    "description": "认证指南",
                    "url": "https://docs.fastblog.example.com/auth"
                }
            },
            {
                "name": "articles",
                "description": "📝 文章管理接口，包括文章的增删改查、发布、定时发布、版本管理等功能",
                "externalDocs": {
                    "description": "文章管理指南",
                    "url": "https://docs.fastblog.example.com/articles"
                }
            },
            {
                "name": "users",
                "description": "👤 用户管理接口，包括用户信息、权限、角色分配等功能",
                "externalDocs": {
                    "description": "用户管理指南",
                    "url": "https://docs.fastblog.example.com/users"
                }
            },
            {
                "name": "categories",
                "description": "📁 分类管理接口，包括分类的创建、编辑、删除、排序等功能",
                "externalDocs": {
                    "description": "分类管理指南",
                    "url": "https://docs.fastblog.example.com/categories"
                }
            },
            {
                "name": "media",
                "description": "🖼️ 媒体文件管理接口，包括文件上传、删除、编辑、缩略图生成等功能",
                "externalDocs": {
                    "description": "媒体管理指南",
                    "url": "https://docs.fastblog.example.com/media"
                }
            },
            {
                "name": "dashboard",
                "description": "📊 仪表板相关接口，包括统计数据、分析图表、趋势报告等功能",
                "externalDocs": {
                    "description": "仪表板指南",
                    "url": "https://docs.fastblog.example.com/dashboard"
                }
            },
            {
                "name": "article-revisions",
                "description": "📜 文章修订历史接口，包括版本管理、回滚、比较差异等功能",
                "externalDocs": {
                    "description": "版本管理指南",
                    "url": "https://docs.fastblog.example.com/revisions"
                }
            },
            {
                "name": "scheduled-publish",
                "description": "⏰ 定时发布接口，包括设置发布时间、立即发布、取消定时等功能",
                "externalDocs": {
                    "description": "定时发布指南",
                    "url": "https://docs.fastblog.example.com/scheduled"
                }
            },
            {
                "name": "feed",
                "description": "📡 RSS/Atom Feed 接口，提供博客内容订阅功能",
                "externalDocs": {
                    "description": "Feed 订阅指南",
                    "url": "https://docs.fastblog.example.com/feed"
                }
            },
            {
                "name": "pages",
                "description": "📄 静态页面管理接口，包括页面的增删改查、模板选择等功能",
                "externalDocs": {
                    "description": "页面管理指南",
                    "url": "https://docs.fastblog.example.com/pages"
                }
            },
            {
                "name": "menu-management",
                "description": "🧭 菜单管理接口，包括菜单和菜单项的增删改查、排序等功能",
                "externalDocs": {
                    "description": "菜单管理指南",
                    "url": "https://docs.fastblog.example.com/menus"
                }
            },
            {
                "name": "backup-management",
                "description": "💾 备份管理接口，包括数据库备份、恢复、下载、定时备份等功能",
                "externalDocs": {
                    "description": "备份管理指南",
                    "url": "https://docs.fastblog.example.com/backup"
                }
            },
            {
                "name": "plugin-management",
                "description": "🔌 插件管理接口，包括插件安装、激活、配置、卸载等功能",
                "externalDocs": {
                    "description": "插件开发指南",
                    "url": "https://docs.fastblog.example.com/plugins"
                }
            },
            {
                "name": "theme-management",
                "description": "🎨 主题管理接口，包括主题安装、激活、配置、自定义等功能",
                "externalDocs": {
                    "description": "主题开发指南",
                    "url": "https://docs.fastblog.example.com/themes"
                }
            },
            {
                "name": "roles",
                "description": "🛡️ 角色和权限管理接口，包括角色创建、权限分配、用户角色绑定等功能",
                "externalDocs": {
                    "description": "权限管理指南",
                    "url": "https://docs.fastblog.example.com/roles"
                }
            },
            {
                "name": "home",
                "description": "🏠 首页数据接口，包括推荐文章、热门文章、分类统计等首页展示数据",
                "externalDocs": {
                    "description": "首页定制指南",
                    "url": "https://docs.fastblog.example.com/home"
                }
            },
            {
                "name": "user-management",
                "description": "👥 用户管理后台接口，包括用户列表、批量操作、用户状态管理等功能",
                "externalDocs": {
                    "description": "用户管理指南",
                    "url": "https://docs.fastblog.example.com/user-management"
                }
            },
            {
                "name": "user-settings",
                "description": "⚙️ 用户个人设置接口，包括偏好设置、通知设置、隐私设置等功能",
                "externalDocs": {
                    "description": "用户设置指南",
                    "url": "https://docs.fastblog.example.com/settings"
                }
            },
            {
                "name": "notifications",
                "description": "🔔 消息通知接口，包括通知列表、标记已读、推送设置等功能",
                "externalDocs": {
                    "description": "通知系统指南",
                    "url": "https://docs.fastblog.example.com/notifications"
                }
            },
            {
                "name": "seo",
                "description": "🔍 SEO 优化接口，包括 meta 标签管理、sitemap 生成、SEO 分析等功能",
                "externalDocs": {
                    "description": "SEO 优化指南",
                    "url": "https://docs.fastblog.example.com/seo"
                }
            },
            {
                "name": "ai-metadata",
                "description": "🤖 AI 元数据接口，包括关键词提取、自动摘要、语义标签、可读性分析等 AI 友好功能",
                "externalDocs": {
                    "description": "AI 元数据指南",
                    "url": "https://docs.fastblog.example.com/ai-metadata"
                }
            },
            {
                "name": "system",
                "description": "🖥️ 系统相关接口，包括健康检查、系统信息、配置管理等",
                "externalDocs": {
                    "description": "系统管理指南",
                    "url": "https://docs.fastblog.example.com/system"
                }
            },
            {
                "name": "widgets",
                "description": "🧩 小部件(Widgets)管理接口，包括 Widget 实例的增删改查、排序、配置，以及数据获取 API（最新文章、标签云、分类目录、文章归档等）",
                "externalDocs": {
                    "description": "Widget 开发指南",
                    "url": "https://docs.fastblog.example.com/widgets"
                }
            },
            {
                "name": "tips",
                "description": "💰 打赏系统接口，包括文章打赏、打赏统计、排行榜、提现申请等功能",
                "externalDocs": {
                    "description": "打赏系统指南",
                    "url": "https://docs.fastblog.example.com/tips"
                }
            },
            {
                "name": "advertisements",
                "description": "📢 广告管理系统接口，包括广告位管理、广告投放、AdSense/百度联盟集成、收益报表等功能",
                "externalDocs": {
                    "description": "广告管理指南",
                    "url": "https://docs.fastblog.example.com/ads"
                }
            },
        ],
        lifespan=lifespan,
        # 自定义文档路径
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        # 增强 OpenAPI 配置
        openapi_version="3.0.3",
        contact={
            "name": "FastBlog Support",
            "url": "https://github.com/fastblog/fast_blog/issues",
            "email": "support@fastblog.example.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        terms_of_service="https://fastblog.example.com/terms",
    )

    # 添加 CORS 中间件 - 从环境变量读取允许的域名（严格安全配置）
    cors_origins_env = os.environ.get('CORS_ORIGINS', '')
    if cors_origins_env:
        # 支持逗号或分号分隔的多个域名
        allow_origins = [origin.strip() for origin in cors_origins_env.replace(';', ',').split(',') if origin.strip()]
    else:
        # 默认允许本地开发环境
        allow_origins = [
            "http://localhost:3000",  # Next.js 开发服务器
            "http://127.0.0.1:3000",
            "http://localhost:9421",  # 生产服务器
            "http://127.0.0.1:9421",
        ]

    # 安全检查：禁止使用 wildcard (*)
    if "*" in allow_origins:
        print("[CORS] WARNING: Wildcard (*) is not allowed in CORS origins for security reasons")
        allow_origins = [origin for origin in allow_origins if origin != "*"]
        if not allow_origins:
            # 如果没有其他源，至少保留 localhost
            allow_origins = ["http://localhost:3000"]

    print(f"[CORS] 允许的源: {allow_origins}")
    print(f"[CORS] Allow credentials: True")

    # 添加 CORS 中间件 - 严格限制
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,  # 严格限制允许的源，不使用 wildcard
        allow_credentials=True,  # 允许携带 credentials (cookies)
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],  # 明确指定允许的方法
        allow_headers=["Authorization", "Content-Type", "Cookie", "X-Requested-With"],  # 明确指定允许的头部，不使用 wildcard
        expose_headers=["Content-Length", "X-Total-Count"],  # 明确指定暴露的头部
    )

    # 添加请求调试中间件（用于调试 422 错误）
    from starlette.middleware.base import BaseHTTPMiddleware

    class DebugRequestMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            # 监控所有敏感词相关的请求
            if "/sensitive-words" in str(request.url):
                print(f"\n{'=' * 80}")
                print(f"[DEBUG MIDDLEWARE] Sensitive Words Request")
                print(f"URL: {request.url}")
                print(f"Method: {request.method}")
                print(f"Content-Type: {request.headers.get('content-type')}")
                print(f"Content-Length: {request.headers.get('content-length')}")
                print(f"Authorization: {request.headers.get('authorization', 'NONE')[:50]}...")
                print(f"All Headers: {dict(request.headers)}")

                # 尝试读取并打印请求体
                if request.method == "POST":
                    try:
                        body = await request.body()
                        print(f"Request Body: {body.decode('utf-8')}")
                    except Exception as e:
                        print(f"Could not read body: {e}")
                
                print(f"{'=' * 80}\n")

            response = await call_next(request)

            # 打印响应状态
            if "/sensitive-words" in str(request.url):
                print(f"[DEBUG MIDDLEWARE] Response Status: {response.status_code}")
                print(f"[DEBUG MIDDLEWARE] Response Headers: {dict(response.headers)}")

                # 如果是422，尝试读取响应体
                if response.status_code == 422:
                    from starlette.responses import JSONResponse
                    if hasattr(response, 'body'):
                        try:
                            body_content = b''
                            async for chunk in response.body_iterator:
                                body_content += chunk
                            print(f"[DEBUG MIDDLEWARE] 422 Response Body: {body_content.decode('utf-8')}")

                            # 重新设置body_iterator，让后续处理能读取
                            async def body_iterator():
                                yield body_content

                            response.body_iterator = body_iterator()
                        except Exception as e:
                            print(f"Could not read 422 response body: {e}")

            return response

    app.add_middleware(DebugRequestMiddleware)
    print("[Debug] Request debug middleware added")

    # 添加 WebSocket 调试中间件（用于调试协作编辑 403 错误）
    from starlette.middleware.base import BaseHTTPMiddleware

    class DebugWebSocketMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            # 检查是否是 WebSocket 升级请求
            if request.headers.get("upgrade", "").lower() == "websocket":
                if "/collaboration/ws/" in str(request.url):
                    print(f"\n{'=' * 80}")
                    print(f"[DEBUG WEBSOCKET] Collaboration WebSocket Connection Attempt")
                    print(f"URL: {request.url}")
                    print(f"Method: {request.method}")
                    print(f"Upgrade: {request.headers.get('upgrade')}")
                    print(f"Connection: {request.headers.get('connection')}")
                    print(f"Sec-WebSocket-Key: {request.headers.get('sec-websocket-key', 'N/A')[:20]}...")
                    print(f"Cookie Header: {request.headers.get('cookie', 'NO COOKIE')[:150]}...")
                    print(f"All Headers:")
                    for key, value in request.headers.items():
                        if key.lower() in ['cookie', 'authorization']:
                            print(f"  {key}: {value[:50]}..." if len(value) > 50 else f"  {key}: {value}")
                    print(f"{'=' * 80}\n")

            response = await call_next(request)
            return response

    app.add_middleware(DebugWebSocketMiddleware)
    print("[Debug] WebSocket debug middleware added")

    # 添加 HTTP 缓存中间件（ETag、Last-Modified、条件请求支持）
    try:
        from src.middleware.http_cache_middleware import HttpCacheMiddleware
        app.add_middleware(
            HttpCacheMiddleware,
            enable_etag=True,
            enable_last_modified=True,
            default_cache_ttl=300,  # 5分钟默认缓存
            skip_paths=[
                '/admin',
                '/api/v1/auth',
                '/api/v1/user',
                '/login',
                '/register',
                '/api/v1/installation',
                '/api/v1/home/categories',  # 排除分类接口，避免 CORS 问题
                '/api/v1/articles',  # 排除文章列表接口，避免 CORS 问题
            ],
            skip_methods=['POST', 'PUT', 'DELETE', 'PATCH'],
            cache_public_only=True,
        )
        print("[HTTP Cache] HTTP cache middleware added (ETag + Last-Modified support)")
    except ImportError as e:
        print(f"Warning: HTTP Cache middleware could not be loaded: {e}")

    # 添加安全中间件（XSS过滤、CSRF保护、速率限制、SQL注入检测）
    try:
        from src.auth.security_middleware import create_security_middleware_stack
        # 配置速率限制：每分钟 100 次请求
        create_security_middleware_stack(
            app,
            rate_limit_requests=100,
            rate_limit_window=60
        )
        print("[Security] Security middleware stack initialized")
    except ImportError as e:
        print(f"Warning: Security middleware could not be loaded: {e}")

    # 添加 API 速率限制中间件（令牌桶算法）
    try:
        from src.middleware.rate_limit_middleware import RateLimitMiddleware
        app.add_middleware(RateLimitMiddleware)
        print("[Rate Limit] API rate limit middleware added (Token Bucket algorithm)")
    except ImportError as e:
        print(f"Warning: Rate Limit middleware could not be loaded: {e}")

    # 添加多站点中间件
    try:
        from src.middleware.multisite_middleware import MultiSiteMiddleware
        app.add_middleware(MultiSiteMiddleware)
        print("[MultiSite] Multi-site middleware added (domain/path-based routing)")
    except ImportError as e:
        print(f"Warning: Multi-site middleware could not be loaded: {e}")

    @app.get("/health",
             summary="健康检查",
             description="检查API服务的健康状态，包括数据库、Redis等依赖服务",
             response_description="返回服务状态信息",
             tags=["system"])
    async def health_check():
        """
        健康检查端点
        检查核心服务的可用性：
        - API服务状态
        - 数据库连接
        - Redis连接（如果配置）
        - 插件系统状态
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {}
        }

        # 检查数据库连接
        try:
            from src.utils.database.main import get_async_session, get_async_session_context
            from sqlalchemy import text

            async with get_async_session_context() as session:
                await session.execute(text("SELECT 1"))
            health_status["services"]["database"] = {
                "status": "healthy",
                "message": "Database connection successful"
            }
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["services"]["database"] = {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}"
            }

        # 检查Redis连接（如果配置）
        try:
            import os
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                import aioredis
                redis = aioredis.from_url(redis_url)
                await redis.ping()
                await redis.close()
                health_status["services"]["redis"] = {
                    "status": "healthy",
                    "message": "Redis connection successful"
                }
            else:
                health_status["services"]["redis"] = {
                    "status": "not_configured",
                    "message": "Redis not configured"
                }
        except ImportError:
            health_status["services"]["redis"] = {
                "status": "not_available",
                "message": "aioredis not installed"
            }
        except Exception as e:
            health_status["status"] = "degraded"
            health_status["services"]["redis"] = {
                "status": "unhealthy",
                "message": f"Redis connection failed: {str(e)}"
            }

        # 检查插件系统
        try:
            from shared.services.plugin_manager import plugin_hooks
            plugin_count = len(plugin_hooks.plugins) if hasattr(plugin_hooks, 'plugins') else 0
            health_status["services"]["plugins"] = {
                "status": "healthy",
                "message": f"{plugin_count} plugins loaded"
            }
        except Exception as e:
            health_status["services"]["plugins"] = {
                "status": "warning",
                "message": f"Plugin system error: {str(e)}"
            }

        return health_status

    # 添加 API v1 路由（FastAPI 原生实现）
    try:
        from src.api.v1.users import router as users_router
        app.include_router(users_router, prefix='/api/v1/users', tags=['users'])

        from src.api.v1.user_management import router as user_mgmt_router
        app.include_router(user_mgmt_router, prefix='/api/v1', tags=['user-management'])

        # 博客文章相关 - 使用统一的 api_v1_router（包含 articles, users, blog 等模块）
        from src.api.v1 import api_v1_router
        app.include_router(api_v1_router)

        # 分类相关
        from src.api.v1.category_management import router as category_router
        app.include_router(category_router, prefix='/api/v1/categories', tags=['categories'])

        # 仪表板相关 - FastAPI 版本保留，用于前端展示统计数据
        from src.api.v1.dashboard import router as dashboard_router
        app.include_router(dashboard_router, prefix='/api/v1/dashboard', tags=['dashboard'])

        # Home 相关路由（router 内部已经有 /home 前缀）
        from src.api.v1.home import router as home_router
        app.include_router(home_router, prefix='/api/v1', tags=['home'])

        # 获取 worker 信息（用于日志输出）
        from src.setting import _get_worker_info
        worker_info = _get_worker_info()

        # 批量 SEO 管理
        try:
            from src.api.v1.batch_seo import router as batch_seo_router
            app.include_router(batch_seo_router, prefix='/api/v1/seo', tags=['batch-seo'])
            print(f"{worker_info} [OK] Batch SEO API 已加载")
        except ImportError as e:
            print(f"Warning: Batch SEO API could not be loaded: {e}")

        # SEO 优化和分析
        try:
            from src.api.v1.seo_optimization import router as seo_optimization_router
            app.include_router(seo_optimization_router, prefix='/api/v1', tags=['seo-optimization'])
            print(f"{worker_info} [OK] SEO Optimization API 已加载")
        except ImportError as e:
            print(f"Warning: SEO Optimization API could not be loaded: {e}")

        # Block 编辑器相关
        try:
            from src.api.v1.block_editor import router as block_editor_router
            app.include_router(block_editor_router, prefix='/api/v1', tags=['block-editor'])
            print(f"{worker_info} [OK] Block Editor API 已加载")
        except ImportError as e:
            print(f"Warning: Block Editor API could not be loaded: {e}")

        # GraphQL API
        try:
            from src.api.v1.graphql import router as graphql_router
            app.include_router(graphql_router, prefix='/graphql', tags=['graphql'])
            print(f"{worker_info} [OK] GraphQL API 已加载")
        except ImportError as e:
            print(f"Warning: GraphQL API could not be loaded: {e}")

        # 文章搜索 API
        try:
            from src.api.v1.article_search import router as search_router
            app.include_router(search_router, prefix='/api/v1', tags=['search'])
            print(f"{worker_info} [OK] Article Search API 已加载")
        except ImportError as e:
            print(f"Warning: Article Search API could not be loaded: {e}")

        # AI 智能推荐 API
        try:
            from src.api.v1.ai_recommendations import router as ai_router
            app.include_router(ai_router, prefix='/api/v1', tags=['ai'])
            print(f"{worker_info} [OK] AI Recommendations API 已加载")
        except ImportError as e:
            print(f"Warning: AI Recommendations API could not be loaded: {e}")

        # 翻译管理 API
        try:
            from src.api.v1.translations import router as translations_router
            app.include_router(translations_router, prefix='/api/v1', tags=['translations'])
            print(f"{worker_info} [OK] Translations API 已加载")
        except ImportError as e:
            print(f"Warning: Translations API could not be loaded: {e}")

        # 区域化设置 API
        try:
            from src.api.v1.localization import router as localization_router
            app.include_router(localization_router, prefix='/api/v1', tags=['localization'])
            print(f"{worker_info} [OK] Localization API 已加载")
        except ImportError as e:
            print(f"Warning: Localization API could not be loaded: {e}")

        # 数据分析 API
        try:
            from src.api.v1.analytics import router as analytics_router
            app.include_router(analytics_router, prefix='/api/v1', tags=['analytics'])
            print(f"{worker_info} [OK] Analytics API 已加载")
        except ImportError as e:
            print(f"Warning: Analytics API could not be loaded: {e}")

        # 批量操作 API
        try:
            from src.api.v1.batch_operations import router as batch_router
            app.include_router(batch_router, prefix='/api/v1', tags=['batch'])
            print(f"{worker_info} [OK] Batch Operations API 已加载")
        except ImportError as e:
            print(f"Warning: Batch Operations API could not be loaded: {e}")

        # 会员订阅 API
        try:
            from src.api.v1.membership import router as membership_router
            app.include_router(membership_router, prefix='/api/v1', tags=['membership'])
            print(f"{worker_info} [OK] Membership API 已加载")
        except ImportError as e:
            print(f"Warning: Membership API could not be loaded: {e}")

        # WebSocket 实时协作 API
        try:
            from src.api.v1.websocket import router as websocket_router
            app.include_router(websocket_router)
            print(f"{worker_info} [OK] WebSocket API 已加载")
        except ImportError as e:
            print(f"Warning: WebSocket API could not be loaded: {e}")

        # Collaboration 实时协作编辑 API
        try:
            from src.api.v1.collaboration import router as collaboration_router
            app.include_router(collaboration_router, prefix='/api/v1')
            print(f"{worker_info} [OK] Collaboration API 已加载")
        except ImportError as e:
            print(f"Warning: Collaboration API could not be loaded: {e}")

        # Collaboration Invites 邀请管理 API
        try:
            from src.api.v1.collaboration_invites import router as collaboration_invites_router
            app.include_router(collaboration_invites_router, prefix='/api/v1')
            print(f"{worker_info} [OK] Collaboration Invites API 已加载")
        except ImportError as e:
            print(f"Warning: Collaboration Invites API could not be loaded: {e}")

        # Collaboration Save 保存协作文档 API
        try:
            from src.api.v1.collaboration_save import router as collaboration_save_router
            app.include_router(collaboration_save_router, prefix='/api/v1')
            print(f"{worker_info} [OK] Collaboration Save API 已加载")
        except ImportError as e:
            print(f"Warning: Collaboration Save API could not be loaded: {e}")

        # Yjs Collaboration 实时协作编辑 API (基于 CRDT)
        try:
            from src.api.v1.yjs_collaboration import router as yjs_collaboration_router
            app.include_router(yjs_collaboration_router, prefix='/api/v1')
            print(f"{worker_info} [OK] Yjs Collaboration API 已加载")
        except ImportError as e:
            print(f"Warning: Yjs Collaboration API could not be loaded: {e}")

        # E-commerce Products 电商产品管理 API
        try:
            from src.api.v1.ecommerce_products import router as ecommerce_products_router
            app.include_router(ecommerce_products_router, prefix='/api/v1')
            print(f"{worker_info} [OK] E-commerce Products API 已加载")
        except ImportError as e:
            print(f"Warning: E-commerce Products API could not be loaded: {e}")

        # E-commerce Cart & Orders 电商购物车和订单 API
        try:
            from src.api.v1.ecommerce_cart_orders import router as ecommerce_cart_orders_router
            app.include_router(ecommerce_cart_orders_router, prefix='/api/v1')
            print(f"{worker_info} [OK] E-commerce Cart & Orders API 已加载")
        except ImportError as e:
            print(f"Warning: E-commerce Cart & Orders API could not be loaded: {e}")

        # Edge Functions API
        try:
            from src.api.v1.edge_functions import router as edge_functions_router
            app.include_router(edge_functions_router, prefix='/api/v1', tags=['edge-functions'])
            print(f"{worker_info} [OK] Edge Functions API 已加载")
        except ImportError as e:
            print(f"Warning: Edge Functions API could not be loaded: {e}")

        # 文章定时发布 API
        try:
            from src.api.v1.scheduled_publish import router as scheduled_publish_router
            app.include_router(scheduled_publish_router, prefix='/api/v1', tags=['scheduled-publish'])
            print(f"{worker_info} [OK] Scheduled Publish API 已加载")
        except ImportError as e:
            print(f"Warning: Scheduled Publish API could not be loaded: {e}")

        # 草稿预览链接 API
        try:
            from src.api.v1.draft_preview import router as draft_preview_router
            app.include_router(draft_preview_router, prefix='/api/v1', tags=['draft-preview'])
            print(f"{worker_info} [OK] Draft Preview API 已加载")
        except ImportError as e:
            print(f"Warning: Draft Preview API could not be loaded: {e}")

        # 自定义块管理 API
        try:
            from src.api.v1.custom_blocks import router as custom_blocks_router
            app.include_router(custom_blocks_router, prefix='/api/v1', tags=['custom-blocks'])
            print(f"{worker_info} [OK] Custom Blocks API 已加载")
        except ImportError as e:
            print(f"Warning: Custom Blocks API could not be loaded: {e}")

        # NFT 内容所有权 API
        try:
            from src.api.v1.nft import router as nft_router
            app.include_router(nft_router, prefix='/api/v1', tags=['nft'])
            print(f"{worker_info} [OK] NFT API 已加载")
        except ImportError as e:
            print(f"Warning: NFT API could not be loaded: {e}")

        # 审计日志 API
        try:
            from src.api.v1.audit_log import router as audit_log_router
            app.include_router(audit_log_router, prefix='/api/v1/audit-log', tags=['audit-log'])
            print(f"{worker_info} [OK] Audit Log API 已加载")
        except ImportError as e:
            print(f"Warning: Audit Log API could not be loaded: {e}")

        # 查询优化 API
        try:
            from src.api.v1.query_optimization import router as query_opt_router
            app.include_router(query_opt_router, prefix='/api/v1/query-optimization', tags=['query-optimization'])
            print(f"{worker_info} [OK] Query Optimization API 已加载")
        except ImportError as e:
            print(f"Warning: Query Optimization API could not be loaded: {e}")

        # 页面缓存管理 API
        try:
            from src.api.v1.page_cache import router as page_cache_router
            app.include_router(page_cache_router, prefix='/api/v1/page-cache', tags=['page-cache'])
            print(f"{worker_info} [OK] Page Cache API 已加载")
        except ImportError as e:
            print(f"Warning: Page Cache API could not be loaded: {e}")

        # 对象缓存管理 API
        try:
            from src.api.v1.object_cache import router as object_cache_router
            app.include_router(object_cache_router, prefix='/api/v1/object-cache', tags=['object-cache'])
            print(f"{worker_info} [OK] Object Cache API 已加载")
        except ImportError as e:
            print(f"Warning: Object Cache API could not be loaded: {e}")

        # 资源优化管理 API
        try:
            from src.api.v1.resource_optimization import router as resource_opt_router
            app.include_router(resource_opt_router, prefix='/api/v1/resource-optimization',
                               tags=['resource-optimization'])
            print(f"{worker_info} [OK] Resource Optimization API 已加载")
        except ImportError as e:
            print(f"Warning: Resource Optimization API could not be loaded: {e}")

        # 图片懒加载 API
        try:
            from src.api.v1.image_lazy_load import router as lazy_load_router
            app.include_router(lazy_load_router, prefix='/api/v1/image-lazy-load', tags=['image-lazy-load'])
            print(f"{worker_info} [OK] Image Lazy Load API 已加载")
        except ImportError as e:
            print(f"Warning: Image Lazy Load API could not be loaded: {e}")

        # 性能监控 API
        try:
            from src.api.v1.performance_monitor import router as perf_monitor_router
            app.include_router(perf_monitor_router, prefix='/api/v1/performance-monitor', tags=['performance-monitor'])
            print(f"{worker_info} [OK] Performance Monitor API 已加载")
        except ImportError as e:
            print(f"Warning: Performance Monitor API could not be loaded: {e}")

        # 慢查询日志 API
        try:
            from src.api.v1.slow_query_log import router as slow_query_router
            app.include_router(slow_query_router, prefix='/api/v1/slow-query', tags=['slow-query'])
            print(f"{worker_info} [OK] Slow Query Log API 已加载")
        except ImportError as e:
            print(f"Warning: Slow Query Log API could not be loaded: {e}")

        # HTTP/2 配置 API
        try:
            from src.api.v1.http2_config import router as http2_router
            app.include_router(http2_router, prefix='/api/v1/http2', tags=['http2'])
            print(f"{worker_info} [OK] HTTP/2 Config API 已加载")
        except ImportError as e:
            print(f"Warning: HTTP/2 Config API could not be loaded: {e}")

        # 翻译进度 API
        try:
            from src.api.v1.translation_progress import router as translation_router
            app.include_router(translation_router, prefix='/api/v1/translation', tags=['translation'])
            print(f"{worker_info} [OK] Translation Progress API 已加载")
        except ImportError as e:
            print(f"Warning: Translation Progress API could not be loaded: {e}")

        # 异常行为检测 API
        try:
            from src.api.v1.anomaly_detection import router as anomaly_router
            app.include_router(anomaly_router, prefix='/api/v1/anomaly-detection', tags=['anomaly-detection'])
            print(f"{worker_info} [OK] Anomaly Detection API 已加载")
        except ImportError as e:
            print(f"Warning: Anomaly Detection API could not be loaded: {e}")

        # 安全事件告警 API
        try:
            from src.api.v1.security_alert import router as alert_router
            app.include_router(alert_router, prefix='/api/v1/security-alert', tags=['security-alert'])
            print(f"{worker_info} [OK] Security Alert API 已加载")
        except ImportError as e:
            print(f"Warning: Security Alert API could not be loaded: {e}")

        # 打赏系统 API
        try:
            from src.api.v1.tipping_system import router as tipping_router
            app.include_router(tipping_router, prefix='/api/v1', tags=['tips'])
            print(f"{worker_info} [OK] Tipping System API 已加载")
        except ImportError as e:
            print(f"Warning: Tipping System API could not be loaded: {e}")

        # 广告管理系统 API
        try:
            from src.api.v1.advertisement_system import router as ads_router
            app.include_router(ads_router, prefix='/api/v1', tags=['advertisements'])
            print(f"{worker_info} [OK] Advertisement System API 已加载")
        except ImportError as e:
            print(f"Warning: Advertisement System API could not be loaded: {e}")

        # 安全报告 API
        try:
            from src.api.v1.security_report import router as report_router
            app.include_router(report_router, prefix='/api/v1/security-report', tags=['security-report'])
            print(f"{worker_info} [OK] Security Report API 已加载")
        except ImportError as e:
            print(f"Warning: Security Report API could not be loaded: {e}")

        # 内容审批工作流 API
        try:
            from src.api.v1.content_approval import router as approval_router
            app.include_router(approval_router, prefix='/api/v1/approval', tags=['approval'])
            print(f"{worker_info} [OK] Content Approval API 已加载")
        except ImportError as e:
            print(f"Warning: Content Approval API could not be loaded: {e}")

        # 团队评论 API
        try:
            from src.api.v1.team_comments import router as team_comment_router
            app.include_router(team_comment_router, prefix='/api/v1/team-comments', tags=['team-comments'])
            print(f"{worker_info} [OK] Team Comments API 已加载")
        except ImportError as e:
            print(f"Warning: Team Comments API could not be loaded: {e}")

        # 速率限制管理 API
        try:
            from src.api.v1.rate_limit import router as rate_limit_router
            app.include_router(rate_limit_router, prefix='/api/v1/rate-limit', tags=['rate-limit'])
            print(f"{worker_info} [OK] Rate Limit API 已加载")
        except ImportError as e:
            print(f"Warning: Rate Limit API could not be loaded: {e}")

        # 页面性能追踪 API
        try:
            from src.api.v1.performance_tracking import router as performance_router
            app.include_router(performance_router, prefix='/api/v1/performance-tracking', tags=['performance-tracking'])
            print(f"{worker_info} [OK] Performance Tracking API 已加载")
        except ImportError as e:
            print(f"Warning: Performance Tracking API could not be loaded: {e}")

        # 翻译导出/导入 API
        try:
            from src.api.v1.translation_io import router as translation_io_router
            app.include_router(translation_io_router, prefix='/api/v1/translation-io', tags=['translation-io'])
            print(f"{worker_info} [OK] Translation I/O API 已加载")
        except ImportError as e:
            print(f"Warning: Translation I/O API could not be loaded: {e}")

        # SEO管理 API
        try:
            from src.api.v1.seo_management import router as seo_router
            app.include_router(seo_router, prefix='/api/v1/seo', tags=['seo'])
            print(f"{worker_info} [OK] SEO Management API 已加载")
        except ImportError as e:
            print(f"Warning: SEO Management API could not be loaded: {e}")

        # 备份管理 API
        try:
            from src.api.v1.backup_management import router as backup_router
            app.include_router(backup_router, prefix='/api/v1/backup', tags=['backup'])
            print(f"{worker_info} [OK] Backup Management API 已加载")
        except ImportError as e:
            print(f"Warning: Backup Management API could not be loaded: {e}")

        # 增量备份 API
        try:
            from src.api.v1.incremental_backup import router as incremental_backup_router
            app.include_router(incremental_backup_router, prefix='/api/v1', tags=['incremental-backup'])
            print(f"{worker_info} [OK] Incremental Backup API 已加载")
        except ImportError as e:
            print(f"Warning: Incremental Backup API could not be loaded: {e}")

        # 数据库迁移工具 API
        try:
            from src.api.v1.database_migration import router as database_migration_router
            app.include_router(database_migration_router, prefix='/api/v1', tags=['database-migration'])
            print(f"{worker_info} [OK] Database Migration API 已加载")
        except ImportError as e:
            print(f"Warning: Database Migration API could not be loaded: {e}")

        # GDPR合规 API
        try:
            from src.api.v1.gdpr_compliance import router as gdpr_router
            app.include_router(gdpr_router, prefix='/api/v1/gdpr', tags=['gdpr'])
            print(f"{worker_info} [OK] GDPR Compliance API 已加载")
        except ImportError as e:
            print(f"Warning: GDPR Compliance API could not be loaded: {e}")

        # 无障碍性审计 API
        try:
            from src.api.v1.accessibility_audit import router as accessibility_router
            app.include_router(accessibility_router, prefix='/api/v1/accessibility', tags=['accessibility'])
            print(f"{worker_info} [OK] Accessibility Audit API 已加载")
        except ImportError as e:
            print(f"Warning: Accessibility Audit API could not be loaded: {e}")

        # CDN管理 API
        try:
            from src.api.v1.cdn_management import router as cdn_router
            app.include_router(cdn_router, prefix='/api/v1/cdn', tags=['cdn'])
            print(f"{worker_info} [OK] CDN Management API 已加载")
        except ImportError as e:
            print(f"Warning: CDN Management API could not be loaded: {e}")

        # IPFS 去中心化存储 API
        try:
            from src.api.v1.ipfs import router as ipfs_router
            app.include_router(ipfs_router, prefix='/api/v1', tags=['ipfs'])
            print(f"{worker_info} [OK] IPFS API 已加载")
        except ImportError as e:
            print(f"Warning: IPFS API could not be loaded: {e}")

        env_key = f"ROUTER_PRINTED_{os.getpid()}"

        if not os.environ.get(env_key):
            print(f"{worker_info} [OK] API v1 路由已加载 (FastAPI 原生)")
            os.environ[env_key] = "1"
    except ImportError as e:
        print(f"警告：API v1 路由加载失败：{e}")

    # 挂载静态文件目录
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    os.makedirs(static_dir, exist_ok=True)  # 确保目录存在
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # 挂载本地存储目录,用于访问本地存储的媒体文件
    try:
        from src.setting import app_config
        local_storage_path = getattr(app_config, 'LOCAL_STORAGE_PATH', 'storage')
    except Exception:
        # 如果配置获取失败,使用默认路径
        local_storage_path = 'storage'

    os.makedirs(local_storage_path, exist_ok=True)  # 确保目录存在
    app.mount("/local-storage", StaticFiles(directory=local_storage_path), name="local-storage")

    # 挂载 storage/objects 目录,用于直接访问媒体文件和缩略图
    objects_dir = os.path.join(local_storage_path, 'objects')
    os.makedirs(objects_dir, exist_ok=True)
    app.mount("/storage/objects", StaticFiles(directory=objects_dir), name="storage-objects")

    # 挂载 themes 目录,用于提供主题样式文件
    themes_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "themes")
    if os.path.exists(themes_dir):
        app.mount("/themes", StaticFiles(directory=themes_dir), name="themes")

    # 返回创建的应用实例
    return app


def register_routes(app: FastAPI, config_class):
    """注册应用路由 - 现在主要通过include_router实现"""

    # 为其他前端路由添加通配符处理，但要排除已知的后端路径
    @app.get('/{full_path:path}', response_class=HTMLResponse)
    async def spa_fallback(request: Request, full_path: str):
        # 排除API路径和其他已知的后端路径,这些应该返回404或正常处理
        excluded_paths = [
            'api', 'static', 'local-storage', 'storage', 'shared', 'thumbnail',
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
                return HTMLResponse(
                    content="<!DOCTYPE html><html><head><title>Blog</title></head><body><div id='app'></div></body></html>")
        except Exception:
            # 如果读取页面文件失败，返回一个简单的默认页面
            return HTMLResponse(
                content="<!DOCTYPE html><html><head><title>Blog</title></head><body><div id='app'></div></body></html>")

    # Catch-all 路由 - 处理所有未匹配的路径
    @app.get("/{path:path}")
    @app.post("/{path:path}")
    @app.put("/{path:path}")
    @app.delete("/{path:path}")
    async def catch_all(request: Request, path: str):
        """捕获所有未匹配的路由，返回404并触发插件钩子"""
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")

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
        from datetime import datetime

        # 准备404错误数据
        error_data = {
            'url': str(request.url),
            'ip': request.client.host if request.client else '',
            'referrer': request.headers.get('referer', ''),
            'user_agent': request.headers.get('user-agent', ''),
            'method': request.method,
            'timestamp': datetime.now().isoformat(),
        }

        # 触发404事件（action）- 直接同步调用
        try:
            print(f"[404Handler] Triggering response_404 hook for: {error_data['url']}")
            plugin_hooks.do_action_sync('response_404', error_data)
            print(f"[404Handler] response_404 hook completed")
        except Exception as e:
            print(f"[Plugin] Failed to trigger response_404 event: {e}")
            import traceback
            traceback.print_exc()

        # 触发插件钩子 - 允许插件拦截或修改404响应
        try:
            response_data = plugin_hooks.apply_filters('response_404', error_data)

            # 检查是否有插件拦截并返回了自定义HTML
            if isinstance(response_data, dict) and response_data.get('intercepted'):
                from fastapi.responses import HTMLResponse

                html_content = response_data.get('html_content', '')
                status_code = response_data.get('status_code', 404)
                content_type = response_data.get('content_type', 'text/html; charset=utf-8')

                if html_content:
                    print(f"[404Handler] Plugin returned custom HTML for: {error_data['url']}")
                    return HTMLResponse(
                        content=html_content,
                        status_code=status_code,
                        headers={'Content-Type': content_type}
                    )

            # 如果插件没有拦截，使用默认404页面
            return error(404, "Page Not Found")

        except Exception as e:
            print(f"[Plugin Hook Error] Failed to process 404 hooks: {e}")
            import traceback
            traceback.print_exc()
            # 出错时使用默认404页面
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
        # 某些错误类型应该显示为 404 页面而非 500 错误
        error_msg = str(exc)
        # 检查是否是常见的导致 404 的错误
        if "not found" in error_msg.lower() or "no result" in error_msg.lower() or "does not exist" in error_msg.lower():
            return error(404, "Page Not Found")
        # 其他未预期的错误应该返回 500
        return error(500, "Internal Server Error")


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
    if config_class.SECRET_KEY == 'your-secret-key-change-in-production':
        logger.critical("CRITICAL: 你若生产模式下使用默认SECRET_KEY运行将存在严重安全风险！！！")
        logger.critical("CRITICAL: 请修改 SECRET_KEY 环境变量的值")
        logger.critical("CRITICAL: 请修改 SECRET_KEY 环境变量的值")
        logger.critical("CRITICAL: 请修改 SECRET_KEY 环境变量的值")

    logger.info("++++++++++==========================++++++++++")


# 创建全局应用实例（供 uvicorn 直接导入使用）
# 这样可以通过 `uvicorn src.app:app` 启动服务
try:
    from src.setting import ProductionConfig

    _default_config = ProductionConfig()
    app = create_app(_default_config)
except Exception as e:
    import traceback

    print(f"Warning: Failed to create global app instance: {e}")
    traceback.print_exc()
    app = None
