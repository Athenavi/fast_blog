# content/yjs 前端接线报告

## 0. 结论摘要

- 后端 `content/yjs` 的 **8 个缺失端点全部接线**，合并进既有 API 模块风格与既有页面。
- **新增 api 模块** `frontend/web/src/api/modules/yjs.ts`（导出 `yjsApi` + 全部类型），不并入 `collaboration.ts`（理由见
  §4）。
- **并入既有页面** `frontend/web/src/pages/content/collaboration.vue`（完整替换版），新增第五个标签「协同文档（yjs）」。*
  *不新建页面、不新增菜单**。
- **新增 i18n 键**：`frontend/web/i18n/locales/{zh-CN,en}.json` 的 `admin.content.collaboration.*` 下 46 个键（两份对称）。
- 需父代理在 `src/api/index.ts` 追加一段 re-export（见文末）。
- ⚠️ **全部产物未经编译验证**（本子代理无 shell 权限，无法运行 `tsc` / `vue-tsc` / `npm build`）。

---

## 1. 端点 → API 函数 → 页面承载位置 映射表

部前缀：`http` 的 `API_BASE_URL` 默认 `/api/v3`，故下表 URL 均省略前缀。

| # | 方法   | 端点（controller 权威）                                                       | API 函数                                        | 页面承载位置                                          | 权限码                                       |
|---|------|-------------------------------------------------------------------------|-----------------------------------------------|-------------------------------------------------|-------------------------------------------|
| 1 | GET  | `/content/yjs/rooms`                                                    | `yjsApi.listRooms()`                          | 「协同文档」标签 → 「本进程活跃房间」卡片（表格 + 口径 alert）           | `module_content:collaboration:view`       |
| 2 | GET  | `/content/yjs/rooms/{document_id}`                                      | `yjsApi.getRoom(id, invite?)`                 | 同上标签 → 「房间详情」`el-descriptions`（连接数 / 状态 / 版本统计） | `...:view` + 文档准入                         |
| 3 | GET  | `/content/yjs/document/{document_id}/access`                            | `yjsApi.getAccess(id, invite?)`               | 同上标签 → 「我的访问权」`el-descriptions`                 | `...:view`                                |
| 4 | GET  | `/content/yjs/document/{document_id}/collaborators`                     | `yjsApi.listCollaborators(id, invite?)`       | 同上标签 → 「协作者」描述 + 邀请表格                           | `...:view` + 文档准入                         |
| 5 | GET  | `/content/yjs/document/{document_id}/versions`                          | `yjsApi.listVersions(id, params)`             | 同上标签 → 「版本历史」分页表格                               | `...:view` + 文档准入                         |
| 6 | GET  | `/content/yjs/document/{document_id}/version/{revision_number}`         | `yjsApi.getVersion(id, n, invite?)`           | 「版本详情」`el-dialog`（`<pre>` 展示正文 + 截断提示）          | `...:view` + 文档准入                         |
| 7 | POST | `/content/yjs/document/{document_id}/snapshot`                          | `yjsApi.saveSnapshot(id, data, invite?)`      | 同上标签 → 「保存正文快照」表单（HTML / 变更说明 / force）          | `module_content:collaboration:edit` + 写准入 |
| 8 | POST | `/content/yjs/document/{document_id}/version/{revision_number}/restore` | `yjsApi.restoreVersion(id, n, data, invite?)` | 「版本历史」行内「回滚」按钮（二次确认）                            | `...:edit` + 写准入                          |

### 与任务书给出的路径差异（以 controller 为准）

- 任务书第 2 条写作 `/rooms/{room}`；**controller 实际参数名是 `document_id: int`**（`room_detail(document_id: int, ...)`
  ），且值就是文章 ID。因此 API 函数参数命名为 `documentId`，URL 为 `/content/yjs/rooms/${documentId}`。**语义未变，仅参数名以
  controller 为准。**
- 任务书第 7 条标注「路径以 controller 为准」；controller 为 `/document/{document_id}/version/{revision_number}`，与此一致。

### 查询参数 `invite`（可选）

