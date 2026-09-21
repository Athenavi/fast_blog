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

- **前台表单校验统一（D2）**：新增 `composables/useFormErrors.ts` —— 字段级校验 + `aria-invalid`
  / `aria-describedby` + 重新输入自动清除该字段错误；`login` / `register` / `profile` 从「只提示
  第一个错误」改为**逐字段定位**（此前用户不知道是哪个输入框有问题，读屏也无法关联）；
  `ToastHost` 上移到 `app.vue`，使 `layout: false` 的登录/注册页同样能收到提示
- **后台列表页迁移（B 第 1 小批，进行中）**：`system/social-accounts`、`system/gdpr`、`system/security`、
  `system/sites`、`system/sensitive-words`、`system/integrations`、`system/log` 已迁移到 `AdminPage` +
  `AdminListShell` + `useAdminList`（筛选栏、工具条、骨架、空/错态、分页统一），补齐 `desc` 与
  空态/筛选无结果文案；其余 system/ops 页面按同一范式推进。细节：
    - `system/security`、`system/integrations` 都是双标签页，两个列表各自使用列表壳（避免 Element Plus
      卡片套卡片）；`security` 的黑名单列表不写 URL，以免与「登录尝试」争用同一份 query
    - `AdminListShell` 新增 `paginate` 开关：`system/integrations` 的两个接口返回数组、不分页，
      此时隐藏分页器但保留工具条的「共 N 条」
    - `system/sites`、`system/integrations` 的筛选项/状态列此前借用了敏感词模块的文案
      （`admin.system.sensitiveWord.*`），已换成本模块自己的 key
    - `system/log` 的日期范围由原来的数组状态改为**扁平化的 `start_date` / `end_date`**，
      这样整套筛选条件都能进 URL（刷新/分享保留时间范围）；导出复用同一套判空规则
  - `system/setting` 一并迁移（接口不分页 → `paginate=false`）
  - **判定为不适用列表壳、保持原结构**：`system/permission`（折叠分组 + 内嵌表）、
    `system/cache`（多级统计卡 + 单键操作）、`system/hub`（服务器面板）、`system/menu`（树形菜单）
    —— 它们不是「筛选 + 分页表格」结构，套用列表壳会扭曲语义；其中 `permission` 换成统一空态组件
  - `system/monitoring` 是 3 个列表 + 3 个表单的复合页：三个列表全部换用 `useAdminList`，
    并把状态映射成原有变量名（避免整页重写带来的回归风险）；metric / sla 两个标签页此前**没有**
    骨架屏与空态，现补齐「骨架 / 失败态+重试 / 空态」三态。该页三个列表共用一份 `route.query`，
    因此只有原本就同步 URL 的 alert 列表保留 `syncUrl`，metric / sla 关闭以免互相覆盖筛选条件
  - `system/user`（用户管理）同样换用 `useAdminList` + 同名别名映射，并给空态补上失败态与重试
  - **统计口径修正**：`system/` 下还有子目录页面，`system/role`、`system/user` 之前被漏计
    （`system/group` 不是列表页、保持原结构）。B 第 1 小批实际为 system(16) + ops(10) = **26 页**，
    而不是先前记录的 23 页
  - **system 域收尾**：`system/role` 迁移完成（同名别名映射 + 空态失败态）
  - **ops 域首批**：`deployments`（脚本 + 执行日志双列表）、`enterprise`（许可 + 数据保留策略双列表）、
    `migrations` 迁移完成。这三个页面此前用的是**重命名解构**（`list: scriptList`、`loading: scriptLoading`
    …），因此迁移脚本按「字段 → 目标属性」逐项映射并还原出原变量名（`list→rows`、`load→reload`），
    模板无需改动；5 个列表的空态统一升级为「失败态 + 重试」
  - **ops 域第二批**：`webhook`、`notification` 迁移完成
      - `webhook` 的分页器原本**没有把页码传给后端**（`webhookApi.list()` 不带参数），是"看起来能翻页"的假象；
        接口本身返回全量，因此改用列表壳并关闭分页器（`paginate=false`），如实反映接口能力
      - `notification` 的多选、批量条交给列表壳内置能力，页面只保留批量动作本身；
        「只看未读」开关关掉时从请求里**移除** `unread_only` 字段（而不是传 `false`）
  - **ops 域收尾**（第 1 小批完成）：
      - `email`：配置列表（接口返回数组 → `paginate=false`）与订阅列表都接入列表壳；
        配置状态列此前借用敏感词模块文案，改用 `admin.common.enabled/disabled`；订阅项类型由
        内联 `{subscribed: boolean}` 换回真实类型 `EmailSubscriptionItem`
      - `backup`、`supervisor`：判定为**面板型页面**（多张统计/操作卡片 + 一个进程或备份表），
        保持原结构不套列表壳，但两者的加载函数此前只有 `try/finally`——**请求失败时界面静默显示"空"**，
        现补上失败态与重试
      - `cdn`（纯配置表单，无列表）、`upgrade`（表格是升级检查结果与历史，不是可筛选的分页列表）
        判定为**不适用**列表壳，保持原结构
  - **至此 B 第 1 小批（system 16 + ops 10 = 26 页）全部处理完毕**：
    20 页迁移到 `AdminPage` + `AdminListShell`（含 6 个双列表/多列表页），6 页判定为不适用并给出理由

### B 第 2 小批（content + extension）

- `content/page` 迁移到 `AdminPage` + `AdminListShell`：筛选（关键词 / 状态）入 URL，批量删除移入列表壳的
  批量条，空态区分「无数据」与「筛选无结果」；`failed` 由列表壳统一给出错误态与重试
