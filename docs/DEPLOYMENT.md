# FastBlog 部署与运维

本文档描述**当前代码**实际支持的部署方式。每个结论都对应仓库中的文件，出处标注在括号里。

> 约定：文中出现的端口分两类 —— **容器内端口**（服务之间通信）与**对外端口**（宿主机映射）。

---

## 1. 组件与端口

| 服务         | 镜像 / 构建来源                                   | 容器内端口    | 对外端口（默认）                             | 对外端口（生产）              |
|------------|---------------------------------------------|----------|--------------------------------------|-----------------------|
| `backend`  | 根目录 `Dockerfile`（`python:3.14-slim`）        | 9421     | `BACKEND_PORT`（默认 9421）              | `127.0.0.1:9421`（仅本机） |
| `frontend` | `frontend/web/Dockerfile`（`node:22-alpine`） | 3000     | 不对外                                  | 不对外                   |
| `nginx`    | `nginx:1-alpine`                            | 80 / 443 | `FRONTEND_PORT`（默认 **4321** → 容器 80） | 80 + 443              |
| `postgres` | `postgres:16-alpine`                        | 5432     | `POSTGRES_PORT`（默认 5432）             | `127.0.0.1:5432`      |
| `redis`    | `redis:7-alpine`                            | 6379     | `REDIS_PORT`（默认 6379）                | `127.0.0.1:6379`      |

请求路径：**nginx 是唯一入口**，`/api/**` 反代到 `backend:9421`，其余路径反代到 `frontend:3000`（SSR node 服务）；前端在 SSR
阶段通过 `NUXT_PUBLIC_API_BASE_URL=http://backend:9421` 直连后端，浏览器侧走同源 `/api`（`docker-compose.yml`、
`nginx/conf.d/fastblog.conf`）。

后端共 **11 个域 / 73 个模块 / 650 条路由**，全部挂在 `/api/v3` 下（实测：`src/api/v3/__init__.py::DOMAIN_MODULES` +
启动期注册统计）。

---

## 2. 前置条件

- Docker 24+（Compose v2，命令为 `docker compose`；旧版 `docker-compose` 亦可）
- **静态 ffmpeg 包**：`tools/ffmpeg/ffmpeg-release-amd64-static.tar.xz`
  后端镜像通过 BuildKit 的 `additional_contexts: ffmpeg_src=./tools/ffmpeg` 加载它，不在主构建上下文里（`Dockerfile` 头部注释、
  `docker-compose.yml`）。
  该文件已加入 `.dockerignore`，本地首次构建前需自备：

  ```bash
  mkdir -p tools/ffmpeg
  curl -fL -o tools/ffmpeg/ffmpeg-release-amd64-static.tar.xz \
    https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
  ```

- 前端镜像构建需要 Node 22（`frontend/web/Dockerfile` 用 `node:22-alpine`），**必须**用 `npm ci` 安装并带锁文件（
  `frontend/web/package-lock.json` 是唯一权威依赖快照）。

---

## 3. 快速部署（默认形态）

推荐使用**交互式安装脚本**（跨平台、仅依赖标准库，会自动生成强密钥、启动容器、执行迁移、导入种子并按角色创建用户）：

```bash
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog
python install.py
```

脚本引导的步骤：环境自检 → 生成 `.env`（写入 4 个强随机密钥）→ 检查（必要时下载）静态 ffmpeg → `docker compose up -d --build`
并等待 `/api/v3/health` → `alembic upgrade head` → 勾选种子数据 → 按内置角色创建用户。

不想交互时可以用参数化调用：

```bash
# 只做数据库初始化（服务已在运行）
FASTBLOG_ADMIN_PASSWORD='<强密码>' python install.py --yes --mode init \
  --seeds rbac,menus,gamification --admin-user admin

python install.py --check        # 只做环境自检，不改动任何东西
```

等价的手工步骤：

```bash
cp .env.example .env
# 编辑 .env：至少填写 SECRET_KEY 与 DB_PASSWORD（见第 6 节）
docker compose up -d --build
docker compose exec backend python -m alembic upgrade head   # 镜像内含 alembic 与迁移目录
```

