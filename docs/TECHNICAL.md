# FastBlog 技术架构

> **版本**: V0.3.26.0521 | **后端**: FastAPI 0.128.0 / Python 3.14+ | **前端**: Astro 5.7 / React 19 | **数据库**:
> PostgreSQL 16+ / Redis 7+

---

## 🏗️ 系统架构

### 单后端架构（FastAPI Only）

```
┌─────────────────────────────────────┐
│         main.py (启动器)            │
│   --backend fastapi --port 9421     │
└───────────────┬─────────────────────┘
                │
                ▼
    ┌───────────────────────┐
    │     FastAPI (异步)     │
    │   API v1 / v2 / v3   │
    └───────────┬───────────┘
                │
        ┌───────┴───────┐
        ▼               ▼
┌──────────────┐ ┌──────────────┐
│ PostgreSQL   │ │    Redis     │
│   (主数据)    │ │  (缓存/会话) │
└──────────────┘ └──────────────┘
```

**说明**: FastBlog 采用 **纯 FastAPI** 后端架构，所有业务逻辑通过 FastAPI 异步框架实现。项目中 `apps/` 目录为历史遗留（Django
模型层），当前主服务完全由 `src/` 目录驱动。

### 进程监督器

```
main.py
    └─ ProcessSupervisor (可选)
        ├─ UpdateChecker (自动更新)
        ├─ Main App (FastAPI Uvicorn)
        └─ Updater (按需)
```

**优势**: 自动故障恢复、进程隔离、统一管理

### API 版本策略

| 版本 | 路径前缀              | 状态     | 说明             |
|----|-------------------|--------|----------------|
| V1 | `/api/v1/`        | ⚠️ 已废弃 | 通过中间件自动重定向到 V2 |
| V2 | `/api/v2/`        | ✅ 主要   | 所有 Web 端 API   |
| V3 | `/api/v3/mobile/` | ✅ 可用   | 移动端专用 API      |

---

## 📐 项目结构

### 后端（FastAPI）

```
src/
├── api/
│   ├── v1/               # V1 API（已废弃，自动重定向到V2）
│   ├── v2/               # V2 API（主要）— 包结构，每个模块为子目录
│   │   ├── articles/     # 文章管理
│   │   ├── dashboard/    # 仪表盘
│   │   ├── users/        # 用户管理
│   │   ├── plugins/      # 插件管理
│   │   ├── seo/          # SEO 追踪
│   │   └── ...           # 其他模块
│   └── v3/mobile/        # V3 移动端 API
├── auth/                 # 认证与授权（JWT、RBAC、2FA）
├── middleware/            # 中间件（限流、缓存、多站点等）
├── mcp/                  # MCP Server（Model Context Protocol）
├── utils/                # 工具函数（数据库、安全、图片处理等）
├── services/             # 服务层（Redis 等）
├── app.py                # FastAPI 应用工厂
├── setting.py            # 配置管理
├── extensions.py         # 扩展初始化（缓存、密码哈希等）
└── scheduler.py          # 定时任务（APScheduler）
```

### 共享服务

```
shared/
├── services/
│   ├── plugins/          # 插件系统核心（BasePlugin、PluginHook、PluginManager）
│   ├── articles/         # 文章服务（搜索、分析、定时发布等）
│   ├── ai/               # AI 集成
│   ├── performance/      # 性能优化（CDN、资源优化）
│   └── ops/              # 运维（备份、健康检查）
└── utils/                # 公共工具（日志、验证、国际化等）
```

### 前端（Astro + React）

```
frontend-astro/
├── src/
│   ├── components/       # React 组件（岛屿 Island）
│   │   ├── pages/        # 页面级组件
│   │   └── admin/        # 管理后台组件
│   ├── layouts/          # Astro 布局组件
│   ├── pages/            # Astro 页面路由（SSG）
│   ├── lib/              # API 客户端、工具库
│   └── styles/           # 全局样式（TailwindCSS）
├── public/               # 静态资源
└── astro.config.mjs      # Astro 配置
```

---

## 🔧 技术栈详情

### 后端

| 组件       | 技术                        | 版本      |
|----------|---------------------------|---------|
| Web 框架   | FastAPI                   | 0.128.0 |
| ASGI 服务器 | Uvicorn                   | -       |
| ORM      | SQLAlchemy 2.0 (async)    | -       |
| 数据库驱动    | asyncpg (PostgreSQL)      | -       |
| 数据库      | PostgreSQL                | 16+     |
| 缓存       | Redis                     | 7+      |
| 认证       | PyJWT + Cookie/Bearer 双模式 | -       |
| 2FA      | TOTP (pyotp)              | -       |
| 定时任务     | APScheduler               | -       |
| 搜索引擎     | Meilisearch (可选)          | -       |
| 任务队列     | Redis 队列                  | -       |

