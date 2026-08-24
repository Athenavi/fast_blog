# FastBlog 运维手册

> 适用版本：V0.6.26+

## 一、故障排查 FAQ

### 安装问题

```bash
# pip 失败
pip install --upgrade pip setuptools wheel
pip cache purge
pip install -r requirements.txt

# npm 失败
npm cache clean --force
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps

# Docker 构建失败
docker system prune -a
docker compose build --no-cache
```

### 配置问题

```bash
# SECRET_KEY / JWT_SECRET_KEY 未设置（应用会拒绝启动）
python -c "import secrets; print(secrets.token_urlsafe(50))"
# 将输出写入 .env 的 SECRET_KEY / JWT_SECRET_KEY

# CORS 错误
# .env 中配置：
# CORS_ORIGINS=http://localhost:4321,http://localhost:9421,https://yourdomain.com
```

### 数据库问题

```bash
alembic current          # 检查当前状态
alembic history          # 查看迁移历史
alembic downgrade base   # 回滚到初始
alembic upgrade head     # 重新应用
```

### 常见错误对照

| 现象 | 原因 | 处理 |
|------|------|------|
| 启动报 `SECRET_KEY 仍为占位值` | 未配置真实密钥 | 生成随机密钥写入 `.env` |
| 全站 429 | 应用层限流器共享单 IP | 检查 Nginx `X-Forwarded-For` 透传 + Redis 可用性 |
| 登录后立即掉线 | `SECRET_KEY` 每次重启变化 | 持久化 `SECRET_KEY` |
| 视频处理不可用 | FFmpeg 未安装 | 安装 FFmpeg 或使用官方 Docker 镜像 |

## 二、AI 交互（MCP）

FastBlog 内置 **MCP (Model Context Protocol)** 服务器，可连接 Claude Desktop、Cursor 等 AI 工具。

### 配置

1. 启动 FastBlog 服务。
2. 在 AI 客户端的 MCP 设置中添加 FastBlog 的 MCP 端点。
3. 连接后 AI 自动获得资源（文章/分类/媒体）与工具（发布/更新/搜索），并受当前用户权限约束。

### 常用场景

- **智能写作发布**："帮我写一篇关于 asyncio 的文章并发布到技术分类"
- **SEO 优化**："分析最近文章并给出 SEO 建议"
- **数据监控**："上个月浏览量最高的前 5 篇文章"

## 三、移动端（v3 API + Capacitor）

移动端使用独立的 v3 RESTful API（`/api/v3`），响应结构更精简：

```
Base URL: /api/v3
认证: Authorization: Bearer <token>
分页: page / per_page（默认 20，最大 50）
错误: {"success": false, "error": "描述"}
```

### 主要模块

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | `/api/v3/auth/login`、`/register` | 登录/注册 |
| 文章 | `/api/v3/articles/list`、`/{id}`、`/search` | 列表/详情/搜索 |
| 评论 | `/api/v3/comments/...` | 列表/发表/点赞 |
| 用户/媒体/分类 | `/api/v3/users`、`/media`、`/categories` | 移动端适配 |

### Capacitor 移动应用

- 工程位于 `mobile-app/`（Android + iOS）。
- 构建与打包：参见 `mobile-app/CAPACITOR_GUIDE.md` 与 `build-and-deploy.ps1`。
- 前端 `config.js` 的 `API_BASE_URL` 需指向可达的后端地址。

## 四、安全建议

- **密钥**：生产必须设置强 `SECRET_KEY` / `JWT_SECRET_KEY`，缺失时应用拒绝启动（占位值会被拦截）。
- **HTTPS**：启用 TLS + HSTS（见 [部署指南](deployment.md) SSL 章节）。
- **限流**：Nginx 层（`limit_req`）+ 应用层（IP/用户）+ 登录锁定三重防护。
- **上传**：系统已限制危险文件类型（HTML/JS/XML 等）并消毒 SVG；请勿擅自放宽 `ALLOWED_MIMES`。
- **SSRF**：离线下载/资源导入已校验目标为公网地址，拒绝内网/云元数据。
- **更新**：关注 CHANGELOG 与 GitHub Security 公告；CI 已内置 `pip-audit` + `npm audit`。

## 相关文档

- [快速开始](getting-started.md)
- [部署指南](deployment.md)
- [开发指南](development.md)
