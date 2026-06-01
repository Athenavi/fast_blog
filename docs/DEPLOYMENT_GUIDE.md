# FastBlog 部署指南

> **版本**: V0.3.26.0521 | 本文档说明如何将 FastBlog 部署到生产环境。

---

## 系统要求

### 推荐配置

| 项目  | 最低配置      | 推荐配置      |
|-----|-----------|-----------|
| CPU | 2 核心      | 4 核心      |
| 内存  | 4 GB RAM  | 8 GB RAM  |
| 存储  | 20 GB SSD | 50 GB SSD |
| 带宽  | 5 Mbps    | 10 Mbps+  |

### 软件依赖

- **Python**: 3.14+
- **PostgreSQL**: 16+
- **Redis**: 7+
- **Nginx**: 1.18+
- **Node.js**: 18+（前端构建）

---

## Docker 部署（推荐）

### 1. 克隆项目

```bash
git clone https://github.com/Athenavi/fast-blog.git
cd fast-blog
```

### 2. 配置环境变量

```bash
# 复制环境配置文件
cp .env.example .env

# 编辑 .env 文件，配置以下关键项：
# - DB_USER, DB_PASSWORD, DB_NAME（数据库）
# - SECRET_KEY（JWT 密钥）
# - REDIS_URL（Redis 连接）
```

### 3. 启动所有服务

项目提供了完整的 Docker Compose 配置，包含以下服务：

| 服务       | 容器名               | 端口     | 说明             |
|----------|-------------------|--------|----------------|
| backend  | fastblog-backend  | 9421   | FastAPI 后端     |
| frontend | fastblog-frontend | 4321   | Astro 前端       |
| postgres | fastblog-postgres | 5432   | PostgreSQL 数据库 |
| redis    | fastblog-redis    | 6379   | Redis 缓存       |
| nginx    | fastblog-nginx    | 80/443 | Nginx 反向代理     |

```bash
# 生产环境部署
docker-compose up -d

# 开发环境部署（使用 docker-compose.dev.yml）
docker-compose -f docker-compose.dev.yml up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
```

### 4. 验证部署

```bash
# 检查后端健康状态
curl http://localhost:9421/api/v2/health

# 检查前端
curl http://localhost:4321

# 通过 Nginx 访问（推荐）
curl http://localhost/health
```

---

## 手动部署

### 1. 安装 Python 依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置数据库

```bash
# 创建 PostgreSQL 数据库
createdb fast_blog

# 运行数据库迁移
alembic upgrade head
```

### 3. 构建前端

```bash
cd frontend-astro
npm install
npm run build
cd ..
```

### 4. 启动后端

```bash
# 使用内置启动器（推荐，支持进程监督）
python main.py --backend fastapi --port 9421

# 或直接使用 Uvicorn
uvicorn src.app:create_app --factory --host 0.0.0.0 --port 9421
```

---

## Nginx 配置

项目提供了生产级 Nginx 配置文件 [`nginx/conf.d/fastblog.conf`](../nginx/conf.d/fastblog.conf)，包含以下特性：

- **反向代理**: 后端 API (`/api/`) 和前端 (`/`) 分离代理
- **速率限制**: API 30r/s、登录 5r/m、通用 50r/s
- **安全头**: X-Frame-Options、X-Content-Type-Options、X-XSS-Protection
- **Gzip 压缩**: 自动压缩文本/JSON/SVG 等资源
- **缓存策略**: 静态资源 7 天、媒体文件 30 天

### 手动配置 Nginx

如果未使用 Docker Compose 自带的 Nginx 服务，可手动配置：

```nginx
upstream backend {
    server 127.0.0.1:9421;
    keepalive 32;
}

upstream frontend {
    server 127.0.0.1:4321;
    keepalive 32;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL 证书
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript image/svg+xml;
    client_max_body_size 60M;

    # API 代理
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 媒体文件
    location /media/ {
        proxy_pass http://backend;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 前端（catch-all）
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 健康检查
    location /health {
        proxy_pass http://backend/api/v2/health;
    }
}
```

### 配置 SSL 证书

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 自动续期（添加 crontab）
0 3 * * * certbot renew --quiet
```

---

## 环境变量

项目通过 `.env` 文件配置，关键变量如下：

| 变量            | 说明            | 默认值          |
|---------------|---------------|--------------|
| `DB_HOST`     | PostgreSQL 主机 | `localhost`  |
| `DB_PORT`     | PostgreSQL 端口 | `5432`       |
| `DB_USER`     | 数据库用户名        | `postgres`   |
| `DB_PASSWORD` | 数据库密码         | -            |
| `DB_NAME`     | 数据库名          | `fast_blog`  |
| `REDIS_HOST`  | Redis 主机      | `localhost`  |
| `REDIS_PORT`  | Redis 端口      | `6379`       |
| `SECRET_KEY`  | JWT 密钥        | -            |
| `ENVIRONMENT` | 运行环境          | `production` |
| `DEBUG`       | 调试模式          | `False`      |

---

## 监控与维护

### 日志管理

```bash
# Docker 环境
docker-compose logs -f backend
docker-compose logs -f frontend

# 手动部署
# 日志输出到 stdout/stderr，可通过 systemd journal 查看
journalctl -u fastblog -f
```

### 备份策略

项目提供了内置备份脚本 [`scripts/backup.sh`](../scripts/backup.sh)：

```bash
# 手动备份数据库
pg_dump -U postgres fast_blog | gzip > backups/db_$(date +%Y%m%d_%H%M%S).sql.gz

# 备份媒体文件
tar czf backups/media_$(date +%Y%m%d_%H%M%S).tar.gz media/

# 通过 API 管理备份（Update Server）
curl -X POST http://localhost:9421/api/v1/backups/create
curl http://localhost:9421/api/v1/backups
```

### 自动更新

FastBlog 内置了 Update Server（`update_server/server.py`），支持：

- 版本检查与自动更新
- 备份与回滚
- 更新包管理

```bash
# 检查更新
curl -X POST http://localhost:9421/api/v1/update/check

# 应用更新
curl -X POST http://localhost:9421/api/v1/update/apply
```

---

## 常见问题

### 端口被占用

```bash
# 查看端口占用
netstat -tlnp | grep 9421
# 或
lsof -i :9421
```

### 数据库连接失败

1. 确认 PostgreSQL 服务已启动
2. 检查 `.env` 中的数据库配置
3. 确认数据库用户有足够权限

### 前端构建失败

```bash
cd frontend-astro
rm -rf node_modules package-lock.json
npm install
npm run build
```

---

## 相关文档

- [技术架构](TECHNICAL.md)
- [快速开始](QUICK_START.md)
- [API 参考](API_REFERENCE.md)
