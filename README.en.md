<div align="center">

# FastBlog

### A modern, self-hosted blogging & content platform

[![CI](https://github.com/Athenavi/fast_blog/actions/workflows/ci.yml/badge.svg)](https://github.com/Athenavi/fast_blog/actions/workflows/ci.yml)
[![Release](https://github.com/Athenavi/fast_blog/actions/workflows/release.yml/badge.svg)](https://github.com/Athenavi/fast_blog/actions/workflows/release.yml)
[![Version](https://img.shields.io/badge/version-0.8.26.0921-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.14-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136.3-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Nuxt](https://img.shields.io/badge/Nuxt-4.5-00DC82.svg?logo=nuxt&logoColor=white)](https://nuxt.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

[简体中文](README.md) | **English**

[Quick start](#quick-start) · [Features](#features) · [Tech stack](#tech-stack) · [Docs](#docs) · [Contributing](#contributing)

</div>

---

## Overview

FastBlog is a self-hostable blog / CMS:

- **Backend**: FastAPI + SQLAlchemy 2 (async) + PostgreSQL + Redis — **11 domains / 73 modules / 650 API routes**, all
  under `/api/v3`.
- **Frontend**: a single **Nuxt 4.5** project serving both the public blog (SSR, SEO-oriented) and the admin console (
  CSR, Element Plus).
- **Batteries included**: RBAC (roles / permission codes / permission groups / data scopes), plugins & themes,
  multi-platform publishing,
  backup and online upgrade, system monitoring, AI integrations (OpenAI-compatible / Anthropic), PWA and a Capacitor
  mobile shell.

## Screenshots

| Articles                                 | Article view                                     | Media library                   |
|------------------------------------------|--------------------------------------------------|---------------------------------|
| ![Articles](docs/assets/ArtclesPage.png) | ![Article view](docs/assets/ArticleViewPage.png) | ![Media](docs/assets/media.png) |

## Features

**Content**: articles / pages / categories / tags, rich-text editor (TipTap), media library (content-addressed storage
with
private-media authorization), comments, custom post types, shortcodes, page builder, content approval, collaborative
editing (Yjs).

**System**: users / roles / permission codes / permission groups / data scopes, menu-level authorization,
write-operation audit log,
system monitoring (sessions & alerts), cache management, logs, sensitive words, GDPR consent records, install wizard,
site settings,
third-party integrations, social accounts.

**Operations**: dashboard and report center, SEO (sitemaps / metadata / structured data), full-text search (
Meilisearch),
backups (full / incremental / S3·OSS cloud storage), CDN operations (Alibaba Cloud / Tencent Cloud / CloudFront), email,
notifications, webhooks, deployment and online upgrade (with rollback), process supervision, data migration (WordPress
WXR, etc.).

**Growth**: VIP subscriptions and payments, tipping with revenue withdrawal, points / badges / expert certification,
follow & followers, personalized feed, group chat and direct messages.

**Extensibility**: plugin system (EventBus), theme engine (bundled `fastblog-default`, `modern-minimal`, `magazine`),
block patterns, widgets, AI configuration (multi-protocol + workflows).

**Frontend**: SSR public site + CSR admin, Tailwind 4 with shadcn-style components, Element Plus admin widgets,
Chinese/English i18n, PWA (offline caching / installable), Capacitor mobile shell.

## Quick start

```bash
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog
python install.py
```

The installer walks you through: env self-check → generating `.env` with strong random secrets → fetching the static
ffmpeg binary if missing → building and starting the containers → running database migrations → picking seed data →
creating a login user with one of the built-in roles (`superadmin` / `admin` / `editor` / `user`).

Non-interactive usage:

```bash
FASTBLOG_ADMIN_PASSWORD='<strong-password>' python install.py --yes --mode init --seeds rbac,menus --admin-user admin
python install.py --check        # environment check only
```

Manual equivalent steps: [docs/DEPLOYMENT.md §3](docs/DEPLOYMENT.md#3-快速部署默认形态) (Chinese).

Then open **<http://localhost:4321>** (the nginx entry point; port controlled by `FRONTEND_PORT`).

For production use `docker-compose.prod.yml`, which *requires* `SECRET_KEY` / `JWT_SECRET_KEY` / `DB_PASSWORD` /
`REDIS_PASSWORD`
and enables multiple workers, Redis auth, resource limits and HTTPS ports:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

For running backend and frontend separately during development, see
the [development guide](docs/DEVELOPMENT.md#3-本地开发) (Chinese).

## Tech stack

| Layer      | Choices                                                                                                                 |
|------------|-------------------------------------------------------------------------------------------------------------------------|
| Backend    | Python 3.14 · FastAPI 0.136 · SQLAlchemy 2 (async) · asyncpg · Alembic · Redis                                          |
| Database   | PostgreSQL 16                                                                                                           |
| Frontend   | Nuxt 4.5 (Vue 3 · TypeScript) · Tailwind 4 with shadcn-style components · Element Plus · Pinia · TipTap · ECharts       |
| Deployment | Docker Compose · nginx (TLS / rate limiting / security headers) · multi-stage images (python:3.14-slim, node:22-alpine) |
| Quality    | pytest · ruff · mypy · vue-tsc · Playwright · GitHub Actions                                                            |

## Project status

- Current version **0.8.26.0921** (see [`version.txt`](version.txt)); Alembic head is `8b7ecb6d053c`.
- Known issues (details in [docs/DEPLOYMENT.md §13](docs/DEPLOYMENT.md#13-已知偏差代码或脚本与当前架构不一致尚未修复),
  Chinese):
    - `docs/FastBlog_API.postman_collection.json` still uses the removed `/api/v1` base URL.
- Interactive API docs are available outside production: `http://localhost:9421/api/v3/docs` (disabled by design when
  `ENVIRONMENT=production`).

## Docs

Project documentation is written in Chinese; the entry points are:

| Document                                         | Contents                                                                                                       |
|--------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)         | Compose topologies, environment variables, nginx, backups/restore, upgrades, troubleshooting                   |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)       | Architecture, backend domains and hard rules, frontend conventions, tests and quality gates, command reference |
| [frontend/web/README.md](frontend/web/README.md) | Frontend layout, scripts, environment variables, conventions                                                   |
| [tests/README.md](tests/README.md)               | Backend test layout and how to run them                                                                        |
| [CHANGELOG.md](CHANGELOG.md)                     | Version timeline and changes                                                                                   |
| [CONTRIBUTING.md](CONTRIBUTING.md)               | Setup, code style, PR workflow                                                                                 |
| [SECURITY.md](SECURITY.md)                       | Vulnerability reporting and built-in security features                                                         |

## Repository layout

```
main.py              Backend entry point (FastAPI on :9421)
install.py           Interactive installer / initializer (env check → .env → migrations → seeds → users)
src/api/v3/          The single authoritative API layer (domain → module → controller/schema/crud/service)
shared/              Models and domain services (shared/models, shared/services)
config/models.yaml   Single source of truth for data models
frontend/web/        Nuxt 4.5 frontend (SSR public site + CSR admin)
plugins/             Plugins and themes
cli/                 Command-line tooling (python -m cli)
scripts/             Generators and seed scripts
tests/               Backend tests (58 test files)
docs/                Documentation
nginx/               nginx configuration (single public entry point)
alembic_migrations/  Database migrations
```

## Contributing

Contributions to code, docs and translations are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and follow the
[Code of Conduct](.github/CODE_OF_CONDUCT.md). For security issues, do **not** open a public issue — report privately
per [SECURITY.md](SECURITY.md).

## License

Licensed under the **Apache License 2.0** — see [LICENSE](LICENSE). Contents of `plugins/` are MIT licensed.

---

<div align="center">

If FastBlog is useful to you, please consider giving it a ⭐

[⬆ Back to top](#fastblog)

</div>
