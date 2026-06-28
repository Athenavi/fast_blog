# FastBlog 部署指南

> **版本**: V0.5.26.0612 | 本文档说明生产环境部署方案。

---

## 系统要求

| 项目 | 最低配置 | 推荐配置 |
|-----|---------|---------|
| CPU | 2 核心 | 4 核心 |
| 内存 | 4 GB RAM | 8 GB RAM |
| 存储 | 20 GB SSD | 50 GB SSD |

### 软件依赖

- **Python**: 3.14+ / **PostgreSQL**: 16+ / **Redis**: 7+
- **Nginx**: 1.18+ / **Node.js**: 18+（前端构建用）

---

## Docker 部署（推荐）

```bash
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog
cp .env_example .env
# 编辑 .env 中的关键配置项

# 启动所有服务
docker-compose up -d

# 验证
curl http://localhost:9421/api/v2/health
curl http://localhost:4321
```

| 服务 | 端口 | 说明 |
|------|------|------|
| backend | 9421 | FastAPI 后端 |
| frontend | 4321 | Astro 前端 |
| postgres | 5432 | PostgreSQL 数据库 |
| redis | 6379 | Redis 缓存 |
| nginx | 80/443 | 反向代理 |

---

## Nginx 配置

项目提供 [`nginx/conf.d/fastblog.conf`](../nginx/conf.d/fastblog.conf)，包含反向代理、速率限制、安全头、Gzip 压缩和缓存策略。

### BT 面板（非 Docker）部署

使用 BT 面板时，Nginx 配置示例（`/www/server/panel/vhost/nginx/node_fb2607.conf`）：

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # API 转发到后端
    location ^~ /api/ {
        proxy_pass http://127.0.0.1:9421;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Media 文件
    location ^~ /media/ {
        proxy_pass http://127.0.0.1:9421;
    }

    # 前端 SSR
    location / {
        proxy_pass http://[::1]:4321;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

> ⚠️ SSR 服务默认监听 `[::1]:4321`（IPv6），Nginx 需用 `[::1]` 而非 `127.0.0.1`。
> 如要改用 IPv4，启动时设置 `HOST=0.0.0.0`。

### SSR 模式启动

```bash
# 安装 PM2
npm install -g pm2

# 启动
cd /www/wwwroot/your-site
pm2 start dist/server/entry.mjs --name fastblog-ssr
pm2 save

# 验证
curl http://localhost:4321
```

### 运行时配置

前端 API 地址通过 `public/config.js` 配置，构建后位于 `dist/client/config.js`：

```js
const runtimeConfig = {
    API_BASE_URL: '',      // 空 = 相对路径，由 Nginx 代理
    API_PREFIX: '/api/v2'
};
```

> 设为空字符串后，浏览器使用 `/api/v2/...` 相对路径，由 Nginx 代理转发到后端。

### SSL 证书

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 自动续期（crontab）
0 3 * * * certbot renew --quiet
```

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_HOST` | PostgreSQL 主机 | `localhost` |
| `DB_PORT` | PostgreSQL 端口 | `5432` |
| `DB_NAME` | 数据库名 | `fast_blog` |
| `REDIS_HOST` | Redis 主机 | `localhost` |
| `SECRET_KEY` | JWT 密钥 | — |
| `ENVIRONMENT` | 运行环境 | `production` |
| `DEBUG` | 调试模式 | `False` |

---

## 监控与维护

### 日志
```bash
docker-compose logs -f backend  # Docker 环境
journalctl -u fastblog -f       # systemd 环境
```

### 备份
```bash
docker-compose exec postgres pg_dump -U postgres fast_blog > backup.sql
tar -czf media_backup.tar.gz media/
```

### 自动更新
```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

---

## 相关文档

- [快速开始](QUICK_START.md)
- [技术架构](TECHNICAL.md)
- [API 参考](API_REFERENCE.md)
