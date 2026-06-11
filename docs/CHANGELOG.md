# 更新日志

所有显著的更改都将记录在这个文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且此项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.6.26.0611] - 2026-06-11

### 重构
- 🔥 **插件系统全面重构** — 删除旧 PluginHook，替换为 EventBus（观察者模式）
  - 新增 `shared/services/plugins/event_bus.py`（emit 广播 + pipeline 管道）
  - BasePlugin 新增 `subscribers()` + SQLite 持久化助手
  - 删除 14 个重复/脚手架插件，保留 code-snippets 和 newsletter
- 🆕 **新增 Newsletter 插件** — SQLite 持久化 + EventBus 自动推送
  - 公开订阅/退订，新文章发布时自动发送邮件
  - 前端管理页面（订阅者列表 + 统计）
- 🆕 **code-snippets 前端管理页** — 完整的 CRUD + 嵌入代码复制
- 🆕 **前端插件引擎** — 构建时自动扫描 `plugins/*/frontend/`
  - 自动生成 Astro 代理页面和侧边栏菜单
  - 新插件只需 manifest.json 声明
- **SSR 迁移** — 首页/文章列表/文章详情/分类页 4 页 SSR
  - `@astrojs/node` adapter，React 组件接受 SSR initial props

### V2 API 接入 EventBus
- 文章创建 → `article.published` | 文章更新 → `article.updated`
- 文章详情 → `article.content` 管道 | 评论创建 → `comment.created`

### 文档
- 重写 PLUGIN_DEVELOPMENT_GUIDE.md（EventBus）
- 更新 TECHNICAL.md、QUICK_START.md

## [0.3.26.0520] - 2026-05-20

### 新增

- 🚀 **Astro 前端重构** - 将前端从 Next.js 迁移到 Astro
  - 采用岛屿架构（Islands Architecture）
  - 零 JavaScript 默认策略，极致性能
  - 静态生成 + 按需 hydration
  - Core Web Vitals 显著改善
  - 更好的 SEO 和首屏加载速度

### 优化

- 📝 **文档彻底重构** - 全面清理和精简项目文档
  - 删除重复内容：API示例文件（api_examples.*）已合并到API参考文档
  - 删除过时文档：FFMPEG安装指南、Meilisearch快速开始、资源转存说明
  - 精简QUICK_START.md和DEPLOYMENT_GUIDE.md，去除大量重复内容
  - 更新所有技术栈版本信息（Python 3.14+, FastAPI 0.136+, Django 6.0+, Astro 5.x）
  - 修正过时的版本号和技术描述
  - 简化文档结构，提高可读性
  - 从多个文档精简到核心文档集

---

## [0.0.2.0] - 2026-04-01

### 优化

- 📝 **文档优化** - 精简和合并项目文档
    - 删除重复和不必要的文档内容
    - 简化技术架构文档
  - 统一版本信息

### 改进

- 🔧 **版本管理** - 统一所有文档的版本标识
- 📚 **文档结构** - 优化文档导航和阅读体验

---

## [0.0.1.0] - 2026-03-26

### 新增

- 🚀 **FastAPI + Django 双后端架构** - 支持 FastAPI 和 Django 两种后端框架
    - 通过命令行参数灵活切换 (`--backend fastapi|django`)
    - 创新的适配器层实现代码复用
    - 同一套路由代码在两个后端之间共享
- 💡 **FastAPI 模式** - 高性能异步 API 服务
    - 异步非阻塞 IO（Async/Await）
    - 自动 API 文档生成（Swagger/ReDoc）
    - SQLAlchemy 异步 ORM
- 🏗️ **Django 模式** - 传统 Web 应用框架
    - 内置强大的 Admin 后台管理系统
    - Django ORM 和认证系统

### 改进

- 🔧 **启动器优化** - 统一的双后端启动流程
- 🎯 **开发体验** - 根据场景选择合适后端

### 技术栈更新

- **后端**: FastAPI 0.100+ / Django 4.2+ / PostgreSQL 14+
- **前端**: Next.js 15 / TypeScript / TailwindCSS

---

## [0.0.0.2] - 2026-02-12

### 新增

- 🚀 **独立更新系统** - 实现业界标准的启动器模式架构
- 🔧 **进程安全管理** - 完全独立的进程架构
- 📊 **系统监控** - 完善的进程状态监控

### 修复

- 🐛 **稳定性修复** - 解决 Windows/Linux/macOS平台问题

---

## [0.0.0] - 2025-11-01

### 新增

- 🚀 **初始发布** - FastBlog 内部谋划中
    - 完整的博客系统功能
    - 用户管理和权限控制
    - 文章发布和编辑功能
    - 评论系统集成

---
*最后更新：2026 年 5 月*
