# FastBlog 开发指南

面向要改动本仓库代码的人。内容以**代码为准**（每节给出出处），描述当前实现，不含历史方案。

---

## 1. 技术栈

| 层     | 选型                                                                      | 出处                                                      |
|-------|-------------------------------------------------------------------------|---------------------------------------------------------|
| 后端    | Python 3.14 + FastAPI + SQLAlchemy 2（async）+ asyncpg                    | `requirements.txt`、`main.py`                            |
| 数据库   | PostgreSQL 16；迁移用 Alembic                                               | `docker-compose*.yml`、`alembic_migrations/`             |
| 缓存/队列 | Redis（限流、缓存、多 worker 共享、分布式锁）                                           | `shared/config/settings.py`                             |
| 前端    | Nuxt 4.5（Vue 3）+ TypeScript；前台 Tailwind 4 + shadcn 风格组件，后台 Element Plus | `frontend/web/package.json`、`nuxt.config.ts`            |
| 内容/媒体 | TipTap 编辑器、ECharts、three；图片走 `@nuxt/image`（ipx）                         | `frontend/web/package.json`                             |
| 部署    | Docker Compose（backend + frontend + nginx + postgres + redis）           | `docker-compose.yml`；见 [DEPLOYMENT.md](./DEPLOYMENT.md) |
| 质量工具  | ruff（pre-commit）、mypy、pytest、vue-tsc、Playwright                         | `.pre-commit-config.yaml`、`.github/workflows/ci.yml`    |

---

## 2. 仓库结构

```
fast_blog/
├── main.py                  后端入口（argparse → create_app → uvicorn）
├── src/
│   ├── app.py               应用工厂：中间件链、路由注册、错误处理、静态挂载
│   ├── api/
│   │   ├── common/          跨版本通用响应/工具
│   │   └── v3/              唯一权威 API 层（域 → 模块 → 五件套）
│   │       ├── __init__.py  DOMAIN_MODULES：路由的唯一天真源
│   │       ├── core/        discover / deps / router_class / secret_box / ws_auth / permission
│   │       ├── common/      response / request / enums / tags / json_field
│   │       └── modules/     system content analytics ops extension marketing mobile ai chat commerce gamification
│   ├── auth/                认证依赖（JWT 解析、可选鉴权）
│   ├── middleware/          缓存、Token 黑名单、暴力破解、性能、多站点
│   ├── mcp/                 MCP（Model Context Protocol）服务端
│   ├── scheduler.py         定时任务（如定时发布）
│   └── services/            redis_service 等
├── shared/
│   ├── models/              领域模型（按域分子包）
│   ├── services/            领域服务（articles、users、ops、plugins、security…）
│   ├── config/settings.py   配置类与 .env 加载
│   └── utils/               version_manager 等
├── config/
│   ├── models.yaml          数据模型的唯一权威定义（见第 6 节）
│   └── .env                 安装向导写入的配置（会被 alembic 与 settings 读取）
├── frontend/web/            Nuxt 4.5 单工程（前台 SSR + 后台 CSR），详见 frontend/web/README.md
├── plugins/                 插件与主题（metadata.json + plugin.py + frontend/）
├── themes/                  预留目录（当前为空）
├── cli/                     Typer 命令行（python -m cli）
├── scripts/                 生成器与种子脚本（generate_routes、seed_rbac、seed_admin_menus…）
├── install.py               交互式安装/初始化脚本（环境自检 → .env → 迁移 → 种子 → 建用户）
├── mobile-app/              Capacitor 壳工程
├── tests/                   后端测试（pytest）
├── nginx/                   nginx.conf + conf.d/fastblog.conf
├── alembic_migrations/      迁移（当前仅 1 个 baseline）
├── vendor/FastApiAdmin/     上游参考实现（第三方，仅供对照，不参与构建）
└── docs/                    本目录
```

---

## 3. 本地开发

