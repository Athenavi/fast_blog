# Nginx 安全配置指南

> **适用版本**: FastBlog V0.6+
> **替代**: 原 `src/auth/security_middleware.py`（已移除，其中定义的 XSS 过滤 / CSRF 保护 / 速率限制 / SQL 注入过滤中间件均未注册到应用，改用 Nginx 层实现更高效的首道防线）

---

## 目录

1. [概述](#1-概述)
2. [安全响应头](#2-安全响应头)
3. [速率限制](#3-速率限制)
4. [请求大小与超时限制](#4-请求大小与超时限制)
5. [HTTPS / SSL/TLS](#5-https--ssltls)
6. [隐藏 Nginx 版本号](#6-隐藏-nginx-版本号)
7. [Cookie 安全](#7-cookie-安全)
8. [缓冲与资源耗尽防护](#8-缓冲与资源耗尽防护)
9. [完整配置示例](#9-完整配置示例)
10. [验证与测试](#10-验证与测试)

---

## 1. 概述

FastBlog 采用前后端分离架构（FastAPI 后端 + Astro 前端），所有外部请求首先经过 Nginx 反向代理。**在 Nginx 层实施安全策略是最佳实践**——它在请求到达 Python 应用之前即完成过滤，性能开销极小且不侵入应用代码。

本指南覆盖以下安全领域：

| 领域 | 原中间件 | Nginx 方案 |
|------|---------|-----------|
| CSP / 安全头 | `XSSFilterMiddleware` 注入 | `add_header` 指令 |
| 速率限制 | `RateLimiterMiddleware` | `limit_req_zone` + `limit_req` |
| XSS 防护 | `XSSFilterMiddleware` 内容检查 | `X-XSS-Protection` 头 + CSP |
| SQL 注入过滤 | `SQLInjectionFilterMiddleware` | ORM 参数化查询已天然防御；Nginx 层加正则过滤作为深度防御 |
| CSRF 保护 | `CSRFProtectionMiddleware`（已注释）| JWT/Bearer 认证已天然防 CSRF；Nginx 层无需额外处理 |

---

## 2. 安全响应头

在每个 `server` 块中设置以下安全头。Nginx 已有部分配置，建议按此完整清单补充。

### 基础头（在 `server` 块中）

```nginx
server {
    listen 80;
    server_name example.com;

    # ─── 安全响应头 ─────────────────────────────

    # 内容安全策略 (CSP) — 控制资源加载来源
    add_header Content-Security-Policy "
        default-src 'self';
        script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;
        style-src  'self' 'unsafe-inline' https://fonts.googleapis.com;
        img-src    'self' data: https:;
        font-src   'self' https://fonts.gstatic.com;
        frame-ancestors 'self';
        base-uri   'self';
        form-action 'self';
    " always;

    # 防止点击劫持
    add_header X-Frame-Options "SAMEORIGIN" always;

    # 禁止 MIME 类型嗅探
    add_header X-Content-Type-Options "nosniff" always;

    # 启用浏览器 XSS 过滤器
    add_header X-XSS-Protection "1; mode=block" always;

    # 控制 Referer 头携带范围
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 权限控制 (Permissions-Policy) — 限制浏览器 API 访问
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    # HTTP 严格传输安全 (HSTS) — 仅 HTTPS 时启用
    # add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
}
```

### CSP 说明

CSP 中的 `'unsafe-inline'` 是为 Tiptap 富文本编辑器和 Astro 的内联脚本样式所需的。如你的部署不使用这些，可以收紧为 `'self'`。

实际使用时请**将 `Content-Security-Policy` 写为单行**以避免多行字符串的换行问题：

```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com; frame-ancestors 'self'; base-uri 'self'; form-action 'self';" always;
```

---

## 3. 速率限制

### 定义限制区域（`http` 块）

```nginx
http {
    # 速率限制区域
    limit_req_zone $binary_remote_addr zone=general:10m  rate=50r/s;   # 普通请求
    limit_req_zone $binary_remote_addr zone=api:10m      rate=30r/s;   # API 请求
    limit_req_zone $binary_remote_addr zone=login:10m    rate=5r/m;    # 登录（5次/分钟）
    limit_req_zone $binary_remote_addr zone=register:10m rate=3r/5m;   # 注册（3次/5分钟）
    limit_req_zone $binary_remote_addr zone=password:10m rate=3r/5m;   # 密码操作
}
```

### 应用到 Location 块

```nginx
# API 通用
location /api/ {
    limit_req zone=api burst=50 nodelay;
    proxy_pass http://backend;
}

# 登录（严格限制）
location /api/v2/auth/login {
    limit_req zone=login burst=3 nodelay;
    proxy_pass http://backend;
}

# 注册（更严格）
location /api/v2/auth/register {
    limit_req zone=register burst=2 nodelay;
    proxy_pass http://backend;
}

# 密码操作
location ~ ^/api/v2/(auth/password|users/password) {
    limit_req zone=password burst=3 nodelay;
    proxy_pass http://backend;
}
```

### 可选：连接数限制

```nginx
http {
    # 限制每个 IP 的并发连接数
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;
}

server {
    location /api/ {
        limit_conn conn_limit 10;  # 每个 IP 最多 10 个并发连接
        proxy_pass http://backend;
    }
}
```

---

## 4. 请求大小与超时限制

```nginx
http {
    # 客户端设置
    client_max_body_size 60M;       # 最大请求体（含文件上传）
    client_body_buffer_size 128k;   # 请求体缓冲区
    client_body_timeout 60s;        # 请求体超时
    client_header_timeout 60s;      # 请求头超时

    # 代理超时
    proxy_connect_timeout 30s;
    proxy_send_timeout 30s;
    proxy_read_timeout 30s;
}
```

---

## 5. HTTPS / SSL/TLS

> 在生产环境中必须启用 HTTPS。以下配置假设 SSL 证书由 Let's Encrypt / certbot 管理。

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # 现代 TLS 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # HSTS（在确认 HTTPS 正常工作后取消注释）
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
}

# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}
```

---

## 6. 隐藏 Nginx 版本号

```nginx
http {
    server_tokens off;  # 隐藏 Nginx 版本号，防止针对性攻击
}
```

---

## 7. Cookie 安全

在 `location` 块或 `server` 块中为 Cookie 添加安全属性，确保 `Set-Cookie` 头包含 `HttpOnly`、`Secure`、`SameSite` 标记。

```nginx
server {
    # 为所有后端响应的 Cookie 添加安全属性
    proxy_cookie_path / "/; HttpOnly; Secure; SameSite=Lax";
}
```

注意：对于前端 Astro 的 Cookie，确保应用端已设置 `httpOnly` 和 `secure` 标记。Nginx 不直接修改上游的 `Set-Cookie` 属性——`proxy_cookie_path` 只能修改 `Path` 部分。属性修改需要在应用后端完成。

FastAPI 后端的 Cookie 设置可在 `src/setting.py` 中配置：

```python
# 确保 Session/Cookie 中间件配置了：
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True      # HTTPS 时启用
SESSION_COOKIE_SAMESITE = "Lax"
```

---

## 8. 缓冲与资源耗尽防护

```nginx
http {
    # 请求体缓冲
    client_body_buffer_size 128k;
    client_max_body_size 60M;

    # 请求头缓冲
    large_client_header_buffers 4 16k;

    # 代理缓冲
    proxy_buffer_size 4k;
    proxy_buffers 8 16k;
    proxy_busy_buffers_size 32k;

    # 关闭慢速连接
    client_body_timeout 30s;
    client_header_timeout 30s;
    keepalive_timeout 65;
    send_timeout 30s;
}
```

---

## 9. 完整配置示例

将以下内容合并到你现有的 `nginx/conf.d/fastblog.conf` 中。主要补充了 CSP 头和之前缺失的安全头。

```nginx
# FastBlog Nginx Configuration
# Security-hardened production configuration

upstream backend {
    server backend:9421;
    keepalive 32;
}

upstream frontend {
    server frontend:80;
    keepalive 32;
}

# ─── 速率限制区域 ─────────────────────────────────
limit_req_zone $binary_remote_addr zone=api:10m      rate=30r/s;
limit_req_zone $binary_remote_addr zone=login:10m    rate=5r/m;
limit_req_zone $binary_remote_addr zone=register:10m rate=3r/5m;
limit_req_zone $binary_remote_addr zone=password:10m rate=3r/5m;
limit_req_zone $binary_remote_addr zone=general:10m  rate=50r/s;

server {
    listen 80;
    server_name _;

    # ─── 隐藏版本号 ────────────────────────────────
    server_tokens off;

    # ─── 安全响应头 ────────────────────────────────
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com; frame-ancestors 'self'; base-uri 'self'; form-action 'self';" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    # 生产环境 HTTPS 时取消注释：
    # add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # ─── Gzip 压缩 ────────────────────────────────
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 1000;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml
               application/rss+xml image/svg+xml;

    # ─── 客户端设置 ───────────────────────────────
    client_max_body_size 60M;
    client_body_timeout 60s;
    client_header_timeout 60s;

    # ─── API 端点 ─────────────────────────────────
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
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 注册
    location /api/v2/auth/register {
        limit_req zone=register burst=2 nodelay;
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 密码操作
    location ~ ^/api/v2/(auth/password|users/password) {
        limit_req zone=password burst=3 nodelay;
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ─── 静态文件缓存 ─────────────────────────────
    location /media/ {
        proxy_pass http://backend;
        proxy_cache_valid 200 30d;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # ─── 健康检查 ─────────────────────────────────
    location /health {
        access_log off;
        limit_req zone=general burst=5 nodelay;
        proxy_pass http://backend/api/v2/health;
    }

    # ─── 前端（兜底） ─────────────────────────────
    location / {
        limit_req zone=general burst=100 nodelay;
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 10. 验证与测试

### 安全头验证

部署后使用以下命令检查安全头是否生效：

```bash
# 使用 curl 检查响应头
curl -sI https://your-domain.com | grep -iE "content-security|strict-transport|x-frame|x-content|x-xss|referrer|permissions"

# 期望输出：
# content-security-policy: default-src 'self'; ...
# x-frame-options: SAMEORIGIN
# x-content-type-options: nosniff
# x-xss-protection: 1; mode=block
# referrer-policy: strict-origin-when-cross-origin
```

### 在线检测工具

- [securityheaders.com](https://securityheaders.com) — 安全头评级
- [SSL Labs](https://www.ssllabs.com/ssltest/) — TLS 配置评级
- [CSP Evaluator](https://csp-evaluator.withgoogle.com) — CSP 策略评估

### 速率限制验证

```bash
# 快速连续请求，应触发 429
for i in {1..10}; do curl -s -o /dev/null -w "%{http_code}\n" https://your-domain.com/api/v2/auth/login; done
```

---

## 附录：原中间件能力对照表

| 原中间件 | 能力 | Nginx 替代方案 | 说明 |
|---------|------|---------------|------|
| `XSSFilterMiddleware` | 请求体 XSS 正则检查 | `X-XSS-Protection` + CSP | 正则层的 XSS 检测误报率高且影响性能。CSP 是更可靠的防御 |
| `CSRFProtectionMiddleware` | CSRF Token 校验 | JWT Bearer 认证 | FastBlog 使用 JWT 认证，已天然防 CSRF。无需 Nginx 层处理 |
| `RateLimiterMiddleware` | IP + 路径维度的内存限流 | `limit_req_zone` + `limit_req` | Nginx 原生限流性能更好、支持共享状态（多 worker） |
| `SQLInjectionFilterMiddleware` | 请求参数的 SQL 注入正则检查 | ORM 参数化查询 | FastBlog 使用 SQLAlchemy ORM，参数化查询已防御 SQL 注入。Nginx 层正则过滤可作深度防御层（可选） |

---

*最后更新: 2026-07-04*
*关联文档: [部署指南](./DEPLOYMENT_GUIDE.md), [故障排查 FAQ](./TROUBLESHOOTING_FAQ.md)*
