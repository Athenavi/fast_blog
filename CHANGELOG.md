# Changelog / 更新日志

All notable changes to FastBlog will be documented in this file.

格式基于 [Keep a Changelog](https://keepachangelog.com/)，
此项目遵循 [语义化版本](https://semver.org/)。

---

## [Unreleased]

### Added
- Bilingual documentation (English & Chinese)
- Comprehensive CI/CD pipeline
- Docker Compose production configuration
- Security policy documentation
- MCP (Model Context Protocol) Server for AI integration

### Changed
- Improved project documentation structure
- Updated all documentation to reflect current architecture

---

## [0.6.26.0611] - 2026-06-11

### 重构 / Refactor

- 🔥 **插件系统全面重构** — 删除旧 PluginHook，替换为 EventBus（观察者模式）
    - 新增 `shared/services/plugins/event_bus.py`（emit 广播 + pipeline 管道）
    - BasePlugin 新增 `subscribers()` + SQLite 持久化助手
    - 删除 14 个重复/脚手架插件，保留 code-snippets 和 newsletter
- 🆕 **新增 Newsletter 插件** — SQLite 持久化 + EventBus 自动推送
- 🆕 **code-snippets 前端管理页** — 完整的 CRUD + 嵌入代码复制
- 🆕 **前端插件引擎** — 构建时自动扫描 `plugins/*/frontend/`
    - 自动生成 Astro 代理页面和侧边栏菜单
- **SSR 迁移** — 首页/文章列表/文章详情/分类页 4 页 SSR
    - `@astrojs/node` adapter，React 组件接受 SSR initial props

### V2 API 接入 EventBus

- 文章创建 → `article.published` | 文章更新 → `article.updated`
- 文章详情 → `article.content` 管道 | 评论创建 → `comment.created`

---

## [V0.3.26.0521] - 2026-05-21

### Added

- MCP Server for AI-powered content management
- Multi-site support with domain-based routing
- Zero-trust security middleware
- Performance monitoring middleware
- Accessibility optimizer
- Plugin hot-reload system (hot_load, hot_unload, hot_reload)
- Plugin dependency resolver with circular dependency detection
- Plugin manifest validator with template generation
- Mobile API V3 with dedicated endpoints
- Capacitor mobile app framework integration
- JavaScript SDK for frontend integration
- Python SDK with async client support
- Update server with backup/restore functionality
- Process supervisor for multi-process management
- Unified database manager with async session management
- SEO traffic tracking and keyword analysis
- Article view statistics service
- Token blacklist for JWT revocation
- Rate limiting middleware with configurable zones

### Changed

- Migrated from Django backend to pure FastAPI
- Upgraded to FastAPI 0.128.0
- Upgraded to Python 3.14+
- Upgraded to PostgreSQL 16+
- Upgraded to Astro 5.7 frontend with React 19 Islands
- Upgraded to TailwindCSS 4.x
- Plugin system imports moved to `shared.services.plugins.plugin_manager.core`
- Theme system migrated from Jinja2 to Astro components
- API routes restructured: V1 (deprecated, auto-redirects), V2 (primary), V3 (mobile)
- Static resource paths unified under `/assets/` prefix

### Removed

- Django backend support (V0.2+)
- Jinja2 template engine (replaced by Astro)
- Flask compatibility layer

---

## [0.0.2.0] - 2026-04-01

### 优化 / Optimize

- 📝 **文档优化** - 精简和合并项目文档，统一版本信息
- 🔧 **版本管理** - 统一所有文档的版本标识

---

## [0.0.1.0] - 2026-03-26

### 新增 / Added

- 🚀 **FastAPI + Django 双后端架构** - 支持命令行参数切换 (`--backend fastapi|django`)
- 💡 **FastAPI 模式** - 异步非阻塞 IO，自动 API 文档生成（Swagger/ReDoc）
- 🏗️ **Django 模式** - 内置 Admin 后台管理系统

### 改进 / Improved

- 🔧 **启动器优化** - 统一的双后端启动流程

### 技术栈 / Tech Stack

- **后端**: FastAPI 0.100+ / Django 4.2+ / PostgreSQL 14+
- **前端**: Next.js 15 / TypeScript / TailwindCSS

---

## [0.0.0.2] - 2026-02-12

### 新增 / Added

- 🚀 **独立更新系统** - 启动器模式架构
- 🔧 **进程安全管理** - 完全独立的进程架构
- 📊 **系统监控** - 完善的进程状态监控

### 修复 / Fixed

- 🐛 **稳定性修复** - 解决 Windows/Linux/macOS 平台问题

---

## [0.0.0] - 2025-11-01

### 新增 / Added

- 🚀 **初始发布** - FastBlog 内部谋划中
- 完整的博客系统功能
- 用户管理和权限控制
- 文章发布和编辑功能
- 评论系统集成

---

[Unreleased]: https://github.com/Athenavi/fast_blog/compare/main...HEAD

[V0.3.26.0521]: https://github.com/Athenavi/fast_blog/releases/tag/V0.3.26.0521
