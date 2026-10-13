# FastBlog P1 / P2 补齐实践方案

> 本文承接《FastBlog 与主流 CMS 差距分析》里的三档建议：P0 已落地（插件市场死链收口 + 自建
> `plugin-market-server/`、CI 纳入 239 项测试并修正失效引用、SAML 标注）。本文规划 **P1（补齐
> headless 核心短板）与 P2（生态级能力）** 的落地方案。
>
> 写法约定：**现状**均给代码证据；**方案**给到具体文件/模型/端点/权限码；**验收**必须是可执行的检查。

---

## 实施进度（截至 2026-10-12）

| 批次                | 状态                   | 交付物                                                                                                                                                                                                 |
|-------------------|----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| P1-2 对外 API Token | ✅ 完成                 | `api_tokens` 表 + 迁移 `b7f3c9e1a204`；`src/auth/api_token.py`（明文 `fbk_<prefix>_<secret>`，库中只存 Argon2 哈希）；`AuthControl` 对令牌身份做 `scopes ∩ 用户权限` 收窄（用户降权即同步失效）；`/api/v3/system/api-token` 列表/签发/撤销；29 项测试 |
| P1-1 GraphQL      | ✅ 完成                 | `/api/v3/graphql`（strawberry 0.315.4）；查询（文章/分类/标签/viewer）+ 少量写（创建/更新文章，内部仍调既有 service）；`GraphQLContext.require` 复用 REST 同一套权限判定；`CategoryLoader` 防嵌套 N+1；16 项测试                                     |
| P2-1 市场客户端        | 🟡 后端完成（前端市场页未做）     | `MarketClient` + `/api/v3/extension/plugin/market/{plugins, plugins/{slug}, updates, install}`；下载强制校验 `X-Checksum-Sha256`；未配置/不可达一律明确报错（不返回空列表冒充成功）；14 项测试                                          |
| P2-2 图片派生         | ✅ 完成（前端 `srcset` 未接） | `content/media/variants.py`（thumb/small/medium/large；`Accept` 协商 avif/webp/original；懒生成且幂等、只缩不放）；`GET /api/v3/content/media/{id}/variant/{name}`；26 项测试                                             |
| P1-3 内容建模器        | 🟡 后端完成（动态表单未做）      | `custom_post_types.fields`（迁移 `c8d2e5f7b913`）+ `field_spec.py`：10 种字段类型的定义校验与取值校验/规范化，非法输入一律 400；31 项测试                                                                                             |
| P1-4 多语言          | ✅ 完成（**方案已修正**）      | 实勘发现 `article_content` 本就是"一行一语言"，故**不新建表**：改为在现有表上做回退链（`zh-CN` → `zh` → 默认语言；链不命中退已有语言并回传 `resolved_locale`）+ `GET /api/v3/content/article/{id}/locales`；31 项测试                                    |
| P2-3 企业特性         | 🟡 2/3 完成            | ✅ 字段级权限（读侧隐藏：他人 `email`/`last_login_at` 仅本人或超管可见，**移除**而非置空；14 项测试）；✅ 审计导出（`GET /api/v3/ops/audit/export`，CSV 带 UTF-8 BOM / JSON，真实文件下载；10 项测试）；⬜ **SSO/OIDC 补全未做**（方案见 §8.2）                       |

**与原方案的差异**：P1-4 原计划"新建 `article_translations` 表 + 数据回填"，实勘后按"不推翻现有架构"改为在
`article_content` 上实现回退链 —— 避免造冗余表与回填风险。

**遗留补齐（第二批，2026-10-12 晚）**：

- ✅ **生成器缺陷修复**：`scripts/templates/sqlalchemy_model.py.jinja2` 里 `Base` 导入原本只在 `module_path` 为空时生成（*
  *子模块分支是空的**）→ 子目录模型（如 `security/api_token.py`）漏导入、实例化即 `NameError`。已改为无条件
  `from shared.models import Base`，并用 `generate-model --model ApiToken` 端到端验证：重新生成的文件含该导入，
  `test_models` + `test_api_token` 共 46 passed。
- ✅ **字段值读写接入**：`custom_fields`（EAV）此前**没有任何读写端点**（只有字段定义）。新增
  `GET/PUT /api/v3/content/custom-post-type/{type_id}/values/{content_id}`（权限 `CPT_VIEW` / `CPT_EDIT`）：写入必经
  `field_spec.validate_values`；**PUT 是全量语义**（必填缺失即 400，不静默保留旧值）；已有值走 upsert；读取按定义补齐未填字段为
  `null`。12 项测试。