> 注意：镜像里**没有** `scripts/` 目录（`.dockerignore` 排除），因此**种子脚本与建用户必须在宿主机执行**（需要
`pip install -r requirements.txt`）。`install.py` 会自动处理这一点；手工路径请参考第 7 节。

访问 `http://localhost:4321`（nginx 对外端口由 `FRONTEND_PORT` 控制）。

该形态下 nginx 只监听 HTTP 80，无 TLS、无 Redis 密码、`WORKERS=1`，适合内网或反代后端场景（`docker-compose.yml`）。

---

## 4. 生产部署

```bash
cp .env.example .env
# 必须显式提供：SECRET_KEY、JWT_SECRET_KEY、DB_PASSWORD、REDIS_PASSWORD
# 生成示例：python -c "import secrets; print(secrets.token_urlsafe(32))"
docker compose -f docker-compose.prod.yml up -d --build
```

相比默认形态的差异（`docker-compose.prod.yml`）：

| 项      | 默认                             | 生产                                                                            |
|--------|--------------------------------|-------------------------------------------------------------------------------|
| 密钥     | 只强制 `SECRET_KEY`、`DB_PASSWORD` | 额外**强制** `JWT_SECRET_KEY`、`REDIS_PASSWORD`（缺失时 compose 直接报错退出）                |
| 后端监听   | `0.0.0.0:9421`                 | `127.0.0.1:9421`                                                              |
| nginx  | 只监听 80                         | 监听 80 + 443（`nginx/ssl/` 只读挂载）                                                |
| Worker | `WORKERS=1`                    | `WORKERS=2`（多进程，依赖 Redis 共享限流/缓存与分布式锁）                                        |
| 资源限制   | 无                              | backend 2C/2G，frontend 1C/512M，nginx 0.5C/128M，postgres 2C/2G，redis 0.5C/512M |
| 重启策略   | `unless-stopped`               | `always`                                                                      |
| 日志     | 默认                             | json-file 轮转 10MB × 3                                                         |
| Redis  | 无密码、256MB                      | `requirepass` + 512MB                                                         |

**多 worker 前置条件**：`WORKERS > 1` 时必须以 Redis 为共享后端，否则限流/缓存各进程独立、定时任务重复执行。启动日志会打印
worker 信息（`src/app.py::_enable_redis_caches`、`main.py`）。

---

## 5. 本地开发用的依赖服务

只起数据库/缓存（不含应用），应用在宿主机跑：

```bash
docker compose -f docker-compose.dev.yml up -d
python main.py --env dev            # 后端 :9421
cd frontend/web && npm run dev      # 前端 :5173
```

可选 profile（`docker-compose.dev.yml`）：

| profile  | 服务                                         | 端口        |
|----------|--------------------------------------------|-----------|
| （默认）     | postgres + redis                           | 5432、6379 |
| `search` | + Meilisearch `getmeili/meilisearch:v1.12` | 7700      |
| `tools`  | + Adminer、Redis Commander                  | 8080、8081 |

```bash
docker compose -f docker-compose.dev.yml --profile search up -d
docker compose -f docker-compose.dev.yml --profile tools --profile search up -d
```

dev 形态的 postgres 使用 `POSTGRES_HOST_AUTH_METHOD=trust`，**不可用于生产**。

---

## 6. 环境变量

配置读取有两处，优先级不同：

| 位置            | 读取者                                                      | 行为                                        |
|---------------|----------------------------------------------------------|-------------------------------------------|
| 仓库根 `.env`    | 应用进程（`shared/config/settings.py` 第 13 行 `load_dotenv()`） | 先加载                                       |
| `config/.env` | 同上（第 14 行）+ `alembic_migrations/env.py`                  | 补充加载，**不覆盖**已有值；alembic 用 `override=True` |

Compose 也会读仓库根的 `.env`（变量插值）。这意味着**改数据库目标时要注意**：alembic 的 `env.py` 以 `config/.env`
为准且会覆盖环境变量，要临时指向别的库应设 `DATABASE_URL`（它优先级最高，且不在 `config/.env` 中）。

主要变量（完整清单见 `.env.example`）：

