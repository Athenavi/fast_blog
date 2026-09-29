# 安全中心接线报告（frontend/web/.gen/security）

> 性质：**并入既有页面**（`src/pages/system/security.vue` + `src/api/modules/security.ts`），
> 既有内容逐字保留，**只追加**。产出物为可直接替换的完整文件。

## 文件清单

| 产出                   | 目标（父 agent 替换）                                         | 说明                                     |
|----------------------|--------------------------------------------------------|----------------------------------------|
| `api/security.ts`    | `frontend/web/src/api/modules/security.ts`             | 既有导出逐字保留，尾部追加异常检测 / 报表接口与类型            |
| `pages/security.vue` | `frontend/web/src/pages/system/security.vue`           | 既有实现逐字保留，追加「异常检测」「安全报告」两个标签页 + 阈值抽屉    |
| `i18n.json`          | 合并进 `frontend/web/i18n/locales/zh-CN.json` 与 `en.json` | 仅新增键，路径 `admin.system.security.*`，两份对称 |
| `REPORT.md`          | 本文件                                                    | —                                      |

## ① 端点 → API 函数 → 页面承载位置（6 个待补端点）

| # | 方法与路径（controller.py）                        | 权限码                           | API 函数                                         | 页面承载                                                                      |
|---|---------------------------------------------|-------------------------------|------------------------------------------------|---------------------------------------------------------------------------|
| 1 | `GET /system/security/anomalies`            | `module_system:security:view` | `securityApi.anomalies(limit?)`                | 「异常检测」标签页：统计卡 + 异常明细表 + 可疑 IP 排行；`loadAnomalies()` 触发                     |
| 2 | `PUT /system/security/anomalies/thresholds` | `module_system:setting:edit`  | `securityApi.updateAnomalyThresholds(payload)` | 「异常检测」标签页 →「调整阈值」抽屉；`submitThresholds()` 提交                               |
| 3 | `GET /system/security/report/weekly`        | `module_system:security:view` | `securityApi.weeklyReport()`                   | 「安全报告」标签页：`reportKind='weekly'` 时 `loadReport()`                          |
| 4 | `GET /system/security/report/monthly`       | `module_system:security:view` | `securityApi.monthlyReport()`                  | 「安全报告」标签页：`reportKind='monthly'` 时 `loadReport()`（含 `security_score` 评分卡） |
| 5 | `POST /system/security/report/archive`      | `module_system:security:view` | `securityApi.archiveReport(kind)`              | 「安全报告」标签页 →「归档报表」按钮；`archiveReport()` 后自动刷新历史                             |
| 6 | `GET /system/security/report/history`       | `module_system:security:view` | `securityApi.reportHistory(params)`            | 「安全报告」标签页底部：报表历史表 + 类型筛选 + 刷新；`loadHistory()`                             |

字段逐条对照的后端来源：

- 端点 1/2：`security/anomaly_service.py`（`DEFAULT_THRESHOLDS` 键、`detect()` 返回结构、`save_thresholds()` 合并返回）+
  `security/schema.py::AnomalyThresholdUpdate`。
- 端点 3/4/5：`security/report_service.py::SecurityReportService.build()`（`report_type` / `period` / `summary` /
  `audit{by_level,by_status,top_actions}` / `logins.top_failed_ips` / `trend[]` / `generated_at` / 仅 monthly 的
  `security_score{score,grade,level}`）。
- 端点 6：`report_service.py::history()`（`{reports[{id,report_name,report_type,format,generated_at}], count}`）。

## ② 对既有文件的改动逐条清单

**重要：以下改动是「逻辑上必需」的结构性调整，除此之外既有行一律逐字未动。**

### `pages/security.vue`（3 条结构性改动）

1. **`activeTab` 类型联合扩展**：
   `ref<'attempts' | 'blacklist'>('attempts')`
   → `ref<'attempts' | 'blacklist' | 'anomalies' | 'report'>('attempts')`
   原因：新增两个标签页需要新的 tab name，`el-tabs v-model` 的类型必须容纳新值。
   既有默认值、既有两个值、`stats`/`attempts`/`blacklist`/`onDeleteBlacklist`/既有模板与既有 `onMounted(loadOverview)`
   均未改动。

2. **新增两条 import（既有 import 行一字未动）**：
   ```ts
   import {reactive} from 'vue'
   import type {AnomalyItem, AnomalyResult, AnomalyThresholds, SecurityReport, SecurityReportHistoryItem, SuspiciousIp}
     from '@/api/modules/security'
   ```
   原因：`reactive` 用于阈值表单；新增响应类型从**模块路径**直接导入。
   注意 —— 这些新类型没有加入 `src/api/index.ts` 的 re-export 列表（本任务硬性边界只允许写 `.gen/security/`，不能改
   `index.ts`），
   因此页面从 `@/api/modules/security` 直接导入。若父 agent 愿意同步补 `index.ts` 的
   `export type {…} from './modules/security'`，
   可把这条改为从 `@/api` 导入（非必需，当前写法可独立工作）。
   为避免 `no-duplicate-imports` 之类 lint 噪音，也可以把 `reactive` 合并进既有
   `import {computed, onMounted, ref} from 'vue'` 一行；此处选择不改既有行、另起一行。

