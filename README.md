# FastBlog - 现代化 Python 博客系统

[![Python Version](https://img.shields.io/badge/python-3.14.4%2B-blue.svg)](https://www.python.org/)
[![FastAPI Version](https://img.shields.io/badge/fastapi-0.136.1%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Django Version](https://img.shields.io/badge/django-6.0.4%2B-red.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-Apache%202.0-orange.svg)](./LICENSE)

功能丰富、易于部署的现代化博客系统，采用前后端分离架构和 **FastAPI + Django 双后端设计**。

> 🚀 **特色**: 高性能、可扩展、插件化、主题化、SEO 优化

## 🎯 核心优势

- **🔄 双后端架构**: FastAPI（高性能）+ Django（快速开发），灵活切换
- **⚡ 极致性能**: 异步处理、缓存优化、CDN 支持
- **🔌 插件系统**: Hook 机制，轻松扩展功能
- **🎨 主题系统**: 多个精美主题，可视化定制
- **📱 响应式设计**: 完美适配桌面、平板、手机
- **🔒 安全可靠**: JWT 认证、CSRF 防护、SQL 注入防护
- **📊 SEO 优化**: 自动生成 Sitemap、Meta 标签

## 🚀 快速开始

### Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog

# 2. 启动服务
docker-compose up -d

# 3. 访问应用
# 前端：http://localhost:3000
# API：http://localhost:9421/docs
```

### 手动部署

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境
cp .env_example .env
# 编辑 .env 文件，配置数据库等信息

# 3. 数据库迁移
python django_blog/manage.py migrate

# 4. 启动服务
python main.py --backend fastapi  # 或 django
```

📖 **详细文档**: [docs/QUICK_START.md](docs/QUICK_START.md)

## 📚 文档导航

### 新手入门

- [快速开始](docs/QUICK_START.md) - 5分钟部署指南
- [技术架构](docs/TECHNICAL.md) - 系统架构详解
- [常见问题](docs/TROUBLESHOOTING_FAQ.md) - FAQ故障排查

### 开发者文档

- [插件开发](docs/PLUGIN_DEVELOPMENT_GUIDE.md) - 插件系统详解
- [主题开发](docs/THEME_DEVELOPMENT_GUIDE.md) - 主题定制指南
- [API参考](docs/API_REFERENCE.md) - 完整API文档
- [贡献指南](docs/CONTRIBUTING.md) - 参与项目开发

### 运维部署

- [部署指南](docs/DEPLOYMENT_GUIDE.md) - Docker/服务器部署

## 🛠️ 技术栈

### 后端

- **框架**: FastAPI 0.100+ / Django 4.2+
- **Python**: 3.10+
- **数据库**: PostgreSQL 14+
- **缓存**: Redis 6+

### 前端
- **框架**: Next.js 15（App Router）
- **语言**: TypeScript 5+
- **样式**: TailwindCSS 3+

## 🤝 参与贡献

我们欢迎任何形式的贡献！

1. **报告Bug**: [提交Issue](https://github.com/Athenavi/fast_blog/issues)
2. **功能建议**: [提出Feature](https://github.com/Athenavi/fast_blog/discussions)
3. **代码贡献**: [查看贡献指南](docs/CONTRIBUTING.md)

## 📄 开源协议

本项目采用 [Apache License 2.0](./LICENSE) 开源协议。

---

<p align="center">
  Made with ❤️ by FastBlog Team
</p>