**第三批（本轮）**：

- ✅ **迁移的离线一致性校验**：本机无 PostgreSQL、Docker daemon 未运行，无法实机 `upgrade`，
  改为静态比对替代（比对迁移与模型的列名/类型族、迁移链是否单头、`version.txt` 指针是否等于 head）：
  `api_tokens` 的 10 列、`custom_post_types.fields` 1 列**全部一致**，链为单头 `c8d2e5f7b913`
  且 `version.txt` 指针与其一致。**注意**：静态比对覆盖不了 SQL 层约束/默认值差异，
  上线前仍应在预发跑一次 `alembic upgrade head`。
- ✅ **「全量测试跑不完」已定位并修复**：卡点是 `tests/test_plugins.py::TestComplianceAuditPlugin`
  —— 它的 `_check_upload_security()` 为了拿一个白名单常量，去 `import src.utils.upload.public_upload`，
  而后者顶层 `import magic`（python-magic）在缺少 libmagic 的环境会**挂起**（用
  `faulthandler.dump_traceback_later(20, exit=True)` 打出业务栈才定位到）。
  已改为静态读取 `content/media/allowed_mimes.py`（顺带把审计口径从"扩展名"换成更准的"MIME 类型"）。
  **结果：全量 `pytest tests/` = 1525 passed / 5 skipped / 0 failed，3 分 49 秒跑完**；
  CI 相应新增 `test-full` job（`test-quick` 保留做快速反馈）。
- ⏭️ **图片变体上传预热**：评估后**不做** —— 当前是按需生成且已走 `asyncio.to_thread`
  （不阻塞事件循环），预热只省下"首次访问的一次编码"；而真正的后台预热需要处理任务生命周期
  （`asyncio.create_task` 无强引用会被回收）与从上传结果反推磁盘路径，风险收益比不划算。
  若要做，建议挂到项目既有 scheduler，而不是请求期后台任务。

**仍未完成（阻塞原因见括号）**：

1. ~~**SSO/OIDC 补全**（§8.2）~~ → **核实后确认无需补全**：`src/api/v3/modules/system/oauth/` 已具备
   `state` 签名校验（HMAC-SHA256 + 过期，纯函数无服务端存储）、**PKCE (S256)**、回调换令牌、
   按「登录用户 → 同邮箱 → 新建」的绑定策略、绑定列表/解绑、以及重复绑定保护。§8.2 里写的
   "缺 state/nonce/回调/绑定"其实是**被接线的源服务（v2）的缺口**，v3 已修复（该模块 docstring
   的对照表可证）。**仅 SAML 仍未实现**（无断言校验，已在 `system/integration/schema.py` 的
   字段描述中如实标注）；
2. **前端接线**：市场页 / GraphQL 客户端 / 图片 `srcset` / 动态表单 / API 令牌管理页（需 `npm run build` 验证，本轮不具备该验证条件）；
3. **图片变体上传后台批处理**（当前为按需生成，首次访问大图会有一次线程池内编码）；
4. **两份新迁移未在真实 PostgreSQL 上执行**（`b7f3c9e1a204` / `c8d2e5f7b913`，本机无 DB，上线前请在预发跑
   `alembic upgrade head`）。

---

---

## 0. 总原则

1. **不推翻现有架构**：v3 REST（882 端点）、`AuthControl` 权限码体系、`discover.py` 路由自动发现、
   `models.yaml → scripts/generate_routes.py → alembic 迁移` 的单一权威链路全部保留。
2. **模型改动一律走 `models.yaml`**：先写 yaml → `python -m scripts.generate_routes generate-model --model X`
   → 再建迁移。（既有教训：不要为加关系而重新生成既有模型，会丢手工内容。）
3. **写操作优先留在 REST**：GraphQL 先做只读层，避免双 API 的写语义长期分叉。
4. **每批交付形态**：侦察 → 实现 → 测试 → 提交；后端端点 + 测试 + 必要的前端接线。

---

## 1. 依赖关系与建议顺序

```
P1-2 API Token ──┬─→ P1-1 GraphQL（字段级鉴权复用 principal）
                 └─→ P2-1 市场客户端（第三方/CI 调用需要 token）
P1-3 内容建模器 ──→ P1-4 多语言内容（同一套内容读写路径）
P2-2 图片派生     （独立，随时可做）
P2-3 企业特性     （独立，SAML 建议最后）
```

