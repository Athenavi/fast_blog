<div align="center">

<img src="docs/assets/fastblog-logo.svg" alt="FastBlog Logo" width="120" height="120" onerror="this.style.display='none'">

# FastBlog

### ⚡ The Modern, High-Performance Blog Platform Built for Developers

[![CI Status](https://github.com/Athenavi/fast_blog/actions/workflows/ci.yml/badge.svg)](https://github.com/Athenavi/fast_blog/actions/workflows/ci.yml)
[![Release](https://github.com/Athenavi/fast_blog/actions/workflows/release.yml/badge.svg)](https://github.com/Athenavi/fast_blog/actions/workflows/release.yml)
[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Astro](https://img.shields.io/badge/Astro-5.x-BC52EE.svg?logo=astro&logoColor=white)](https://astro.build/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](./LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/Athenavi/fast_blog?style=social)](https://github.com/Athenavi/fast_blog/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/Athenavi/fast_blog?style=social)](https://github.com/Athenavi/fast_blog/network/members)
[![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker&logoColor=white)](https://github.com/Athenavi/fast_blog/pkgs/container/fastblog)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Athenavi/fast_blog/blob/main/CONTRIBUTING.md)

**English** | [中文](README_zh.md)

[🚀 Quick Start](#-quick-start) · [📖 Documentation](#-documentation) · [🎯 Features](#-features) · [🗺️ Roadmap](#%EF%B8%8F-roadmap) · [🤝 Contributing](#-contributing)

</div>

---

## 📸 Preview

<div align="center">
  <em>Modern, fast, and beautiful — a blog platform designed for the modern web.</em>
</div>

---

## ✨ Why FastBlog?

FastBlog is a **next-generation blog platform** that combines the raw performance of **FastAPI** with the modern
frontend architecture of **Astro**. It's built for developers who want a production-ready blog system without the bloat.

| Feature           | FastBlog | WordPress | Ghost | Strapi |
|-------------------|----------|-----------|-------|--------|
| API-First         | ✅        | ❌         | ✅     | ✅      |
| Static Generation | ✅        | ❌         | ❌     | ❌      |
| Plugin System     | ✅        | ✅         | ❌     | ✅      |
| Mobile App        | ✅        | ❌         | ❌     | ❌      |
| Zero-JS Frontend  | ✅        | ❌         | ❌     | ❌      |
| Docker Ready      | ✅        | ✅         | ✅     | ✅      |

---

## 🎯 Features

### 🚀 Performance First

- **Astro Islands Architecture** — Zero JavaScript by default, 80%+ faster first paint
- **Async Everything** — FastAPI + asyncpg for non-blocking database operations
- **Smart Caching** — Multi-layer Redis caching with intelligent invalidation
- **CDN Optimized** — Static asset optimization with cache headers

### 🔌 Extensible

- **Plugin System** — Hook-based architecture (`do_action` / `apply_filters`), extend without touching core code
- **Theme Engine** — Hot-swappable Astro themes with React Islands
- **RESTful API** — Complete v2 API with auto-generated Swagger/ReDoc documentation
- **SDK Support** — Python & JavaScript SDK for programmatic access

### 🔒 Enterprise-Ready

- **JWT + OAuth2** — Secure authentication with Cookie/Bearer dual-mode, 2FA (TOTP)
- **Role-Based Access** — Granular RBAC permission system with capability-based roles
- **Zero Trust Security** — IP tracking, anomaly detection, content approval workflows
- **Audit Logging** — Track all sensitive operations
- **Rate Limiting** — Configurable per-endpoint rate limits

### 📱 Modern UX

- **Responsive Design** — Pixel-perfect on desktop, tablet, and mobile
- **Dark Mode** — System-aware dark/light theme switching
- **SEO Optimized** — Auto-generated sitemaps, meta tags, structured data
- **PWA Ready** — Installable as a native application with offline support
- **Mobile App** — Capacitor-wrapped native Android/iOS app

### 🛠️ Developer Experience

- **Hot Reload** — Instant feedback during development
- **CLI Tools** — Powerful command-line utilities (`python scripts/cli.py`)
- **Type Safe** — Full type annotations throughout the codebase
- **MCP Server** — AI integration for Claude Desktop & Cursor IDE

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx / CDN                          │
├────────────────────────┬────────────────────────────────────┤
│    Astro Frontend      │         FastAPI Backend            │
│   (Static SSG)        │    (Async REST API Server)         │
│                        │                                    │
│  ┌──────────────┐      │  ┌───────────┐  ┌──────────────┐  │
│  │  React 19    │      │  │  Routes   │  │  Middleware  │  │
│  │  Islands     │      │  │  (v2/v3)  │  │              │  │
│  └──────────────┘      │  └─────┬─────┘  └──────────────┘  │
│                        │        │                          │
│  ┌──────────────┐      │  ┌─────▼─────┐  ┌──────────────┐  │
│  │ TailwindCSS  │      │  │ Services  │  │  Plugin Hook │  │
│  └──────────────┘      │  └─────┬─────┘  └──────────────┘  │
│                        │        │                          │
│  ┌──────────────┐      │  ┌─────▼─────┐  ┌──────────────┐  │
│  │ TanStack     │      │  │  Models   │  │    Cache     │  │
│  │ React Query  │      │  │(SQLAlchemy)│  │   (Redis)    │  │
│  └──────────────┘      │  └─────┬─────┘  └──────────────┘  │
│                        │        │                          │
│                        │  ┌─────▼─────┐                    │
│                        │  │PostgreSQL │                    │
│                        │  └───────────┘                    │
├────────────────────────┴────────────────────────────────────┤
│                      Shared Models & Utils                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Tech Stack

<table>
<tr>
<td valign="top" width="50%">

**Backend**

- [FastAPI](https://fastapi.tiangolo.com/) 0.128 — Async web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) 2.0 — ORM & database toolkit
- [PostgreSQL](https://www.postgresql.org/) — Primary database (asyncpg)
- [Redis](https://redis.io/) — Caching & sessions
- [Alembic](https://alembic.sqlalchemy.org/) — Database migrations
- [Uvicorn](https://www.uvicorn.org/) — ASGI server
- [APScheduler](https://apscheduler.readthedocs.io/) — Background tasks

</td>
<td valign="top" width="50%">

**Frontend**

- [Astro](https://astro.build/) 5.7 — Static site generator (SSG)
- [React](https://react.dev/) 19 — UI components (Islands)
- [TailwindCSS](https://tailwindcss.com/) — Utility-first CSS
- [TypeScript](https://www.typescriptlang.org/) — Type safety
- [TanStack React Query](https://tanstack.com/query) — Data fetching
- [TipTap](https://tiptap.dev/) — Rich text editor
- [Radix UI](https://www.radix-ui.com/) — Accessible components

</td>
</tr>
<tr>
<td valign="top">

**Infrastructure**

- [Docker](https://www.docker.com/) — Containerization
- [Nginx](https://nginx.org/) — Reverse proxy
- [Capacitor](https://capacitorjs.com/) — Mobile app (Android/iOS)

</td>
<td valign="top">

**Integrations**

- [Meilisearch](https://www.meilisearch.com/) — Full-text search
- [Sentry](https://sentry.io/) — Error tracking
- [S3-compatible](https://aws.amazon.com/s3/) — Object storage
- [MCP Server](https://modelcontextprotocol.io/) — AI integration

</td>
</tr>
</table>

---

## 🚀 Quick Start

### One-Click Docker (Recommended)

```bash
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog
cp .env_example .env
# Edit .env with your database credentials

docker-compose up -d
```

Visit `http://localhost:4321` for the frontend, `http://localhost:9421/docs` for API docs.

### Manual Installation

<details>
<summary><b>Prerequisites</b></summary>

- Python 3.14+
- Node.js 18+
- PostgreSQL 17+
- Redis 7+ (optional, for caching)

</details>

```bash
# 1. Clone & setup backend
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
pip install -r requirements.txt

# 2. Configure environment
cp .env_example .env
# Edit .env with your settings

# 3. Run database migrations
alembic upgrade head

# 4. Start backend
python main.py --backend fastapi

# 5. Setup frontend (new terminal)
cd frontend-astro
npm install
npm run dev
```

### CLI Quick Start

```bash
# Using the built-in CLI
python scripts/cli.py create my-blog   # Initialize project
python scripts/cli.py user create admin --admin  # Create admin user
python scripts/cli.py dev --port 9421  # Start development server
```

---

## 📖 Documentation

| Document                                               | Description                |
|--------------------------------------------------------|----------------------------|
| [Quick Start](docs/QUICK_START.md)                     | Installation & setup guide |
| [Technical Architecture](docs/TECHNICAL.md)            | System design & decisions  |
| [API Reference](docs/API_REFERENCE.md)                 | Complete REST API docs     |
| [Plugin Development](docs/PLUGIN_DEVELOPMENT_GUIDE.md) | Build custom plugins       |
| [Theme Development](docs/THEME_DEVELOPMENT_GUIDE.md)   | Create custom themes       |
| [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)           | Production deployment      |
| [Troubleshooting](docs/TROUBLESHOOTING_FAQ.md)         | Common issues & solutions  |
| [Changelog](CHANGELOG.md)                              | Version history            |
| [Security Policy](SECURITY.md)                         | Vulnerability reporting    |

---

## 📊 Performance

Benchmarked against a typical blog with 1000 articles:

| Metric                   | FastBlog (Astro) | Typical SSR | Improvement |
|--------------------------|------------------|-------------|-------------|
| First Contentful Paint   | **~0.5s**        | ~1.5s       | ⬇️ 67%      |
| Largest Contentful Paint | **~0.8s**        | ~2.5s       | ⬇️ 68%      |
| Time to Interactive      | **~0.5s**        | ~3.0s       | ⬇️ 83%      |
| Homepage JS Size         | **~0KB**         | ~250KB      | ⬇️ 100%     |
| Lighthouse Score         | **98-100**       | 60-80       | ⬆️ 25%+     |

> Benchmarks run on standard hardware. Results may vary based on configuration and content.

---

## 🗺️ Roadmap

### ✅ Completed

- [x] FastAPI async backend with 100+ data models
- [x] Astro SSG frontend with React 19 Islands architecture
- [x] Plugin system with Hook mechanism (18 built-in plugins)
- [x] Theme engine with hot-swap (3 themes: default, magazine, modern-minimal)
- [x] RESTful API v2 with auto-generated Swagger docs
- [x] JWT authentication with 2FA (TOTP) & Zero Trust security
- [x] Article management with TipTap rich editor
- [x] Comment system with nested replies
- [x] Media management with S3-compatible storage
- [x] Full-text search (Meilisearch)
- [x] SEO optimization toolkit (sitemap, meta, structured data)
- [x] Docker deployment support
- [x] PWA support with offline capabilities
- [x] Real-time collaboration (Yjs-based)
- [x] AI integration via MCP Server
- [x] Mobile app (Capacitor Android/iOS)
- [x] E-commerce module (products, orders, cart)
- [x] Internationalization (i18n) with translation management

### 🚧 In Progress

- [ ] Multi-tenant support
- [ ] GraphQL API
- [ ] Advanced analytics dashboard

### 📅 Planned

- [ ] Webhook system
- [ ] Content versioning with diff view

See the [open issues](https://github.com/Athenavi/fast_blog/issues) for a full list of proposed features and known
issues.

---

## 🤝 Contributing

We welcome contributions of all kinds! Whether you're fixing a typo, adding a feature, or improving documentation, every
contribution matters.

**Quick Links:**

- 🐛 [Report a Bug](https://github.com/Athenavi/fast_blog/issues/new?template=bug_report.md)
- 💡 [Request a Feature](https://github.com/Athenavi/fast_blog/issues/new?template=feature_request.md)
- 💬 [Join the Discussion](https://github.com/Athenavi/fast_blog/discussions)
- 📖 [Read the Contributing Guide](CONTRIBUTING.md)

```bash
# 1. Fork & clone
git clone https://github.com/YOUR_USERNAME/fast_blog.git
cd fast_blog

# 2. Create a branch
git checkout -b feature/amazing-feature

# 3. Make your changes & test
python -m pytest tests/

# 4. Commit with conventional commits
git commit -m "feat: add amazing feature"

# 5. Push & create PR
git push origin feature/amazing-feature
```

Please read our [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

---

## 🌟 Contributors

<a href="https://github.com/Athenavi/fast_blog/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Athenavi/fast_blog" alt="Contributors" />
</a>

---

## 📄 License

This project is licensed under the **Apache License 2.0** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/) — The amazing async web framework
- [Astro](https://astro.build/) — The modern static site builder
- [SQLAlchemy](https://www.sqlalchemy.org/) — The Python SQL toolkit
- All our [contributors](https://github.com/Athenavi/fast_blog/graphs/contributors) who make this project better

---

<div align="center">

**If you find FastBlog useful, please consider giving it a ⭐ on GitHub!**

[⬆ Back to Top](#fastblog)

</div>
