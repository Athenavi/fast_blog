# ops/upgrade 前端接线报告

工作区：`X:\project\fast_blog`（Windows）。全部产物位于 `frontend/web/.gen/ops_upgrade/`，
**未修改仓库中任何其它文件**。

## 一、端点 → 前端映射表

| 后端端点                                               | 方法   | 权限码（`codes.py`）              | 前端 `upgradeApi` 方法                         | 承载位置（`pages/upgrade.vue`） |
|----------------------------------------------------|------|------------------------------|--------------------------------------------|---------------------------|
| `/api/v3/ops/upgrade/status`                       | GET  | `module_ops:upgrade:view`    | `upgradeApi.status()`（既有）                  | 顶部「当前版本」卡                 |
| `/api/v3/ops/upgrade/check`                        | POST | `module_ops:upgrade:execute` | `upgradeApi.check()`（既有）                   | 顶部「检查更新」按钮                |
| `/api/v3/ops/upgrade/apply`                        | POST | `module_ops:upgrade:execute` | `upgradeApi.apply()`（既有）                   | 顶部「立即升级」按钮 + 干跑结果         |
| `/api/v3/ops/upgrade/settings`                     | GET  | `module_ops:upgrade:view`    | `upgradeApi.getSettings()`（新增）             | 「升级设置」卡                   |
| `/api/v3/ops/upgrade/settings`                     | PUT  | `module_ops:upgrade:execute` | `upgradeApi.saveSettings(payload)`（新增）     | 「升级设置」卡保存按钮               |
| `/api/v3/ops/upgrade/versions`                     | GET  | `module_ops:upgrade:view`    | `upgradeApi.versions()`（新增）                | 「版本明细」卡                   |
| `/api/v3/ops/upgrade/paths`                        | GET  | `module_ops:upgrade:view`    | `upgradeApi.paths()`（新增）                   | 「路径策略」卡                   |
| `/api/v3/ops/upgrade/backups`                      | GET  | `module_ops:upgrade:view`    | `upgradeApi.backups(limit)`（新增）            | 「升级备份」卡                   |
| `/api/v3/ops/upgrade/packages`                     | GET  | `module_ops:upgrade:view`    | `upgradeApi.packages()`（新增）                | 「本地更新包」卡                  |
| `/api/v3/ops/upgrade/packages/{filename}/download` | GET  | `module_ops:upgrade:view`    | `upgradeApi.downloadPackage(filename)`（新增） | 「本地更新包」卡每行「下载」按钮          |
| `/api/v3/ops/upgrade/plan`                         | POST | `module_ops:upgrade:execute` | `upgradeApi.plan(target_version)`（新增）      | 「升级计划预览」卡「预览计划」按钮         |
| `/api/v3/ops/upgrade/execute`                      | POST | `module_ops:upgrade:execute` | `upgradeApi.execute(payload)`（新增）          | 「升级计划预览」卡内「真实升级」区         |
| `/api/v3/ops/upgrade/rollback`                     | POST | `module_ops:upgrade:execute` | `upgradeApi.rollback(payload)`（新增）         | 「升级备份」卡每行「回滚」按钮           |

承载页：`frontend/web/src/pages/ops/upgrade.vue`（既有页，**逐字保留**原有 `<script>` 逻辑
与 `<template>` 结构，仅**追加**新卡片与新逻辑）。页级权限 `module_ops:upgrade:view` 覆盖全部只读入口；
所有写操作按钮再加 `v-auth="'module_ops:upgrade:execute'"` 细化。

页面形态（追加式改动清单）：

- 顶部注释块追加一段「批次 18」说明；
- icon import 追加 `Download` / `RefreshLeft` / `View`；vue import 追加 `watch`；
  新增 `import {formatDateTime, formatFileSize} from '@/utils/format'`；
- `from '@/api'` 聚合 import 末尾追加新类型；
- `<script>` 末尾追加「升级设置 / 版本明细 / 路径策略 / 更新包 / 计划执行 / 备份回滚」逻辑段，
  并追加第二个 `onMounted` 并发加载这些数据；
- 既有「升级历史」卡之后、`</div>` 之前追加 6 张新卡片；
- 追加 `<style scoped>`（既有页原本无 style 块）。

## 二、字段来源

### 请求体（`schema.py`）

- `UpgradeSettingsPayload`：`restart_command`（≤500，可空）→ `UpgradeSettingsPayload`。留空即不自动重启。
- `UpgradeApplyPayload`：`target_version`（1..64）→ 复用于 `plan` 请求体（DTO 与 `apply` 同构）。
- `UpgradeExecutePayload`：`target_version`(1..64) / `confirm`(默认 false，**必须显式 true**) /
  `run_migration`(默认 true) / `clear_cache`(默认 true) / `stop_service`(≤100，可空) → `UpgradeExecutePayload`。