建议执行顺序：**P1-2 → P1-1 → P2-1 → P2-2 → P1-3 → P1-4 → P2-3**

理由：API Token 是"对外开放"的认证前提（GraphQL 与市场客户端都依赖它）；P2-1 服务端已交付、
只差客户端接线，性价比最高；P1-3/P1-4 动内容模型，风险最高故靠后；SAML 复杂度最高放最后。

---

## 2. P1-1 GraphQL 只读层

**现状（证据）**：全仓无 `graphql` / `strawberry` / `graphene`（grep 为空）；API 仅 REST，
通过 `src/api/v3/core/discover.py` 扫描 `modules/{域}/{模块}/controller.py` 的顶层 `APIRouter` 挂载。

**目标**：提供 `/api/v3/graphql`，覆盖文章/分类/标签/媒体/用户的**查询**，且鉴权与 REST 同源。

**方案**

- 依赖：`strawberry-graphql[fastapi]`（与 FastAPI 原生集成，类型注解式，支持 DataLoader）。
- 落点：
    - `src/api/v3/graphql/schema.py`：`Query` 根（article/articleList/category/tag/media/me）
    - `src/api/v3/graphql/context.py`：从请求解析 principal（复用 `src/auth/auth_deps`）
    - `src/api/v3/graphql/loaders.py`：DataLoader（按 id 批量取文章/作者/分类，**必须**，否则重现 N+1）
    - `src/app.py`：在 `register_v3_routes()` 之后挂载（`include_router` 或 `GraphQLRouter`），
      仅在 `_expose_docs` 为真时暴露 GraphiQL 界面。
- 权限：每个 resolver 上声明所需权限码（与 REST 同码），失败抛 403 且**不回显内部结构**；
  fail-closed 与 `AuthControl` 一致。
- 分页：复用 `src/api/v3/common/request.py` 的 `PageQuery` 语义，输出 Connection 形状
  （`items/total/page/page_size`，与 REST 一致，减少前端两套心智）。
- 复杂度防护：限制查询深度与单请求节点数（防恶意嵌套查询打爆 DB）。

**步骤**：① 依赖 + schema 骨架 + `/graphql` 可跑通 → ② 接 DataLoader 与权限 → ③ 快照测试
→ ④（可选）少量 mutation（article create/update，内部直接调既有 service）。

**验收**

- `pytest tests/test_v3_graphql.py`：schema 快照、字段权限（无权限字段不可见/报错）、
  N+1 断言（一次 `articleList` 查询的 SQL 条数不随条目数线性增长）。
- 与 REST 同源比对：同一文章经 REST 与 GraphQL 取到的字段一致。

**风险**：双 API 维护成本（→ 只做读 + 少量写）；GraphQL 暴露面更广（→ 默认关闭 introspection，
生产仅对管理员开放 GraphiQL）。

---

## 3. P1-2 对外 API Token（scoped）

**现状（证据）**：无任何 API Key/Token 模型（`shared/models/` 下仅 `article_preview_token.py`、
`token_blacklist.py`）；对外只有用户 JWT 会话（`src/auth/auth_deps.py`）。第三方前端/CI 目前
无法在不共享用户密码的前提下调用 API。

**目标**：可创建带**权限码子集**的长期 Token，供第三方应用/CI 使用，且可审计、可撤销、可限流。

**方案**

- 模型（`config/models.yaml` 新增 → 生成 → 迁移）`api_tokens`：

  | 列 | 说明 |
    |---|---|
  | `id` | 主键 |
  | `name` | 用途备注（必填） |
  | `token_prefix` | 明文前 8 位，仅用于展示与检索 |
  | `token_hash` | **只存哈希**（argon2，项目已依赖 `argon2-cffi`） |
  | `scopes` | JSON 数组，权限码子集（如 `["module_content:article:view"]`） |
  | `user_id` | 归属用户（权限上限 ≤ 该用户当前权限） |
  | `expires_at` / `last_used_at` / `is_active` / `created_at` | 生命周期 |

- 认证落点：`src/auth/api_token.py`
    - `resolve_principal(request, db)`：`Authorization: Bearer <jwt>`（用户会话）优先，
      其次 `X-API-Key: <token>`；两者都无 → 401。
    - 返回 `Principal(user, scopes, source)`，其中 JWT 的 scopes = 该用户全部权限码。