3. **新增一段 `<script setup>` 逻辑**（追加在既有 `onDeleteBlacklist` 之后）：
   异常检测状态与函数（`loadAnomalies`/`openThresholds`/`submitThresholds`/`typeLabel`/`severityLabel` 及映射常量）、
   报表状态与函数（`loadReport`/`archiveReport`/`loadHistory`/`toRows`）、以及新增
   `onMounted(() => { loadAnomalies(); loadHistory() })`。
   既有 `onMounted(loadOverview)` 保留；两个 `onMounted` 并存合法。

4. **模板追加**：在既有 `el-tabs` 内、`blacklist` pane 之后追加两个 `el-tab-pane`（`anomalies` / `report`），
   并在 `</el-tabs>` 之后、`</AdminPage>` 之前追加阈值 `el-drawer`。既有两个 pane、统计卡、`AdminPage` 包裹均逐字未动。

> 模板追加区仅使用既有页面已出现过的 Tailwind 语义类（`mb-*`/`grid`/`text-fg`/`text-fg-subtle` 等）与 Element Plus 组件。

### `api/security.ts`（0 条既有改动，纯追加）

- 既有 `SecurityOverview` / `LoginAttemptItem` / `LoginAttemptQuery` / `BlacklistItem` 四个接口与 `securityApi` 的
  `overview` / `attempts` / `blacklist` / `removeBlacklist` 四个方法**逐字保留**。
- 追加：类型 `AnomalyThresholds` / `AnomalyThresholdUpdate` / `AnomalyItem` / `SuspiciousIp` / `AnomalyResult` /
  `SecurityReportPeriod` / `SecurityReportSummary` / `SecurityReportTrendPoint` / `SecurityScore` / `SecurityReport` /
  `SecurityReportHistoryItem` / `SecurityReportHistoryQuery` / `SecurityReportHistoryResult`；
  `securityApi` 追加 `anomalies` / `updateAnomalyThresholds` / `weeklyReport` / `monthlyReport` / `archiveReport` /
  `reportHistory`。

### `i18n.json`（0 条既有改动，纯新增键）

- 仅含新增键，未重复定义既有 `admin.system.security.*`（如 `title`/`desc`/`tabAttempts`/`tabBlacklist`… 均不在此文件）。
- 未出现字面量花括号，故无需 `{'{'}` / `{'}'}` 转义。

## ③ 未接线端点及原因

- **报告历史的「真实文件下载」**：本批 6 个端点里**没有下载端点**。`GET /report/history` 的
  `report_service.history()` 明确「不返回 `content` 正文」，且 `report_history` 的 `format` 固定为 `json`，
  controller 也未暴露导出 / 下载路由。因此**不采用 `http.raw` + `responseType:'blob'`**——没有可下载的二进制源，
  强行套用会凭空捏造不存在的下载接口。历史仅以表格展示元数据。
- 既有端点（`/overview`、`/attempts`、`/blacklist`、`DELETE /blacklist/{id}`）已在此前批次接线，本批不动。
- `report/weekly|monthly` 在 controller 中**只有 GET**（无 POST 变体），故 API 模块未生成 `POST report/*` 之类函数。

## ④ 存疑项

1. **`report_history.report_type` 过滤值**：后端落库值为 `security_weekly` / `security_monthly`，
   而 `history()` 的入参接受 `weekly` / `monthly` 并在内部归一化（`security_` 前缀补全）。页面筛选下拉传 `weekly` /
   `monthly`，
   与 `history()` 的归一化逻辑一致；如后端未来收紧，需同步。
2. **`anomalies` 未传 `limit`**：走后端默认（`max_items`=50）。若希望页面可控，可后续在 UI 增加条数选择。
3. **阈值表单初值**：`thresholdForm` 以 `reactive<AnomalyThresholds>({} as AnomalyThresholds)` 初始化为空对象，
   打开抽屉时用后端返回的真实 `thresholds` 覆盖（`Object.assign`）。空初值不会被渲染（抽屉 `destroy-on-close` + 打开即填充）；
   未在任何地方硬编码默认阈值。
4. **`el-radio-button` 用 `value`**：Element Plus 为 `~2.14.3`（lock 2.14.5），`value` 属性写法与仓库既有页面
   （`analytics/search.vue`、`content/tag.vue`）一致。
5. **类型未走 `@/api` 聚合导出**：见 ②.2；如需统一可让父 agent 顺带补 `index.ts`。

## ⑤ 未经编译验证声明

- 本次**未执行任何构建 / 类型检查 / lint / 运行**（子智能体无 shell 权限，且硬性边界要求不执行 shell）。
- 所有「可编译」「字段一致」判断均为**静态阅读源码**得出，未经过 `nuxt typecheck` / `vue-tsc` / `pnpm build` 验证。
- 字段名逐条对照后端 `controller.py` / `schema.py` / `anomaly_service.py` / `report_service.py` 与 `codes.py`；
  端点与权限码以 `controller.py` 为准（如 `PUT /anomalies/thresholds` 的权限码为 `SETTING_EDIT`，非 `SECURITY_*`）。
- 建议父 agent 在替换后运行 `npm run type-check`（含 `vue-tsc`）与 `npm run check:i18n` 确认。
