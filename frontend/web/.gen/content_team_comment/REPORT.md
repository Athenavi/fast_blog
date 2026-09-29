# 团队内部评论（content/team_comment）前端接线报告

产出目录：`frontend/web/.gen/content_team_comment/`（**只读校验前**，需父代理按下述目标路径落地）。
所有产物 **未经编译验证**（本子任务无 shell 权限，见「⑤」）。

## 落地目标路径（父代理）

| 产物                       | 目标路径                                                                                 |
|--------------------------|--------------------------------------------------------------------------------------|
| `api/teamComment.ts`     | `frontend/web/src/api/modules/teamComment.ts`（**新建**，见「⑥」re-export）                  |
| `pages/team-comment.vue` | `frontend/web/src/pages/content/team-comment.vue`（**新建**，路由 `/content/team-comment`） |
| `i18n.json`              | 内容并入 `frontend/web/i18n/locales/zh-CN.json` 与 `en.json`（仅新增键）                        |

> 承载页判断：**新建页面**，不复用 `comment.vue` / `collaboration.vue`。理由：
> ① 后端 `content/team_comment` 是**独立模块**（独立路由前缀），与 `collaboration` 的 workspace 解耦（不依赖 workspace）；
> ② `collaboration.vue` 第 4 标签「团队评论」绑定的是**旧前缀** `content/collaboration/comment`（见
`modules/collaboration.ts` L171-196），
> 与本任务的 `content/team_comment` 是两个端点，硬塞会与既有区块重复且语义混淆；
> ③ `comment.vue` 是**公开文章评论**（`content/comment`），职责不同（见 `team_comment/__init__.py` L20-29 的"职责边界"）。
> 文件名用 kebab-case（对齐 `third-party-publish.vue` / `custom-post-types.vue` 的既有约定）。

---

## ① 端点 → 函数 → 页面位置映射

| HTTP 端点（controller 为准）                    | `teamCommentApi` 函数                      | 页面位置                                                                                                          |
|-------------------------------------------|------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| `GET /content/team_comment`               | `list(params)`                           | `onSearch` → `list.search()` → fetcher（`useAdminList`）；筛选栏 `content_type` / `content_id` / `include_resolved` |
| `POST /content/team_comment`              | `create(data)`                           | `submitCreate()`（发表评论对话框）；表格行「回复」按钮 `openCreate(row.id)`                                                      |
| `GET /content/team_comment/{id}`          | `detail(id)`                             | **未在页面调用**（见「③」）；API 已导出                                                                                      |
| `PUT /content/team_comment/{id}`          | `update(id, {text})`                     | `submitEdit()`（修改评论对话框）                                                                                       |
| `DELETE /content/team_comment/{id}`       | `remove(id)`                             | `onDelete(row)`（表格行删除）                                                                                        |
| `POST /content/team_comment/{id}/resolve` | `resolve(id)`                            | `onResolve(row)`（表格行「标记解决」）                                                                                   |
| `GET /content/team_comment/mentions`      | `mentions({limit, unread_only})`         | `loadMentions()`（「@ 到我的评论」对话框）                                                                                |
| `GET /content/team_comment/statistics`    | `statistics({content_type, content_id})` | `loadStatistics()`（页面顶部统计卡片 + 按作者计数表）                                                                         |

页面 `permission: 'module_content:collaboration:view'`；按钮 `v-auth` 用真实权限码：
`module_content:collaboration:create`（发表）、`module_content:collaboration:edit`（修改 / 解决）、
`module_content:collaboration:delete`（删除）。
字符串来源：`src/api/v3/core/permission/codes.py` L278-281（`COLLABORATION_VIEW/CREATE/EDIT/DELETE`）。

---

## ② 字段来源逐条对照（前端 interface ↔ 后端）

### `TeamCommentOut`（`schema.TeamCommentOut`，字段由 `service._row_to_dict` 填充）

