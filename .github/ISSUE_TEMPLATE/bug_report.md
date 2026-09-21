---
name: 🐛 Bug 报告
about: 创建一个 bug 报告以帮助我们改进
title: '[BUG] '
labels: bug
assignees: ''
---

## 🐛 问题描述

清晰简洁地描述这个 bug。

## 🔄 复现步骤

1. 进入 '...'
2. 点击 '....'
3. 看到错误

## ✅ 预期行为

描述你期望发生的结果。

## 📱 截图

如果适用，添加截图帮助说明问题。

## 💻 环境信息

- **部署方式**: Docker Compose（`docker-compose.yml` / `docker-compose.prod.yml`）或 手动部署
- **FastBlog 版本**: 例如 `0.8.26.0921`（见仓库根 `version.txt`）
- **操作系统**: 例如 Ubuntu 22.04 / Windows 11
- **Python 版本**: 例如 3.14
- **Node.js 版本**: 例如 22.x（前端要求 ≥ 22.19）
- **浏览器**（前端问题时）: 例如 Chrome 120
- **数据库 / 缓存**: 例如 PostgreSQL 16 / Redis 7

## 📋 日志信息

后端日志（`logs/` 或 `docker compose logs backend`）、浏览器控制台、以及响应体中的 `{code, msg}`：

```
在此粘贴相关日志
```

## 🔧 附加上下文

任何其他有助于定位的信息（相关提交、配置片段、是否可稳定复现等）。

## ✅ 检查清单

- [ ] 我已搜索现有 Issues，确认没有重复
- [ ] 我已查阅[部署与运维文档](../../docs/DEPLOYMENT.md)（第 12 节「健康检查与排障」）
- [ ] 我提供了足够的信息来复现问题
- [ ] 已脱敏（不含密钥、密码、真实用户数据）