| 变量                                                                          | 必填   | 说明                                                                                                            |
|-----------------------------------------------------------------------------|------|---------------------------------------------------------------------------------------------------------------|
| `SECRET_KEY`                                                                | ✅    | ≥32 位随机串；占位值会导致启动失败（`shared/config/settings.py`）                                                              |
| `JWT_SECRET_KEY`                                                            | 生产 ✅ | 留空则跟随 `SECRET_KEY`                                                                                            |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME`               | ✅    | 数据库连接                                                                                                         |
| `DB_POOL_SIZE` / `DB_POOL_OVERFLOW` / `DB_POOL_TIMEOUT` / `DB_POOL_RECYCLE` | —    | 连接池                                                                                                           |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` / `REDIS_PASSWORD`                 | —    | 缓存、限流、多 worker 共享                                                                                             |
| `ENVIRONMENT`                                                               | —    | `production` 时关闭 API 文档界面（`/api/v3/docs`、`/api/v3/redoc`、`/api/v3/openapi.json` 全部为 `None`）、Cookie 置 `Secure` |
| `DEBUG`                                                                     | —    | 开启后打印调试中间件日志（含请求体，`src/app.py`）                                                                               |
| `WORKERS`                                                                   | —    | 进程数，>1 需 Redis                                                                                                |
| `DISABLED_MODULES`                                                          | —    | 逗号分隔关闭内置模块                                                                                                    |
| `PERMISSION_AUDIT_STRICT`                                                   | —    | `1/true/yes` 时启动期权限审计失败即拒绝启动                                                                                  |
| `UPLOAD_LIMIT` / `USER_FREE_STORAGE_LIMIT`                                  | —    | 上传大小上限（默认 60MB）与用户免费存储（默认 512MB）                                                                              |
| `CORS_ORIGINS`                                                              | —    | 逗号/分号分隔；不设则用内置 localhost 白名单（`src/app.py::register_middleware`）                                               |
| `BRUTE_FORCE_MAX_PER_IP` / `BRUTE_FORCE_MAX_PER_USER`                       | —    | 暴力破解阈值（默认 10 次/15 分钟、5 次）                                                                                     |
| `MAIL_*`                                                                    | —    | SMTP                                                                                                          |
| `S3_*`                                                                      | —    | S3 兼容对象存储                                                                                                     |
| `MEILISEARCH_HOST` / `MEILISEARCH_API_KEY`                                  | —    | 全文搜索（可选）                                                                                                      |
| `SENTRY_DSN`                                                                | —    | 错误上报（可选）                                                                                                      |
| `FFMPEG_PATH` / `FFPROBE_PATH`                                              | —    | 默认 `ffmpeg` / `ffprobe`（镜像内已在 PATH）                                                                           |
| `FRONTEND_PORT` / `BACKEND_PORT` / `POSTGRES_PORT` / `REDIS_PORT`           | —    | 宿主机端口映射（compose 层）                                                                                            |

前端运行时变量（`frontend/web/.env.*`、`nuxt.config.ts::runtimeConfig.public`）：

| 变量                                | 开发                                                    | 生产                                         |
|-----------------------------------|-------------------------------------------------------|--------------------------------------------|
| `NUXT_PUBLIC_API_BASE_URL`        | `http://localhost:9421`（SSR 绝对地址）                     | 由 compose 注入 `http://backend:9421`；浏览器侧走同源 |
| `NUXT_PUBLIC_WS_BASE_URL`         | `ws://127.0.0.1:9421`（dev 下 WS 不经 nitro/Vite 代理，必须显式） | 留空 = 同源，由 nginx 转发 `Upgrade`               |
| `NUXT_PUBLIC_RUM_ENDPOINT`        | 留空（仅本地采集）                                             | 留空                                         |
| `VITE_PORT` / `VITE_PROXY_TARGET` | `5173` / `http://localhost:9421`                      | —                                          |

---

## 7. 首次初始化

> 一站式做法：`python install.py --mode init`（或交互模式 `python install.py` 选「仅初始化」）会把本节三步串起来执行，并可按角色创建登录用户。以下为手工等价命令。

