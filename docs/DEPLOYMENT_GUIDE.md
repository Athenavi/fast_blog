# FastBlog 部署指南

本文档说明如何将 FastBlog 部署到生产环境。

## 系统要求

### 推荐配置

- **CPU**: 4 核心
- **内存**: 8 GB RAM
- **存储**: 50 GB SSD
- **带宽**: 10 Mbps+

### 软件依赖

- Python 3.9+
- PostgreSQL 17+
- Redis 7+
- Nginx 1.18+
- Node.js 18+ (前端构建)

## Docker 部署

### 1. 配置环境

```bash
# 复制环境配置文件
cp .env_example .env
# 编辑 .env 文件配置数据库等信息
```

### 2. 启动服务

```bash
docker-compose up -d
```

### 3. 配置 Nginx

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

### 4. 配置 SSL 证书

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 自动续期
sudo crontab -e
# 添加: 0 3 * * * certbot renew --quiet
```

## 监控与维护

### 日志管理

```bash
# 查看应用日志
sudo journalctl -u fastblog -f

# Nginx 访问日志
sudo tail -f /var/log/nginx/fastblog_access.log
```

### 备份策略

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

## 相关资源

- [配置指南](./CONFIGURATION_GUIDE.md)
- [API 使用示例](./API_EXAMPLES.md)
