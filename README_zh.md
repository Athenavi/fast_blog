<div align="center">

# FastBlog

### ⚡ 面向开发者的现代化高性能博客平台

[![CI Status](https://github.com/Athenavi/fast_blog/actions/workflows/ci.yml/badge.svg)](https://github.com/Athenavi/fast_blog/actions/workflows/ci.yml)
[![Release](https://github.com/Athenavi/fast_blog/actions/workflows/release.yml/badge.svg)](https://github.com/Athenavi/fast_blog/actions/workflows/release.yml)
[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136.3-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Astro](https://img.shields.io/badge/Astro-5.x-BC52EE.svg?logo=astro&logoColor=white)](https://astro.build/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](./LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker&logoColor=white)](https://github.com/Athenavi/fast_blog/pkgs/container/fastblog)

[English](README.md) | **中文**

[🚀 快速开始](#-快速开始) · [📖 文档](#-文档) · [🎯 特性](#-特性) · [🤝 参与贡献](#-参与贡献)

</div>

---

## 🎯 特性

- **FastAPI 后端** — 异步 Web 框架，自动生成 API 文档
- **Astro 前端** — 岛屿架构，默认零 JavaScript，极速首屏加载
- **插件系统** — EventBus 事件驱动架构，无需修改核心代码
- **富文本编辑器** — 基于 TipTap 的所见即所得编辑器
- **主题引擎** — 支持热切换的 Astro 主题
- **JWT + OAuth2** — Cookie/Bearer 双模式认证，支持 2FA (TOTP)
- **RBAC 权限** — 细粒度的角色权限控制系统
- **全文搜索** — Meilisearch 集成
- **SEO 工具包** — 自动站点地图、元标签、结构化数据
- **PWA 支持** — 可安装为本地应用，支持离线使用
- **多语言** — 国际化支持与翻译管理

---

## 🚀 快速开始

```bash
# Docker 部署（推荐）
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog
cp .env.example .env
# 编辑 .env：设置 SECRET_KEY / JWT_SECRET_KEY（>=32 位随机）与数据库密码
docker compose up -d
```

> 生产部署请使用 `docker compose -f docker-compose.prod.yml up -d`（强制要求显式密钥，自动启用多 worker + Redis）。

详细的手动部署指南请参阅[快速开始文档](docs/getting-started.md)。

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [快速开始](docs/getting-started.md) | 安装和部署指南 |
| [部署指南](docs/deployment.md) | 生产部署、Nginx 安全、SSL |
| [开发指南](docs/development.md) | 系统架构、插件、主题、API |
| [运维手册](docs/operations.md) | 故障排查、AI/MCP、移动端 |

> 完整 API 参考由运行中的服务自动生成：`http://localhost:9421/api/v2/docs`（Swagger UI）

---

## 🤝 参与贡献

欢迎各种形式的贡献！在提交 PR 前请阅读[贡献指南](docs/development.md#二贡献规范)。

---

## 📄 许可证

本项目基于 **Apache License 2.0** 许可 — 详见 [LICENSE](LICENSE) 文件。

---

<div align="center">

**如果您觉得 FastBlog 有用，请在 GitHub 上给我们一个 ⭐！**

[⬆ 返回顶部](#fastblog)

</div>