数据库结构由 Alembic 管理，当前只有**一个**迁移：`8b7ecb6d053c_initial_full_schema`（`alembic_migrations/versions/`），即
head 与 baseline 是同一个版本。

```bash
python -m alembic upgrade head           # 建表（会读取 config/.env 指向的库）
python -m scripts.seed_rbac              # 从 codes.py 派生 194 条 capability + 4 个内置角色
python -m scripts.seed_admin_menus --apply --grant-system-roles   # 后台菜单与授权
```

注意两条脚本的默认行为相反：

- `scripts/seed_rbac.py`：**没有 `--dry-run`，也没有 argparse**，直接执行并写库（幂等，会同步全部 capability
  并把内置角色的能力清单覆盖成定义值）。
- `scripts/seed_admin_menus.py`：默认 dry-run，写库需显式 `--apply`。

创建管理员（按角色创建，推荐）：

```bash
python -m scripts.create_user --list-roles                                  # 查看可选角色
python -m scripts.create_user -u admin -r superadmin -e admin@example.com   # 密码交互输入
python -m scripts.create_user -u ops -r admin --password-env MY_PW          # 自动化：密码走环境变量
```

`scripts/create_user.py` 会同时写入 `users` 与 `user_role_assignments`（`superadmin` 角色自动置 `is_superuser=True`）；
另一条路径是 Typer CLI 的 `python -m cli user create-user`（只区分超级用户/普通用户，不绑定角色）。

**已存在但"几乎每个后台页面都 403"的用户**：页面级权限由 `frontend/web/src/middleware/auth.ts` 用
`/system/auth/me` 下发的 `permissions` 做严格比对，而该集合的唯一来源是
`user_role_assignments → roles → role_capabilities → capabilities`；用户**没有任何角色绑定**时集合为空，
除未声明 `meta.permission` 的页面外全部跳 `/403`。用下面这条幂等脚本补齐：

```bash
python -m scripts.seed_user_permissions              # 默认 = id 最小的用户 + superadmin 角色（写库）
python -m scripts.seed_user_permissions --dry-run    # 只打印计划
python -m scripts.seed_user_permissions -u admin     # 指定用户（--role/--data-scope 可覆盖）
```

它会：补齐 `capabilities` 缺码 → 把全部权限码与全部激活菜单授权给目标角色 → 把该角色 `data_scope`
提升为 3（全部数据，NULL 时业务层按"仅本人"处理）→ 绑定用户 ↔ 角色 → 失效该用户权限缓存 →
复核"前端每个页面声明的权限码是否都已被授予"。生效前提：前端需**重新登录**（`localStorage` 里的
`userInfo` 缓存了旧权限集）；后端未接 Redis 时需重启服务或等 300s 内存缓存 TTL。

**安装向导**：后端在启动时检查安装状态（
`shared/services/install/install_manager.installation_wizard_service.is_installed()`，`src/app.py::check_installation`
），未安装时会提示访问 `http://localhost:4321/install`，并提供 `GET /api/v3/system/install/status` 自检端点。前端侧目前只有 `
installApi`（`frontend/web/src/api/modules/install.ts`）与布局里的 `PWAInstallPrompt`，**没有 `/install` 页面**——该路径当前会落到
catch-all 路由。

---

## 8. 反向代理与安全

`nginx/conf.d/fastblog.conf` 的要点：

- **upstream**：`backend` → `backend:9421`，`frontend` → `frontend:3000`，均保持 keepalive 32。
- **限流 zone**：`api` 30r/s、`login` 5r/m、`general` 50r/s（`remote_addr` 维度）。
- **请求体**：`client_max_body_size 60M`（与 `UPLOAD_LIMIT=62914560` 对齐）。
- **WebSocket**：`/api/` location 用 `map $http_upgrade $connection_upgrade` 转发 `Upgrade`，覆盖群聊
  `/api/v3/chat/message/ws/**` 与协作 `yjs` 两类长连接；`location /` 对前端强制 `Connection: upgrade`。