| 前端字段           | 类型                 | 后端来源                                                                           |
|----------------|--------------------|--------------------------------------------------------------------------------|
| `id`           | `number`           | `schema.TeamCommentOut.id` ← `team_comments.id`（`BigInteger` PK）               |
| `content_type` | `string \| null`   | ← `team_comments.content_type`（`String(50)`，nullable）                          |
| `content_id`   | `number \| null`   | ← `team_comments.content_id`（`BigInteger`）                                     |
| `author_id`    | `number \| null`   | ← `team_comments.author_id`（FK `users.id`）                                     |
| `author_name`  | `string \| null`   | `service._author_names`：`users.username`（表无该列，读取时补齐）                           |
| `parent_id`    | `number \| null`   | ← `team_comments.parent_id`（FK 自引用）                                            |
| `text`         | `string \| null`   | ← `team_comments.text`（`Text`；写入前 `html.escape`）                               |
| `mentions`     | `number[]`         | `service.parse_mentions`：`team_comments.mentions`（`String(500)` JSON 串）解析为整数列表 |
| `is_resolved`  | `boolean`          | ← `team_comments.is_resolved`（`Boolean`，`bool()` 归一）                           |
| `resolved_by`  | `number \| null`   | ← `team_comments.resolved_by`                                                  |
| `resolved_at`  | `string \| null`   | ← `team_comments.resolved_at`（`DateTime`）                                      |
| `created_at`   | `string \| null`   | ← `team_comments.created_at`                                                   |
| `updated_at`   | `string \| null`   | ← `team_comments.updated_at`                                                   |
| `children`     | `TeamCommentOut[]` | `service.build_threads` 组装的子回复（默认 `[]`）                                        |

### 请求体

- `TeamCommentCreatePayload`（`schema.TeamCommentCreate`）：`content_type`(1..50) / `content_id` / `text`(1..5000) /
  `parent_id?` / `mentions?: number[]`。
- `TeamCommentUpdatePayload`（`schema.TeamCommentUpdate`）：仅 `text`(1..5000)。
- `TeamCommentListQuery`（controller `list_team_comments` Query）：`content_type`(必填) / `content_id`(必填) → 前端
  `content_id` 用可选 + 空则不发请求；`include_resolved`(默认 true) / `page` / `page_size`。`page`/`page_size` 由
  `useAdminList` 注入。
- `TeamCommentMentionsQuery`（controller `list_my_mentions` Query）：`limit`(1..200，默认 20) / `unread_only`(默认
  false，语义=未解决)。
- `TeamCommentStatisticsQuery`（controller `comment_statistics` Query）：`content_type?` / `content_id?`。

### 统计（`schema.TeamCommentStatisticsOut` / `AuthorCountOut`）

`TeamCommentStatistics`：`total_comments` / `resolved_comments` / `unresolved_comments` /
`by_author: TeamCommentAuthorCount[]`；
`TeamCommentAuthorCount`：`author_id` / `count`。来源：`service.summarize`。

### `team_comments` 表（`shared/models/comment/team_comment.py`）

列：`id` / `content_type` / `content_id` / `author_id` / `parent_id` / `text` / `mentions` / `is_resolved` /
`resolved_by` / `resolved_at` / `created_at` / `updated_at`。
**未新建任何表 / ORM 模型**（与 `team_comment/__init__.py` L5-9 一致）。

---

## ③ 未接线端点及原因

- **`GET /content/team_comment/{id}`（`teamCommentApi.detail`）**：API 层已完整接线并导出，但页面**未调用**——评论树列表接口（
  `GET /content/team_comment`）已返回每条评论（含 `children`）的全部字段，单条详情在页面上无独立入口。为避免"接了不用"
  的臆造入口，未在 UI 添加按钮；如需「查看单条详情」弹窗，可后续在 `onResolve`/行操作中接入 `detail`。

其余 7 个端点全部接线。

---

## ④ 存疑项

