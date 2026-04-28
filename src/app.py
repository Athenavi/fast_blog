"""
主应用文件
负责 FastAPI 应用工厂函数和核心配置"""

import logging
import os
from contextlib import asynccontextmanager
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
from shared.models.schemas.user import UserRead  # FastAPI-Users 需要的 Pydantic 模型


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

    # 添加 CORS 中间件 - 从环境变量读取允许的域名
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

    print(f"[CORS] 允许的源: {allow_origins}")
    print(f"[CORS] Allow credentials: True")

    # 添加 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,  # 允许携带 credentials (cookies)
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*", "Authorization", "Content-Type", "Cookie"],
        expose_headers=["*"],
    )

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

    @app.get("/health",
             summary="健康检查",
             description="检查API服务的健康状态",
             response_description="返回服务状态信息",
             tags=["system"])
    async def health_check():
        return {"status": "healthy"}

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