- **安全响应头**：X-Frame-Options、X-Content-Type-Options、X-XSS-Protection、Referrer-Policy、Permissions-Policy、CSP（脚本/样式放行
  `cdn.jsdelivr.net`，`connect-src 'self' wss:`）。
- **HSTS 只在 443 server 块开启**（纯 HTTP 下发 HSTS 无效，配置里有说明）。
- `/health` → 反代到 `backend/api/v3/health`，供 nginx 容器健康检查使用。
- HTTPS：把证书放进 `nginx/ssl/`（该目录以只读方式挂载），并在 443 server 块配置；启用后如需全站跳转 HTTPS，把 80 块的
  location 换成 `return 301 https://$host$request_uri;`（配置注释中给了示例）。

应用侧还叠了一层安全头与中间件（`src/app.py::register_middleware`）：CSP/Permissions-Policy、Token 黑名单、速率限制、暴力破解防护、HTTP
缓存、性能监控、多站点、请求性能中间件。

---

## 9. 数据持久化

后端容器内的可写目录全部使用**命名卷**（避免宿主目录权限问题，`docker-compose.yml`）：

| 卷                           | 容器路径                         | 内容                            |
|-----------------------------|------------------------------|-------------------------------|
| `fastblog-postgres`         | `/var/lib/postgresql/data`   | 数据库                           |
| `fastblog-redis`            | `/data`                      | Redis AOF                     |
| `fastblog-media`            | `/app/media`                 | 媒体文件                          |
| `fastblog-uploads`          | `/app/uploads`               | 上传分片/原始文件                     |
| `fastblog-storage`          | `/app/storage`               | 内容寻址对象存储（sha256 路径）           |
| `fastblog-backups`          | `/app/backups`               | 备份文件（含 `automated/`）          |
| `fastblog-logs`             | `/app/logs`、`/var/log/nginx` | 应用与 nginx 日志                  |
| `fastblog-config`           | `/app/config`                | `config/.env`、`models.yaml` 等 |
| `fastblog-plugins-data`     | `/app/plugins_data`          | 插件持久化数据                       |
| `fastblog-static-generated` | `/app/static_generated`      | 生成的静态产物                       |

容器启动时 entrypoint 会补齐缺失目录并统一 `chown appuser:appuser`，然后以 `gosu appuser` 降权运行（
`docker-entrypoint.sh`）。

---

## 10. 备份与恢复

备份能力在两处可用：后台「运维 → 备份」（`/api/v3/ops/backup/*`）与 CLI（`python -m cli backup create-backup|restore-backup`，
`cli/commands/backup.py` 直接调 `pg_dump -F c`）。

实现要点（`shared/services/system/backup_service.py`，由 `/api/v3/ops/backup/*` 端点调用）：

- 数据库备份产物是 **`pg_dump -F c` 输出再 gzip** 的 `*.sql.gz`，恢复时先解压到临时文件再交给 `pg_restore`（`pg_restore`
  不能直接读 gz）。
- 文件备份打包项目根下的相对路径（`media`、`static` 等），恢复也解到项目根。
- 增量/差异备份用**表级 `xmin` 上界**做变更检测，恢复路径是「基准全量 → 逐表 `TRUNCATE ... CASCADE` +
  `pg_restore --data-only --table=`」，因此增量包必须覆盖所有变化过的表。
- 备份路径参数一律经 `resolve_backup_path` 收口到 `BACKUP_DIR`，防止越权读写任意路径。
- 依赖 `pg_dump` / `pg_restore` / `createdb` / `dropdb` / `psql` 在 PATH 上。**注意后端镜像里没有这些命令行工具**：
  `Dockerfile` 只安装了 `libpq5`（客户端库，供 `psycopg2` 使用），未安装 `postgresql-client`
  。因此容器内的备份/恢复端点会因为找不到可执行文件而失败——要么在宿主机上执行（CLI 或 `docker exec` 到 postgres
  容器），要么在镜像里补装客户端。
- 云上传支持 S3 / 阿里云 OSS：用 `httpx` + 自实现 SigV4 签名（`src/api/v3/core/sigv4.py`）**单次 PUT**，单对象上限
  5GB，超限如实报错；凭据经 `secret_box` 加密存于 `system_settings` 的 `backup.cloud.secret_encrypted`，读接口只回
  `has_secret`。