1. **`content_type` 取值域**：后端为自由字符串（`String(50)`，示例 `article` / `page`）。前端筛选下拉硬编码
   `['article','page','block','product']`，其中 `block` 来自 ORM 注释、`product` 为常见内容类型推测；若后端有权威枚举，应替换。发表评论对话框同用该列表。
2. **`unread_only` 语义**：后端明确 `unread_only` = **未解决**（既有表无独立已读状态，见 `__init__.py` L42-44）。前端 i18n
   文案「仅未解决」据此命名，未称「未读」。
3. **列表分页口径**：`list_for_content` 仅对**顶层评论**分页，子回复随 roots 批量返回（`total` 为顶层数）。页面表格按
   `children` 渲染树、分页器反映顶层数。
4. **写操作授权**：后端 service 层强制「作者或管理员」，前端仅以权限码 `v-auth` 做提示性禁用，**不**在页面判断"是否作者"
   （前端不持有 `author_id == 当前用户` 的可靠上下文）。
5. **页面 `content_id` 校验**：列表接口要求 `content_id` 必填，`useAdminList` 的 `immediate:false` + fetcher 空值返回空页；
   `onSearch` 在缺 `content_id` 时仅提示不请求。

---

## ⑤ 未经编译验证声明

本子任务**无 shell / 无构建权限**，产物**未经过 `vue-tsc` / `eslint` / `nuxt build` 编译验证**，也未在运行态联调。已按既有代码风格（
`comment.vue` / `collaboration.vue` / `useAdminList.ts`）逐处对齐以下约束：

- 页面所有 api 调用与类型一律 `from '@/api'`（`PageResult` 类型 `from '@/api/types'`，与 `collaboration.vue` 一致）；
- 未使用 `as` 断言掩盖类型错误（仅对 el-table 插槽的 `any` 行做 `row as TeamCommentOut` 标注，属既有约定）；
- `context` 变量与 icons 均有 import 来源；`http.page/get/post/put/delete` 均来自 `api/request.ts`；
- 行尾 LF。

**仍建议父代理在落地后执行类型检查**。

---

## ⑥ 需要父代理在 `frontend/web/src/api/index.ts` 追加的 re-export 代码块

> 建议插入到「批次 18（ops 进程监督）」块之后、或紧邻 `content` 分节。**命名已避开既有导出**：
> 现有 `TeamCommentItem` / `CommentPayload` 来自 `./modules/collaboration`，本模块一律用 `TeamComment*` 前缀，**无冲突**。

```ts
// ---------------------------------------------------------------- content（团队内部评论 team_comment）
export {teamCommentApi} from './modules/teamComment'
export type {
  TeamCommentAuthorCount,
  TeamCommentCreatePayload,
  TeamCommentListQuery,
  TeamCommentMentionsQuery,
  TeamCommentOut,
  TeamCommentStatistics,
  TeamCommentStatisticsQuery,
  TeamCommentUpdatePayload,
} from './modules/teamComment'
```

### 其它需父代理同步的事项

1. **i18n 合并**：把 `i18n.json` 的 `zh-CN.admin.content.teamComment` 与 `en.admin.content.teamComment` 两个对象分别并入
   `i18n/locales/zh-CN.json` 与 `en.json` 的 `admin.content` 下（`en.json` 结构同级，参考 L2764
   `admin.content.collaboration`）。两份键**完全对称**。
2. **菜单项**（`frontend/web/src/utils/menus.ts`，`Content.children` 内，参考 L72-77 `Collaboration` 项）：

   ```ts
   {
     name: 'TeamComment',
     path: '/content/team-comment',
     title: '团队评论',
     permission: 'module_content:collaboration:view'
   },
   ```
3. **后端路由登记**（非前端，提示）：`team_comment/__init__.py` L51-52 明确本模块需在 `src/api/v3/__init__.py` 的
   `DOMAIN_MODULES['/content']` 登记 `team_comment` 才会加载；该文件为本次任务禁改项，若尚未登记，前端请求会 404。