- 授权落点：`src/api/v3/core/permission/control.py` 的 `AuthControl` 增加分支 ——
  principal 带 scopes 时按 `scopes ⊆ required`（ANY 语义保持）判定，**fail-closed**。
- 权限码（`codes.py` 追加 + `scripts/seed_rbac.py` 播种）：
  `module_system:apitoken:view` / `:create` / `:delete`。
- 管理端点：`/api/v3/system/api-token`（GET 列表 / POST 创建 / DELETE 撤销），
  创建响应**仅此一次**返回明文。
- 安全：Token 用 `hash_equals` 式常量时间比较；撤销走现有 `token_blacklist` + 权限缓存失效；
  每 token 维度限流（复用 `RateLimitMiddleware` 的 key 策略）。

**步骤**：① models.yaml + 迁移 + 模型测试 → ② 认证/授权分支 + 单测 → ③ 管理端点 + 权限码播种
→ ④ 前端（用户设置页「API 令牌」列表/创建/撤销）。

**验收**：`pytest tests/test_api_token.py` —— 越权 scope 被拒（403）、撤销后立即 401、
过期 401、明文仅出现一次、审计有记录。

**风险**：Token 长期有效（→ 强制过期时间 + 默认 90 天 + 可撤销）；权限放大
（→ scopes 必须与归属用户权限取交集）。

---

## 4. P1-3 内容建模器

**现状（证据）**：`content/custom_post_type/` 只有类型定义的 CRUD
（`name`/`slug`/`description`，见 `service.py` docstring）；字段值走 `custom_fields` 挂在内容上，
**没有字段定义与可视化建模**。

**目标**：让站长在不写代码的前提下定义字段（8–10 种类型）并用于内容编辑。

**方案（两阶段，先做阶段 1）**

- **阶段 1（推荐，低风险）**：类型定义加 `fields`（JSON Schema 数组）：
  ```json
  [{"key":"price","type":"number","label":"价格","required":true,"min":0},
   {"key":"cover","type":"media","label":"封面"},
   {"key":"tags","type":"relation","target":"tag","multiple":true}]
  ```
    - 首批类型：`text / textarea / number / boolean / select / date / media / relation / json / richtext`
    - 校验：`service.py` 在写入前做类型/必填/范围校验（不合法 400，不静默截断）
    - 存储：沿用 `custom_fields`（EAV），但为 `(post_type, field_key, post_id)` 加索引
    - 前端：`frontend/web/src/pages/content/**` 的动态表单渲染（按 `fields` 生成控件）
- **阶段 2（仅在阶段 1 性能不足时）**：每类型独立表 + 动态 DDL。**不建议现在做**：会碰
  `models.yaml` 生成器与迁移体系，且回到"改 schema 要跑迁移"的老问题。

**步骤**：① 加 `fields` 字段与校验 + 单测 → ② 前端动态表单 → ③ 导入/导出兼容（复用 WP 导入）。

**验收**：非法字段定义 400；必填缺失 400；关系字段只接受存在的目标 id；同一类型字段变更
不影响既有值。

**风险**：EAV 查询性能（→ 索引 + 限制 relation 复杂度）；字段定义变更的向后兼容
（→ 只允许新增，删除走"软删 + 隐藏"）。

---

## 5. P1-4 多语言内容

**现状（证据）**：`shared/models/article/article_content.py:33` 有 `language_code`（字段级），
但**没有 locale 维度的内容表与回退链**；另有一套**词条级**翻译（translation bundles）。

**目标**：同一篇文章可有多个语言版本，查询时按 `?locale=` + 回退链返回。

**方案**

- 新表 `article_translations`（`article_id, locale, title, slug, excerpt, content, seo_title,
  seo_description, status, updated_at`），唯一键 `(article_id, locale)`。
- 回退链：`zh-CN → zh → en（默认语言）`；实现思路复用现有 translation bundles 的 fallback
  （`system/translation/service.py` 已有回退链逻辑，直接对齐语义）。
- API：`GET /api/v3/content/article/{id}?locale=xx`；无 `locale` 时按 `Accept-Language`
  （项目已有语言识别 `languages/detect`），最终回退到默认语言并在响应里标注 `resolved_locale`。
- SEO：`hreflang_generator`（已存在）输出各 locale 的 alternate 链接。
- 迁移：把现有 `article_content.language_code` 数据回填为默认语言的 translation 行。

