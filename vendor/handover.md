# fast_blog 交接文档（P10 后端完成 → 前端接线进行中）

> 生成时间：2026-09-29（会话结束时）
> 工作区：`X:\project\fast_blog`
> **所有改动均留在工作区，未提交（用户自行提交）。**

---

## 1. 一句话现状

- **后端 P10 接线清单 18 类：全部完成**（v3 真实实现，882 个端点，全量测试 1509 passed / 5 skipped）。
- **前端接线：刚开始**。按域推进，`/system` 域首批派了 11 个子任务，**只有 1 个（accessibility）完整交付**，另有 3 个留下未完成的中间产物；
  **尚无任何前端改动落地到最终位置**（全部还在暂存目录 `frontend/web/.gen/`）。
- 后端进程（9421）与前端 dev server（5173）**当前都已停止**，需重新启动。

---

## 2. 环境与启动命令

| 项     | 值                                                                                                 |
|-------|---------------------------------------------------------------------------------------------------|
| 工作区   | `X:\project\fast_blog`                                                                            |
| 后端    | FastAPI，`http://127.0.0.1:9421`（启动：仓库根 `.venv\Scripts\python.exe main.py`）                        |
| 前端    | Nuxt 4 + Vue 3 + Element Plus，`http://127.0.0.1:5173`（启动：`cd frontend/web; npm run dev`）          |
| Redis | `127.0.0.1:6379`（会话结束时仍在监听）                                                                       |
| 本地数据库 | PostgreSQL 库 **`fb260928`**（`config/.env` 指向本地；原 Supabase 配置备份在 `config/.env.bak-20260928175546`） |
| PG 账号 | 用户 `postgres` / 密码 `c9nmoX5YwcqyJs3zGZFrhc61njO8jW_c`；psql 必须带 `-h localhost`                     |
| 管理账号  | `admin` / `MfKL@hy?yDfs4MHM`（superadmin，`is_superuser=True`，前端菜单全通过）                              |
| 测试库   | `fast_blog_test` **不存在** → 需要 DB 的 pytest 会报 `InvalidCatalogNameError`（要么 monkeypatch，要么改走运行时验证）  |

**前端常用命令**（在 `frontend/web` 下）：

```powershell
npm run dev          # 开发服务器（5173，含 prescan 生成 .plugin-pages）
npm run type-check   # prescan + nuxt typecheck（本项目最有效的静态把关）
npm run check:i18n   # 校验代码里用到的 i18n key 都存在 + 两份 locale 对称 + menu.<name> 齐备
npm run test:e2e     # playwright
```

---

## 3. 后端：P10 已完成的内容（勿重做）

### 3.1 交付范围

P10 清单 18 类全部落 v3 真实实现。本会话完成的是 **任务 15–18**（前序批次 1–14 已完成）：

| 模块                     | 落点（真实数据源）                                                                                                        | 端点数 |
|------------------------|------------------------------------------------------------------------------------------------------------------|-----|
| `content/amp`          | 真表读文章生成完整 AMP 文档；`html.parser` 元素级转换 + 违规校验                                                                      | 3   |
| `gamification/points`  | **重写**：`user_points` / `points_transactions` / `points_rules`；刻意不暴露 v2 的 `POST /record-action`（可刷分）              | 15  |
| `system/edge`          | `system_settings.edge.{functions,deployments}`；静态校验 + 产物摘要；**从不执行用户代码**                                          | 7   |
| `chat/web_push`        | `system_settings.chat.web_push.subscriptions.{uid}`（v2 是进程内 dict）                                                | 8   |
| `content/yjs`          | `article_content` + `article_revisions`（完整正文 + sha256，v2 截断 500 字符）；复用 `content/collaboration` 的同一 room_registry | 8   |
| `content/team_comment` | 既有表 `team_comments`                                                                                              | 8   |
| `system/translation`   | `system_settings.translation.{bundles,memory,locales,settings}`                                                  | 27  |
| `system/utility`       | 直接复用 `block_pattern_defs` / `user_defs.is_vip` / `nlp_command_parser`                                            | 5   |
| `system/oauth`         | `oauth_accounts` + `system_settings.oauth.providers`；state HMAC 校验 + PKCE S256                                   | 6   |

**没有新增表 / 没有新增 ORM 模型 → `config/models.yaml` 与 alembic 迁移本批无需改动。**