---

## 11. 升级

两条路径：

1. **后台**：`/api/v3/ops/upgrade/*`（预检 → 快照 → 备份 → 拉取更新包 → 执行 → 回滚），前端页面在
   `frontend/web/src/pages/ops/upgrade`。
2. **CLI**：`python -m cli upgrade`（`cli/commands/upgrade.py`），内部封装 alembic 升级与快照。

版本元数据在 `version.txt`，格式为 **INI**：

```ini
[RELEASE]
version = 0.8.26.0921
build_time = ...
[DATABASE]
migration = 8b7ecb6d053c
status = up_to_date
[AUTHOR]
maintainer = ...
repository = ...
```

`[DATABASE] migration` 是升级系统的数据库基线记录，由 `shared/utils/version_manager.py` 读写。**手动新增迁移后要同步这一项
**，否则 `/ops/upgrade/*` 会报告过期的版本号。

发布包由 `scripts/build_release.py` 生成（`fastblog-v<version>.zip` + checksums + `RELEASE_NOTES.md`），CI 在打 tag 时执行（
`.github/workflows/release.yml`），产物通过 GitHub Release 分发。

---

## 12. 健康检查与排障

compose 内置健康检查（可直接复用手工排查）：

```bash
curl -f http://localhost:9421/api/v3/health        # 后端
curl -f http://localhost:3000/                     # 前端容器内（Node SSR）
curl -f http://localhost:4321/health               # 经 nginx（默认形态）
```

常见问题定位：

| 现象                               | 排查方向                                                                                                                         |
|----------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| 登录请求长时间挂住（不是 401/500）            | Redis 不可用。限流/防爆破中间件同步等待缓存，Redis 掉线会让请求卡住；先确认 6379 可达（`src/app.py` 中间件链、`shared/services/security/rate_limiter.py`）           |
| 启动即失败并提示密钥                       | `SECRET_KEY` / `JWT_SECRET_KEY` 为空或仍是占位值（`shared/config/settings.py`）                                                        |
| 生产环境看不到 `/api/v3/docs`           | `ENVIRONMENT=production` 时文档界面被显式关闭，属预期行为                                                                                    |
| `alembic upgrade` 打到了错误的库        | `alembic_migrations/env.py` 用 `config/.env` 覆盖环境变量；要改目标请设 `DATABASE_URL`                                                     |
| 前端某页面 500 且提示 `useRequestURL` 相关 | `useRequestURL()` 必须在 setup 顶层调用，不能放进 `useHead` 的响应式回调                                                                       |
| 后台菜单为空                           | 菜单结构在前端（`src/utils/menus.ts`），授权在后端（`admin_menus` + `role_admin_menus`）；新菜单需 `seed_admin_menus --apply --grant-system-roles` |

端口被占用时 Nuxt dev server 会**静默**换端口，排查前先确认实际监听端口。

---

## 13. 已知偏差（代码或脚本与当前架构不一致，尚未修复）

以下是核对仓库时发现、**当前确实存在**的偏差。文档如实记录，修复与否由维护者决定：

| 位置                                          | 问题                                                                                                              |
|---------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| `docs/FastBlog_API.postman_collection.json` | Base URL 写的是 `http://localhost:9421/api/v1`（v1 已不存在）                                                            |
| `.pre-commit-config.yaml`                   | `model-lifecycle` hook 调用的 `scripts/model_lifecycle_check.py` 不存在；`detect-secrets` 依赖仓库里没有的 `.secrets.baseline` |
| `shared/upgrade/`                           | 仅剩 `normalize_article_slugs.py`，目录名已名不副实                                                                        |
| 两套 CLI 并存                                   | `cli/`（Typer，`python -m cli`）与 `scripts/cli.py`（`Makefile` 的 `cli` 目标）；`create-admin` / `routes` 目标已改用前者        |
| 后端镜像缺少 pg 客户端                               | 容器内没有 `pg_dump` / `pg_restore`（详见第 10 节），备份与恢复需在宿主机执行或补装 `postgresql-client`                                    |
