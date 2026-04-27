# FastBlog 技术架构

**版本**: V0.0.2.0 | **Python**: 3.14+ | **FastAPI**: 0.136+ | **Django**: 6.0.4+

## 🏗️ 系统架构

### 双后端架构

```
┌─────────────────────────────────┐
│       main.py (启动器)          │
│   --backend fastapi|django     │
└───────────────┬─────────────────┘
                │
        ┌───────┴────────┐
        ▼                ▼
┌──────────────┐  ┌──────────────┐
│   FastAPI    │  │    Django    │
│   (异步)     │  │   (同步)     │
└──────────────┘  └──────────────┘
        │                │
        └───────┬────────┘
                ▼
      ┌─────────────────┐
      │ PostgreSQL 17+  │
      └─────────────────┘
```

**对比**:

| 特性 | FastAPI | Django |
|------|---------|--------|
| 性能 | 高（异步） | 中（同步） |
| 后台管理 | 需自开发 | 内置 Admin |
| ORM | SQLAlchemy | Django ORM |
| 适用场景 | API/微服务 | 企业应用 |

### 进程监督器

```
SupervisedLauncher
    └─ ProcessSupervisor
        ├─ UpdateChecker
        ├─ Main App
        └─ Updater (按需)
```

**优势**: 自动故障恢复、进程隔离、统一管理

## 📐 项目结构

### 后端

```
src/ (FastAPI)
├── api/v1/           # API 接口
├── models/           # 数据模型
├── services/         # 业务逻辑
└── utils/            # 工具函数

apps/ (Django)
├── user/             # 用户认证
├── blog/             # 博客文章
├── category/         # 分类管理
└── media/            # 媒体文件
```

### 前端

```
frontend-next/
├── app/              # 页面路由
├── components/       # UI 组件
├── hooks/            # 自定义 Hooks
└── lib/              # 工具库
```

## 🔧 技术栈

### 前端
- Next.js 16 / TypeScript / TailwindCSS

### 后端
- **FastAPI**: 0.136+ / Python 3.14+ / SQLAlchemy (异步)
- **Django**: 6.0.4+ / Python 3.14+ / Django ORM
- **数据库**: PostgreSQL 17+ / Redis 7+

### 部署
- Docker / Nginx / Gunicorn/Uvicorn

## 💻 开发环境

### 系统要求
- Python 3.14+
- Node.js 18+
- PostgreSQL 17+
- **最低配置**: 4核4G (生产推荐)

### 快速开始
详见 [QUICK_START.md](QUICK_START.md)

## 🔍 核心组件

### 1. 双后端
- FastAPI Adapter: 路由适配层
- 统一路由代码: `src/api/v1/*.py`

### 2. 进程管理
- SupervisedLauncher: 主启动器
- ProcessSupervisor: 生命周期管理

### 3. 业务功能
- 文章/用户/评论/媒体管理
- 插件系统 (Hook 机制)
- 主题系统 (自定义配置)

## 🛡️ 安全架构

- JWT Token + RBAC 权限控制
- 输入验证和 SQL 注入防护
- HTTPS/TLS 加密

## 📚 相关文档

- [快速开始](QUICK_START.md)
- [插件开发](PLUGIN_DEVELOPMENT_GUIDE.md)
- [主题开发](THEME_DEVELOPMENT_GUIDE.md)
- [部署指南](DEPLOYMENT_GUIDE.md)