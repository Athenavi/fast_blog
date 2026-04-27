# FastBlog - 现代化 Python 博客系统

[![Python Version](https://img.shields.io/badge/python-3.14.4%2B-blue.svg)](https://www.python.org/)
[![FastAPI Version](https://img.shields.io/badge/fastapi-0.136.1%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Django Version](https://img.shields.io/badge/django-6.0.4%2B-red.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-Apache%202.0-orange.svg)](./LICENSE)

功能丰富、易于部署的现代化博客系统，采用前后端分离架构和 **FastAPI + Django 双后端设计**。

> 🚀 **特色**: 高性能、可扩展、插件化、主题化、SEO 优化

## 🎯 为什么选择 FastBlog?

### ✨ 核心优势

- **🔄 双后端架构**: FastAPI（高性能）+ Django（快速开发），灵活切换
- **⚡ 极致性能**: 异步处理、缓存优化、CDN 支持
- **🔌 插件系统**: Hook 机制，轻松扩展功能
- **🎨 主题系统**: 多个精美主题，可视化定制
- **📱 响应式设计**: 完美适配桌面、平板、手机
- **🔒 安全可靠**: JWT 认证、CSRF 防护、SQL 注入防护
- **📊 SEO 优化**: 自动生成 Sitemap、Meta 标签

### 🆚 与 WordPress 对比

| 特性   | FastBlog         | WordPress   |
|------|------------------|-------------|
| 性能   | ⚡⚡⚡⚡⚡ 极快         | ⚡⚡⚡ 中等      |
| 技术栈  | Python + Next.js | PHP + MySQL |
| 学习曲线 | 中等               | 简单          |
| 插件生态 | growing 🌱       | 成熟 🌳       |
| 安全性  | 🔒🔒🔒🔒🔒 优秀    | 🔒🔒🔒 良好   |
| 定制化  | 💯 完全可控          | 💯 完全可控     |
| 适用场景 | 技术博客、企业站         | 通用博客        |

## 🚀 开始

📖 **详细安装指南**: [docs/QUICK_START.md](docs/QUICK_START.md)

## 💡 核心特性详解

### 🔄 双后端架构

FastBlog 采用双后端设计，兼顾性能和开发效率：

**FastAPI 模式** (生产环境推荐):

- ✅ 异步处理，高并发支持
- ✅ 自动 API 文档（Swagger/OpenAPI）
- ✅ 类型安全，代码提示
- 🎯 适用场景: 高流量博客、API 服务

**Django 模式** (开发和管理推荐):

- ✅ 内置 Admin 后台，开箱即用
- ✅ ORM 强大，快速开发
- ✅ 成熟的生态系统
- 🎯 适用场景: 内容管理、快速原型

**灵活切换**:

```bash
python main.py --backend fastapi  # 切换到 FastAPI
python main.py --backend django   # 切换到 Django
```

**数据兼容**: 两种模式共用数据库，无缝切换

### 🎯 主要功能模块

#### 📝 文章管理

- Markdown 编辑器，实时预览
- 分类和标签系统
- 全文搜索（支持中文）
- 草稿箱和定时发布
- 修订历史和版本控制
- SEO 元数据管理

#### 👥 用户系统

- 注册登录（邮箱/手机号）
- JWT token 认证
- 角色权限管理（管理员、编辑、作者、订阅者）
- 第三方登录（GitHub、Google、微信）
- 个人资料和头像

#### 💬 评论系统

- Giscus 集成（GitHub Discussions）
- Disqus 集成
- 评论审核和反垃圾

#### 🖼️ 媒体管理

- S3 协议兼容（AWS S3、阿里云 OSS、腾讯云 COS）
- 本地存储支持
- 自动缩略图生成
- 图片懒加载和 CDN 加速

#### 🔌 插件系统

- Hook 机制，类似 WordPress
- 热插拔，无需重启
- 自定义插件开发指南

#### 🎨 主题系统

- 多个精美主题可选
- 可视化主题定制器
- 响应式设计
- 深色模式支持

#### 📊 数据分析

- 访客统计（PV/UV）
- 热门文章排行
- Google Analytics 集成

#### 🔍 SEO 优化

- 自动生成 Sitemap
- Robots.txt 管理
- Meta 标签优化
- Open Graph 社交分享

## 📚 完整文档导航

### 🎓 新手入门

- [🚀 快速开始](docs/QUICK_START.md) - 5 分钟部署指南
- [🏗️ 技术架构](docs/TECHNICAL.md) - 系统架构详解
- [❓ 常见问题](docs/TROUBLESHOOTING_FAQ.md) - FAQ 故障排查

### 👨‍💻 开发者文档

- [🔌 插件开发指南](docs/PLUGIN_DEVELOPMENT_GUIDE.md) - 插件系统详解
- [🎨 主题开发指南](docs/THEME_DEVELOPMENT_GUIDE.md) - 主题定制指南
- [📖 API 参考文档](docs/API_REFERENCE.md) - 完整 API 文档
- [🤝 贡献指南](docs/CONTRIBUTING.md) - 参与项目开发
- [📝 更新日志](docs/CHANGELOG.md) - 版本历史

### 🚀 运维部署

- [📦 部署指南](docs/DEPLOYMENT_GUIDE.md) - Docker/服务器部署
- [🗄️ 插件数据库指南](docs/PLUGIN_DATABASE_GUIDE.md) - 插件数据管理

### 🌐 前端文档

- [Next.js 前端文档](frontend-next/README.md) - 前端项目说明

## 🛠️ 技术栈

### 后端技术

- **核心框架**: FastAPI 0.100+ / Django 4.2+
- **Python 版本**: 3.10+
- **数据库**: PostgreSQL 14+（主数据库）
- **缓存**: Redis 6+（会话、缓存）
- **ORM**: SQLAlchemy 2.0+ / Django ORM
- **API**: Django Ninja / FastAPI Router
- **认证**: JWT (PyJWT)
- **Web 服务器**: Uvicorn / Gunicorn

### 前端技术

- **框架**: Next.js 15（App Router）
- **语言**: TypeScript 5+
- **样式**: TailwindCSS 3+
- **UI 组件**: Radix UI / Shadcn/ui
- **状态管理**: React Context / Zustand
- **HTTP 客户端**: Axios / Fetch API
- **图标**: Lucide React

### 部署和运维

- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx
- **CI/CD**: GitHub Actions

### 最低配置要求

- **开发环境**: 2核2G
- **生产环境**: 4核4G（推荐）

## 🔧 开发工具和命令

### 路由代码生成

FastBlog 使用自动化路由生成工具，减少重复代码：

```bash
# 生成所有路由代码
python scripts/generate_routes.py

# 监听模式，文件变化时自动重新生成
python scripts/generate_routes.py --watch
```

### 开发辅助工具

```bash
# 数据库迁移
python django_blog/manage.py migrate
python django_blog/manage.py makemigrations

# 创建管理员账号
python django_blog/manage.py createsuperuser

# 进入 Django Shell
python django_blog/manage.py shell
```

### 前端开发命令

```bash
cd frontend-next

# 开发服务器（热重载）
npm run dev

# 生产构建
npm run build

# 启动生产服务器
npm run start

# 代码检查
npm run lint
```

## 🌟 社区和生态

### 🔌 插件生态

**官方插件**:

- analytics - 数据分析
- seo-optimizer - SEO 优化
- social-share - 社交分享
- backup-manager - 备份管理
- security-guard - 安全防护
- related-posts - 相关文章
- image-lazy-load - 图片懒加载
- page-cache - 页面缓存

**社区插件**: 欢迎开发者贡献插件，详见[插件开发指南](docs/PLUGIN_DEVELOPMENT_GUIDE.md)

### 🎨 主题生态

**官方主题**:

- default - 默认主题（简洁优雅）
- modern-minimal - 现代极简
- magazine - 杂志风格

**自定义主题**: 支持开发者创建和分享主题，详见[主题开发指南](docs/THEME_DEVELOPMENT_GUIDE.md)

## 🤝 参与贡献

我们欢迎任何形式的贡献！

### 贡献方式

1. **报告 Bug**: [提交 Issue](https://github.com/Athenavi/fast_blog/issues/new?template=bug_report.md)
2. **功能建议**: [提出 Feature](https://github.com/Athenavi/fast_blog/issues/new?template=feature_request.md)
3. **改进文档**: 帮助完善文档
4. **开发插件**: 创建有趣的插件
5. **设计主题**: 分享你的主题设计
6. **翻译**: 帮助翻译成其他语言
7. **代码贡献**: [查看贡献指南](docs/CONTRIBUTING.md)

### 开发流程

```bash
# 1. Fork 项目
git fork https://github.com/Athenavi/fast_blog.git

# 2. 创建分支
git checkout -b feature/your-feature-name

# 3. 提交更改
git commit -am 'Add new feature'

# 4. 推送分支
git push origin feature/your-feature-name

# 5. 创建 Pull Request
```

详见: [CONTRIBUTING.md](docs/CONTRIBUTING.md)

## 📄 开源协议

本项目采用 [Apache License 2.0](./LICENSE) 开源协议。

**你可以**:

- ✅ 商业使用
- ✅ 修改代码
- ✅ 分发代码
- ✅ 专利使用
- ✅ 私人使用

**你需要**:

- 📝 注明版权
- 📄 包含许可证副本

**你不能**:

- ❌ 追究作者责任
- ❌ 使用商标

## 🙏 致谢

感谢以下开源项目的支持:

- [FastAPI](https://fastapi.tiangolo.com/) - 现代高性能 Web 框架
- [Django](https://www.djangoproject.com/) - 完美的 Web 框架
- [Next.js](https://nextjs.org/) - React 框架
- [TailwindCSS](https://tailwindcss.com/) - 实用优先的 CSS 框架
- [PostgreSQL](https://www.postgresql.org/) - 强大的开源数据库
- [Redis](https://redis.io/) - 内存数据结构存储

## 📞 联系我们

- **GitHub**: [Athenavi/fast_blog](https://github.com/Athenavi/fast_blog)
- **Issues**: [问题反馈](https://github.com/Athenavi/fast_blog/issues)
- **Discussions**: [社区讨论](https://github.com/Athenavi/fast_blog/discussions)

---

<p align="center">
  Made with ❤️ by FastBlog Team
</p>
<p align="center">
  If you like this project, please give it a ⭐️ on GitHub!
</p>