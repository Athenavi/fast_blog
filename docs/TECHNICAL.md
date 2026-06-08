# FastBlog 技术架构

> **版本**: V0.3.26.0521 | **后端**: FastAPI 0.136 / Python 3.14+ | **前端**: Astro 5.7 / React 19 | **数据库**: PostgreSQL 16+ / Redis 7+

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

### API 版本策略

| 版本 | 路径前缀 | 状态 | 说明 |
|------|---------|------|------|
| V1 | `/api/v1/` | ⚠️ 已废弃 | 自动重定向到 V2 |
| V2 | `/api/v2/` | ✅ 主要 | Web 端 API |
| V3 | `/api/v3/mobile/` | ✅ 可用 | 移动端专用 API |

---

## 📐 项目结构

### 后端（FastAPI）
```
src/
├── api/
│   ├── v1/               # V1 API（已废弃，自动重定向到V2）
│   ├── v2/               # V2 API（主要）
│   └── v3/mobile/        # V3 移动端 API
├── auth/                 # 认证与授权（JWT、RBAC、2FA）
├── middleware/            # 中间件（限流、缓存等）
├── mcp/                  # MCP Server
├── utils/                # 工具函数
├── services/             # 服务层
├── app.py                # FastAPI 应用工厂
├── setting.py            # 配置管理
└── extensions.py         # 扩展初始化
```

### 共享服务
```
shared/
├── services/
│   ├── plugins/          # 插件系统核心
│   ├── articles/         # 文章服务
│   ├── ai/               # AI 集成
│   ├── performance/      # 性能优化
│   └── ops/              # 运维（备份、健康检查）
└── utils/                # 公共工具
```

### 前端（Astro + React）
```
frontend-astro/
├── src/
│   ├── components/       # React 组件（Island）
│   ├── layouts/          # Astro 布局组件
│   ├── pages/            # Astro 页面路由（SSG）
│   ├── lib/              # API 客户端、工具库
│   └── styles/           # 全局样式
├── public/               # 静态资源
└── astro.config.mjs      # Astro 配置
```

---

## 🔧 技术栈

- **后端**: FastAPI / Uvicorn / SQLAlchemy 2.0 / asyncpg / Redis
- **前端**: Astro (SSG) / React 19 / TailwindCSS 4.x / TanStack React Query / TipTap
- **基础设施**: Docker / Nginx / GitHub Actions
- **集成**: Meilisearch / Sentry / S3 兼容存储

---

## 🔍 核心组件

### 1. FastAPI 后端
- **应用工厂**: [`src/app.py`](../src/app.py) — `create_app()` 创建 FastAPI 实例
- **路由注册**: V2 路由通过 [`src/api/v2/__init__.py`](../src/api/v2/__init__.py) 的 `ROUTE_REGISTRY_V2` 注册
- **认证系统**: JWT + Cookie/Bearer 双模式，支持 TOTP 2FA

### 2. 插件系统
- **基类**: `BasePlugin` — WordPress 风格 `do_action` / `apply_filters`
- **管理器**: `PluginManager` 负责发现、加载、激活插件
- 详见 [PLUGIN_DEVELOPMENT_GUIDE.md](PLUGIN_DEVELOPMENT_GUIDE.md)

### 3. 前端架构
- **Astro SSG**: 零 JavaScript 默认策略，静态生成 + 按需 hydration
- **React Islands**: 交互组件按需加载
- **@tanstack/react-query**: 数据获取与缓存管理

### 4. 主题系统
- **3 个内置主题**: default、magazine、modern-minimal
- **配置**: `metadata.json` + `theme.json` + `theme.config.js`
- 详见 [THEME_DEVELOPMENT_GUIDE.md](THEME_DEVELOPMENT_GUIDE.md)

### 5. MCP Server
- Model Context Protocol，支持文章、分类、用户、媒体资源管理
- 详见 [`src/mcp/server.py`](../src/mcp/server.py)

---

## 🛡️ 安全架构

| 层级 | 措施 |
|------|------|
| 认证 | JWT (access + refresh token)、Cookie/Bearer 双模式 |
| 授权 | RBAC 角色权限、VIP 等级控制 |
| 2FA | TOTP 双因素认证 |
| 输入验证 | Pydantic 模型验证、SQL 注入防护 |
| 传输安全 | HTTPS/TLS、Nginx SSL 终结 |
| 速率限制 | Nginx + FastAPI 中间件双层限流 |

---

## 📚 相关文档

- [快速开始](QUICK_START.md)
- [API 参考](API_REFERENCE.md)
- [部署指南](DEPLOYMENT_GUIDE.md)
- [插件开发](PLUGIN_DEVELOPMENT_GUIDE.md)
- [主题开发](THEME_DEVELOPMENT_GUIDE.md)