- `content/page-builder` 迁移到列表壳：筛选（关键词 / 发布状态）入 URL，页内的骨架/空态/`<el-table>`/
  分页全部交给列表壳，页面只保留**列定义**与区块编辑抽屉；`failed` 由列表壳统一处理
- **判定为不套列表壳**（保持原结构）：
    - `content/category`：树形结构 + 原生拖拽排序，不是「筛选 + 分页表格」；外观已由骨架/空态统一
    - `content/media`：文件夹侧栏 + 网格/列表**双视图** + 详情抽屉，列表壳只覆盖其中一种视图；
      该页已使用 `useAdminList`，URL 同步 / 三态 / 统一工具条均已具备
    - `content/article/[id]`：文章编辑页，非列表
- `extension/block-patterns` 迁移到列表壳（页内三态/`<el-table>`/分页交给列表壳）；
  筛选标签此前借用敏感词模块文案（`admin.system.sensitiveWord.keyword/category`），
  已换成本模块自己的 key

### B 第 3 小批（marketing + analytics + commerce，进行中）

- `commerce/tipping` 迁移到 `useAdminList`，并**修掉一个真实缺陷**：表格的骨架/空态判断里混进了统计卡的
  `loading`——写法是 `v-else-if="!loading || tableLoading && !list.length"`，当统计已加载完且**表格有数据**时
  该表达式仍为真，会把有数据的表格盖成「暂无数据」。现改为只依据表格自身的 `tableLoading`，
  同时补上失败态与重试
- `marketing/ads`（2 个列表）、`marketing/vip`（3 个列表）、`marketing/forms`（2 个列表）迁移到
  `useAdminList`：
    - `ads` 是**重命名解构**（`list: adList`…），按「字段 → 目标属性」映射并还原原变量名
    - `vip` / `forms` 是**直接持有** `useTable` 返回值（模板走 `planTable.list.value`），
      改为 `useAdminList` 后把引用统一为 `…rows.value` 与 `…reload()`
    - `vip` / `forms` 的主列表空态补上失败态与重试
- `commerce/payment`（4 个列表：网关 / 交易 / 加密货币 / 税率）、`commerce/revenue`（记录 / 提现）、
  `analytics/report`（定时报表 / 历史）迁移到 `useAdminList`：三页都是**重命名解构**，
  迁移脚本从 `loading: xxxLoading` 反推前缀并生成 `xxxState` / `xxxFailed`，模板沿用原变量名
    - `payment` 的主列表空态升级为失败态 + 重试
    - `revenue` / `report` 此前**没有骨架屏与空态**，现按同一模式补上「骨架 / 失败态+重试 / 空态」三态
- **第 3 小批完成**（9 页）：7 页迁移 + 2 页非列表（`analytics/search`、`analytics/seo`）保持原结构
- 剩余待迁移（均为大页面，解构形式不一）：`content/page-builder`（无前缀解构）、
  `content/collaboration`（重命名解构，多列表）、`content/third-party-publish`（直接持有
  `useTable` 返回值，模板走 `x.list.value`）、`extension/block-patterns`、`extension/plugin`、
  `extension/theme`、`extension/widget`
- **样式块内的硬编码色收口**（补 A 包的遗漏）：上一轮只替换了 Tailwind 类名，**没有覆盖 `<style>` 块**。
  实测 8 个文件存在不随主题变化的固定色值，共 **25 处**——`#f5f7fa` / `#fafcff`（浅底）、`#909399` /
  `#6b7280` / `#9ca3af` / `#606266`（灰字）、`#409eff`（主色）、`#ebeef5`（边框）等，在暗色模式下会露出
  浅色块；现全部改为语义令牌（`--color-surface-soft` / `--color-fg-subtle` / `--color-primary` /
  `--color-line` …）。`components/admin/*` 与 `layouts/admin.vue` 里形如 `var(--admin-x, #hex)` 的
  **fallback 值属正常用法**，未改动

- **前台 UI/UX 收口（批次 1，用户确认方案 dec-9655ab5083bd2640）**：
    - **令牌收口**：24 处硬编码灰阶（`text-gray-500` / `text-gray-400` 等）改为语义令牌
      （`text-fg-muted` / `text-fg-subtle`）；`components/site/audio/*` 播放器配色、媒体灯箱遮罩、
      `.plugin-pages/*` 示例页保留硬编码并在注释中写明例外理由
    - **图片与无障碍**：24 个 `<img>` 补 `decoding="async"`（8 个列表缩略图补 `loading="lazy"`，
      PWA 图标补 `width/height`），消除解析阻塞与 CLS 风险
    - **前台内容页**：VIP 套餐列表补**失败态**（此前失败只会显示空占位）；分类筛选空态新增
      「查看全部文章」出口；专家列表与「我的勋章」空态新增「去发现」入口
    - **统一反馈**：新增 `composables/useToast.ts` + `components/site/ToastHost.vue`
      （挂载于 `layouts/default.vue`，`aria-live="polite"`，点击可关闭）；媒体库、个人资料、
      VIP 页的操作结果提示从各自的内联 `message` ref 改为统一 toast

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
- **站内通知支持批量操作**：后端新增 `POST /ops/notification/batch/read`、`POST /ops/notification/batch/delete`
  （仅限本人通知，服务层强制 `recipient == 当前用户`；已登记到写操作审计豁免清单）；前端通知页新增多选与
  批量条（批量标记已读 / 批量删除）。路由总数 655 → 657
- **前台用户中心状态统一**：`badges` / `certification` / `fans` / `points` / `tipping` 的失败态改用 `ErrorState`；
  用户中心媒体库（`/media`）补上失败提示与重试（此前加载异常没有任何反馈，只在控制台报错）
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