### 3.2 收口动作（已完成）

1. 补 `src/api/v3/modules/content/amp/__init__.py`（缺包文件会让 controller 导入失败）。
2. `src/api/v3/__init__.py` 的 `DOMAIN_MODULES` 登记 9 个模块：`/system` 30（+edge/oauth/translation/utility）、`/content`
   18（+amp/team_comment/yjs）、`/chat` 3（+web_push）。
3. 同步 5 个契约测试：`tests/test_v3_system.py`（+36 路径）、`tests/test_v3_group_scope.py`（*
   *它有一份独立的 `SYSTEM_MODULES` 副本，最易漏**）、`tests/test_v3_content.py`（+16）、`tests/test_v3_ai_chat.py`（+8）、
   `tests/test_v3_gamification.py`（points 11→15）。
4. `src/api/v3/core/permission/audit.py` 的 `EXEMPT_WRITE_ENDPOINTS` 补 5 条：`chat/web_push/{subscribe,unsubscribe}`、
   `system/utility/nlp/parse`（纯计算但方法是 POST）、`system/oauth` 的 POST callback 与 DELETE `{provider}`。审计**只按
   HTTP 方法判定**，GET 会写库也不登记。
5. 暂存测试全部迁入 `tests/`（`_pending_test_*.py` → `tests/test_v3_*.py`），模块目录零残留。

### 3.3 本批修掉的真实缺陷

1. `system/translation/service.py` 少一个 `]`（`List[Dict[str, Any]:`）→ 启动期 SyntaxError，整个 v3 加载失败（fail-fast
   拦下）。
2. `translation` 的 **PO 解析把 header（空 msgid）当词条** → 导出再导入多出 `""` 词条；已跳过空 msgid。
3. `content/amp` 的 `render_document`：**封面图的 `<amp-img>` 不进 `components`** → head 不注入组件脚本，生成的文档真实
   AMP 校验会失败；已修（并同步测试断言）。
4. 3 处子智能体的错误断言：translation 相对时间用 `now.replace(minute=55)` 会回绕、PO 断言、oauth
   `assert verifier == generate_code_verifier()` 应为 `!=`。

### 3.4 验证结论

- `ruff check`：9 个新模块 + 相关测试全绿。
- 全量 `pytest tests/ -q`：**1509 passed / 5 skipped**（约 13 分钟，必须用后台 job 跑）。
- 真实端到端（后端 9421 + psql 核对落库）：points 签到真加分（5→10）；amp 按真文章生成 `validation.valid=true`；edge
  注册/校验/部署（无凭据时 `deployed:false` + reason + 所需环境变量）/路由命中预览/本地日志；web_push 订阅落
  `chat.web_push.subscriptions.1`、stats 真聚合、send 返 400；team_comment 建/改/解决/统计落 `team_comments`；yjs `access`
  判作者、snapshot 真写 `article_revisions` 且第二次**幂等去重**；translation 词条/记忆/导入/导出（CSV 带 BOM +
  中文表头）/进度/报告 + 记忆精确 1.0、模糊 0.9167 + 机器翻译未配置返 `available=false`；utility NLP 解析 `intent=create` +
  vip-status；oauth providers 5 个 `configured=false`、`authorize-url` 返 400、bindings 空。
- **如实降级（绝不伪造）**：无边缘平台凭据 / 未装 pywebpush / 无翻译密钥 / 无 OAuth 凭据 —— 全部返回明确错误或
  `available=false`。
- e2e 产生的数据**已清理**（`system_settings` / `team_comments` / `article_revisions` 归零，`user_points` 恢复 `1|5|5`）。

---

## 4. 前端：接线任务（进行中，重点看这里）

### 4.1 用户已确认的方向

1. **按域逐个补全**：如先 `/system`（30 模块）→ `/content` → 其它域，每域一次到位（含"部分缺失"的端点）。
2. **页面形态：尽量并入既有页面，不新增独立页面**；只有在某模块能力**没有任何可承载页面**时才新建页面。

### 4.2 缺口测绘（实测，可复现）

方法：dump 后端 `app.routes` 的 `/api/v3` 路由（排除 HEAD/OPTIONS），再用正则扫描 `frontend/web/src/**/*.{ts,vue}`
里出现的路径（把前端模板串的 `${...}` 归一成占位符后匹配）。

