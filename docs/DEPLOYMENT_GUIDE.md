# FastBlog 部署指南

**适用版本**: FastBlog 0.0.2.0+

---

## 📋 目录

1. [系统要求](#系统要求)
2. [Docker 部署（推荐）](#docker-部署推荐)
3. [传统服务器部署](#传统服务器部署)
4. [数据库管理](#数据库管理)
5. [性能优化](#性能优化)
6. [安全加固](#安全加固)

---

## 系统要求

### 最低配置

| 组件         | 要求                                      |
|------------|-----------------------------------------|
| CPU        | 2 核心                                    |
| 内存         | 2 GB RAM                                |
| 存储         | 10 GB 可用空间                              |
| 操作系统       | Linux (Ubuntu 24.04+) / macOS / Windows |
| Python     | 3.14+                                   |
| Node.js    | 18+ (前端构建)                              |
| PostgreSQL | 17+                                     |
| Redis      | 6+ (可选)                                 |

### 推荐配置（生产环境）

| 组件         | 要求               |
|------------|------------------|
| CPU        | 4+ 核心            |
| 内存         | 4+ GB RAM        |
| 存储         | 50+ GB SSD       |
| 操作系统       | Ubuntu 22.04 LTS |
| PostgreSQL | 17               |
| Redis      | 7                |
| Nginx      | 1.24+            |

---

## Docker 部署（推荐）

Docker 部署是最简单、最可靠的部署方式。

### 前置条件

- Docker 20.10+
- Docker Compose 2.0+

### 步骤 1: 克隆项目

```bash
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog
```

### 步骤 2: 配置环境变量

复制示例配置文件：

```bash
cp .env_example .env
```

编辑 `.env` 文件，修改关键配置：

```env
# 数据库配置
DB_NAME=fast_blog
DB_USER=postgres
DB_PASSWORD=your-strong-password-here
DB_PORT=5432

# 应用配置
SECRET_KEY=your-super-secret-key-change-this
DOMAIN=https://yourdomain.com

# JWT 配置
JWT_SECRET_KEY=your-jwt-secret-key

# 端口配置
BACKEND_PORT=9421
FRONTEND_PORT=3000
```

**⚠️ 重要**: 务必修改 `SECRET_KEY` 和 `DB_PASSWORD` 为强密码！

### 步骤 3: 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 检查服务状态
docker-compose ps
```

### 步骤 4: 初始化数据库

首次启动时，数据库会自动迁移。如果需要手动执行：

```bash
docker-compose exec backend python django_blog/manage.py migrate
```

### 步骤 5: 创建管理员账户

```bash
docker-compose exec backend python django_blog/manage.py createsuperuser
```

### 步骤 6: 访问应用

- **前端**: http://localhost:3000
- **后端 API**: http://localhost:9421
- **API 文档**: http://localhost:9421/docs
- **管理后台**: http://localhost:9421/admin

### 常用 Docker 命令

```bash
# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 进入容器
docker-compose exec backend bash
docker-compose exec db psql -U postgres

# 更新服务
docker-compose pull
docker-compose up -d

# 清理未使用的资源
docker system prune -a
```

---

## 传统服务器部署

### 1. 准备服务器

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要工具
sudo apt install -y python3-pip python3-venv nginx postgresql redis-server
```

### 2. 安装 Python 依赖

```bash
# 创建虚拟环境
python3 -m venv /opt/fastblog/venv
source /opt/fastblog/venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置数据库

```bash
# 创建数据库和用户
sudo -u postgres psql
CREATE DATABASE fast_blog;
CREATE USER fastblog WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE fast_blog TO fastblog;
\q
```

### 4. 配置环境变量

```bash
cp .env_example .env
nano .env
```

### 5. 运行迁移

```bash
python django_blog/manage.py migrate
python django_blog/manage.py collectstatic
python django_blog/manage.py createsuperuser
```

### 6. 配置 Gunicorn

创建 `gunicorn_config.py`：

```python
bind = "127.0.0.1:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
```

### 7. 配置 Nginx

创建 `/etc/nginx/sites-available/fastblog`：

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /opt/fastblog/static/;
        expires 30d;
    }

    location /media/ {
        alias /opt/fastblog/media/;
        expires 30d;
    }
}
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/fastblog /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 8. 配置 systemd 服务

创建 `/etc/systemd/system/fastblog.service`：

```ini
[Unit]
Description = FastBlog Backend
After = network.target

[Service]
User = www-data
Group = www-data
WorkingDirectory = /opt/fastblog
Environment = "PATH=/opt/fastblog/venv/bin"
ExecStart = /opt/fastblog/venv/bin/gunicorn -c gunicorn_config.py main:app
Restart = always

[Install]
WantedBy = multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable fastblog
sudo systemctl start fastblog
```

---

## 数据库管理

### 备份数据库

```bash
# PostgreSQL 备份
pg_dump -U postgres fast_blog > backup_$(date +%Y%m%d).sql

# Docker 环境
docker-compose exec postgres pg_dump -U postgres fast_blog > backup.sql
```

### 恢复数据库

```bash
# PostgreSQL 恢复
psql -U postgres fast_blog < backup.sql

# Docker 环境
docker-compose exec -T postgres psql -U postgres fast_blog < backup.sql
```

### 数据库优化

```sql
-- 分析表
ANALYZE;

-- 重建索引
REINDEX DATABASE fast_blog;

-- 清理死元组
VACUUM FULL;
```

---

## 性能优化

### 1. 启用缓存

配置 Redis 缓存：

```env
REDIS_URL=redis://localhost:6379/0
CACHE_BACKEND=redis
```

### 2. CDN 加速

使用 CDN 加速静态资源：

```env
CDN_ENABLED=true
CDN_URL=https://cdn.yourdomain.com
```

### 3. 图片优化

启用图片压缩和懒加载：

```env
IMAGE_OPTIMIZATION=true
LAZY_LOADING=true
```

### 4. 数据库优化

- 添加适当的索引
- 使用连接池
- 定期清理旧数据

### 5. Gzip 压缩

在 Nginx 中启用 Gzip：

```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript;
gzip_min_length 1000;
```

---

## 安全加固

### 1. HTTPS 配置

使用 Let's Encrypt 获取免费 SSL 证书：

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 2. 防火墙配置

```bash
# 启用防火墙
sudo ufw enable

# 允许必要端口
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https

# 检查状态
sudo ufw status
```

### 3. 数据库安全

```env
# 使用强密码
DB_PASSWORD=strong-random-password

# 限制数据库访问
# 在 pg_hba.conf 中配置
```

### 4. 定期更新

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 更新 Python 依赖
pip install --upgrade -r requirements.txt

# 更新 Node.js 依赖
cd frontend-next && npm update
```

### 5. 监控和日志

配置日志轮转：

```bash
sudo nano /etc/logrotate.d/fastblog
```

```
/opt/fastblog/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
```

---

## 常见问题

### Q: 如何查看服务状态？

```bash
# Docker 环境
docker-compose ps
docker-compose logs -f

# Systemd 环境
sudo systemctl status fastblog
sudo journalctl -u fastblog -f
```

### Q: 如何重置管理员密码？

```bash
docker-compose exec backend python django_blog/manage.py changepassword admin
```

### Q: 如何处理高并发？

- 增加 Gunicorn workers 数量
- 启用 Redis 缓存
- 使用 CDN
- 优化数据库查询

---

## 总结

- ✅ 推荐使用 Docker 部署，简单可靠
- ✅ 生产环境务必启用 HTTPS
- ✅ 定期备份数据库
- ✅ 配置监控和日志
- ✅ 保持系统和依赖更新

更多详细信息请参考 [QUICK_START.md](QUICK_START.md) 和 [TROUBLESHOOTING_FAQ.md](TROUBLESHOOTING_FAQ.md)。