**步骤**：① 建表 + 回填迁移 → ② 只读 API 支持 locale/回退（**先读后写**）→ ③ 编辑侧
（编辑器按 locale 保存）→ ④ hreflang 与 sitemap 多语言。

**验收**：回退链命中顺序正确；缺某 locale 时回落默认语言且响应标明；`resolved_locale`
与 `hreflang` 一致。

**风险**：内容模型改动面大（编辑器/发布/审批都要感知 locale）；→ 分"只读先上"两步走。

---

## 6. P2-1 插件市场客户端接线（服务端已就绪）

**现状（证据）**：`plugin-market-server/`（Go + PHP，契约见其 `API.md`）已交付并通过
`go test` 与两版契约对齐检查；FastBlog 侧只做到 `marketplace.py` 的
`PLUGIN_MARKETPLACE_URL` 可配 + `remote_enabled`，**没有任何远程拉取逻辑**。

**目标**：后台能浏览/搜索/一键安装远端插件，并显示更新。

**方案（三步）**

1. **代理端点**（`src/api/v3/modules/extension/plugin/`，权限 `module_extension:plugin:view`）：
    - `GET /market/plugins`（列表/搜索：透传 keyword/category/sort/page）
    - `GET /market/plugins/{slug}`（详情）
    - `GET /market/updates`（按本地已装插件批量查更新）
    - **未配置 `PLUGIN_MARKETPLACE_URL` 或服务端不可达 → 如实返回错误状态**，
      绝不返回空列表冒充"没有插件"（与项目"不静默 mock"的既有要求一致）
    - 出站请求统一走 `src/utils/security/safe.py::validate_public_url` 的**可选**校验
      （管理员配置的内网市场应放行，故设计为可配置白名单而非硬拦）
2. **安装链路**：下载 zip → 校验响应头 `X-Checksum-Sha256` → 交给既有
   `PluginInstaller.install_from_zip()`（依赖检查 → 版本兼容 → 落地 `plugins/{slug}/`）→
   记录安装来源（市场 URL + slug + version + sha256）。
3. **前端**：`frontend/web` 插件页增加「市场」标签（浏览/搜索/安装/更新提示），
   危险动作沿用项目惯例——二次确认 + 显式 `confirm: true`。

**步骤**：① 代理端点 + 契约测试 → ② 安装链路（含校验和不匹配即拒绝）→ ③ 前端页面
→ ④（可选）签名与官方托管实例。

**验收**：用本地跑的 `plugin-market-server` 作对端做端到端（列表 → 安装 → 激活）；
校验和被篡改时**拒绝安装**；市场不可达时前端显示明确原因。

**风险**：安装插件 = 执行第三方 Python 代码（→ 二次确认 + 强制校验和 + 建议后续加插件签名）；
网络出站（→ 超时与重试上限，避免拖垮请求）。

---

## 7. P2-2 图片派生流水线

**现状（证据）**：`shared/services/media/image_tool/image_processor.py` 已有
`process_image`（crop/flip/brightness/contrast/filter/rotate/resize）、`_create_thumbnail`、
`get_image_info`、`validate_image`；media 侧有内容寻址存储、私密鉴权、EXIF 清理，交付走
`media_file_url(media_id)`。

**目标**：上传后自动派生多尺寸 + 现代格式，并在访问时按 `Accept` 协商。

**方案**

- 变体命名：`media/{hash}/{variant}.{ext}`（内容寻址天然去重；`hash` 即现有文件哈希）
- 尺寸档：`thumb 200 / small 480 / medium 800 / large 1600`（可配置，写入站点设置）
- 格式：主格式保留原图；派生 `webp`（Pillow 支持）+ `avif`（Pillow ≥ 11 内置或 `pillow-avif-plugin`）
- 访问：`GET /api/v3/content/media/{id}/{variant}`；按 `Accept` 选择格式，命中不了回落原图；
  **私密媒体仍走既有鉴权**（变体不绕过）
- 生成时机：上传响应返回后异步生成（复用现有后台任务/scheduler），避免阻塞上传；
  大图/视频复用 `video_processor.generate_multiple_resolutions` 的既有并发上限策略
- 前端：`<picture>` + `srcset`（前端已有 media 组件）

**步骤**：① 变体生成 + 幂等（同 hash 不重复生成）→ ② 交付端点 + Accept 协商 → ③ 异步化与
并发上限 → ④ 前端 srcset。

**验收**：同图重复上传不重复生成；`Accept: image/avif` 返回 avif 且 `Content-Type` 正确；
私密媒体变体未授权返回 401/403；删除媒体时变体一并清理。

