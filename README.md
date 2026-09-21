<div align="center">

# FastBlog

### 现代化的自托管博客与内容平台

[![CI](https://github.com/Athenavi/fast_blog/actions/workflows/ci.yml/badge.svg)](https://github.com/Athenavi/fast_blog/actions/workflows/ci.yml)
[![Release](https://github.com/Athenavi/fast_blog/actions/workflows/release.yml/badge.svg)](https://github.com/Athenavi/fast_blog/actions/workflows/release.yml)
[![Version](https://img.shields.io/badge/version-0.8.26.0921-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.14-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136.3-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Nuxt](https://img.shields.io/badge/Nuxt-4.5-00DC82.svg?logo=nuxt&logoColor=white)](https://nuxt.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

**简体中文** | [English](README.en.md)

[快速开始](#快速开始) · [功能](#功能) · [技术栈](#技术栈) · [文档](#文档) · [贡献](#贡献)

</div>

---

## 简介

FastBlog 是一套可自托管的博客 / 内容管理系统：

- **后端**：FastAPI + SQLAlchemy 2（async）+ PostgreSQL + Redis，共 **11 个业务域 / 73 个模块 / 650 条 API**，统一挂在
  `/api/v3` 下；
- **前端**：Nuxt 4.5 **单工程**同时提供博客前台（SSR，面向 SEO）与管理后台（CSR，Element Plus）；
- **开箱能力**：权限体系（角色 / 权限码 / 用户组 / 数据范围）、插件与主题、多平台内容发布、备份与在线升级、
  系统监控、AI 接入（OpenAI 兼容 / Anthropic）、PWA 与移动端外壳。

## 截图

| 文章列表                                 | 文章详情                                     | 媒体库                           |
|--------------------------------------|------------------------------------------|-------------------------------|
| ![文章列表](docs/assets/ArtclesPage.png) | ![文章详情](docs/assets/ArticleViewPage.png) | ![媒体库](docs/assets/media.png) |

## 功能

**内容**：文章 / 页面 / 分类 / 标签、富文本编辑器（TipTap）、媒体库（内容寻址存储 + 私密媒体鉴权）、
评论、自定义文章类型、短代码、页面构建器、内容审批、协同编辑（Yjs）

**系统**：用户 / 角色 / 权限码 / 权限组 / 数据范围、菜单级授权、写操作审计、系统监控（会话与告警）、
缓存管理、日志、敏感词、GDPR 同意记录、扫码安装向导、站点设置、第三方集成、社交账号

**运营**：仪表盘与报表中心、SEO（sitemap / 元数据 / 结构化数据）、全文搜索（Meilisearch）、
备份（全量 / 增量 / S3·OSS 云存储）、CDN 远端操作（阿里云 / 腾讯云 / CloudFront）、邮件、通知、
Webhook、部署与在线升级（含回滚）、进程监督、数据迁移（WordPress WXR 等）

**增长**：VIP 订阅与支付、打赏与收益提现、积分 / 勋章 / 专家认证、关注与粉丝、关注流、群聊与站内信

**扩展**：插件系统（EventBus 事件总线）、主题引擎（内置 `fastblog-default`、`modern-minimal`、`magazine`）、
区块模式、小工具、AI 配置（多协议 + 工作流）

**前端**：前台 SSR + 后台 CSR、Tailwind 4 + shadcn 风格组件、Element Plus 管理组件、中英双语 i18n、
PWA（离线缓存 / 可安装）、移动端 Capacitor 外壳

## 快速开始

```bash
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog
python install.py
```

安装脚本会引导你完成：生成 `.env`（自动写入强随机密钥）→ 检查/下载静态 ffmpeg → 构建并启动容器 → 数据库迁移 →
勾选种子数据 → 按内置角色（`superadmin` / `admin` / `editor` / `user`）创建登录用户。

非交互用法：

```bash
FASTBLOG_ADMIN_PASSWORD='<强密码>' python install.py --yes --mode init --seeds rbac,menus --admin-user admin
python install.py --check        # 只做环境自检
```

手工等价步骤见[部署与运维](docs/DEPLOYMENT.md#3-快速部署默认形态)。

完成后访问 **<http://localhost:4321>**（nginx 入口，端口由 `FRONTEND_PORT` 控制）。

生产部署使用 `docker-compose.prod.yml`（强制 `SECRET_KEY` / `JWT_SECRET_KEY` / `DB_PASSWORD` / `REDIS_PASSWORD`，
自动启用多 worker、Redis 密码、资源限制与 HTTPS 端口）：

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

本地开发（后端 + 前端分离运行）见 [开发指南](docs/DEVELOPMENT.md#3-本地开发)。

## 技术栈

| 层   | 选型                                                                                               |
|-----|--------------------------------------------------------------------------------------------------|
| 后端  | Python 3.14 · FastAPI 0.136 · SQLAlchemy 2（async）· asyncpg · Alembic · Redis                     |
| 数据库 | PostgreSQL 16                                                                                    |
| 前端  | Nuxt 4.5（Vue 3 · TypeScript）· Tailwind 4 + shadcn 风格组件 · Element Plus · Pinia · TipTap · ECharts |
| 部署  | Docker Compose · nginx（TLS / 限流 / 安全头）· 多阶段镜像（python:3.14-slim、node:22-alpine）                   |
| 质量  | pytest · ruff · mypy · vue-tsc · Playwright · GitHub Actions                                     |

## 项目状态

- 当前版本 **0.8.26.0921**（见 [`version.txt`](version.txt)），数据库迁移 head 为 `8b7ecb6d053c`。
- 已知待办（详见 [部署文档第 13 节](docs/DEPLOYMENT.md#13-已知偏差代码或脚本与当前架构不一致尚未修复)）：
    - `docs/FastBlog_API.postman_collection.json` 的 Base URL 仍是已删除的 `/api/v1`。
- API 文档界面在非生产环境下可用：`http://localhost:9421/api/v3/docs`（`ENVIRONMENT=production` 时按设计关闭）。

## 文档

| 文档                                  | 内容                               |
|-------------------------------------|----------------------------------|
| [部署与运维](docs/DEPLOYMENT.md)         | Compose 形态、环境变量、nginx、备份恢复、升级、排障 |
| [开发指南](docs/DEVELOPMENT.md)         | 架构、后端域模块与硬约定、前端约定、测试与质量门、常用命令    |
| [前端 README](frontend/web/README.md) | `frontend/web` 的目录、脚本、环境变量与前端约定  |
| [测试说明](tests/README.md)             | 后端测试组织与运行方式                      |
| [更新日志](CHANGELOG.md)                | 版本时间线与变更                         |
| [贡献指南](CONTRIBUTING.md)             | 环境准备、代码规范、PR 流程                  |
| [安全策略](SECURITY.md)                 | 漏洞报告与内置安全能力清单                    |

## 目录结构

```
main.py              后端启动入口（FastAPI :9421）
install.py           交互式安装/初始化脚本（环境自检 → .env → 迁移 → 种子 → 建用户）
src/api/v3/          唯一权威 API 层（域 → 模块 → 五件套）
shared/              模型与领域服务（shared/models、shared/services）
config/models.yaml   数据模型唯一权威
frontend/web/        Nuxt 4.5 前端（前台 SSR + 后台 CSR）
plugins/             插件与主题
cli/                 命令行工具（python -m cli）
scripts/             生成器与种子脚本
tests/               后端测试（58 个用例文件）
docs/                文档
nginx/               nginx 配置（唯一对外入口）
alembic_migrations/  数据库迁移
```

## 贡献

欢迎提交代码、文档与翻译。开始前请阅读[贡献指南](CONTRIBUTING.md)，并遵守[行为准则](.github/CODE_OF_CONDUCT.md)。
安全漏洞请**不要**开公开 Issue，按[安全策略](SECURITY.md)私下报告。

## 许可

本项目基于 **Apache License 2.0** 授权，详见 [LICENSE](LICENSE)。`plugins/` 下的作品为 MIT 许可。

---

<div align="center">

如果 FastBlog 对你有帮助，欢迎给一个 ⭐

[⬆ 回到顶部](#fastblog)

</div>