`rooms/{id}`、`access`、`collaborators`、`versions`、`version/{n}`、`snapshot`、`restore` 七个端点都接受可选 query `invite`
（文章协作邀请码，非作者时需要；写端点要求 `permission='edit'` 的码）。页面在「协同文档」标签顶部提供 `yjsInviteCode`
输入框，空串按「未填」处理，通过 `currentInvite()` 传给所有请求。

---

## 2. 字段来源逐条对照（全部来自后端，无编造）

字段均取自 `src/api/v3/modules/content/yjs/schema.py`（响应模型）与 `service.py`（真实值来源）。

### RoomOut / RoomDetailOut（`schema.py:34-50`）

| 前端类型字段                                 | 后端字段                                   | 来源                                          |
|----------------------------------------|----------------------------------------|---------------------------------------------|
| `YjsRoomItem.document_id`              | `RoomOut.document_id`                  | `room_registry.snapshot()` 的 `document_id`  |
| `YjsRoomItem.clients`                  | `RoomOut.clients`                      | 注册表 `clients`（WS 连接数）                       |
| `YjsRoomItem.state`                    | `RoomOut.state`                        | `room_state()` 纯函数：empty / active / crowded |
| `YjsRoomItem.active`                   | `RoomOut.active`                       | `clients > 0`                               |
| `YjsRoomDetail.revision_count`         | `RoomDetailOut.revision_count`         | `article_revisions` 计数（真表）                  |
| `YjsRoomDetail.latest_revision_number` | `RoomDetailOut.latest_revision_number` | `_latest_revision()` 的 `revision_number`    |
| `YjsRoomDetail.latest_revision_at`     | `RoomDetailOut.latest_revision_at`     | `_latest_revision()` 的 `created_at`         |
| `YjsRoomDetail.content_chars`          | `RoomDetailOut.content_chars`          | `article_content.content` 字符数               |
| `YjsRoomDetail.has_content`            | `RoomDetailOut.has_content`            | 当前是否有正文                                     |

### `GET /rooms` 外层返回体（`service.py:337-352`）

| 前端字段                   | 来源                                                       |
|------------------------|----------------------------------------------------------|
| `YjsRoomsResult.rooms` | `rooms()` 的 `rooms` 数组                                   |
| `YjsRoomsResult.count` | `rooms()` 的 `count`                                      |
| `YjsRoomsResult.scope` | `rooms()` 的 `scope`（`ROOM_SCOPE_NOTE`，口径说明，页面用 alert 展示） |

### DocumentAccessOut（`schema.py:54-65`）

| 前端字段                                  | 后端字段 | 来源                                              |
|---------------------------------------|------|-------------------------------------------------|
| `document_id` / `title` / `author_id` | 同名   | `article.id` / `article.title` / `article.user` |
| `is_author`                           | 同名   | `article.user == user_id`                       |
| `allowed`                             | 同名   | `via is not None`                               |
| `can_edit`                            | 同名   | 作者或 `permission='edit'` 邀请                      |
| `via`                                 | 同名   | `author` / `invite` / `null`                    |
| `permission`                          | 同名   | `view` / `edit` / `null`                        |
| `reason`                              | 同名   | 人类可读判定依据                                        |

### AuthorOut / InviteCollaboratorOut / CollaboratorsOut（`schema.py:68-104`）

| 前端字段                                                   | 后端字段        | 来源                                    |
|--------------------------------------------------------|-------------|---------------------------------------|
| `YjsAuthor.user_id` / `username`                       | 同名          | `article.user` / `users.username`     |
| `YjsAuthor.role` / `source` / `can_edit`               | 同名          | 固定值 `owner` / `author` / `true`       |
| `YjsInviteCollaborator.invite_id`                      | `invite_id` | `collaboration_invites.id`            |
| `invite_code`                                          | 同名          | 仅作者回显，否则 `null`                       |
| `permission` / `creator_id` / `expires_at`             | 同名          | 邀请行同名列                                |
| `max_uses` / `use_count`                               | 同名          | 邀请行同名列                                |
| `usable`                                               | 同名          | `invite_is_usable()`（激活 / 未过期 / 未超次数） |
| `can_edit`                                             | 同名          | `permission == 'edit'`                |
| `YjsCollaborators.author` / `invites` / `invite_count` | 同名          | `CollaboratorsOut`                    |

### RevisionOut / RevisionDetailOut（`schema.py:107-127`）