- 后端 v3 端点总数：**882**
- 前端已调用：**383**
- **缺失：499**

**23 个「完全缺失」模块（156 端点）**：

```
ai/skill 4            analytics/tracking 12   chat/web_push 8        commerce/shop 21
content/amp 3         content/feed 4          content/recommend 5    content/redirect 8
content/team_comment 8  content/yjs 8         mobile/category 2      system/accessibility 8
system/admin-menu 14  system/edge 7           system/export 3        system/help 7
system/maintenance 9  system/oauth 6          system/quota 3         system/screen-options 7
system/translation 27 system/utility 5        system/workflow 13
```

**61 个「部分缺失」模块（343 端点）**，`/system` 域明细（共 91）：

```
cache 3/6      gdpr 3/7       group 10/16    health 4/5     integration 4/8   log 2/6
menu 7/14      monitor 14/37  permission 1/7 role 12/14     security 7/10     setting 2/8
site 9/11      social 1/2     user 12/14
```

> ⚠️ 重要判读：`*/**/*/list`、`/detail/{id}`、`/create`、`/update/{id}`、`/delete` 这类是 v3 为 FastApiAdmin 兼容提供的**别名
**，前端用纯 REST 主路径（`GET /system/user` 等）即可，**不算真缺口**，不要为了"清零"去接它们。

### 4.3 前端设施事实（续作必读）

- **HTTP 客户端**：`src/api/request.ts` —— axios，`baseURL = API_BASE_URL`（`/api/v3`），自动带 `Bearer` token，401 静默刷新一次，
  `code !== 200` 统一 `ElMessage`/toast 并 reject。导出 `http.get/page/post/put/patch/delete/upload/raw`。
- **API 模块**：`src/api/modules/<name>.ts`（68 个），统一 `import http from '../request'`，导出 `xxxApi` 对象 + interface
  类型；**聚合出口是 `src/api/index.ts`**（页面一律 `from '@/api'` 导入，必须在那里登记 export）。
- **页面**：Nuxt 文件路由 `src/pages/**`。管理端页面模板：

```vue
definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.<域>.<模块>.title',
  permission: 'module_system:xxx:view',
})
```

- **可复用组件**：
  `@/components/admin/{AdminPage,AdminListShell,AdminFormDrawer,AdminTableSkeleton,AdminEmpty,AdminSelectionBar,CommandPalette,SettingGroupForm,...}`。
- **列表 composable**：`@/composables/useAdminList`（筛选 + 表格 + 分页 + URL 同步）；反馈用 `@/utils/feedback` 的
  `ElMessage`/`ElMessageBox`；按钮级权限用 `v-auth` 指令。
- **i18n**：`i18n/locales/zh-CN.json` 与 `en.json`（**两份 key 必须完全对称**，`npm run check:i18n` 会失败）。
  `admin.system.*` 段在 zh-CN.json 约 773–1302 行，`menu.*` 段约 3084 行起；**en.json 结构镜像、行号几乎一致**。
- **菜单**：`src/utils/menus.ts` 的 `ADMIN_MENUS`（`name` 必须等于后端 `admin_menus.code`，且**必须有 `menu.<name>` 翻译
  **）；`store/modules/permission.ts` 按「权限码 **AND** 后端菜单授权」过滤（`isSuperuser` 直接全通过）；路由侧越权由
  `src/middleware/auth.ts` 跳 `/403`。
- **既有 e2e**：
  `frontend/web/e2e/{articles,certification-tipping,chat-ws,login,media,third-party-publish,users,a11y,visual}.spec.ts`。

### 4.4 子智能体的真实能力边界（本会话实测，务必遵守）

- `fleet` 任务的 `write_paths` **必须是「独立目录」**；给单个**文件**或 `tests/` 会被拒：
  `blocked: this sub-agent cannot expand write access. Needed directories: ...`
- 带 `write_paths` 的子智能体**不能执行任何 shell**（不能跑 `npm`/`nuxt typecheck`/`pytest`/`git`）。
- 因此采用的套路是：**子智能体只往自己的暂存目录写**，父代理负责搬运、合并、登记、跑校验。
- 子智能体**每次只做少量模块**（本会话一次派 11 个 → 90 分钟只完成 1 个并被 kill）。**建议每批 3–4 个**。