**后端**

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                # 填 SECRET_KEY、DB_PASSWORD
docker compose -f docker-compose.dev.yml up -d      # postgres + redis
python -m alembic upgrade head
python main.py --env dev                            # http://localhost:9421
```

`main.py` 的参数：`--mode {app,supervisor}`、`--port`（默认 9421）、`--host`、`--env {prod,dev,test}`、`--workers`、`--nolog`。
`--mode supervisor` 已废弃，会明确报错退出（进程托管交给 Docker / systemd 与 `ops/supervisor` 模块）。

**前端**

```bash
cd frontend/web
npm ci --legacy-peer-deps      # 或 npm ci；两者都应能装上（见 frontend/web/README.md）
npm run dev                    # http://localhost:5173，/api 代理到 :9421
```

**开发期也可只跑依赖服务**：`docker compose -f docker-compose.dev.yml --profile search up -d`（含 Meilisearch）。

---

## 4. 后端架构

### 4.1 入口与工厂

`main.py` → `shared.config.settings.get_config_by_env()` → `src.app.create_app()`：注册中间件 → 注册 v3 路由 → 错误处理 →
静态挂载（`src/app.py`）。

- API 文档界面：`/api/v3/docs`、`/api/v3/redoc`、`/api/v3/openapi.json`；**`ENVIRONMENT=production` 时三者均为 `None`**（不暴露
  API 结构）。
- 静态资源：`/api/v3/static`（`static/` 目录）、`/api/v3/assets/themes`（`themes/`）。
- 媒体文件**不走 StaticFiles**：`/api/v3/assets/storage/{path}` 由受控视图提供，校验目录遍历，并按 sha256 反查媒体记录判断
  `is_public`（私密媒体仅作者可见）。

### 4.2 中间件链

`register_middleware()` 依次加入：CORS → 调试（仅 `DEBUG`）→ HTTP 缓存（ETag / Last-Modified）→ 速率限制 →
安全响应头（X-Frame-Options、CSP、Permissions-Policy、Referrer-Policy）→ API 版本头 → 性能监控（惰性）→ 多站点（惰性）→ Token
黑名单 → 暴力破解防护。
重依赖（psutil、Site 模型）用 `_make_lazy_middleware` 延迟到首次请求时导入。

### 4.3 生命周期

`lifespan` 顺序：安装状态检查 → 数据库管理器 → 扩展 → 调度器 → 插件系统 → 审计日志订阅者（依赖 EventBus，必须在插件之后）→
下载队列处理器 → 权限缓存预热 + Redis 广播订阅；关闭时反向清理。
定时发布由 `src/scheduler.py`（每 5 分钟）统一处理。

### 4.4 API v3：域 → 模块

路由前缀 `/api/v3/<domain>/<module>`，**11 个域 / 73 个模块**（实测 650 条路由），清单以
`src/api/v3/__init__.py::DOMAIN_MODULES` 为唯一事实来源：

| 域               | 模块数 | 模块                                                                                                                                            |
|-----------------|-----|-----------------------------------------------------------------------------------------------------------------------------------------------|
| `/system`       | 19  | admin_menu auth cache gdpr group health install integration log menu monitor permission role security sensitive_word setting site social user |
| `/content`      | 12  | approval article category collaboration comment custom_post_type media page page_builder shortcode tag third_party_publish                    |
| `/analytics`    | 4   | dashboard report search seo                                                                                                                   |
| `/ops`          | 10  | backup cdn deployment email enterprise migration notification supervisor upgrade webhook                                                      |
| `/extension`    | 4   | block_pattern plugin theme widget                                                                                                             |
| `/marketing`    | 3   | ad form vip                                                                                                                                   |
| `/mobile`       | 11  | article auth category comment feed follow media message revenue user vip                                                                      |
| `/ai`           | 2   | config workflow                                                                                                                               |
| `/chat`         | 2   | group message                                                                                                                                 |
| `/commerce`     | 3   | payment revenue tipping                                                                                                                       |
| `/gamification` | 3   | badge certification points                                                                                                                    |

注册流程（`register_v3_routes`，`fail_fast=True`）：

1. 按 `DOMAIN_MODULES` 导入各模块 `controller.py` 的 `router`；
2. 校验 `APIRouter.prefix` 与目录名一致（不一致只告警，以 prefix 为准）；
3. 启动期**路由冲突**与**路径遮蔽**检测（`core/discover.py`）——静态路径不得注册在能匹配它的参数路径之后，否则拒绝启动；
4. 扫描域下"未登记模块"并告警（不注册）；
5. 注册 v3 统一异常处理。

**加一个模块的最小步骤**：建目录（五件套）→ 在 `DOMAIN_MODULES` 登记 → 补权限码（见 4.6）→ 同步测试里的模块集合期望常量 → 前端补
`api/modules/*.ts` 与页面（见第 5 节）。

### 4.5 分层与响应约定

模块目录结构（"五件套"）：

```
modules/<domain>/<module>/
├── controller.py     APIRouter（prefix 必须与目录名一致）
├── schema.py         Pydantic 出入参
├── crud.py           数据访问
├── service.py        业务逻辑
└── model.py          可选（模型通常在 shared/models/ 下）
```

统一响应（`src/api/v3/common/response.py`）：

```json
{"code": 200, "msg": "success", "data": ..., "pagination": {"page":1,"page_size":20,"total":0,"pages":0}}
```

- `code == 200` 表示成功；业务失败默认仍是 **HTTP 200 + 非 200 code**，前端按 `code` 判成败（
  `frontend/web/src/api/request.ts` 与之对齐）。
- 需要非 200 HTTP 时用 `fail(..., http_status=...)` 配合 `JSONResponse`。
- 路由风格：**纯 RESTful 主路径**（`/system/user` 的 GET/POST、`/system/user/{id}` 的 GET/PUT/DELETE）+ FastApiAdmin 兼容别名（
  `/list`、`/detail/{id}`、`/create`、`/update/{id}`、`/delete`，`include_in_schema=False`）。别名是静态路径，*
  *必须注册在 `/{id}` 之前**，由 `assert_no_shadowed_routes` 在启动期强制。

### 4.6 权限

- 权限码格式：**三段式 `module_{域}:{模块}:{动作}`**；唯一权威是 `src/api/v3/core/permission/codes.py::CODE_LABELS`（当前 *
  *194 条**）。
- 落库：`python -m scripts.seed_rbac`（从 `CODE_LABELS` 派生 `capabilities` 并覆盖内置角色定义）。只改代码不 seed，库里就没有这枚码。
- 校验：路由级 `AuthControl` / `AuthPermission` 依赖（`src/api/v3/core/deps.py` 重导出 `core/permission/*`），按钮级由前端
  `v-auth` 指令控制。
- 缓存：`core/permission/` 提供内存缓存 + Redis 失效广播；启动时预热超管权限。
- **启动期审计**：`audit_permissions(app, strict=...)` 检查"写操作必须声明权限码、码必须已登记、通配告警、豁免清单"。默认只告警，
  `PERMISSION_AUDIT_STRICT=1` 时问题即拒绝启动。
- 数据范围（`data_scope`）只作用于管理端；公开读一律不过滤。

### 4.7 加密与审计

- 通用凭据：`src/api/v3/core/secret_box.py`（AES-256-GCM，密钥 `SHA256(SECRET_KEY)`），密文永不回传，出参只给 `has_xxx`。
- 用户级凭据（如个人 AI api_key）：`core/user_secret_box.py`，密钥 `HKDF(SECRET_KEY, salt=该用户 password 哈希)` ——
  服务端不需要明文密码即可解密；用户改密码后旧密文失效，此时应**如实提示重新填写**，不要静默降级。
- 写操作审计：`core/router_class.py::OperationLogRoute` 对 POST/PUT/PATCH/DELETE 在响应后异步写 `audit_logs`
  （fire-and-forget，审计失败不影响响应）。模块 router 用 `route_class=OperationLogRoute` 启用。

### 4.8 WebSocket

全仓两个 WS 端点：`/api/v3/content/collaboration/yjs/ws/{document_id}`（协同编辑）与 `/api/v3/chat/message/ws/{group_id}`
（群聊），共用 `core/ws_auth.py`：

- 鉴权三级回退：Cookie → 子协议 `bearer.<token>` → query `token`（浏览器无法自定义 WS 请求头）。
- **准入失败必须先 `accept` 再 `close(4401/4403)`**：未 accept 就 close 会被 uvicorn 按 ASGI 规范转成 HTTP 403，浏览器只看到
  `1006`，业务码传不到客户端。
- WS 路由没有 `methods`，启动期权限审计会跳过它，**准入逻辑必须写在路由体内**。

---

## 5. 前端架构（`frontend/web`）

### 5.1 一个工程承载前台与后台

| 区域                                                                                                                                                | 渲染                | 布局                    | UI                                      |
|---------------------------------------------------------------------------------------------------------------------------------------------------|-------------------|-----------------------|-----------------------------------------|
| 前台（`/`、`/articles`、`/p/[slug]`、`/categories`、`/search`、`/experts`、`/home/{username}`、`/feed`、`/chat`、`/vip`、`/profile`…）                          | SSR               | `layouts/default.vue` | Tailwind 4 + `components/ui`（shadcn 风格） |
| 后台（`/dashboard`、`/system/**`、`/content/**`、`/analytics/**`、`/extension/**`、`/ops/**`、`/marketing/**`、`/commerce/**`、`/gamification/**`、`/my/**`…） | CSR（`routeRules`） | `layouts/admin.vue`   | Element Plus                            |

当前 **87 个页面**、**62 个 `api/modules/*.ts`**。SSR 关闭清单集中在 `nuxt.config.ts::routeRules`
（后台、用户中心、消息、积分/勋章、认证/打赏、群聊等），列表页用 `swr: 60` 短缓存。

### 5.2 目录约定

| 路径                                              | 作用                                                                                       |
|-------------------------------------------------|------------------------------------------------------------------------------------------|
| `src/app.vue` / `error.vue`                     | 根组件（写入 `data-theme` / `data-accent`）/ 全局错误页                                              |
| `src/layouts/`                                  | `default`（前台）、`admin`（后台，Element Plus 懒加载）                                               |
| `src/middleware/auth.ts`                        | 后台鉴权：登录态 + `definePageMeta({permission})` → 越权跳 `/403`                                   |
| `src/api/request.ts`                            | axios 客户端：前缀 `/api/v3`、注入 Bearer、`code===200` 为成功、HTTP 401 静默续期后重放                       |
| `src/api/modules/*.ts`                          | 按后端模块拆分的接口封装，`src/api/index.ts` 聚合导出                                                     |
| `src/composables/`                              | `useApi`（前台 `$fetch`）、`useSiteInfo`、`useTheme`、`useJsonLd`、`useHreflang`、`useWebVitals`… |
| `src/store/modules/`                            | Pinia：`user` / `permission` / `app`（客户端持久化）                                              |
| `src/styles/index.css`                          | 设计令牌（Tailwind 4 `@theme`）+ 深浅色 + 自选配色                                                    |
| `src/utils/menus.ts`                            | 后台菜单结构，`name` 必须与后端 `admin_menus.code` 对应                                                |
| `i18n/locales/{zh-CN,en}.json`                  | 文案（**两语言必须对称**）                                                                          |
| `e2e/*.spec.ts`                                 | Playwright 回归用例                                                                          |
| `scripts/check-i18n.mjs`、`scripts/i18n_tool.py` | i18n 校验与批量抽取替换                                                                           |

### 5.3 设计令牌（不要硬编码色值）

颜色/圆角/宽度定义在 `src/styles/index.css` 的 `@theme`：`--color-canvas|surface|surface-soft`、
`--color-fg|fg-muted|fg-subtle`、`--color-line|line-strong`、`--color-primary(+fg/soft/hover)`、
`--color-danger|success|warning(-soft)`、`--radius-control|card|pill`、`--container-read|wide`。

- 深浅色：覆盖 `[data-theme='dark']`；`data-theme=system` 由脚本解析。
- 用户自选配色：切换 `[data-accent='violet'|'emerald'|'rose'|'amber']`，只影响主色系。
- 组件里只引用语义令牌；唯一例外是主题切换器的色板。

### 5.4 数据层与 WebSocket

|     | 前台                                                | 后台                               |
|-----|---------------------------------------------------|----------------------------------|
| 客户端 | `composables/useApi.ts`（`$fetch`；SSR 用绝对地址，浏览器同源） | `api/request.ts`（axios，401 静默续期） |
| 前缀  | `/api/v3`                                         | `/api/v3`                        |

浏览器侧 WS 基址由 `NUXT_PUBLIC_WS_BASE_URL` 提供：**dev 必须显式指定**（`Upgrade` 不经 `nitro.devProxy`，也不经 Vite 的
`server.proxy`），生产留空走同源，由 nginx 转发 Upgrade。

### 5.5 权限与菜单

- 页面**始终存在**，越权由 `middleware/auth.ts` 按 `definePageMeta({permission: 'module_x:y:z'})` 拦截。
- 菜单结构在前端（`utils/menus.ts`），授权在后端（`admin_menus` + `role_admin_menus`），两者取 AND；后端未下发 `menu_codes`
  时前端不做过滤，避免"已迁移未 seed"导致菜单全空。
- 后端新增模块后，前端要补：`api/modules/*.ts` + `api/index.ts` 导出 → `pages/**` → `menus.ts` 菜单项 + 两语言
  `menu.<name>` → `python -m scripts.seed_admin_menus --apply --grant-system-roles`（新菜单不授权，任何角色都看不到）。
- UI 边界：前台只用 `components/ui` + Tailwind；后台只用 `el-*`。前台页面会走 SSR，**不要**在非后台路由里直接使用 Element
  Plus；后台也不要静态 `import {ElMessage}`（会把 EP 拉进共享 chunk），统一用 `@/utils/feedback`。

### 5.6 i18n

- 文案在 `i18n/locales/*.json`，当前 **2830 个 key**、代码引用 2269 个、菜单动态 key 66 个。
- `npm run check:i18n` 校验：key 存在、两份 locale 对称、菜单 `menu.<name>` 齐全、单花括号、*
  *每条文案可被 `@intlify/core-base` 编译**。
- **文案里不要写 `{...}` 字面量**（例如 JSON 示例），vue-i18n 会当插值编译，导致页面白屏。

---

## 6. 数据模型与迁移

- **`config/models.yaml` 是数据模型的唯一权威**（237KB）。流程：写 yaml →
  `python -m scripts.generate_routes generate-model --model X` 生成骨架 → 写 Alembic 迁移。**不要重新生成既有模型**
  （会覆盖手工内容，例如加密字段包装）。
- 迁移目录 `alembic_migrations/versions/` 当前只有 **1 个** baseline：`8b7ecb6d053c_initial_full_schema`（
  `down_revision = None`）。
- 迁移连哪个库由 **`config/.env`（`load_dotenv(..., override=True)`）** 决定；环境变量会被它覆盖。要临时指向别的库请设
  `DATABASE_URL`（优先级最高，且不在 `config/.env` 里）。
- 新增迁移后同步 `version.txt` 的 `[DATABASE] migration`，否则 `/ops/upgrade/*` 报告的版本会过期。
- 删主记录前先看外键：新表一律显式写 `ondelete`（历史上有表因缺 `ON DELETE CASCADE` 让删除接口 500）。

---

## 7. 测试与质量门

| 层               | 命令                                                                   | 说明                                                                                                            |
|-----------------|----------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| 后端测试            | `python -m pytest tests/`                                            | `tests/` 下 58 个 `test_*.py`（其中 41 个是 v3 域模块测试）；`pytest.ini` 定义 `unit` / `integration` / `slow` / `asyncio` 标记 |
| 后端 lint         | `ruff check src/api/v3`（pre-commit 亦启用 `ruff --fix` + `ruff-format`） | 只对 `src                                                                                                       |shared|scripts|tests|plugins` |
| 后端类型            | `python -m mypy src/ --ignore-missing-imports`                       | CI 中非阻塞                                                                                                       |
| 前端类型            | `npm run type-check`（`nuxt typecheck`）                               | 需先 `npm run prescan`                                                                                          |
| 前端 tsc pre-push | pre-commit 的 `tsc` hook                                              | `working_directory: frontend/web`                                                                             |
| i18n            | `npm run check:i18n`                                                 | 改文案后必跑                                                                                                        |
| 端到端             | `npm run test:e2e`（Playwright，7 个 spec）                              | 复用或拉起 dev server，带认证的用例需 `.env.e2e` 凭证                                                                        |
| 性能              | `k6 run tests/load/benchmark.js`                                     | v3 路径，详见 tests/load/README.md                                                                                 |

CI（`.github/workflows/ci.yml`）分 6 个 job：`lint`（mypy）→ `test-quick`（4 个 mock 用例集）与 `test-frontend`（`npm ci` →
build → type-check）→ `test-backend`（Postgres + Redis service，跑 `tests/` 全量 + alembic upgrade/downgrade 往返）→
`build-frontend`、`security`（pip-audit / npm audit，非阻塞）→ `docker`（构建镜像）。
`release.yml` 在打 `v*.*.*` tag 时构建发布包；`docker-publish.yml` 推送镜像到 GHCR。

---

## 8. 常用命令

```bash
# 后端（项目根）
python install.py                               # 交互式安装/初始化（迁移 + 种子 + 按角色建用户）
python main.py --env dev                        # 启动（:9421）
python -m pytest tests/ -q                      # 全量测试
python -m ruff check --no-cache src/api/v3      # lint
python -m alembic upgrade head                  # 迁移
python -m scripts.seed_rbac                     # 同步 capability 与内置角色
python -m scripts.seed_admin_menus --apply --grant-system-roles
python -m scripts.create_user -u admin -r superadmin   # 按角色创建用户（--list-roles 查看可选角色）
python -m scripts.generate_routes generate-model --model X   # 从 models.yaml 生成骨架
python -m cli --help                            # CLI（user / backup / cache / migrate / health / shell / upgrade）

# 前端（cd frontend/web）
npm run dev / build / type-check / check:i18n / test:e2e
npm run prescan                                 # 扫描 plugins/*/frontend 生成插件页面登记表
python scripts/i18n_tool.py extract|apply|check # i18n 批量改写
```

---

## 9. 注意事项（踩过且已验证的点）

1. **`DOMAIN_MODULES` 是模块清单的唯一真相**；漏登记不会报错，只会有一条"未登记模块"告警，端点不存在。
2. **别名必须注册在 `/{id}` 之前**，否则启动期 `assert_no_shadowed_routes` 直接拒绝启动。
3. **权限码只改 `codes.py` 不 `seed_rbac`**，库里就没有该码 → 前端入口被 `v-auth` 隐藏、后端也匹配不上。
4. **`layouts/` 的静态 import 会进所有页面的初始包**（layouts 属 app 层，不按页面分割）；后台要懒加载 Element Plus 必须动态
   `import()`。
5. **`<script setup>` 里不能 `export`**（`export interface` 直接编译失败）→ 类型外置到 `src/types/*.ts`。
6. **Nuxt 保留 `Lazy*` 组件前缀**：组件不要取名 `LazyImage` 之类。
7. **`useRequestURL()` 必须在 setup 顶层调用**，放进 `useHead` 的响应式回调会丢上下文导致 500。
8. **本机 Redis 停了会让登录"挂住"**（不是 401/500）：限流/防爆破中间件同步等 cache；排查顺序是 health 通 → login 挂 → 查
   6379。
9. **独立脚本要显式加载全部模型**，否则 relationship 的字符串目标解析不到（`NoReferencedTableError`）。
10. **`system_settings.setting_value` 存的是 JSON 配置**：列类型是 `TEXT`（历史上一度是 `VARCHAR(255)`，导致保存长配置直接
    500），读写请走 `setting_service.get_setting/upsert`，不要直接操作模型。
11. **`scripts/seed_rbac.py` 没有 dry-run / argparse**，执行即写库；`seed_admin_menus.py` 默认 dry-run。
12. **本仓库同时存在两套 CLI**：`cli/`（Typer，`python -m cli`）与 `scripts/cli.py`（被 `Makefile` 调用）。
13. 修改文档或代码时注意：仓库里不少文件用 **UTF-8 + LF**，读写时不要用会改编码/换行的工具重写整文件（`.gitattributes` 对
    `*.py`/`*.yml`/`*.json`/`*.md` 强制 LF）。
