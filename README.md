# FastBlog - 现代化Python FastAPI博客系统

[![Python Version](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/)
[![FastAPI Version](https://img.shields.io/badge/fastapi-0.104.x-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-Apache%202.0-orange.svg)](./LICENSE)

一个功能丰富、易于部署的现代化博客系统，采用前后端分离架构和先进的进程监督器模式，支持安全自动更新、主题定制和响应式页面。

[📖 快速开始](./docs/GETTING_STARTED.md) • [🏗️ 系统架构](./docs/ARCHITECTURE.md) • [👨‍💻 开发指南](./docs/DEVELOPMENT.md) • [🤝 参与贡献](./docs/CONTRIBUTING.md)

## 🌟 核心特性

### 🚀 现代化技术栈
- **后端**：Python 3.14+ / FastAPI / PostgreSQL
- **前端**：Next.js 14+ / TypeScript / TailwindCSS
- **部署**：Docker / Docker Compose / Nginx

### 💪 核心功能
- **文章管理** - Markdown编辑器、标签分类、全文搜索
- **用户系统** - 完整的用户注册/登录、权限管理
- **评论系统** - 集成Giscus评论系统
- **媒体管理** - S3协议支持、自动缩略图生成

### 🔧 高级特性
- **安全更新** - 基于监督器的独立进程架构
- **进程管理** - 自动重启、状态监控、健康检查
- **安全防护** - SQL注入防护、XSS过滤、输入验证
- **性能优化** - 多级缓存、CDN加速、数据库优化

## 🚀 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog

# 2. 选择启动方式

# 方式一：标准应用启动（推荐新手）
python main.py

# 方式二：进程监督器启动（推荐生产环境）
python main.py --mode supervisor

# 3. 访问应用
# 前端：http://localhost:3000
# 管理后台：http://localhost:3000/admin
# API文档：http://localhost:9421/docs
```

> 💡 **详细安装指南**请查看 [快速开始文档](./docs/GETTING_STARTED.md)

## 🏗️ 系统架构

FastBlog提供灵活的启动模式以适应不同使用场景：

### 1. 标准应用模式 (`--mode app`)
```
┌─────────────────┐
│    main.py      │ ◄─ 直接启动FastAPI应用
└─────────────────┘
        │
        ▼
┌─────────────────┐
│   FastAPI App   │
│   (端口:9421)   │
└─────────────────┘
```

### 2. 进程监督器模式 (`--mode supervisor`)
```
┌─────────────────────────────────────────┐
│           SupervisedLauncher            │ ◄─ 主监督器
└─────────────────┬───────────────────────┘
                  │
                  ▼
        ┌─────────────────┐
        │ ProcessSupervisor │ ◄─ 进程监督核心
        └────────┬────────┘
                 │
        ┌────────┴────────┬───────────────┬───────────────┐
        ▼                 ▼               ▼               ▼
┌─────────────┐   ┌──────────────┐  ┌──────────┐  ┌──────────┐
│ IPC Server  │   │ UpdateChecker│  │ Main App │  │ Updater  │
│ (端口:12345)│   │ (端口:8001)  │  │(端口:9421)│  │ (按需)   │
└─────────────┘   └──────────────┘  └──────────┘  └──────────┘
```

### 3. 启动器模式 (`--mode launcher`)
```
┌─────────────────┐
│ Launcher Mode   │ ◄─ 智能启动器（版本检查）
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Version Check   │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Launch Main App │
└─────────────────┘
```


## 🔄 启动模式对比

| 启动模式 | 适用场景 | 特点 | 推荐用户 |
|---------|---------|------|----------|
| `app` | 开发调试、简单部署 | 直接启动应用，轻量级 | 新手、开发者 |
| `supervisor` | 生产环境、高可用 | 进程监督、自动重启 | 运维人员、生产环境 |

> 📖 **详细了解架构设计**请查看 [系统架构文档](./docs/ARCHITECTURE.md)

## 📚 文档导航

| 角色 | 推荐文档 | 学习路径 |
|------|----------|----------|
| 👨‍💻 **开发者** | [开发指南](./docs/DEVELOPMENT.md) → [系统架构](./docs/ARCHITECTURE.md) | 环境搭建 → 架构理解 → 功能开发 |
| 🚀 **运维人员** | [部署指南](./docs/DEPLOYMENT.md) → [系统架构](./docs/ARCHITECTURE.md) | 部署实践 → 架构理解 → 运维管理 |
| 💡 **普通用户** | [快速开始](./docs/GETTING_STARTED.md) | 快速部署 → 基础使用 |
| 🤝 **贡献者** | [贡献指南](./docs/CONTRIBUTING.md) | 贡献流程 → 开发规范 |

## 🤝 参与贡献

欢迎参与FastBlog的开发！

1. Fork 项目并创建功能分支
2. 遵循 [开发指南](./docs/DEVELOPMENT.md) 进行开发
3. 编写测试并确保通过
4. 提交 Pull Request

详细贡献流程请查看 [贡献指南](./docs/CONTRIBUTING.md)。

## 📄 开源协议

本项目采用 [Apache License 2.0](./LICENSE) 开源协议。

## 🆘 获取帮助

- 💬 [社区讨论](https://github.com/Athenavi/fast_blog/discussions) - 交流和问答
- 🐛 [问题反馈](https://github.com/Athenavi/fast_blog/issues) - 报告bug和建议

---

<p align="center">
  <strong>FastBlog</strong> - 让博客开发变得更简单<br>
  <a href="./docs/GETTING_STARTED.md">📖 快速开始</a> • 
  <a href="./docs/ARCHITECTURE.md">🏗️ 系统架构</a> • 
  <a href="./docs/CONTRIBUTING.md">🤝 参与贡献</a>
</p>