| 前端字段                                                 | 后端字段 | 来源                                      |
|------------------------------------------------------|------|-----------------------------------------|
| `YjsRevision.id` / `article_id` / `revision_number`  | 同名   | `article_revisions` 同名列                 |
| `YjsRevision.title` / `author_id` / `change_summary` | 同名   | 修订行同名列                                  |
| `YjsRevision.author_name`                            | 同名   | `service._author_names()` 关联 `users` 得到 |
| `YjsRevision.hash_code`                              | 同名   | 正文 sha256（`content_hash()`）             |
| `YjsRevision.content_chars`                          | 同名   | `len(row.content)`                      |
| `YjsRevision.created_at`                             | 同名   | 修订行 `created_at`                        |
| `YjsRevisionDetail.content`                          | 同名   | 该版本完整正文（超 20 万字符截断）                     |
| `YjsRevisionDetail.content_is_truncated`             | 同名   | 是否截断                                    |
| `YjsRevisionDetail.stats`                            | 同名   | `html_stats()` 结果字典                     |

### SnapshotRequest / SnapshotResultOut（`schema.py:131-155`）

| 前端字段                                                          | 后端字段                             | 说明                             |
|---------------------------------------------------------------|----------------------------------|--------------------------------|
| `YjsSnapshotPayload.html`                                     | `SnapshotRequest.html`           | 富文本 HTML（完整入库）                 |
| `YjsSnapshotPayload.change_summary`                           | `SnapshotRequest.change_summary` | 最长 255                         |
| `YjsSnapshotPayload.force`                                    | `SnapshotRequest.force`          | 默认 false；true 强制新建             |
| `YjsSnapshotResult.document_id` / `saved` / `revision_number` | 同名                               | `saved=false` = 去重跳过（非失败）      |
| `YjsSnapshotResult.content_hash` / `change` / `reason`        | 同名                               | `change` 为 `diff_summary()` 结果 |

### RestoreRequest / RestoreResultOut（`schema.py:158-170`）

| 前端字段                                   | 后端字段                            | 说明                                 |
|----------------------------------------|---------------------------------|------------------------------------|
| `YjsRestorePayload.change_summary`     | `RestoreRequest.change_summary` | 可选；缺省后端用 `DEFAULT_RESTORE_SUMMARY` |
| `YjsRestoreResult.document_id`         | 同名                              | —                                  |
| `YjsRestoreResult.restored_from`       | 同名                              | 被恢复的历史版本号                          |
| `YjsRestoreResult.new_revision_number` | 同名                              | 回滚产生的新版本号                          |
| `YjsRestoreResult.content_hash`        | 同名                              | 恢复后正文 sha256                       |

---

## 3. 未接线端点及原因

- **全部 8 个端点均已接线**，无遗漏。
- 实时协同的 **WebSocket** 通道（`/content/collaboration/yjs/ws/{document_id}`）**不属于本模块**（controller docstring 明确：由
  `content/collaboration` 提供）。页面沿用既有约定，**不使用**该通道 —— 它属于文章编辑器，而非本管理页。
- 既有 `collaborationApi.listRooms` / `saveDocument`（v2 语义端点）**保持原样不动**：它们指向
  `/content/collaboration/yjs/*`（协作域），与本次新增的 `/content/yjs/*`（yjs 域）**不是同一 URL**。二者后端共用同一份
  `room_registry`，房间数据一致。

---

## 4. 存疑项 / 需父代理确认

1. **api 归属决策**：本端点归 `content/yjs` 域（URL 前缀 `/content/yjs`），与既有 `content/collaboration` 域（
   `/content/collaboration`）**不同域**，故**新建** `modules/yjs.ts`，而非并入 `collaboration.ts`。若项目要求「一页一模块」强行合并，则需改动
   `collaboration.ts`（父代理收口范围），本子代理按域隔离更清晰的原则新建。
2. **页面承载决策**「协同文档（yjs）」并入 `collaboration.vue`：yjs 与协作编辑同源（共用 room_registry、共用权限码、共用
   `collaboration_invites`），无独立菜单语义，故并入既有页面，**不新增菜单**（无须 `menu.<name>` 翻译）。
