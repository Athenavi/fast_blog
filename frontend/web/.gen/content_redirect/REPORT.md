# content/redirect 前端接线报告

模块：`src/api/v3/modules/content/redirect`（URL 跳转规则，SEO 能力）
产物：`frontend/web/.gen/content_redirect/`（仅此目录，未改动仓库其它文件）

## 产物与落位建议

| 本目录文件             | 建议落到仓库                                                                                                                        |
|-------------------|-------------------------------------------------------------------------------------------------------------------------------|
| `api/redirect.ts` | `frontend/web/src/api/modules/redirect.ts`（**新建**）                                                                            |
| `pages/seo.vue`   | `frontend/web/src/pages/analytics/seo.vue`（**完整替换**，逐字保留既有内容 + 新增「跳转规则」标签页）                                                   |
| `i18n.json`       | 把其中 `zh-CN` / `en` 两份键并入 `frontend/web/i18n/locales/zh-CN.json`、`en.json` 的 `admin.analytics.seo` 对象内（尚无任何 `redirect*` 键，无冲突） |
| `REPORT.md`       | 本文件                                                                                                                           |

### 为什么新建 `api/modules/redirect.ts` 而不并入 `seo.ts`

既有 `seo.ts` 全部指向 `/api/v3/analytics/seo*`（SEO **分析**），与 `content/redirect`（跳转**规则**
CRUD）不是同一后端模块、不同前缀、不同响应骨架（分析多为只读对象，跳转含分页 CRUD + 批量 + 统计 + 解析）。混入 `seoApi`
会让一个文件横跨两个模块。因此新建 `redirectApi` 独立模块，与项目「一后端模块一前端模块」的惯例一致（见 `api/index.ts`
的批次分节）。

## ① 端点 → API 函数 → 页面承载位置

承载力：`pages/analytics/seo.vue` 新增的 `name="redirect"` 标签页（`activeTab` 之外独立）。

| 后端端点（以 controller.py 为准）                     | 权限                          | API 函数（`redirectApi`） | 页面承载                                                              |
|----------------------------------------------|-----------------------------|-----------------------|-------------------------------------------------------------------|
| `GET /content/redirect`（分页列表）                | `module_analytics:seo:view` | `list(params)`        | 标签页列表：`useAdminList` 的 `fetcher`；`AdminListShell` 渲染表格/分页/空态      |
| `POST /content/redirect`                     | `module_analytics:seo:edit` | `create(payload)`     | 「新建跳转规则」对话框 `submitRedirect`（`redirectEditingId` 为空分支）            |
| `GET /content/redirect/{id}`                 | `module_analytics:seo:view` | `detail(id)`          | 行「编辑」`openRedirectEdit`：先拉详情再填表单（失败回退列表行）                         |
| `PUT /content/redirect/{id}`                 | `module_analytics:seo:edit` | `update(id, payload)` | 「编辑跳转规则」对话框 `submitRedirect`（`redirectEditingId` 非空分支）            |
| `DELETE /content/redirect/{id}`              | `module_analytics:seo:edit` | `remove(id)`          | 行「删除」`removeRedirect`（经 `redirectState.remove` 二次确认 + 删除后回退页码）    |
| `POST /content/redirect/bulk`                | `module_analytics:seo:edit` | `bulk(payload)`       | 「批量导入」对话框 `submitRedirectBulk`（`parseRedirectBulk` 解析文本为 `items`） |
| `GET /content/redirect/resolve`（**公开，无需鉴权**） | 无                           | `resolve(path)`       | 「路径解析测试」对话框 `runRedirectResolve`（命中会刷新统计）                         |
| `GET /content/redirect/stats`                | `module_analytics:seo:view` | `stats()`             | 标签页顶部统计（总数/启用/停用/累计命中）与「命中 Top 5」表；`loadRedirectStats`            |

权限码字符串形式（来自 `src/api/v3/core/permission/codes.py`）：

- `codes.SEO_VIEW = "module_analytics:seo:view"`
- `codes.SEO_EDIT = "module_analytics:seo:edit"`

页面 `definePageMeta` 用 `permission: 'module_analytics:seo:view'`（与既有 SEO 页一致）；写操作按钮用
`v-auth="'module_analytics:seo:edit'"` 控制。

## ② 字段来源逐条对照（不编造）

**`RedirectItem`（列表/详情行）** ← `service.RedirectService._out()` 返回的 dict 键，逐条一致：

```
id, from_path, to_path, status_code, is_active, hits,
source, source_reference, notes, created_by, created_at, updated_at
```

**`RedirectCreatePayload`（新建）** ← `schema.RedirectCreate`：
`from_path`(必填), `to_path`(必填), `status_code?`, `is_active?`, `notes?`

**`RedirectUpdatePayload`（更新）** ← `schema.RedirectUpdate`：同上五项，但**全部可选**（因此单独定义，未复用 Create）。

**`RedirectBatchPayload`（批量）** ← `schema.RedirectBatchRequest`：`items: RedirectCreatePayload[]`,
`overwrite?: boolean`。
**`RedirectBatchResult`** ← `service.bulk_import()` 返回：`{created, updated, skipped}`。

**`RedirectStats`** ← `service.stats()` 返回：
`total, active, inactive, total_hits, by_source: Record<string, number>, top_hits: Array<{from_path, to_path, hits}>`。

