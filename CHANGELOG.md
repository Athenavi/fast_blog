# 更新日志

本项目版本号格式为 `主.次.年份.月日`（例如 `0.8.26.0921` = 第 8
次发布、2026-09-21），遵循[语义化版本](https://semver.org/lang/zh-CN/)
思路；日志结构参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

> 条目按该版本的 git 提交归纳。历史版本的逐条变更可用 `git log <旧tag>..<新tag> --oneline` 或 GitHub Releases 查询。

## [Unreleased]

### 变更

- **后台 UI/UX 重构（第一阶段：骨架）**：
    - 新增 `styles/admin.css`：与前台同源的设计令牌（oklch 色板 + 间距/圆角/阴影），并把 **Element Plus 变量
      映射**到这些令牌（含 `color-mix` 生成的主色/语义色浅色变体），组件不再硬编码色值
    - **后台暗色模式**：复用前台的 `data-theme` 机制，同时维护 `html.dark`（Element Plus 官方暗色主题挂载点）；
      后台按需加载 EP 暗色变量与令牌样式；头部新增主题切换（浅色/深色/跟随系统），首屏内联脚本同步避免闪色
    - 共享骨架组件：`AdminPage`（页面壳）、`AdminListShell`（筛选栏/工具条/批量条/空态/骨架屏/分页）、
      `AdminEmpty`、`AdminTableSkeleton`、`AdminSelectionBar`、`AdminFormDrawer`
    - `useAdminList` 组合式：行选择与批量、URL 查询同步（刷新保持筛选）、空态/失败态判定；
      `hooks/useTable.ts` 改为它的兼容别名（既有页面零改动）
    - 侧边栏与头部改为令牌驱动（含菜单激活态、hover 色）
- **文章管理重构**：列表迁到新骨架（`/content/article`，代码移至 `pages/content/article/index.vue`），
  新增**独立编辑页** `/content/article/[id]`（`new` 为新建）—— 左侧标题/摘要/别名/Tiptap 富文本
  （复用 `RichEditor`），右侧发布设置（状态、定时发布、分类、标签、封面）与属性（置顶/推荐/隐藏/VIP/排序），
  顶部操作条（返回/预览/保存草稿/立即发布）与未保存离开确认；列表新增封面缩略图与状态标记、排序选项、
  批量发布/下架（后端无批量端点，逐条真实调用并汇报失败数）、"无数据 / 筛选无结果"两种空态
- **文档全面重构**：README.md 改为中文（英文版迁移到 README.en.md，原 README_zh.md 移除）；`docs/` 精简为
  [DEPLOYMENT.md](docs/DEPLOYMENT.md) 与 [DEVELOPMENT.md](docs/DEVELOPMENT.md) 两篇（原 `DEPLOYMENT_GUIDE.md`
  的云平台通用内容与 `docs/refactor/HANDOVER.md` 不再单独维护）；子项目 README（前端、移动端、SDK、测试、插件、主题）
  与 `CHANGELOG` / `CONTRIBUTING` / `SECURITY` / Issue 与 PR 模板一并按当前代码事实重写

### 修复

- `frontend/web`：显式声明 `vite` 依赖并重建 lockfile，修复 `npm ci --legacy-peer-deps` 下 `nuxt prepare`
  报 `Cannot find module 'vite'` 导致的安装失败（顶层 vite 升为 8.3.0，与 `@nuxt/vite-builder` 对齐）
- CI：`release.yml` 的 Node 版本由 25 调整为 22，与 `ci.yml`、前端 Dockerfile 保持一致
- `Dockerfile`：`CMD` 去掉已被移除的 `--backend fastapi` 参数（此前容器内后端会因 argparse 报错无法启动）；
  `HEALTHCHECK` 由 `/api/v2/health` 改为 `/api/v3/health`
- `Makefile`：修正 `.env_example` 拼写（实际文件为 `.env.example`）、`--backend` 参数、
  `/api/v1/health` 探活地址与 `docker-compose exec app` 服务名；`create-admin` / `routes` 目标改用 Typer CLI
- `tests/load/benchmark.js`：迁移到 API v3 的路径、分页参数（`page_size`）与 `{code, msg, data, pagination}` 响应约定
- `frontend/web/src/hooks/useTable.ts`：`confirmBox` 被误写成自递归（`await confirmBox(...)`），会让所有走
  `useTable().remove()` 的删除操作永久挂起；改为调用 `ElMessageBox.confirm`

### 新增

- **后端批量与事务端点**（消除前端逐条调用的技术债，均带权限码与启动期审计）：
    - `POST /content/article/batch/publish` 批量发布 / 撤回（`article:publish`）
    - `POST /content/comment/batch/decide` 批量通过 / 拒绝（`comment:approve`）
    - `POST /content/comment/{id}/reply` 管理端回复（以当前登录用户为作者，`comment:edit`）
    - `POST /content/media/batch/update` 批量改可见性 / 所属文件夹（`media:upload`）
    - `POST /content/category/{id}/merge` **同一事务内**迁移子分类与文章后删除源分类（`category:delete`）
    - 路由总数 650 → 655；`tests/test_v3_content.py` 补路由与鉴权断言
- **前端接入上述端点**：文章批量发布、评论批量审核与回复、媒体批量移动/公开、分类合并全部改为**单次请求**，
  不再由前端 `Promise.allSettled` 逐条调用
- **后台列表页批量升级**：除 content 域外 23 个仍用旧骨架的页面统一补上 **URL 查询同步**（刷新保持筛选）与
  **首次加载骨架屏 + 空态**；另 10 个手写列表页（extension/plugin·widget、gamification/badges·points、
  ops/notification·supervisor·webhook·backup、system/log·menu）补齐骨架屏与空态
- **前台补齐"加载失败态"**：新增 `components/site/ErrorState.vue`，并让 `ArticleListSection` 支持 `error` / `retry`
  —— 此前接口异常会被伪装成「暂无内容」，现在明确显示失败原因与重试按钮；文章列表、搜索、分类页、分类总览、
  专家列表、首页文章区、关注流全部接入（详情页保持 `createError` 语义）
- 后台**媒体库重构**（`/content/media`）：文件树（增删改文件夹）+ **网格/列表双视图**（视图选择持久化）+
  **拖拽上传**（拖到内容区任意位置，自动归入当前文件夹）+ 详情侧栏（预览/元信息/URL 复制/元数据编辑/删除）+
  批量操作（移动到文件夹、设为公开/私有、批量删除）；筛选支持关键词/类型/可见性，URL 同步
- 后台**评论管理重构**（`/content/comment`）：三个标签页对应审核状态（全部/待审核/已通过，带待审数量徽标）+
  批量通过/拒绝（后端 `batch/decide` 单次请求）+ **管理员回复**（后端 `/{id}/reply`，以当前登录用户为作者）
    + 内容编辑、垃圾评分高亮、跳转所属文章
- 后台**分类管理重构**（`/content/category`）：树形列表 + **拖拽排序**（同层内 HTML5 DnD，只对 `sort_order`
  变化的行发请求）+ **内联重命名**（点击名称就地编辑）+ **合并**（后端 `/{id}/merge` 在**同一事务**内迁移
  子分类与该分类下文章后删除源分类）+ 可见性开关
- 后台**标签管理重构**（`/content/tag`）：内联重命名（目标同名即**合并**，使用后端 `rename` 的 `merged` 结果）+
  按标签查看文章（抽屉，含状态与时间）+ 删除（提示将影响多少篇文章）+ 排序切换（文章数/名称）
- 后台 **content 域剩余页面统一到新骨架**：
    - `approvals`（审批）：重写为 `AdminPage` + `AdminListShell`，保留详情步骤条与时间线、通过/驳回；
      审批需要逐条阅读内容，因此**刻意不提供批量操作**
    - `shortcodes`（短代码）：重写为骨架 + 抽屉表单，新增「复制用法」、启用开关（行内切换）与 code 锁定提示
    - `custom-post-types`：重写为骨架 + 抽屉表单，新增 slug 锁定提示、菜单图标/位置、启用状态列
    - `page-builder` / `third-party-publish` / `collaboration`：保留既有功能结构，补 **URL 查询同步**
      （刷新保持筛选）、首次加载骨架屏与空态
    - `styles/admin.css` 新增**旧类名兼容样式**（`.page-container` / `.table-toolbar` / `.table-pagination`
      按新令牌定义），因此尚未迁移的页面（system/ops/ai/marketing/commerce/gamification 等）也自动跟随
      深浅色与自选配色，后台整体观感一致
- 后台**页面管理**（`/content/page`）：此前是 `<Placeholder>` 占位页，现支持分页列表 + 关键词/状态筛选、
  新建与编辑（标题、别名、上级页面、模板、排序、摘要、内容、SEO 三件套）、发布/撤回、单条与批量删除、
  前台链接跳转（复用既有 `pageApi`，无需后端改动）
- 后台**权限组管理**（`/system/group`）：新增 `api/modules/group.ts` 与页面 —— 树形列表、增删改、
  组成员（远程搜索用户、全量覆盖）、组角色绑定（含数据范围展示与说明）；后台菜单新增 `GroupList`，
  已通过 `seed_admin_menus --apply --grant-system-roles` 入库并授权（4 个内置角色 × 67 个菜单）
- `roles` 接口补 `data_scope` 字段（`role/schema.py::RoleOut` + `role/service.py::_to_out`），
  前端 `RoleItem` 同步 —— 便于辨识数据范围为「自定义组」的角色
- `install.py`：**跨平台交互式安装 / 初始化脚本**（仅依赖标准库）—— 环境自检 → 生成 `.env` 并写入 4 个强随机密钥
  （已存在则备份后补齐占位项）→ 检查/下载静态 ffmpeg → `docker compose up -d --build` 并等待 `/api/v3/health`
  → `alembic upgrade head` → 选装种子数据（RBAC / 后台菜单与授权 / 成长体系 / 历史批次菜单）→ 按内置角色创建用户。
  支持 `--yes` 非交互、`--mode docker|init`、`--check` 仅自检、`--install-deps` 自动装依赖
- `scripts/create_user.py`：按角色创建用户并写入 `user_role_assignments`（内置 `superadmin` / `admin` / `editor` /
  `user`），
  支持 `--password-env`（避免密码出现在进程列表）、`--list-roles`、`--force`（重置密码并覆盖角色）

### 移除

- `sdk/`（Python 与 JavaScript SDK）：两者都指向已下线的 v2 API，已整体移除；调用 v3 请直接用 HTTP 客户端
  （开发环境可在 `/api/v3/docs` 交互查看）
- `install.sh` 与 `install.bat`：由跨平台的 `install.py` 取代（原有 `.env_example`、`/api/v1/health`、
  `%RANDOM%` 弱密钥等问题一并消除）

## [0.8.26.0921] - 2026-09-21

### 新增

- **云存储备份**：S3 / 阿里云 OSS 上传（`httpx` + 自实现 SigV4 单次 PUT，可离线验签），凭据加密存储，读接口只回 `has_secret`
- **增量 / 差异备份**：以表级 `xmin` 上界做变更检测；恢复走「基准全量 → 逐表 `TRUNCATE ... CASCADE` +
  `pg_restore --data-only --table=`」
- **进程监督**：`/api/v3/ops/supervisor/*`（进程登记、三层健康检查、受控启停、日志）
- **在线升级**：预检 → 快照 → 备份 → 执行 → 回滚的完整流程
- **CDN 远端操作**：阿里云 / 腾讯云 / CloudFront，签名与端点均可用 `settings.endpoint` 覆盖
- **数据迁移**：真实导入（WordPress WXR 等）
- **多平台内容发布**：`content/third_party_publish`（接有官方 API 的平台；无官方写接口的平台如实失败）
- **群聊消息**（`chat/message`，WebSocket 实时通道）与**关注流**（`mobile/feed`、`mobile/follow`）
- **VIP**：支付订单模型 + 前台自助开通
- **打赏与提现**（`commerce/tipping`、`commerce/revenue`）
- **用户成长**：积分、勋章、专家认证（`gamification/*`）
- **系统监控中心**（`system/monitor`：总览、在线会话、告警管理）
- **内容协作**（`content/collaboration`：Yjs 协同编辑 + WebSocket）
- **报表中心**（`analytics/report`）
- 页面构建器、内容审批、GDPR 同意记录、第三方集成、安全中心、社交账号管理
- 移动端媒体库与个人投稿

### 变更

- 媒体文件服务迁移到 v3：`/api/v3/content/media/{id}/file` 与受控的 `/api/v3/assets/storage/**`（校验目录遍历 + 私密媒体鉴权）
- RBAC 重构：菜单级授权（`admin_menus` + `role_admin_menus`）、权限用户组与数据范围；权限码统一为三段式
  `module_{域}:{模块}:{动作}`
- API v3 路由注册机制与统一响应结构 `{code, msg, data, pagination}` 落地
- 前端迁移为 Nuxt 4.5 单工程（前台 SSR + 后台 CSR），Element Plus 改为按需动态加载
- i18n 体系完善：locale 两语言对称校验、菜单动态 key 校验、文案可编译校验
- PWA 与前端打包结构优化

### 移除

- 独立进程监督器模块（能力整合进 `ops/supervisor`）
- OpenAPI 基线文档

## [0.7.26.0918] - 2026-09-18

### 新增

- 两个主题插件：`magazine`（杂志风）、`modern-minimal`（现代简约）
- 完整的 SEO 能力（sitemap、meta、结构化数据）

### 变更

- 权限控制系统重构，引入三重缓存机制
- 多个模块的数据统计与缓存实现优化
- CI：Node 20 → 22（适配前端构建）

### 测试

- 更新性能测试工具与数据库会话模拟

## 版本时间线

| 版本            | 日期         |
|---------------|------------|
| `0.8.26.0921` | 2026-09-21 |
| `0.7.26.0918` | 2026-09-18 |
| `0.7.26.0906` | 2026-09-06 |
| `0.7.26.0905` | 2026-09-06 |
| `0.7.26.0904` | 2026-09-04 |
| `0.6.26.0831` | 2026-08-31 |
| `0.6.26.0824` | 2026-08-24 |
| `0.6.26.0705` | 2026-07-05 |
| `0.5.26.0617` | 2026-06-17 |
| `0.5.26.0615` | 2026-06-15 |
| `0.5.26.0613` | 2026-06-13 |
| `0.5.26.0612` | 2026-06-12 |
| `0.4.26.0610` | 2026-06-10 |
| `0.4.26.0604` | 2026-06-04 |
| `0.3.26.0603` | 2026-06-03 |
| `0.3.26.0602` | 2026-06-03 |
| `0.3.26.0601` | 2026-06-01 |
| `0.3.26.0530` | 2026-05-30 |
| `0.3.26.0525` | 2026-05-25 |
| `0.3.26.0523` | 2026-05-23 |
| `0.3.26.0521` | 2026-05-21 |
| `0.3.26.0520` | 2026-05-20 |
| `0.2.26.0519` | 2026-05-19 |

`0.2` – `0.7.26.0906` 的逐条变更未在本文件维护，请按上文方式从 git 历史或 GitHub Releases 查询。
