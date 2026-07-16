# Nginx 安全配置指南

> **适用版本**: FastBlog V0.6+
> **替代**: 原 `src/auth/security_middleware.py`（XSS 过滤 / CSRF 保护 / 速率限制 / SQL 注入过滤中间件均未注册到应用，改用
> Nginx 层实现更高效的首道防线）

---

## 概述

FastBlog 采用前后端分离架构，所有外部请求首先经过 Nginx 反向代理。**在 Nginx 层实施安全策略是最佳实践**——它在请求到达
Python 应用之前即完成过滤，性能开销极小。

| 领域        | 原中间件                    | Nginx 方案                       |
|-----------|-------------------------|--------------------------------|
| CSP / 安全头 | `XSSFilterMiddleware`   | `add_header` 指令                |
| 速率限制      | `RateLimiterMiddleware` | `limit_req_zone` + `limit_req` |
| XSS 防护    | 内容检查                    | `X-XSS-Protection` 头 + CSP     |
| SQL 注入    | 正则过滤                    | ORM 参数化查询已天然防御                 |

---

## 安全响应头

在 `server` 块中设置：

```nginx
server {
    listen 80;
    server_name example.com;

    # CSP — 控制资源加载来源
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com; frame-ancestors 'self'; base-uri 'self'; form-action 'self';" always;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
    # add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;  # HTTPS 启用
}
```

> CSP 中的 `'unsafe-inline'` 是为 Tiptap 编辑器所需，如不使用可收紧为 `'self'`。

---

## 速率限制

```nginx
http {
    limit_req_zone $binary_remote_addr zone=general:10m  rate=50r/s;
    limit_req_zone $binary_remote_addr zone=api:10m      rate=30r/s;
    limit_req_zone $binary_remote_addr zone=login:10m    rate=5r/m;
    limit_req_zone $binary_remote_addr zone=register:10m rate=3r/5m;
}
```

```nginx
location /api/ {
    limit_req zone=api burst=50 nodelay;
    proxy_pass http://backend;
}
location /api/v2/auth/login {
    limit_req zone=login burst=3 nodelay;
    proxy_pass http://backend;
}
location /api/v2/auth/register {
    limit_req zone=register burst=2 nodelay;
    proxy_pass http://backend;
}
```

---

## HTTPS / SSL/TLS

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
}

server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}
```

---

## 其他安全设置

```nginx
http {
    server_tokens off;                    # 隐藏 Nginx 版本号
    client_max_body_size 60M;            # 上传限制
    client_body_buffer_size 128k;
    client_body_timeout 30s;
    client_header_timeout 30s;
    large_client_header_buffers 4 16k;
}
```

---

## 完整配置示例

合并到 `nginx/conf.d/fastblog.conf`：

```nginx
upstream backend  { server backend:9421;  keepalive 32; }
upstream frontend { server frontend:80;   keepalive 32; }

limit_req_zone $binary_remote_addr zone=api:10m      rate=30r/s;
limit_req_zone $binary_remote_addr zone=login:10m    rate=5r/m;
limit_req_zone $binary_remote_addr zone=register:10m rate=3r/5m;
limit_req_zone $binary_remote_addr zone=general:10m  rate=50r/s;

server {
    listen 80;
    server_name _;

    server_tokens off;

    # 安全头
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com; frame-ancestors 'self'; base-uri 'self'; form-action 'self';" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 1000;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/rss+xml image/svg+xml;

    client_max_body_size 60M;
    client_body_timeout 60s;
    client_header_timeout 60s;

    # API
    location /api/ {
        limit_req zone=api burst=50 nodelay;
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        proxy_buffering on;
        proxy_buffer_size 8k;
        proxy_buffers 8 16k;
    }

    # 登录（严格限流）
    location /api/v2/auth/login {
        limit_req zone=login burst=3 nodelay;
        proxy_pass http://backend;
    }

    # 注册
    location /api/v2/auth/register {
        limit_req zone=register burst=2 nodelay;
        proxy_pass http://backend;
    }

    # 静态文件缓存
    location /media/ {
        proxy_pass http://backend;
        proxy_cache_valid 200 30d;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 健康检查
    location /health {
        access_log off;
        limit_req zone=general burst=5 nodelay;
        proxy_pass http://backend/api/v2/health;
    }

    # 前端
    location / {
        limit_req zone=general burst=100 nodelay;
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 验证

```bash
# 检查安全头
curl -sI https://your-domain.com | grep -iE "content-security|strict-transport|x-frame|x-content|x-xss|referrer|permissions"

# 速率限制测试
for i in {1..10}; do curl -s -o /dev/null -w "%{http_code}\n" https://your-domain.com/api/v2/auth/login; done
```

### 在线检测

- [securityheaders.com](https://securityheaders.com) — 安全头评级
- [SSL Labs](https://www.ssllabs.com/ssltest/) — TLS 配置评级
- [CSP Evaluator](https://csp-evaluator.withgoogle.com) — CSP 策略评估

---

*关联文档: [部署指南](./DEPLOYMENT_GUIDE.md), [故障排查 FAQ](./TROUBLESHOOTING_FAQ.md)*