**`RedirectResolveResult`** ← `service.resolve_path()` 返回：
`matched, from_path, to_path(nullable), status_code(nullable), hits`。

**`RedirectQuery`（列表查询）** ← controller `list_redirects` 的 Query 参数：
`keyword?`, `is_active?`, `source?`（`page` / `page_size` 由 `PageQuery` 基类承载）。

**页面状态码下拉** ← `service.STATUS_CODES = (301, 302, 307, 308)`，页面常量 `REDIRECT_STATUS_CODES` 与之一致。
**来源标签** ← `source` 取值 `"manual"`（手工/批量）与 `"migration"`（迁移导入生成），见 `create_redirect` 默认 `"manual"` 与
`record_from_import` 写 `"migration"`。

## ③ 未接线端点及原因

- **别名端点按任务要求不接线**：`/list`、`/detail/{id}`、`/create`、`/update/{id}`、`/delete`（controller 内的兼容别名，权威路径已覆盖）。
  注：任务给出的 8 行端点中 `/list` 等并非 controller 的独立装饰器路径，controller 实际仅注册 8 个权威端点，均已接线。
- **无其它遗漏**：controller 注册的 8 个端点 8/8 已接（API 层 + 页面调用点均在）。

## ④ 存疑项

1. **`el-table-column` 插槽 `row` 未做类型断言**：Element Plus 默认插槽 scope 通常为 `any`，本页沿用既有 `seo.vue` 的
   `{row}` 直接取字段写法（未用 `as`）。若项目临时开启更严格的模板类型检查，`row.source` 等可能被标 `unknown`；按仓库既有页面（如
   `analytics/report.vue` 对同名栏位使用了 `row as X`）判断，现状不会报错。
2. **`useAdminList` 的 `is_active` 从 URL 还原为字符串**：`coerce()` 依据 `defaultQuery` 值类型推断，而该键默认值为
   `undefined`，故仅当用户手工在地址栏带 `?is_active=true` 时，`query.is_active` 会是字符串 `'true'`；正常点选交互始终是
   `boolean`。行为与既有 `analytics/report.vue` 完全一致。
3. **`status_code` 可选**：`redirectForm.status_code` 为 `number | undefined`，未选择时不传，后端 `_status_code()` 默认 301
   兜底。
4. **批量导入分隔符**：采用「逗号分隔，每行 `源路径,目标路径[,状态码]`，`#` 开头为注释」。若源/目标路径本身含逗号会解析异常（URL
   路径含逗号极罕见）。
5. **`detail` 失败静默**：编辑时 `detail` 取最新成功则用之，否则回退列表行，不弹错误（列表行已含全字段，回退无副作用）。
6. **`resolve` 是公开接口**：页面把它做成「路径解析测试」工具，供管理员核对规则；命中会真实累加 `hits`（后端行为），故解析后刷新统计。该工具按钮未加
   `v-auth`（接口本身不鉴权），整页仍受 `module_analytics:seo:view` 约束。

## ⑤ 未经编译验证声明

本产物由子智能体在**无 shell（不能跑 `npm` / `vue-tsc` / `eslint` / `git`）**环境下产出，**未经过任何编译、类型检查或运行时验证
**。已尽力保证：

- 页面每个标识符都有来源（import 见下方清单）；
- 一律 `import {...} from '@/api'`（未从 `@/api/modules/*` 导入）；
- 未使用 `as` 断言掩盖类型错误、未 mock/占位/编造字段或端点；
- i18n 两份 `zh-CN` / `en` 对称；
- 文件行尾为 LF。

`pages/seo.vue` 的新增 import 清单（均可从各自源解析）：
`@element-plus/icons-vue`: `Delete, Edit, Plus, Refresh, Search, Upload`；
`@/utils/feedback`: `ElMessage`；
`vue`: `reactive, ref`；
`@/api`: `redirectApi, seoApi` + 类型
`PageQuery, RedirectBatchResult, RedirectCreatePayload, RedirectItem, RedirectResolveResult, RedirectStats`；
`@/composables/useAdminList`: `useAdminList`；
`@/utils/format`: `formatDateTime`。
模板中的 `AdminListShell`、`el-*`、`$t` 均为 Nuxt/EP 自动导入/全局，无需 import（与既有 `analytics/report.vue` 一致）。

## ⑥ 需要父代理在 `frontend/web/src/api/index.ts` 追加的 re-export

建议放在 `content` 分节内（`export {pageApi} ...` 之后、`-------- analytics` 之前）：

```ts
export {redirectApi} from './modules/redirect'
export type {
  RedirectBatchPayload,
  RedirectBatchResult,
  RedirectCreatePayload,
  RedirectItem,
  RedirectQuery,
  RedirectResolveResult,
  RedirectStats,
  RedirectUpdatePayload,
} from './modules/redirect'
```

## 菜单 / i18n 事项

- **菜单无需新增**：`frontend/web/src/utils/menus.ts` 已有
  `{name: 'SeoAnalysis', path: '/analytics/seo', title: 'SEO 分析', permission: 'module_analytics:seo:view'}`
  ；跳转规则作为该页新标签页，无需新菜单项。若希望独立入口，可另加指向 `/analytics/seo` 的项（本期未做）。
- **i18n**：把 `i18n.json` 的键并入 `admin.analytics.seo`（两份语言文件同名同序，均在该段 `startAnalysis` 之后追加即可）。
