# FastBlog 开发指南

> 适用版本：V0.6.26+ | 后端：FastAPI 0.136 / Python 3.14+ | 前端：Astro 5.x / React 19 | 数据库：PostgreSQL 16+ / Redis 7+

## 一、系统架构

### 技术栈与数据流

```
用户 ──► Nginx（反代/安全/缓存）──► FastAPI（异步，API v2/v3）
                                        │
                          ┌─────────────┼─────────────┐
                          ▼             ▼             ▼
                     PostgreSQL      Redis          Meilisearch(可选)
                     (主数据)      (缓存/限流/     (全文搜索)
                                   会话/调度锁)
```

- **单后端架构**：FastAPI 处理 Web 与移动端全部 API；前端 Astro 通过 Nginx 同源反代。
- **API 版本**：V2（`/api/v2/`，Web 主要）、V3（`/api/v3/`，移动端专用）。V1 已删除。
- **多 worker**：`WORKERS>1` 时多进程部署，Redis 共享限流/缓存，定时任务由 Redis 分布式锁保证单次执行。

### 目录结构

```
src/                    # FastAPI 后端
├── api/v2/             # Web API（聚合路由器模式）
├── api/v3/             # 移动端 API
├── auth/               # JWT / RBAC / 2FA
├── middleware/         # 限流 / 缓存 / 暴力破解防护等
├── mcp/                # MCP 服务器（AI 交互）
├── app.py              # 应用工厂（路由注册/中间件/生命周期）
└── extensions.py       # 扩展初始化（含 SQL 慢查询监控）
shared/
├── services/           # 30+ 领域服务（articles/plugins/performance/security...）
├── models/             # SQLAlchemy 模型
└── utils/              # 公共工具
frontend-astro/         # Astro + React Islands
plugins/                # 插件（含主题）
```

### 关键机制

- **缓存**：`CacheService`（内存 + Redis 双后端）、`MultiLevelCache`、`PageCacheService`（磁盘 HTML 缓存）、缓存失效经 `cache:invalidate` Pub/Sub 广播。
- **调度器**：`src/scheduler.py`（APScheduler）统一管理浏览量落库、定时发布、VIP 过期、自动备份。
- **慢查询监控**：`extensions.py` 挂载 SQLAlchemy 事件钩子，`/api/v2/performance/query-monitor/summary`（管理员）可查。
- **插件**：EventBus（观察者 + 管道）驱动，插件自带 SQLite 与前端管理页，与核心解耦。

## 二、贡献规范

欢迎提交 PR、完善文档或参与讨论。

### 流程

```bash
git clone https://github.com/Athenavi/fast_blog.git
git checkout -b feature/your-feature
git commit -m "feat: 添加新功能"
git push origin feature/your-feature
# 创建 Pull Request
```

### 提交规范（Conventional Commits）

```
<type>(<scope>): <subject>
feat(auth): 添加 OAuth 登录
fix(api): 修复用户查询 bug
docs(readme): 更新安装说明
```

类型：`feat | fix | docs | style | refactor | test | chore`

### 开发检查

```bash
# 后端
black src/ && flake8 src/
pytest

# 前端
cd frontend-astro && npm run lint
```

### Issue 报告

在 [GitHub Issues](https://github.com/Athenavi/fast_blog/issues) 提交，附上：问题描述与重现步骤、期望/实际行为、环境信息。

## 三、插件开发

插件基于 **EventBus**，订阅事件与核心交互，完全解耦。

### 目录结构

```
plugins/<your-plugin>/
├── metadata.json       # 元数据（必选）
├── plugin.py           # Python 代码（必选）
└── frontend/           # 前端（可选）
    ├── manifest.json   # 前端声明（自动发现）
    └── admin/Page.tsx  # 管理页面
```

### 事件模型

```
event_bus.emit("article.published", payload)   # 观察者：通知/推送
event_bus.pipeline("article.content", html)    # 管道：替换短代码等
```

### 内置插件示例

| 插件 | 功能 | 说明 |
|------|------|------|
| newsletter | 邮件订阅 | SQLite + EventBus |
| code-snippets | 代码片段嵌入 | SQLite + EventBus |
| article-likes | 文章点赞 | SQLite |
| katex-render | KaTeX 公式 | 管道 |
| popular-articles | 阅读排行 | 侧边栏 widget |
| approval / enterprise / migration | 审批 / 企业 / 迁移 | 管理页 |

## 四、主题开发

主题作为 `category: "theme"` 的插件存放于 `plugins/<theme>/`，基于 Astro SSG + TailwindCSS。

- **配置**：`theme.json` + `theme.config.js`
- **支持**：完全自定义视觉、深色模式、用户可配置选项
- **内置主题**：`fastblog-default`（默认）、`magazine`（杂志）、`modern-minimal`（现代简约）

主题结构、配置项与样式定制的最佳实践参见各主题源码与 `theme.config.js` 注释。

## 五、API 参考

完整 API 由运行中的服务自动生成（始终最新）：

- **Swagger UI**：`http://localhost:9421/api/v2/docs`
- **移动端 v3**：基础信息见 [运维手册](operations.md) 移动端章节

### 快速示例

```bash
# 登录
curl -X POST "http://localhost:9421/api/v2/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "你的密码"}'
```

```python
import requests
r = requests.post("http://localhost:9421/api/v2/auth/login",
                  json={"username": "admin", "password": "你的密码"})
token = r.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}
```

> 登录支持 `username` 或 `email`；认证支持 `Authorization: Bearer <token>` 头或 Cookie 双模式。

> 💡 另有现成的 [Postman 集合](../docs/FastBlog_API.postman_collection.json) 可直接导入调试。

## 相关文档

- [快速开始](getting-started.md)
- [部署指南](deployment.md)
- [运维手册](operations.md)
