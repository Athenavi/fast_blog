# FastBlog 部署指南

> 适用版本：V0.6.26+ | 环境：Linux（推荐）/ Windows / macOS

## 系统要求

| 项目 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核心 | 4 核心 |
| 内存 | 4 GB | 8 GB |
| 存储 | 20 GB SSD | 50 GB SSD |

依赖：Python 3.14+ / PostgreSQL 16+ / Redis 7+ / Nginx 1.18+（Node.js 18+ 仅前端构建需要）。

## Docker 部署（推荐）

```bash
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog
cp .env.example .env
# 编辑 .env：SECRET_KEY / JWT_SECRET_KEY 必须设置（>=32 位随机）

docker compose up -d
# 生产：docker compose -f docker-compose.prod.yml up -d

# 验证
curl http://localhost:9421/api/v2/health
```

| 服务 | 端口 | 说明 |
|------|------|------|
| backend | 9421 | FastAPI 后端（生产仅绑定 `127.0.0.1`） |
| frontend (nginx) | 80/443 | Nginx：静态前端 + 反代 `/api` |
| postgres | 5432 | PostgreSQL（生产仅绑定 `127.0.0.1`） |
| redis | 6379 | Redis 缓存/限流/调度锁（生产仅绑定 `127.0.0.1`） |

> **端口 4321 仅开发环境使用**（`npm run dev` 或开发 compose）。生产架构为：Nginx 在 80/443 统一提供前端静态文件并反代 `/api` 到后端 9421；后端/数据库/Redis 不直接暴露公网。

## Nginx 反向代理

项目提供两份 Nginx 配置：

- `frontend-astro/nginx.conf` — 生产镜像内置（前端静态文件 + 反代 API，推荐，用于 `docker compose -f docker-compose.prod.yml`）
- `nginx/conf.d/fastblog.conf` — 独立 Nginx 反代示例（配合手动部署/裸机）

核心反代片段（独立 Nginx 场景，后端由 9421 提供，静态由 Astro 独立服务 4321 提供）：

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location ^~ /api/ {
        proxy_pass http://127.0.0.1:9421;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:4321;
    }
}
```

### 安全响应头

FastBlog 采用前后端分离架构，安全策略在 Nginx 层实施（性能开销最小）。官方配置已内置：

```nginx
server {
    server_tokens off;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: blob: https:; font-src 'self' data: https://cdn.jsdelivr.net; connect-src 'self' wss:; object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'" always;
}
```

> CSP 中的 `'unsafe-inline'` 为 Tiptap 编辑器所需；如不使用可收紧为 `'self'`。

### 速率限制

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

location ^~ /api/ {
    limit_req zone=api burst=50 nodelay;
    ...
}
```

> 登录接口限速更严格（5r/m），后端同时有应用层限流 + 账户锁定双重防护。

### 运行时 API 地址

前端通过 `public/config.js`（构建后为 `dist/client/config.js`）配置 API 地址：

```js
const runtimeConfig = {
    API_BASE_URL: '',      // 空 = 相对路径，由 Nginx 代理
    API_PREFIX: '/api/v2'
};
```

## SSL 证书（HTTPS）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
# 自动续期：0 3 * * * certbot renew --quiet
```

## 直接运行 Astro 服务（可选，替代 Nginx 托管静态）

前端构建产物为静态文件（`output: 'static'`），同时附带了独立 Node 服务（`@astrojs/node` standalone）：

```bash
cd frontend-astro
npm install
npm run build        # 产物在 dist/
node dist/server/entry.mjs   # 独立服务，默认监听 4321（可用 HOST/PORT 环境变量覆盖）
```

> 生产默认推荐由 Nginx 直接托管 `dist/client` 静态文件（性能最好）；需要动态能力时再运行独立 Node 服务。
> 如用 PM2 托管：`pm2 start dist/server/entry.mjs --name fastblog`。

## 环境变量速查

| 变量 | 说明 | 默认 |
|------|------|------|
| `SECRET_KEY` / `JWT_SECRET_KEY` | 加密密钥（**必填**，≥32 位随机） | — |
| `DB_HOST` / `DB_PORT` / `DB_NAME` | PostgreSQL | `localhost/5432/fast_blog` |
| `REDIS_HOST` / `REDIS_PORT` | Redis | `localhost/6379` |
| `WORKERS` | 多 worker 进程数（>1 需 Redis） | `1` |
| `DISABLED_MODULES` | 关闭非核心内置插件（如 `ecommerce,enterprise`） | 空 |
| `ENVIRONMENT` / `DEBUG` | 运行环境 | `production/False` |

## 监控与维护

```bash
# 日志
docker compose logs -f backend
journalctl -u fastblog -f

# 备份
docker compose exec postgres pg_dump -U postgres fast_blog > backup.sql
tar -czf media_backup.tar.gz media/

# 更新
git pull
docker compose build --no-cache
docker compose up -d
```

> 数据库/文件备份亦可在管理后台触发，并支持定时自动备份（每天 02:00 数据库、每周日 03:00 完整备份）。

## 相关文档

- [快速开始](getting-started.md)
- [开发指南](development.md)
- [运维手册](operations.md)
