# FastBlog 文档索引

**最后更新**: 2026-06-01
**当前版本**: V0.3.26.0521

---

## 📚 核心文档

### 🚀 新手入门

| 文档                     | 说明         | 适合人群    |
|------------------------|------------|---------|
| [快速开始](QUICK_START.md) | 安装和部署指南    | 所有用户    |
| [技术架构](TECHNICAL.md)   | 系统架构和技术栈详解 | 开发者、架构师 |

### 👨‍💻 开发者文档

| 文档                                    | 说明                  | 适合人群        |
|---------------------------------------|---------------------|-------------|
| [API 参考](API_REFERENCE.md)            | RESTful API v2 完整文档 | 前端开发者、第三方集成 |
| [插件开发指南](PLUGIN_DEVELOPMENT_GUIDE.md) | 插件系统开发和扩展教程         | 插件开发者       |
| [主题开发指南](THEME_DEVELOPMENT_GUIDE.md)  | 主题定制和开发指南           | 主题开发者       |
| [贡献指南](CONTRIBUTING.md)               | 参与项目开发的规范和流程        | 贡献者         |
| [AI 交互指南](AI_INTERACTION_GUIDE.md)    | MCP Server AI 集成指南  | AI 开发者      |

### 🔧 运维部署

| 文档                                 | 说明            | 适合人群  |
|------------------------------------|---------------|-------|
| [部署指南](DEPLOYMENT_GUIDE.md)        | 生产环境部署方案和最佳实践 | 运维工程师 |
| [故障排查 FAQ](TROUBLESHOOTING_FAQ.md) | 常见问题解答和解决方案   | 所有用户  |

### 📱 移动端

| 文档                                            | 说明            | 适合人群   |
|-----------------------------------------------|---------------|--------|
| [移动端 API](../src/api/v3/MOBILE_API_README.md) | V3 移动端 API 文档 | 移动端开发者 |

### 📝 其他

| 文档                                        | 说明           |
|-------------------------------------------|--------------|
| [更新日志](CHANGELOG.md)                      | 版本历史和变更记录    |
| [Astro 前端文档](../frontend-astro/README.md) | Astro 前端开发指南 |

---

## 🎯 快速查找

**我想...**

- **快速部署系统** → [快速开始](QUICK_START.md)
- **调用 API 接口** → [API 参考](API_REFERENCE.md)（当前为 v2 版本）
- **开发自定义插件** → [插件开发指南](PLUGIN_DEVELOPMENT_GUIDE.md)
- **定制网站主题** → [主题开发指南](THEME_DEVELOPMENT_GUIDE.md)
- **部署到生产环境** → [部署指南](DEPLOYMENT_GUIDE.md)
- **解决遇到的问题** → [故障排查 FAQ](TROUBLESHOOTING_FAQ.md)
- **参与项目贡献** → [贡献指南](CONTRIBUTING.md)
- **了解技术架构** → [技术架构](TECHNICAL.md)
- **查看更新历史** → [更新日志](CHANGELOG.md)
- **AI 工具集成** → [AI 交互指南](AI_INTERACTION_GUIDE.md)

---

## 🌟 核心特性速览

### 技术栈

- **后端**: FastAPI 0.128 + SQLAlchemy 2.0 + PostgreSQL (asyncpg)
- **前端**: Astro 5.7 SSG + React 19 Islands + TanStack React Query
- **移动端**: Capacitor 5.x (Android/iOS)
- **搜索**: Meilisearch 全文搜索
- **缓存**: Redis 多层缓存

### 性能优化

- Astro 岛屿架构：零 JavaScript 默认策略
- 智能缓存层：Redis + 数据库查询优化
- CDN 友好：静态资源优化

### 开发体验

- 插件系统：Hook 机制（`do_action` / `apply_filters`），无需修改核心代码
- 完整 API v2：Swagger 文档自动生成
- MCP Server：AI 集成支持
- CLI 工具：`python scripts/cli.py`

### 安全可靠

- JWT 认证（Cookie/Bearer 双模式）和 RBAC 权限控制
- 零信任安全中间件
- SQL 注入防护和 CSRF 保护
- 双因素认证 (TOTP)

---

## 🔗 外部资源

### 官方文档
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Astro 文档](https://docs.astro.build/)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)
- [Redis 文档](https://redis.io/documentation)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)

### 社区

- [GitHub Issues](https://github.com/Athenavi/fast_blog/issues) - 报告问题
- [GitHub Discussions](https://github.com/Athenavi/fast_blog/discussions) - 社区讨论
- [Pull Requests](https://github.com/Athenavi/fast_blog/pulls) - 代码贡献

---

## 📊 文档统计

- **核心文档**: 11 个
- **总页数**: 约 60+ 页
- **最后更新**: 2026-06-01
- **维护状态**: ✅ 活跃维护