### 4.5 本会话那次协调的真实结果（必须知道）

`fleet-6`（11 个任务，后台运行约 90 分钟后被 kill）产物现状 —— 全部在 `frontend/web/.gen/`：

| 任务                                                                                         | 实际产物                                                                     | 状态                                        |
|--------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|-------------------------------------------|
| accessibility                                                                              | `api/accessibility.ts`、`pages/accessibility.vue`、`i18n.json`、`REPORT.md` | ✅ **完整交付**（REPORT 里逐条核对 8 端点 + 权限码 + 存疑项） |
| maintenance                                                                                | `api/maintenance.ts`、`pages/maintenance.vue`、`i18n.json`                 | ⚠️ 页面已出，**无 REPORT**，未验证                  |
| translation                                                                                | 仅 `api/translation.ts`                                                   | ⚠️ 半成品（页面未产出）                             |
| workflow                                                                                   | 仅 `api/workflow.ts`                                                      | ⚠️ 半成品（页面未产出）                             |
| edge / admin_menu / help / utility_export / oauth_screen / system_patch_a / system_patch_b | 无                                                                        | ❌ 未产出                                     |

> ⚠️ 以上中间产物**都是子智能体静态编写、未经任何编译/运行验证**（它们不能跑 shell）。收口时必须先 `npm run type-check` 把关。

---

## 5. 下一步（按优先级，可直接照做）

### 第 1 步：重启服务

```powershell
# 后端（后台）
cd X:\project\fast_blog
.venv\Scripts\python.exe main.py

# 前端（后台）
cd X:\project\fast_blog\frontend\web
npm run dev
```

健康检查：`GET http://127.0.0.1:9421/api/v3/system/health/live`

### 第 2 步：收口已交付的 `accessibility`（+ 核对 maintenance）

1. `Move-Item frontend/web/.gen/accessibility/api/accessibility.ts frontend/web/src/api/modules/accessibility.ts`
2. `Move-Item frontend/web/.gen/accessibility/pages/accessibility.vue frontend/web/src/pages/system/accessibility.vue`
3. 把 `.gen/accessibility/i18n.json` 的 `zh-CN`/`en` 两段**合并**进 `i18n/locales/{zh-CN,en}.json` 的 `admin.system`
   段（en.json 结构镜像，注意 key 对称）。
4. 在 `src/api/index.ts` 追加 `accessibilityApi` 与相关类型的导出（照文件里既有分节格式）。
5. 在 `src/utils/menus.ts` 的 `System` 组里加菜单项（如
   `{name:'AccessibilitySettings', path:'/system/accessibility', title:'无障碍设置', permission:'module_system:setting:view'}`），
   **同时在两份 locale 里加 `menu.AccessibilitySettings`**，否则 `check:i18n` 失败。
6. 跑 `npm run type-check` + `npm run check:i18n`，修掉报错。
7. `maintenance` 同样待遇，但**先核对**它引用的端点/字段（无 REPORT，风险更高）；`translation` / `workflow` 目前只有 api
   文件，可考虑与页面一起重做。
8. 收口完成后删除 `frontend/web/.gen/`（它是临时目录，不属于最终交付）。

### 第 3 步：继续 `/system` 域剩余部分（建议拆成 3 批 × 3–4 个任务）

- **新建页面类**：`translation`（27 端点，最大）、`workflow`（13）、`edge`（7）、`admin-menu`（14，注意后端 prefix 是
  `/system/admin-menu` 带连字符）、`help`（7）、`utility`（5）、`export`（3，真实 CSV 文件下载）。
