# FastBlog

<div align="center">

**现代化、高性能的 Python 博客系统**

[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/)
[![FastAPI Version](https://img.shields.io/badge/fastapi-0.136+-green.svg)](https://fastapi.tiangolo.com/)
[![Astro Version](https://img.shields.io/badge/astro-5.x-orange.svg)](https://astro.build/)
[![License](https://img.shields.io/badge/license-Apache%202.0-orange.svg)](./LICENSE)

[快速开始](docs/QUICK_START.md) · [文档](docs/README.md) · [API 参考](docs/API_REFERENCE.md) · [贡献指南](docs/CONTRIBUTING.md)

</div>

---

## 🌟 特性

### 🚀 极致性能

- **Astro 岛屿架构**：零 JavaScript 默认策略，首屏加载速度提升 80%+
- **双后端支持**：FastAPI（异步高性能）和 Django（成熟稳定）灵活切换
- **智能缓存**：Redis 缓存层，数据库查询优化
- **CDN 友好**：静态资源优化，支持全球加速

### 💡 开发者友好

- **插件系统**：Hook 机制，轻松扩展功能，无需修改核心代码
- **主题引擎**：可视化定制，多套精美主题可选
- **完整 API**：RESTful API，Swagger 文档自动生成
- **TypeScript 支持**：前端类型安全，开发体验更佳

### 🔒 安全可靠

- **JWT 认证**：安全的用户认证和授权机制
- **SQL 注入防护**：ORM 层全面防护
- **CSRF 保护**：跨站请求伪造防护
- **输入验证**：严格的数据验证和清理

### 📱 现代化体验

- **响应式设计**：完美适配桌面、平板、手机
- **SEO 优化**：自动生成 Sitemap、Meta 标签
- **深色模式**：支持系统级深色模式切换
- **PWA 支持**：可安装为原生应用

## 🎯 技术栈

### 后端

- **框架**：FastAPI 0.136+ / Django 6.0+
- **语言**：Python 3.14+
- **数据库**：PostgreSQL 17+
- **缓存**：Redis 7+
- **ORM**：SQLAlchemy (FastAPI) / Django ORM

### 前端

- **框架**：Astro 5.x（岛屿架构）
- **UI 库**：React 19 / Vue 3（按需加载）
- **样式**：TailwindCSS 3.x
- **状态管理**：SWR / TanStack Query
- **图标**：Lucide Icons

### 部署

- **容器化**：Docker & Docker Compose
- **Web 服务器**：Nginx
- **进程管理**：Supervisor / Gunicorn / Uvicorn

## 📦 快速开始

### 前置要求

- Python 3.14+
- Node.js 18+
- PostgreSQL 17+
- Redis 7+

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog

# 2. 后端设置
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt

# 3. 配置环境
cp .env_example .env
# 编辑 .env 文件，配置数据库等信息

# 4. 前端设置
cd frontend-astro
npm install
cp .env.example .env

# 5. 启动服务
# 终端 1 - 后端
cd ..
python main.py --backend fastapi

# 终端 2 - 前端
cd frontend-astro
npm run dev
```

访问 http://localhost:4321 查看前端，http://localhost:9421/docs 查看 API 文档。

## 📚 文档

- **[快速开始](docs/QUICK_START.md)** - 详细的安装和配置指南
- **[技术架构](docs/TECHNICAL.md)** - 系统架构和技术选型说明
- **[API 参考](docs/API_REFERENCE.md)** - 完整的 RESTful API 文档
- **[插件开发](docs/PLUGIN_DEVELOPMENT_GUIDE.md)** - 开发和扩展插件
- **[主题开发](docs/THEME_DEVELOPMENT_GUIDE.md)** - 创建自定义主题
- **[部署指南](docs/DEPLOYMENT_GUIDE.md)** - 生产环境部署方案
- **[故障排查](docs/TROUBLESHOOTING_FAQ.md)** - 常见问题解答
- **[贡献指南](docs/CONTRIBUTING.md)** - 参与项目开发

## 🏗️ 项目结构

```
fast_blog/
├── src/                    # FastAPI 后端源码
│   ├── api/v1/            # API 路由
│   ├── models/            # 数据模型
│   ├── services/          # 业务逻辑
│   └── utils/             # 工具函数
├── apps/                  # Django 应用（可选后端）
├── frontend-astro/        # Astro 前端
│   ├── src/
│   │   ├── components/    # React/Vue 组件
│   │   ├── layouts/       # 布局组件
│   │   └── pages/         # 页面路由
│   └── public/            # 静态资源
├── plugins/               # 插件目录
├── themes/                # 主题目录
├── shared/                # 共享模块
│   ├── models/            # 数据模型定义
│   ├── services/          # 共享服务
│   └── utils/             # 工具函数
└── docs/                  # 文档
```

## 🤝 参与贡献

我们欢迎任何形式的贡献！

### 贡献方式

1. **报告 Bug** → [提交 Issue](https://github.com/Athenavi/fast_blog/issues)
2. **功能建议** → [发起讨论](https://github.com/Athenavi/fast_blog/discussions)
3. **代码贡献** → [Fork & PR](docs/CONTRIBUTING.md)
4. **文档改进** → 完善文档、翻译、编写教程
5. **社区帮助** → 回答问题、分享经验

### 开发流程

```bash
# 1. Fork 并克隆
git clone https://github.com/YOUR_USERNAME/fast_blog.git
cd fast_blog

# 2. 创建分支
git checkout -b feature/your-feature-name

# 3. 开发和测试
# ... 你的代码更改 ...

# 4. 提交更改
git add .
git commit -m "feat: 添加新功能描述"
git push origin feature/your-feature-name

# 5. 创建 Pull Request
```

详细规范请查看 [贡献指南](docs/CONTRIBUTING.md)。

## 📊 性能对比

| 指标           | Next.js | Astro | 改善     |
|--------------|---------|-------|--------|
| 首页 JS        | ~250KB  | ~0KB  | ↓ 100% |
| FCP (首次内容绘制) | ~1.5s   | ~0.5s | ↓ 67%  |
| LCP (最大内容绘制) | ~2.5s   | ~0.8s | ↓ 68%  |
| TTI (可交互时间)  | ~3.0s   | ~0.5s | ↓ 83%  |

## 🗺️ 路线图

### ✅ 已完成

- [x] FastAPI + Django 双后端架构
- [x] Astro 前端重构（岛屿架构）
- [x] 插件系统（Hook 机制）
- [x] 主题系统
- [x] RESTful API
- [x] 用户认证和权限管理
- [x] 文章管理系统
- [x] 评论系统
- [x] 媒体管理

### 🚧 进行中

- [ ] PWA 支持
- [ ] 国际化（i18n）
- [ ] 实时通知系统
- [ ] 数据分析仪表板

### 📅 计划中

- [ ] GraphQL API
- [ ] WebSocket 实时通信
- [ ] AI 辅助写作
- [ ] 多租户支持

## 📄 开源协议

本项目采用 [Apache License 2.0](./LICENSE) 开源协议。

## 🙏 致谢

感谢所有为 FastBlog 做出贡献的开发者和社区成员！

## 📞 联系方式

- **GitHub Issues**: [报告问题](https://github.com/Athenavi/fast_blog/issues)
- **GitHub Discussions**: [社区讨论](https://github.com/Athenavi/fast_blog/discussions)
- **Email**: contact@fastblog.dev

---

<div align="center">

Made with ❤️ by FastBlog Team

[⬆ 回到顶部](#fastblog)

</div>