- `UpgradeRollbackPayload`：`backup_id`(1..128) / `confirm`(默认 false) → `UpgradeRollbackPayload`。
- 查询参数：`backups` 的 `limit`（default 20，1..100）。
- 路径参数：`download` 的 `filename`。

### 响应体（`service.py` / `executor.py` / `packages.py`）

- `GET /settings` ← `upgrade_service.get_settings` → `UpgradeSettingsOut`
  `{restart_command, configured}` → `UpgradeSettings`。
- `GET /versions` ← `upgrade_service.versions`（`packages.version_summary`）→ `UpgradeVersionsOut`
  `{current_version, release, database, author, backend, frontend}`；其中 `release/database/author`
  来自 `version_manager`（`Dict[str, str]`），`backend/frontend` 同为 `Dict[str, str]`，
  故类型统一为 `Record<string, string>`（`UpgradeVersionInfo`）。
- `GET /paths` ← `upgrade_executor.path_policy()` → `{allowed_prefixes, allowed_files,
  protected_dirs, protected_files, project_root, releases_dir, backup_root}` → `UpgradePathPolicy`。
- `GET /backups` ← `upgrade_service.list_backups` → `{items, total}`，item ← `upgrade_executor.list_backups`
  `{backup_id, from_version, target_version, created_at, files, path}` → `UpgradeBackupItem`。
- `GET /packages` ← `upgrade_service.packages`（`packages.list_packages`）→ `UpgradePackagesOut`
  `{items, total, releases_dir}`，item `{filename, version, size, modified_at, build_time,
  sha256_file, metadata}` → `UpgradePackageItem`。
- `GET /packages/{filename}/download` → `FileResponse`（**非 JSON 信封**，见第四节）。
- `POST /plan` ← `upgrade_service.plan`（`upgrade_executor.plan`）→ `UpgradePlanOut`
  `{target_version, package, package_detail, will_replace_count, skipped_count,
  will_replace, skipped, collisions_with_protected}` → `UpgradePlan`。
- `POST /execute` ← `upgrade_service.execute`：
    - 后台模式（默认）直接返回裸 dict `{started, target_version, in_progress, need_restart, detail}`；
    - 同步 / 完成 ← `UpgradeExecuteOut` `{dry_run, ok, from_version, target_version, backup_id,
    files_replaced, skipped, need_restart, restart_detail, steps}`，`steps` 元素 `{step, ok, detail}`。
    - 前端用同一 `UpgradeExecuteResult`（字段全可选）覆盖两种形状。
- `POST /rollback` ← `upgrade_service.rollback` → `UpgradeExecuteOut`（`steps` 单条
  `{step: 'rollback', ok: true, detail}`；`from_version/target_version` 为空）。

### 危险操作护栏（前端行为）

- **保存重启命令**：`ElMessageBox.confirm` 提示「会被真实执行」后才 PUT。
- **真实升级**：`ElMessageBox.confirm`（`type: 'error'` + 危险按钮）→ 请求体显式 `confirm: true`；
  结果卡展示 `ok` / `files_replaced` / `skipped` / `backup_id` / `need_restart` / `restart_detail`
  与逐步 `steps`（每步 `ok` 用 tag）——绝不静默。
- **回滚**：同样二次确认 + 显式 `confirm: true`；结果用同一结果卡展示。
- 所有失败（含后端 `BadRequestError`：未 `confirm`、预检未通过、版本非法、并发升级中）
  由 `request.ts` 拦截器统一弹错误提示，页面不吞错、不伪成功。

### i18n

新增键全部挂在 `admin.ops.upgrade.*`（承载页调用路径），`i18n.json` 以
`{"zh-CN":…, "en":…}` 给出双语对称的**仅新增键**，共 89 键 ×2，无字面花括号
（`planSummary` 等使用真实占位符 `{replace}`/`{skipped}`/`{n}`/`{version}`/`{id}`/`{name}`）。

## 三、未接线及原因

- **无遗漏**：controller 中本批次 9 个待接端点全部接线（settings 的 GET/PUT 计两端点，
  实际接线端点数为 10 条路由）。
- `service.py` / `executor.py` / `packages.py` 中的内部函数（`_run_execute`、`precheck_apply`、
  `verify_package`、`_strip_package_root`、`_sha256`、`_write_manifest` 等）无独立路由，不接线。
- 既有 `/apply`（干跑预检）**保持不变**：它在新页中仍作为「立即升级」按钮，与新增的
  `/plan`（文件级预演）+ `/execute`（真实执行）并存，三者后端语义不同，互不替代。
- 未新增独立路由/菜单项：沿用既有 `ops/upgrade` 承载页（任务指定）。

## 四、存疑

1. **下载端点路径参数名**：任务书写 `/packages/{name}/download`，但 controller 实际为
   `/packages/{filename}/download`（`controller.py` 第 122 行）。**以 controller 为准**，前端按
   `filename` 拼接并 `encodeURIComponent`。
