<div align="center">

<img src="docs/assets/fastblog-logo.svg" alt="FastBlog Logo" width="120" height="120" onerror="this.style.display='none'">

# FastBlog

### ⚡ The Modern, High-Performance Blog Platform Built for Developers

[![CI Status](https://github.com/Athenavi/fast_blog/actions/workflows/ci.yml/badge.svg)](https://github.com/Athenavi/fast_blog/actions/workflows/ci.yml)
[![Release](https://github.com/Athenavi/fast_blog/actions/workflows/release.yml/badge.svg)](https://github.com/Athenavi/fast_blog/actions/workflows/release.yml)
[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136.3-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Astro](https://img.shields.io/badge/Astro-5.x-BC52EE.svg?logo=astro&logoColor=white)](https://astro.build/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](./LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker&logoColor=white)](https://github.com/Athenavi/fast_blog/pkgs/container/fastblog)

**English** | [中文](README_zh.md)

[🚀 Quick Start](#-quick-start) · [📖 Documentation](#-documentation) · [🎯 Features](#-features) · [🤝 Contributing](#-contributing)

</div>

---

## 🎯 Features

- **FastAPI Backend** — Async web framework with auto-generated API docs
- **Astro Frontend** — Islands architecture, zero-JS by default, blazing-fast first paint
- **Plugin System** — EventBus-driven architecture, extend without touching core code
- **Rich Editor** — TipTap-based WYSIWYG editor
- **Theme Engine** — Hot-swappable themes with React Islands
- **JWT + OAuth2** — Secure auth with cookie/bearer dual-mode, 2FA (TOTP)
- **RBAC** — Granular role-based permission system
- **Full-Text Search** — Meilisearch integration
- **SEO Toolkit** — Auto sitemaps, meta tags, structured data
- **PWA Ready** — Installable as native app with offline support
- **Multi-Language** — i18n support with translation management

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

## 🚀 Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog
cp .env_example .env
# Edit .env with your database credentials
docker-compose up -d
```

Visit `http://localhost:4321` for the frontend, `http://localhost:9421/docs` for API docs.

### Manual Installation

```bash
# Backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env_example .env       # Edit .env with your settings
alembic upgrade head
python main.py

# Frontend (new terminal)
cd frontend-astro
npm install
npm run dev
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Quick Start](docs/QUICK_START.md) | Installation & setup guide |
| [Technical Architecture](docs/TECHNICAL.md) | System design & decisions |
| [API Reference](docs/API_REFERENCE.md) | Complete REST API docs |
| [Plugin Development](docs/PLUGIN_DEVELOPMENT_GUIDE.md) | Build custom plugins |
| [Theme Development](docs/THEME_DEVELOPMENT_GUIDE.md) | Create custom themes |
| [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) | Production deployment |
| [Troubleshooting](docs/TROUBLESHOOTING_FAQ.md) | Common issues & solutions |
| [AI Interaction](docs/AI_INTERACTION_GUIDE.md) | MCP Server integration |

---

## 🤝 Contributing

We welcome contributions! Please read our [Contributing Guide](CONTRIBUTING.md) before submitting PRs.

```bash
git clone https://github.com/YOUR_USERNAME/fast_blog.git
cd fast_blog
git checkout -b feature/amazing-feature
git commit -m "feat: add amazing feature"
git push origin feature/amazing-feature
```

---

## 📄 License

This project is licensed under the **Apache License 2.0** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**If you find FastBlog useful, please consider giving it a ⭐ on GitHub!**

[⬆ Back to Top](#fastblog)

</div>