3. **`v-auth` 指令**：沿用既有页面写法 `v-auth="'module_content:collaboration:edit'"`。写操作按钮（保存快照 / 回滚）用 edit
   码；页面 `definePageMeta.permission` 为 view 码（与既有页面一致）。
4. **`admin.common.*` 复用键**：新页面使用了
   `admin.common.{name,status,actions,edit,delete,save,cancel,refresh,search,reset,enabled,disabled,yes,no,notice,loadFailed,retry,totalItems,description}` ——
   这些均为既有键（既有 `collaboration.vue` 已使用），**未在 i18n.json 中重复新增**。
5. **版本历史分页器**：`useAdminList` 的 `syncUrl` 设为 `false`（版本列表依赖 `document_id`/`invite` 动态上下文，不适合写入
   URL 全局 query）；这与同一文件里 task/invite 列表的 `syncUrl: true` 不同，为有意为之。
6. **`rooms/{id}` 参数命名**：任务书写 `{room}`，controller 实为 `document_id`（int 文章 ID）。已按 controller 处理，语义无歧义。
7. **i18n 花括号**：新增文案中的字面花括号已在 `i18n.json` 中作为 `{n}` 占位符（`snapshotSaved` / `restored` /
   `restoreConfirm`）——这些是**占位符**而非字面花括号，无需 `{'{'}` 转义。文案中**没有**需要转义的字面花括号。

---

## 5. ⚠️「未经编译验证」声明

本子代理**没有 shell 权限**，无法运行 `npm` / `tsc` / `vue-tsc` / `nuxt build` / `eslint`。因此：

- `api/yjs.ts`、`pages/content/collaboration.vue`、`i18n.json` 均为**手工编写、未经任何编译或类型检查**。
- 已尽力规避常见收口失败：所有标识符（`yjsApi`、类型、EP 图标 `Clock/Document/Upload`、`computed/onMounted/reactive/ref`、
  `ElMessage/ElMessageBox`、`useAdminList`、`useI18n`）均已 import 或定义；页面从 `@/api` 导入（非 `@/api/modules/*`）；未使用
  `as` 断言掩盖类型（模板中的 `as Xxx` 与既有页面同风格，用于 `el-table` 插槽 `row` 解类型）；`useAdminList` 泛型参数满足
  `Q extends PageQuery`。
- **合并前请父代理执行一次类型检查 / 构建**，尤其是：新增图标名是否存在于项目锁定的 `@element-plus/icons-vue` 版本；
  `i18n.json` 合并后两份 key 对称性。

---

## 6. 需父代理在 `src/api/index.ts` 追加的 re-export（可直接粘贴）

建议放在「批次 9（content 协作域）」之后、或新增一段：

```ts
// ---------------------------------------------------------------- 批次 19（content 协同文档 yjs）
export {yjsApi} from './modules/yjs'
export type {
  AccessVia,
  InvitePermission,
  RoomState,
  YjsAuthor,
  YjsCollaborators,
  YjsDocumentAccess,
  YjsInviteCollaborator,
  YjsRestorePayload,
  YjsRestoreResult,
  YjsRevision,
  YjsRevisionDetail,
  YjsRoomDetail,
  YjsRoomItem,
  YjsRoomsResult,
  YjsSnapshotPayload,
  YjsSnapshotResult,
} from './modules/yjs'
```

### 需要落位的源文件路径（父代理复制到真实位置）

| 本产物路径（`.gen/content_yjs/` 下）      | 目标仓库路径                                                                                   |
|-----------------------------------|------------------------------------------------------------------------------------------|
| `api/yjs.ts`                      | `frontend/web/src/api/modules/yjs.ts`                                                    |
| `pages/content/collaboration.vue` | `frontend/web/src/pages/content/collaboration.vue`（完整替换）                                 |
| `i18n.json`                       | 合并进 `frontend/web/i18n/locales/zh-CN.json` 与 `en.json` 的 `admin.content.collaboration` 段 |

### 菜单 / i18n 事项

- **无新增菜单**（并入既有 `content/collaboration` 页面，其菜单与权限已知）。因此无须新增 `menu.<name>` 翻译。
- 所有新增 i18n 键均在 `admin.content.collaboration.*` 命名空间下，两份语言键严格对称（46 键 × 2）。