- **并入既有页面类**（产出"既有文件完整替换版"）：
    - cache `items/{key}` → `system/cache.vue`
    - gdpr `compliance/*` → `system/gdpr.vue`
    - health `live/ready/site-report/web-vitals` → `system/monitoring.vue`
    - integration 的 PUT/DELETE → `system/integrations.vue`
    - log `users/{username}/{history,stats}` → `system/log.vue`
    - menu 的 items CRUD / order → `system/menu.vue`
    - permission `capabilities` → `system/permission.vue`
    - role 的 permissions 读写 → `system/role/index.vue`
    - security anomalies + report/* + blacklist delete → `system/security.vue`
    - site members/domains/default/mine/resolve → `system/sites.vue`
    - social delete + **oauth** → `system/social-accounts.vue`
    - quota + **screen-options** → `system/sites.vue` / `profile.vue`

### 第 4 步：其余域按同一套路推进

`/content`（104 缺失）→ `/commerce`（45）→ `/analytics`（37）→ `/ops`（35）→ `/mobile`（20）→ `/extension`（15）→ `/marketing`（14）→
`/chat`（13，含 web_push）→ `/gamification`（10）→ `/ai`（6，含 skill）。

### 第 5 步：每批收口后的固定动作

```powershell
cd frontend/web
npm run type-check     # 必须过
npm run check:i18n     # 必须过
npm run test:e2e       # 至少跑受影响的 spec
```

---

## 6. 约定与坑（避免重踩）

### 后端

- **业务异常 HTTP 语义**：`ForbiddenError`→403；`BadRequestError`→**200 + `{"code":400,...}`**；`NotFoundError`→404；schema
  校验失败→422。
- `DOMAIN_MODULES`（`src/api/v3/__init__.py`）是路由的**唯一事实来源**；新增 v3 模块不登记就静默不加载（只告警）。
- 数据库模型唯一权威是 `config/models.yaml`（先写 yaml → 生成 → 迁移）；**不要为加关系去重生成既有模型**。
- `.gitattributes` 强制 `*.py/*.ts/*.yml/*.json/*.md` 用 **LF**；每次编辑后建议归一化换行。
- PowerShell 发**中文 body** 必须用 UTF-8 字节：
  `-Body ([Text.Encoding]::UTF8.GetBytes($json)) -ContentType 'application/json; charset=utf-8'`；控制台看到的中文乱码多为显示问题，以
  psql 查库为准。
- psql 命令行传中文会 `invalid byte sequence` → 用 `E'\uXXXX'` 或写 `.sql` 文件 + `psql -f`。
- alembic 陷阱：先生成模板再 `upgrade head` 会只写版本号不执行 DDL → 需 `alembic stamp <上一版>` 再 `upgrade head`。

### 前端

- `i18n` 两份 locale **必须 key 对称**；新增文案要同时改 `zh-CN.json` 和 `en.json`。
- `menus.ts` 里每个 `name` 都需要 `menu.<name>` 翻译；`name` 要与后端 `admin_menus.code` 一致。
- 文案里出现**字面量花括号**（如 `{"a": "b"}`）会让 vue-i18n 编译失败 → 需写成 `{'{'}`。
- `t('x.y')` 拼错不会报错、只会把 key 渲染出来 → 靠 `npm run check:i18n` 抓。
- 普通（非 superadmin）账号要看到新菜单，需要后端 `admin_menus` + `role_admin_menus` 里有对应数据（**这条待确认/可能需要补
  seed**）。

---

## 7. 风险与提醒

1. **后端 P10 改动全部未提交**（用户自行提交）；前端接线目前**没有任何改动落到最终位置**。
2. `frontend/web/.gen/` 是临时暂存目录：`git status` 里会出现，**收口后应删除**。
3. 子智能体产物**未经编译验证**，`npm run type-check` 是唯一的把关手段；不要直接相信 REPORT 里的"已验证"字样（它们明确说了没跑）。
4. 本会话结束时 **9421 / 5173 都已停止**（后端进程被 kill）；Redis 仍在。
5. 上下文已很长：**建议新会话直接从「第 5 节 第 1 步」开始**，并改用小批次（3–4 个）派发子任务。
6. 缺失端点里**有一批是兼容别名**（`/list`、`/detail/{id}`、`/create`、`/update/{id}`、`/delete`），不要为了数字归零而接它们。

---

## 8. 相关记忆/文档

- 记忆 `p10-cleanup-and-wiring`：P10 全部 18 类的落点、验证结论、fleet 子智能体边界。
- 记忆 `no-mock-implementations`：用户强偏好 —— **永不实现/保留占位或 mock 实现**。
- 记忆 `refactor-fastapiadmin*`：v3 路径策略（REST 主路径 + 别名）、权限码三段式、`models.yaml` 唯一权威。
- 方案文档：`docs/refactor/PERMISSION_REFACTOR_PLAN.md`、`docs/refactor/PHASE2_EVALUATION.md`。