2. **文件下载非 JSON 信封**：下载端点返回 `FileResponse`（`media_type=application/zip`），
   无 `{code,data,msg}` 包装，故 `downloadPackage` 用 `http.raw`（同一 axios 实例，自动注入
   Bearer token）以 `responseType: 'blob'` 拉取后触发浏览器下载，写法与既有
   `systemExport.downloadCsv` / `translation.downloadGet` 一致。**错误分支**：400（如包不存在）
   时响应体是 blob，拦截器的 `error.response.data.msg` 取不到，会退回 `error.message` 的通用提示
   ——可接受但不如 JSON 端点精确。
3. **`execute` 后台返回不在 schema 内**：`service.execute` 后台模式返回裸 dict
   （`started/target_version/in_progress/need_restart/detail`），`UpgradeExecuteOut` 并不覆盖。
   前端 `UpgradeExecuteResult` 用可选字段同时兼容两种形状，避免用 `as` 掩盖。
4. **`stop_service` 客户端不校验**：必须是 `ops/supervisor` 登记过、且登记了 stop/start 命令的
   进程名，否则后端返回 400（`entry_or_404` / 无命令），页面如实弹错。前端只做「留空即不透传」。
5. **`plan` 仅对本地包有效**：`plan`/`execute` 都要求 `releases/update_{version}.zip` 已就位；
   若只从远端 `check` 拿到版本但本地无包，`plan` 会返回 400（`verify_package` 失败），页面弹错、
   不渲染计划。远端下载不在本模块（controller 注释：远端下载由部署侧负责）。
6. **`versions` 的字典字段类型**：`release/database/author/backend/frontend` 后端声明为
   `dict`（实际内容为 `version.txt` 的字符串键值），前端按 `Record<string, string>` 渲染为键值列表；
   若未来出现非字符串值，页面仍能显示（模板不做类型断言），但类型标注需同步调整。
7. **`onExecute` 与 `onPlan` 共用 `planTarget`**：单一「目标版本」输入驱动预览与执行，避免两处不一致；
   并 `watch(checkResult)` 在 `check` 拿到 `latest_version` 后自动带入（用户可改）。
8. **`in_progress` 与后台执行**：`/status` 的 `in_progress` 来自进程内状态，多 worker 下只反映本 worker；
   执行按钮据此禁用，但跨 worker 并发护卫最终由后端 `_EXECUTING` 判定（后端会拒绝并发）。

## 五、未编译声明

**本子智能体无 shell 权限，未运行任何构建 / 类型检查（`vue-tsc` / `vite build` / eslint 均未执行）。**
以下为静态自查结论，非编译验证：

- 无 mock、无编造数据；类型字段与后端 `schema.py` / `service.py` 返回逐项对齐。
- **新增模板代码未使用 `as`**（`el-table` 的 `#default="{ row }"` 中 `row` 由 Element Plus 推断为
  `any`，直接取属性，与同域 `backup.vue` 写法一致）；既有页中原有的 `as UpgradeApplyCheck` /
  `as UpgradeHistoryItem` **逐字保留**（未改动既有行为）。
- 新增脚本无未 import 的符号；`Download`/`RefreshLeft`/`View`/`watch`/`formatDateTime`/
  `formatFileSize` 均已 import 且被使用。
- 页面 API 与类型通过 `from '@/api'` 聚合导入，**依赖下方 re-export 块先合入
  `src/api/index.ts`**，否则 `upgradeApi` 的新方法返回值类型与新增类型名不可解析
  （这是集成前提，非本产物缺陷）。
- 集成步骤（需在仓库其它文件上执行，本次未做）：
    1. 将 `api/upgrade.ts` 复制覆盖 `frontend/web/src/api/modules/upgrade.ts`；
    2. 将 `pages/upgrade.vue` 复制覆盖 `frontend/web/src/pages/ops/upgrade.vue`；
    3. 将下方 re-export 块并入 `frontend/web/src/api/index.ts`（追加到既有 upgrade 段）；
    4. 将 `i18n.json` 的 `zh-CN` / `en` 子树分别合并进
       `frontend/web/i18n/locales/zh-CN.json`、`en.json`（合并进既有 `admin.ops.upgrade` 对象）。

## 六、需父代理补的 re-export 块

`frontend/web/src/api/index.ts` 已有 `upgradeApi` 段（第 164–171 行，status/check/apply 时代）。
**保留该段原样**，在其后（或把类型并入其 `export type {…}` 列表末尾）追加以下内容：

```ts
export type {
  UpgradeBackupItem,
  UpgradeBackupList,
  UpgradeExecutePayload,
  UpgradeExecuteResult,
  UpgradePackageItem,
  UpgradePackages,
  UpgradePathPolicy,
  UpgradePlan,
  UpgradeRollbackPayload,
  UpgradeSettings,
  UpgradeSettingsPayload,
  UpgradeStep,
  UpgradeVersionInfo,
  UpgradeVersions,
} from './modules/upgrade'
```

（`upgradeApi` 的 `export {upgradeApi} from './modules/upgrade'` 已存在，无需重复。）
