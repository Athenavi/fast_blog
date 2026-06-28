# 部署指南

## 架构概览

```
用户 → marklume.cn:80
      ↓
    Nginx (BT Panel)
      ├── /api/*   → 127.0.0.1:9421 (Python 后端)
      ├── /media/* → 127.0.0.1:9421
      └── /*       → [::1]:4321      (Astro SSR Node)
                          ↓
                    静态页面 → 直接返回 HTML
                    SSR 页面 → 调用后端 API → 渲染 HTML
```

---

## 一、环境要求

| 组件 | 版本/要求 |
|------|----------|
| Node.js | ≥ 22.x |
| npm | ≥ 10.x |
| Python | 3.14 (fb2607 虚拟环境) |
| PostgreSQL | 16.x |
| Nginx | ≥ 1.24 (BT Panel 管理) |

---

## 二、前端部署

### 2.1 构建

```bash
cd /www/wwwroot/fast_blog/frontend-astro

# 安装依赖
npm install

# 生产构建
npm run build
```

构建产物：
```
dist/
├── client/          # 静态文件（HTML/JS/CSS）
│   ├── index.html
│   ├── admin/index.html
│   ├── _astro/      # 编译后的 JS/CSS（带内容 hash）
│   ├── config.js    # 运行时配置
│   └── ...
└── server/
    └── entry.mjs    # SSR Node 服务入口
```

### 2.2 运行时配置

`dist/client/config.js`（从 `public/config.js` 复制）：

```js
const runtimeConfig = {
    API_BASE_URL: '',      // 空 = 相对路径，由 Nginx 代理
    API_PREFIX: '/api/v2'
};
```

> **为什么是空字符串？** 生产环境 Nginx 代理 `/api/*` → 后端 9421，
> 浏览器用相对路径 `/api/v2/...` 即可，不需要硬编码地址。

### 2.3 部署文件

```bash
# 复制静态文件到网站根目录
cp -r dist/client/* /www/wwwroot/marklume.cn/
```

### 2.4 启动 SSR 服务

```bash
# 用 PM2 守护 Node 进程
cd /www/wwwroot/marklume.cn
pm2 start dist/server/entry.mjs --name fastblog-ssr
pm2 save
```

验证：

```bash
curl http://localhost:4321
# 应返回 HTML 页面内容
```

---

## 三、后端部署

### 3.1 启动

```bash
cd /www/wwwroot/fast_blog
nohup python3 main.py --port 9421 > logs/app.log 2>&1 &
```

### 3.2 验证

```bash
curl http://127.0.0.1:9421/api/v2/health
```

---

## 四、Nginx 配置

BT Panel → 网站 → `marklume.cn` → 配置文件：

```nginx
server {
    listen 80;
    server_name marklume.cn;

    # ========== API 转发到后端 ==========
    location ^~ /api/ {
        proxy_pass http://127.0.0.1:9421;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ========== Media 文件 ==========
    location ^~ /media/ {
        proxy_pass http://127.0.0.1:9421;
    }

    # ========== 前端所有流量转发到 SSR ==========
    location / {
        proxy_pass http://[::1]:4321;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    access_log  /www/wwwlogs/marklume.cn.log;
    error_log  /www/wwwlogs/marklume.cn.error.log;
}
```

> ⚠️ SSR 服务监听 `[::1]:4321`（IPv6 loopback），Nginx 需用 `[::1]` 而非 `127.0.0.1`。

---

## 五、数据库迁移

### 5.1 首次迁移

```bash
cd /www/wwwroot/fast_blog

# alembic.ini 被 .gitignore 忽略，需手动创建或从仓库拉取
git pull origin alpha  # 确保 alembic.ini 存在

# 执行迁移
/www/server/pyporject_evn/fb2607/bin/python3 -m alembic -c alembic.ini upgrade head
```

### 5.2 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `permission denied for schema public` | 数据库用户权限不足 | 用 postgres 超级用户授权 |
| `relation "xxx" does not exist` | 迁移未执行 | 运行 `alembic upgrade head` |
| `No 'script_location' key` | `alembic.ini` 不存在 | `git pull` 或手动创建 |

### 5.3 授权命令

```bash
# 用 postgres 超级用户授权 fastblog 用户
psql -h localhost -U postgres -d fb260628 -c "
GRANT ALL PRIVILEGES ON DATABASE fb260628 TO fastblog;
GRANT ALL PRIVILEGES ON SCHEMA public TO fastblog;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fastblog;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fastblog;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO fastblog;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO fastblog;
"
```

---

## 六、本地开发

### 6.1 启动

```bash
cd fast_blog/frontend-astro

# 安装依赖
npm install

# 启动开发服务器（自动代理 /api/ 到 localhost:9421）
npm run dev
```

`astro.config.mjs` 中已配置：

```js
server: {
    proxy: {
        '/api': 'http://localhost:9421',
    },
},
```

开发时浏览器访问 `http://localhost:4321`，`/api/*` 请求自动转发到后端 9421。

### 6.2 后端

```bash
cd fast_blog
python3 main.py --port 9421
```

---

## 七、常见问题

### 7.1 502 Bad Gateway

**可能原因**：
- 后端未启动 → `ss -tlnp | grep 9421`
- SSR 未启动 → `pm2 list` 或 `ss -tlnp | grep 4321`
- Nginx 配置错误 → `nginx -t`

### 7.2 ERR_INCOMPLETE_CHUNKED_ENCODING

SSR 服务传输中断，重启：

```bash
pm2 restart fastblog-ssr
```

### 7.3 页面请求 localhost:9421

浏览器端 `API_BASE_URL` 未正确配置：

```bash
# 确认 config.js 内容
cat /www/wwwroot/marklume.cn/config.js
# API_BASE_URL 应为 ''（空字符串）
```

### 7.4 构建失败（Unterminated string literal）

Vite 解析 `.astro` 文件时遇到 `import` 语句放在动态代码后面。
修复：确保 `import` 在 frontmatter 顶部。

---

## 八、技术决策记录

### 为什么用 runtime config.js 而非构建时注入？

| 方式 | 优点 | 缺点 |
|------|------|------|
| `public/config.js`（运行时） | 部署后可直接修改，无需重新构建 | 需确保文件路径正确 |
| `.env` + `import.meta.env` | 类型安全，构建时确定 | 不同环境需重新构建 |
| Nginx 代理（当前方案） | 无需改代码 | 前后端必须同域名 |

**选择**：运行时 `config.js` + Nginx 代理组合，兼顾灵活与简洁。

### 为什么不用 uwsgi？

uWSGI 使用二进制协议，Nginx 用 `uwsgi_pass` 而非 `proxy_pass`。
后端改用 `python main.py`（基于 uvicorn）后，使用标准 HTTP 协议，
Nginx 只需 `proxy_pass`，配置更简单。

### 为什么 SSR 而非纯静态？

首页 (`index.astro`) 和文章详情 (`p/[slug].astro`) 使用 SSR
（`prerender = false`），需要从后端 API 实时获取数据。
纯静态部署无法满足这些动态页面。
