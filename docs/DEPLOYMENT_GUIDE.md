# FastBlog 部署指南

本文档详细说明如何将 FastBlog 部署到生产环境。

## 目录

- [系统要求](#系统要求)
- [快速部署](#快速部署)
- [手动部署](#手动部署)
- [Docker 部署](#docker-部署)
- [配置优化](#配置优化)
- [监控与维护](#监控与维护)
- [故障排查](#故障排查)

---

## 系统要求

### 最低配置

- **CPU**: 2 核心
- **内存**: 4 GB RAM
- **存储**: 20 GB SSD
- **操作系统**: Ubuntu 20.04+ / CentOS 8+

### 推荐配置

- **CPU**: 4 核心
- **内存**: 8 GB RAM
- **存储**: 50 GB SSD
- **带宽**: 10 Mbps+

### 软件依赖

- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- Nginx 1.18+
- Node.js 18+ (前端构建)

---

## 快速部署

### 1. 一键部署脚本

```bash
# 下载部署脚本
wget https://raw.githubusercontent.com/fastblog/fastblog/main/scripts/deploy.sh
chmod +x deploy.sh

# 执行部署
sudo ./deploy.sh production
```

**脚本功能：**

- ✅ 自动检查依赖
- ✅ 备份现有数据
- ✅ 更新代码
- ✅ 数据库迁移
- ✅ 重启服务
- ✅ 健康检查

---

## 手动部署

### 步骤 1: 准备服务器

#### Ubuntu/Debian

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y git curl wget vim

# 安装 Python
sudo apt install -y python3 python3-pip python3-venv

# 安装 PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# 安装 Redis
sudo apt install -y redis-server

# 安装 Nginx
sudo apt install -y nginx
```

#### CentOS/RHEL

```bash
# 安装 EPEL
sudo yum install -y epel-release

# 安装 Python
sudo yum install -y python3 python3-pip

# 安装 PostgreSQL
sudo yum install -y postgresql-server postgresql-contrib
sudo postgresql-setup --initdb

# 安装 Redis
sudo yum install -y redis

# 安装 Nginx
sudo yum install -y nginx
```

### 步骤 2: 配置数据库

```bash
# 切换到 postgres 用户
sudo -i -u postgres

# 创建数据库和用户
psql << EOF
CREATE USER fastblog WITH PASSWORD 'your_secure_password';
CREATE DATABASE fast_blog OWNER fastblog;
GRANT ALL PRIVILEGES ON DATABASE fast_blog TO fastblog;
EOF

# 退出
exit
```

### 步骤 3: 克隆代码

```bash
# 创建应用目录
sudo mkdir -p /opt/fastblog
sudo chown $USER:$USER /opt/fastblog

# 克隆代码
cd /opt/fastblog
git clone https://github.com/fastblog/fastblog.git .
```

### 步骤 4: 配置环境变量

```bash
# 复制示例配置
cp .env_example .env

# 编辑配置
vim .env
```

**关键配置项：**

```env
# 数据库
DB_HOST=localhost
DB_PORT=5432
DB_USER=fastblog
DB_PASSWORD=your_secure_password
DB_NAME=fast_blog

# 安全
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 环境
ENVIRONMENT=production
DEBUG=False

# 域名
DOMAIN=https://yourdomain.com
```

### 步骤 5: 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

### 步骤 6: 数据库迁移

```bash
# 运行 Alembic 迁移
alembic upgrade head
```

### 步骤 7: 构建前端（如果需要）

```bash
cd frontend-next

# 安装依赖
npm install

# 构建
npm run build

# 返回项目根目录
cd ..
```

### 步骤 8: 配置 Systemd 服务

创建服务文件 `/etc/systemd/system/fastblog.service`：

```ini
[Unit]
Description = FastBlog Application
After = network.target postgresql.service redis.service

[Service]
Type = simple
User = www-data
Group = www-data
WorkingDirectory = /opt/fastblog
Environment = "PATH=/opt/fastblog/venv/bin"
ExecStart = /opt/fastblog/venv/bin/python main.py
Restart = always
RestartSec = 10

# 日志
StandardOutput = journal
StandardError = journal
SyslogIdentifier = fastblog

# 安全
NoNewPrivileges = true
ProtectSystem = strict
ReadWritePaths = /opt/fastblog/logs /opt/fastblog/media

[Install]
WantedBy = multi-user.target
```

**启用服务：**

```bash
sudo systemctl daemon-reload
sudo systemctl enable fastblog
sudo systemctl start fastblog
```

### 步骤 9: 配置 Nginx

创建配置文件 `/etc/nginx/sites-available/fastblog`：

```nginx
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
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # 日志
    access_log /var/log/nginx/fastblog_access.log;
    error_log /var/log/nginx/fastblog_error.log;
    
    # 静态文件
    location /static/ {
        alias /opt/fastblog/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /opt/fastblog/media/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # 前端静态文件
    location / {
        root /opt/fastblog/frontend-next/out;
        try_files $uri $uri/ /index.html;
        expires 1h;
    }
    
    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:9421;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # WebSocket 支持（如果需要）
    location /ws/ {
        proxy_pass http://127.0.0.1:9421;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

**启用配置：**

```bash
# 创建符号链接
sudo ln -s /etc/nginx/sites-available/fastblog /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

### 步骤 10: 配置 SSL 证书

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 自动续期
sudo crontab -e
# 添加: 0 3 * * * certbot renew --quiet
```

### 步骤 11: 启动应用

```bash
# 启动 FastBlog
sudo systemctl start fastblog

# 查看状态
sudo systemctl status fastblog

# 查看日志
sudo journalctl -u fastblog -f
```

---

## Docker 部署

### 1. 创建 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 暴露端口
EXPOSE 9421

# 启动命令
CMD ["python", "main.py"]
```

### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "9421:9421"
    environment:
      - DB_HOST=db
      - REDIS_HOST=redis
    volumes:
      - ./media:/app/media
      - ./logs:/app/logs
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: fast_blog
      POSTGRES_USER: fastblog
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 3. 启动服务

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 配置优化

### 1. PostgreSQL 优化

编辑 `/etc/postgresql/15/main/postgresql.conf`：

```conf
# 内存配置
shared_buffers = 2GB              # 系统内存的 25%
effective_cache_size = 6GB        # 系统内存的 75%
work_mem = 10MB                   # 根据并发调整
maintenance_work_mem = 512MB

# 连接配置
max_connections = 200
superuser_reserved_connections = 3

# WAL 配置
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# 查询优化
random_page_cost = 1.1            # SSD 使用 1.1，HDD 使用 4.0
effective_io_concurrency = 200    # SSD 使用 200，HDD 使用 2
```

**重启 PostgreSQL：**

```bash
sudo systemctl restart postgresql
```

### 2. Redis 优化

编辑 `/etc/redis/redis.conf`：

```conf
# 内存限制
maxmemory 2gb
maxmemory-policy allkeys-lru

# 持久化
save 900 1
save 300 10
save 60 10000

# 网络
tcp-keepalive 300
timeout 300
```

**重启 Redis：**

```bash
sudo systemctl restart redis
```

### 3. Nginx 优化

编辑 `/etc/nginx/nginx.conf`：

```nginx
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    multi_accept on;
    use epoll;
}

http {
    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    
    # 缓存
    open_file_cache max=10000 inactive=30s;
    open_file_cache_valid 60s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;
    
    # 限流
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}
```

---

## 监控与维护

### 1. 日志管理

**查看应用日志：**

```bash
# Systemd 日志
sudo journalctl -u fastblog -f

# Nginx 访问日志
sudo tail -f /var/log/nginx/fastblog_access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/fastblog_error.log
```

**日志轮转配置** `/etc/logrotate.d/fastblog`：

```
/var/log/fastblog/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 www-data www-data
}
```

### 2. 性能监控

**安装监控工具：**

```bash
# 安装 htop
sudo apt install -y htop

# 安装 iotop
sudo apt install -y iotop

# 安装 nethogs
sudo apt install -y nethogs
```

**监控系统资源：**

```bash
# CPU 和内存
htop

# 磁盘 I/O
iotop

# 网络流量
nethogs
```

### 3. 数据库监控

```sql
-- 查看活跃连接
SELECT count(*)
FROM pg_stat_activity;

-- 查看慢查询
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC LIMIT 10;

-- 查看表大小
SELECT schemaname,
       tablename,
       pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 4. 备份策略

**自动备份脚本** `/opt/scripts/backup.sh`：

```bash
#!/bin/bash

BACKUP_DIR="/opt/backups/fastblog"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 备份数据库
pg_dump -U fastblog fast_blog | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

# 备份媒体文件
tar czf "$BACKUP_DIR/media_$TIMESTAMP.tar.gz" /opt/fastblog/media/

# 清理旧备份（保留 7 天）
find "$BACKUP_DIR" -type f -mtime +7 -delete

echo "Backup completed: $TIMESTAMP"
```

**设置定时任务：**

```bash
# 每天凌晨 2 点备份
0 2 * * * /opt/scripts/backup.sh >> /var/log/fastblog/backup.log 2>&1
```

---

## 故障排查

### 问题 1: 应用无法启动

**症状：**

```
● fastblog.service - FastBlog Application
   Active: failed
```

**解决：**

```bash
# 查看详细日志
sudo journalctl -u fastblog -n 50

# 检查配置文件
cat /opt/fastblog/.env

# 测试手动启动
cd /opt/fastblog
source venv/bin/activate
python main.py
```

### 问题 2: 数据库连接失败

**症状：**

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**解决：**

```bash
# 检查 PostgreSQL 状态
sudo systemctl status postgresql

# 测试连接
psql -U fastblog -d fast_blog -h localhost

# 检查监听地址
sudo grep listen_addresses /etc/postgresql/*/main/postgresql.conf

# 检查防火墙
sudo ufw status
```

### 问题 3: Nginx 502 Bad Gateway

**症状：**
浏览器显示 502 错误

**解决：**

```bash
# 检查后端服务
sudo systemctl status fastblog

# 检查 Nginx 配置
sudo nginx -t

# 检查端口占用
sudo ss -tlnp | grep 9421

# 查看 Nginx 错误日志
sudo tail -f /var/log/nginx/fastblog_error.log
```

### 问题 4: 性能缓慢

**症状：**
页面加载时间超过 3 秒

**解决：**

```bash
# 检查系统负载
uptime

# 检查内存使用
free -h

# 检查磁盘空间
df -h

# 检查慢查询
sudo -u postgres psql -d fast_blog -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# 检查 Redis
redis-cli info stats
```

---

## 安全加固

### 1. 防火墙配置

```bash
# 启用 UFW
sudo ufw enable

# 允许必要端口
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# 查看状态
sudo ufw status
```

### 2. Fail2Ban

```bash
# 安装 Fail2Ban
sudo apt install -y fail2ban

# 配置 SSH 保护
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo systemctl restart fail2ban
```

### 3. 定期更新

```bash
# 创建更新脚本
cat > /opt/scripts/update.sh << 'EOF'
#!/bin/bash
apt update && apt upgrade -y
systemctl restart fastblog
systemctl restart nginx
echo "Update completed: $(date)"
EOF

chmod +x /opt/scripts/update.sh

# 每周日自动更新
0 4 * * 0 /opt/scripts/update.sh >> /var/log/update.log 2>&1
```

---

## 相关资源

- [配置指南](./CONFIGURATION_GUIDE.md)
- [数据库管理](./DATABASE_MANAGEMENT.md)
- [API 使用示例](./API_EXAMPLES.md)
- [日志系统](./LOGGING_SYSTEM.md)

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01