**风险**：存储增长（复用 `USER_FREE_STORAGE_LIMIT` 配额与清理任务）；
AVIF 编码 CPU 高（→ 异步 + 限并发 + 可关闭）。

---

## 8. P2-3 企业特性

### 8.1 字段级权限

- **现状**：只有行级 `data_scope` + 权限码（`core/permission/scope.py`），无字段级。
- **方案**：在序列化层加字段策略（`src/api/v3/core/permission/field_policy.py`）：
  按权限码决定字段"可读/可写/隐藏"，先只做**读侧隐藏**（如 `user.email/phone`、密钥类字段
  对低权限角色隐藏）；写侧后置。
- **验收**：低权限角色响应中不含敏感字段（且不是空串冒充）；高权限不受影响。

### 8.2 SSO 真实现

- **现状**：`system/integration` 只有 SSO/LDAP **配置记录的 CRUD**（`provider_type` 含
  `oauth2/oidc/saml`），OAuth2/OIDC 有既有实现（`system/oauth`），**SAML 无断言校验**
  （已在 schema description 中如实标注）。
- **方案**：二选一或都做 ——
    - OIDC 补完（推荐先做）：`/api/v3/system/auth/sso/{provider}/callback` + 状态/Nonce 校验 +
      账户绑定策略（按 email 或 sub 绑定），复用既有 oauth service。
    - SAML：`pysaml2` 或 `python3-saml`，落点 `system/integration` + 元数据端点
      （`/sso/{provider}/metadata`）+ **断言签名/有效期/重放**校验（这三项必须做全，否则等于没有）。
- **验收**：断言过期被拒；签名不匹配被拒；同 `AssertionID` 重放被拒；未绑定账户给出明确引导。

### 8.3 审计导出

- **现状**：写操作审计已有（`core/permission/audit.py` + 审计表）。
- **方案**：`GET /api/v3/ops/audit/export?from=&to=&format=csv|json`，产出**真实文件下载**
  （`Content-Disposition`），权限码 `module_ops:audit:view`；大区间走后台任务生成 + 下载令牌。
- **验收**：导出文件可被 Excel 打开且中文正常（参照项目既有 CSV 导出做法）。

**风险**：SAML 复杂度高（→ 排最后，且必须做全签名/过期/重放三件套）；
字段级权限改动面广（→ 先只做读侧隐藏）。

---

## 9. 工作量与优先级总表

| 项              | 规模（估算）  | 依赖         | 建议批次      | 用户可见收益                |
|----------------|---------|------------|-----------|-----------------------|
| P1-2 API Token | 3–4 人日  | 无          | **第 1 批** | 第三方/CI 可安全接入          |
| P1-1 GraphQL   | 5–8 人日  | P1-2（鉴权复用） | **第 2 批** | 对比 headless CMS 的最大短板 |
| P2-1 市场客户端     | 4–6 人日  | P1-2（可选）   | **第 3 批** | 服务端已就绪，链条闭环           |
| P2-2 图片派生      | 3–5 人日  | 无          | 第 4 批     | 首屏体积/流量显著下降           |
| P1-3 内容建模器     | 5–7 人日  | 无          | 第 5 批     | 免代码扩展内容类型             |
| P1-4 多语言内容     | 6–10 人日 | P1-3（同路径）  | 第 6 批     | 多语言站点真正可用             |
| P2-3 企业特性      | 8–14 人日 | 无          | 最后        | 可进入企业采购清单             |

> 估算按"单人、含测试与前端必要接线"计；每项都可独立交付，不需要一次性做完。

---

## 10. 验收通用模板（每批都套用）

1. **测试**：`pytest tests/ -q -k "<本批关键词>"` 全绿；新增端点纳入 `tests/test_v3_route_contract.py`
   快照（`--update-snapshot` 后必须人工复核 diff）。
2. **权限**：新增端点必须有权限码，并在 `codes.py` + `seed_rbac.py` 同步；
   跑一次 `audit_permissions`（strict）确认无"无鉴权端点"。
3. **静态**：`ruff check --select E9,F63,F7,F82,F811 src shared cli`（CI 已阻断）+
   `git diff --check`。
4. **契约**：涉及前端消费的端点，同步更新 `tests/v3_route_snapshot.txt` 与 Postman collection。
5. **模型类改动**：`models.yaml → generate-model → alembic upgrade/downgrade 双向验证`。