### 前端

| 组件    | 技术                       | 版本  |
|-------|--------------------------|-----|
| 框架    | Astro (SSG 岛屿架构)         | 5.7 |
| UI 库  | React                    | 19  |
| 数据获取  | @tanstack/react-query    | -   |
| 样式    | TailwindCSS              | 4.x |
| UI 组件 | Radix UI                 | -   |
| 富文本编辑 | TipTap                   | -   |
| 图标    | Lucide Icons / Heroicons | -   |
| 构建工具  | Vite (Astro 内置)          | -   |
| 测试    | Vitest + Playwright      | -   |

### 基础设施

| 组件    | 技术                      |
|-------|-------------------------|
| 容器化   | Docker + Docker Compose |
| 反向代理  | Nginx                   |
| SSL   | Let's Encrypt (Certbot) |
| CI/CD | GitHub Actions          |
| 进程管理  | 自定义 ProcessSupervisor   |

---

## 💻 开发环境

### 系统要求

- **Python**: 3.14+
- **Node.js**: 18+
- **PostgreSQL**: 16+
- **Redis**: 7+
- **最低配置**: 4核4G（生产推荐 4核8G）

### 快速开始

详见 [QUICK_START.md](QUICK_START.md)

---

## 🔍 核心组件

### 1. FastAPI 后端

- **应用工厂**: [`src/app.py`](../src/app.py) — `create_app()` 创建 FastAPI 实例
- **路由注册**: V2 路由通过 [`src/api/v2/__init__.py`](../src/api/v2/__init__.py) 的 `ROUTE_REGISTRY_V2` 统一注册
- **认证系统**: JWT + Cookie/Bearer 双模式，支持 TOTP 2FA
- **权限系统**: RBAC 角色/权限控制

### 2. 插件系统

- **基类**: `shared.services.plugins.plugin_manager.core.BasePlugin`
- **钩子系统**: WordPress 风格的 `do_action` / `apply_filters`
- **管理器**: `PluginManager` 负责发现、加载、激活插件
- **沙箱**: `PluginSandbox` 提供安全隔离
- 详见 [PLUGIN_DEVELOPMENT_GUIDE.md](PLUGIN_DEVELOPMENT_GUIDE.md)

### 3. 前端架构

- **Astro SSG**: 零 JavaScript 默认策略，静态生成 + 按需 hydration
- **React Islands**: 交互组件按需加载
- **@tanstack/react-query**: 数据获取与缓存管理
- **TipTap Editor**: 富文本编辑器
- 极致性能和 SEO 优化

### 4. 主题系统

- **3 个内置主题**: default、magazine、modern-minimal
- **配置文件**: `metadata.json` + `theme.json` + `theme.config.js`
- **样式**: TailwindCSS + CSS 变量
- 详见 [THEME_DEVELOPMENT_GUIDE.md](THEME_DEVELOPMENT_GUIDE.md)

### 5. MCP Server

- **协议**: Model Context Protocol
- **资源**: 文章、分类、用户、媒体、设置
- **工具**: 创建/更新/删除文章、搜索、SEO 描述生成
- 详见 [`src/mcp/server.py`](../src/mcp/server.py)

---

## 🛡️ 安全架构

| 层级   | 措施                                             |
|------|------------------------------------------------|
| 认证   | JWT (access + refresh token)、Cookie/Bearer 双模式 |
| 授权   | RBAC 角色权限、VIP 等级控制                             |
| 2FA  | TOTP 双因素认证                                     |
| 输入验证 | Pydantic 模型验证、SQL 注入防护                         |
| 传输安全 | HTTPS/TLS、Nginx SSL 终结                         |
| 速率限制 | Nginx + FastAPI 中间件双层限流                        |
| 审计   | 操作日志审计（PluginAuditLogger）                      |
| 零信任  | Zero Trust 中间件                                 |

---

## 📚 相关文档

- [快速开始](QUICK_START.md)
- [API 参考](API_REFERENCE.md)
- [部署指南](DEPLOYMENT_GUIDE.md)
- [插件开发](PLUGIN_DEVELOPMENT_GUIDE.md)
- [主题开发](THEME_DEVELOPMENT_GUIDE.md)
