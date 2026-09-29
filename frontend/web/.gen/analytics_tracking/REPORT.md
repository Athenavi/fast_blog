# analytics/tracking 前端接线报告

模块：`src/api/v3/modules/analytics/tracking`（访问埋点上报 + 读侧聚合）
产物：`frontend/web/.gen/analytics_tracking/`（**仅此目录**，未改动仓库其它任何文件）
权威契约：`controller.py`（路由/权限/参数）、`schema.py`（上报入参）、`service.py`（写入与聚合返回）

## 产物与落位建议

| 本目录文件                       | 建议落到仓库                                                                                                                   |
|-----------------------------|--------------------------------------------------------------------------------------------------------------------------|
| `api/tracking.ts`           | `frontend/web/src/api/modules/tracking.ts`（**新建**）                                                                       |
| `pages/dashboard/index.vue` | `frontend/web/src/pages/dashboard/index.vue`（**完整替换**：逐字保留既有内容 + 追加权限门控的「访问统计」板块）                                        |
| `i18n.json`                 | 把其中 `zh-CN` / `en` 两份键并入 `frontend/web/i18n/locales/zh-CN.json`、`en.json` 的 `admin.analytics` 对象内（新增 `tracking` 子对象，无冲突） |
| `REPORT.md`                 | 本文件                                                                                                                      |

### 承载页选择（关键决策，需复核）

7 个读聚合端点**全部要求权限码 `module_analytics:dashboard:view`**（见 controller.py 的
`AuthControl(codes.DASHBOARD_VIEW)`）。候选承载页与其页面权限码：

| 候选页                          | 页面/菜单权限码                             | 是否匹配  | 结论     |
|------------------------------|--------------------------------------|-------|--------|
| `pages/dashboard/index.vue`  | 菜单 `module_analytics:dashboard:view` | ✅ 一致  | **采用** |
| `pages/analytics/report.vue` | `module_analytics:report:view`       | ❌ 不一致 | 未采用    |
| `pages/analytics/search.vue` | `module_analytics:search:view`       | ❌ 不一致 | 未采用    |
| `pages/analytics/seo.vue`    | `module_analytics:seo:view`          | ❌ 不一致 | 未采用    |

任务指引为「报表类优先并入既有 analytics 页」，且把 `dashboard/index.vue` 列为候选。四个候选中**只有 dashboard 页的权限码与端点要求一致
**，且该页已有成熟的「按权限门控可选板块」模式（`canViewCertification` / `canViewTipping`：无权限则不发请求、不占位）。因此把 7
个报表端点并入 `dashboard/index.vue`，复用同一模式新增 `canViewTracking` 门控。**未采用**的替代方案见 ④-1。

`api/tracking.ts` 独立建模块而不并入 `dashboard.ts` / `report.ts`：它指向 `/api/v3/analytics/tracking/*`，与
`dashboard.ts`（`/analytics/dashboard`）、`report.ts`（`/analytics/report`）不是同一后端前缀，符合项目「一后端模块一前端模块」惯例。

## ① 端点 → API 函数 → 页面承载位置

承载力：`pages/dashboard/index.vue` 新增的「访问统计」板块（`v-if="canViewTracking"`，`el-tabs` 7 个标签页 + 天数切换）。

### 读聚合（require `module_analytics:dashboard:view`）

| 后端端点（以 controller.py 为准）                                                         | 权限               | API 函数（`trackingApi`）            | 页面承载                                                                        |
|----------------------------------------------------------------------------------|------------------|----------------------------------|-----------------------------------------------------------------------------|
| `GET /analytics/tracking/traffic-sources`（`days` 1–365 默认 7；`limit` 1–100 默认 20） | `dashboard:view` | `trafficSources({days, limit})`  | 标签「流量来源」：`trafficSources` 表；`loadTracking` 首屏并行拉取                           |
| `GET /analytics/tracking/devices`（`days` 默认 7）                                   | `dashboard:view` | `devices(days)`                  | 标签「设备分布」：`deviceBreakdown` 三张表（设备/浏览器/系统）                                   |
| `GET /analytics/tracking/popular-pages`（`days` 默认 7；`limit` 默认 20）               | `dashboard:view` | `popularPages({days, limit})`    | 标签「热门页面」：`popularPages` 表                                                   |
| `GET /analytics/tracking/sessions`（`days` 默认 7）                                  | `dashboard:view` | `sessions(days)`                 | 标签「会话统计」：`sessionStats` 三张 `el-statistic`                                   |
| `GET /analytics/tracking/articles/{article_id}`（`days` 默认 30）                    | `dashboard:view` | `articleEvents(articleId, days)` | 标签「文章行为」：输入文章 ID 后 `loadArticleEvents` 按需查询；`articleEventRows` 摊平 `by_type` |
| `GET /analytics/tracking/searches`（`days` 默认 30；`limit` 默认 20）                   | `dashboard:view` | `searches({days, limit})`        | 标签「搜索统计」：`searchStats` 两张 `el-statistic` + 热门词表                             |
| `GET /analytics/tracking/ads`（`days` 默认 30）                                      | `dashboard:view` | `ads(days)`                      | 标签「广告统计」：`adStats` 三张 `el-statistic` + `top_ads` 表                          |

### 上报（可选登录，供前台访客调用）

| 后端端点                                     | 权限      | API 函数（`trackingApi`）   | 页面承载               |
|------------------------------------------|---------|-------------------------|--------------------|
| `POST /analytics/tracking/page-view`     | 无（可选登录） | `pageView(payload)`     | **不建后台页**；前台承载点见 ③ |
| `POST /analytics/tracking/event`         | 无（可选登录） | `event(payload)`        | 同上                 |
| `POST /analytics/tracking/search`        | 无（可选登录） | `search(payload)`       | 同上                 |
| `POST /analytics/tracking/ad-impression` | 无（可选登录） | `adImpression(payload)` | 同上                 |
| `POST /analytics/tracking/ad-click`      | 无（可选登录） | `adClick(payload)`      | 同上                 |

权限码字符串（`src/api/v3/core/permission/codes.py`）：`codes.DASHBOARD_VIEW = "module_analytics:dashboard:view"`。
页面 `definePageMeta` 沿用既有 `pages/dashboard/index.vue` 的写法（`layout: 'admin'` / `middleware: 'auth'` /
`title: 'menu.dashboard'`，**本页无 page 级 permission**）；「访问统计」板块用
`userStore.hasPermission('module_analytics:dashboard:view')` 做 `v-if` 门控与请求门控。

## ② 字段来源逐条对照（不编造）

### 上报入参 ← `schema.py`

- `PageViewTrackPayload` ← `PageViewTrackRequest`：`page_url`(必填,1–500)、`page_title?`(≤500)、`referrer?`(≤500)、
  `session_id?`(≤255)
- `EventTrackPayload` ← `EventTrackRequest`：`activity_type`(必填,1–100)、`target_type?`(≤50)、`target_id?`(≥1)、`details?`(
  ≤255)
- `SearchTrackPayload` ← `SearchTrackRequest`：`keyword`(必填,1–255)、`results_count?`(0–1000000,默认 0)
- `AdImpressionTrackPayload` ← `AdImpressionTrackRequest`：`ad_id`(必填,≥1)、`page_url?`(≤500)
- `AdClickTrackPayload` ← `AdClickTrackRequest`：`ad_id`(必填,≥1)、`referrer?`(≤500)

### 上报返回 ← `service.py` 各 `record_*` 的返回 dict

- `PageViewTrackResult` ← `record_page_view`：`{id, device_type, browser, platform}`（后三者来自 `parse_user_agent`，识别不到为
  null）
- `EventTrackResult` ← `record_event`：`{id, activity_type}`
- `SearchTrackResult` ← `record_search`：`{id, keyword}`
- `AdImpressionTrackResult` ← `record_ad_impression`：`{id, ad_id}`
- `AdClickTrackResult` ← `record_ad_click`：`{id, ad_id}`

### 报表返回 ← `service.py` 各聚合方法

- `TrafficSourcesResult` ← `traffic_sources`：`{period_days, total, items:[{source, views, share}]}`；`source` 为空
  referrer 时后端置 `"(direct)"`，`share` 为 `round(views/total,4)` 的 0–1 小数
- `DeviceBreakdownResult` ← `device_breakdown`：
  `{period_days, device_type:[{name,views}], browser:[...], platform:[...]}`；`name` 识别不到时后端置 `"unknown"`
- `PopularPagesResult` ← `popular_pages`：`{period_days, items:[{page_url, views, sessions}]}`（`sessions` 为 distinct
  session_id）
- `SessionStatsResult` ← `session_stats`：`{period_days, sessions, avg_views_per_session, max_views_in_session}`
- `ArticleEventsResult` ← `article_events`：`{article_id, period_days, by_type:Record<string,number>, total}`（`by_type`
  的键可能为 `"unknown"`）
- `SearchStatsResult` ← `search_stats`：
  `{period_days, total_searches, zero_result_rate, items:[{keyword, count, avg_results}]}`；`zero_result_rate` 为
  `round(zero/total,4)` 的 0–1 小数，无搜索时为 `0.0`
- `AdStatsResult` ← `ad_stats`：`{period_days, impressions, clicks, ctr, top_ads:[{ad_id, clicks}]}`；`ctr` 为
  `round(clicks/impressions,4)` 的 0–1 小数，无曝光时为 `0.0`

### 页面展示映射

- `(direct)` → i18n `admin.analytics.tracking.direct`；`unknown`（设备维度）→ `...tracking.unknown`
- 0–1 小数（`share` / `zero_result_rate` / `ctr`）→ 页面 `percent()` 统一 `(rate*100).toFixed(1)+'%'`
- `avg_results` → 页面 `Number(row.avg_results ?? 0).toFixed(1)`（与既有 `analytics/search.vue` 同写法）

## ③ 未接线端点及原因

controller.py 注册的 **12 个端点已 12/12 接线**（5 上报 + 7 报表，均在 `trackingApi` 导出）。具体：

- **5 个上报端点（page-view / event / search / ad-impression / ad-click）**：按任务「上报类若前台需要，说明承载点」的要求，*
  *只在 `trackingApi` 暴露方法，未加后台页面按钮**。它们的设计用途是**前台访客页面自动上报**，承载点应为站点前台（Nuxt）而非后台管理页：

    - `page-view`：前台页面进入时上报。建议在 Nuxt 路由中间件或前台 layout 的 `onMounted` / `afterEach` 钩子调用
      `trackingApi.pageView({page_url, page_title, referrer, session_id})`；`session_id` 由前台生成并在会话内复用（如存
      `sessionStorage`），后端据此聚合会话统计。
    - `event`：前台交互（点赞/收藏/分享/评论/滚动等）时上报
      `trackingApi.event({activity_type, target_type:'article', target_id, details})`。
    - `search`：前台搜索提交时上报 `trackingApi.search({keyword, results_count})`，供后台「搜索统计」的零结果率。
    - `ad-impression` / `ad-click`：前台广告位曝光（进入视口）与点击时上报。

  注意：`trackingApi` 走后台 axios 实例（`@/api/request`，自动带 Bearer 与后台错误提示），**前台直接复用它并不理想**。前台应改用前台的
  `$fetch` 数据层（`@/composables/useApi` 的 `apiGet`/或直接 `$fetch`）。因此本目录的 `trackingApi.pageView` 等方法*
  *更适合后台侧需要手工上报的场景**；前台接入时建议在 `useApi` 层新增等价的 POST 封装。此点见 ④-2。

- **别名/重复端点**：controller.py 未注册别名端点，无遗漏。

## ④ 存疑项

1. **承载页选择（见上文「承载页选择」）**：因无交互用户裁决，按「并入既有页 + 权限码一致 + 候选列表 + 复用既有权限门控模式」的最稳妥默认为
   `dashboard/index.vue`。**替代方案**（供父代理复核）：
    - 并入 `pages/analytics/report.vue` 的「访问统计」标签页：符合「报表中心」语义，但页面权限 `report:view` 与端点要求的
      `dashboard:view` 不一致，需额外按 `dashboard:view` 隐藏/门控该标签页；
    - 新建 `pages/analytics/tracking.vue`（权限 `module_analytics:dashboard:view`）+ 新增菜单项：模块 12
      端点独立承载最干净，但与「报表类优先并入既有页」相左，且需加菜单；
    - 拆分：`searches` 并入 `analytics/search.vue`，其余并入 dashboard：主题就近，但会拆散同一后端模块且权限码仍不一致。
      若父代理决定换承载页，`api/tracking.ts`、`i18n.json`、字段映射均可原样复用，仅需把「访问统计」模板片段搬过去。

2. **上报端点与后台 axios 客户端不匹配前台场景**：`trackingApi` 基于 `@/api/request`（后台靠 Bearer + ElMessage
   提示）。前台访客埋点应走 `@/composables/useApi` 的 `$fetch` 链路（`credentials: 'omit'`
   ）。本产物按任务「上报类若前台需要，说明承载点」的措辞，仅导出方法 + 说明承载点，未新建前台插件。若需要，可在 `.gen`
   追加前台封装（本次未做）。

3. **`pages/dashboard/index.vue` 对既有内容的两处必要改动**（非纯追加，逐字版其余部分保持一致）：
    - 合并 import：既有 `import {certificationApi, tippingApi} from '@/api'` 扩为同时导入 `trackingApi` 与 7 个报表类型；新增
      `import {Refresh, Search} from '@element-plus/icons-vue'` 与 `import {ElMessage} from '@/utils/feedback'`。
    - `onMounted(load)` 改为 `onMounted(() => { void load(); void loadTracking() })`。
      其余既有代码（模板、脚本逻辑、样式）逐字保留。

4. **`el-table` 插槽 `row` 未做类型断言**：Element Plus 默认插槽 scope 为 `any`，沿用既有页面（`dashboard/index.vue`、
   `analytics/report.vue`）的 `{ row }` 直接取字段写法（未用 `as`）。`row.source` / `row.share` / `row.name` /
   `row.avg_results` 等均为运行时字段，与后端返回键一致。

5. **`searches` 与既有 `analytics/search.vue` 数据源不同**：本模块 `/analytics/tracking/searches` 来自 `search_history`
   真表（`service.search_stats`），与既有 `searchAnalyticsApi`（`/analytics/search/*`）是**两个不同后端实现**。本产物未改动
   search.vue，仅在 dashboard 板块新增「搜索统计」标签；若认为二者重复，可后续合并。

6. **时间范围选项**：报表端点 `days` 允许 1–365。页面统一提供 7/30/90 三档（与既有 `analytics/search.vue` 一致的交互习惯）。
   `traffic-sources` / `popular-pages` / `searches` 的 `limit` 未在 UI 暴露，使用后端默认值 20。

7. **`device_breakdown` 的 `name` 为 `"unknown"` 时**：页面用 i18n 显示为「未知/Unknown」，不改写后端值。

## ⑤ 未经编译验证声明

本产物由子智能体在**无 shell（不能跑 `npm` / `vue-tsc` / `eslint` / `git`）**环境下产出，**未经过任何编译、类型检查或运行时验证
**。已尽力保证：

- 页面每个标识符都有来源（import 见下）；
- 一律从 `@/api` 导入（未从 `@/api/modules/tracking` 直接导入页面层）；`api/tracking.ts` 按既有模块惯例
  `import http from '../request'`；
- 未使用 `as` 断言掩盖类型错误、未 mock/占位/编造字段或端点；
- i18n `zh-CN` / `en` 两份键**同名同序、数量一致**；
- 文件行尾为 LF；无过程性注释。

`pages/dashboard/index.vue` 的 import 清单（均可从各自源解析）：

- `@element-plus/icons-vue`：`Refresh, Search`
- `dayjs`、`vue`：`computed, onMounted, ref`
- `@/api`：`certificationApi, tippingApi, trackingApi` + 类型
  `AdStatsResult, ArticleEventsResult, DeviceBreakdownResult, PopularPagesResult, SearchStatsResult, SessionStatsResult, TrafficSourcesResult`
- `@/api/modules/dashboard`：`dashboardApi` + 类型 `DashboardOverview, RecentArticle, RecentComment, TopArticle`（*
  *既有导入，未改**）
- `@/store/modules/user`：`useUserStore`
- `@/utils/feedback`：`ElMessage`

模板中的 `DonutChart`、`NuxtLink`、`el-*`、`$t`、`useI18n`、`useRouter` 均为 Nuxt/EP 自动导入或全局组件（与既有本文件一致，无需
import）。

`api/tracking.ts` 仅依赖 `import http from '../request'`，类型全部自包含。

## ⑥ 需要父代理在 `frontend/web/src/api/index.ts` 追加的 re-export

建议放在 `-------- 批次 8（analytics 报表）` 的 `reportApi` 之后、`-------- 批次 9` 之前：

```ts
export {trackingApi} from './modules/tracking'
export type {
  AdClickTrackPayload,
  AdClickTrackResult,
  AdImpressionTrackPayload,
  AdImpressionTrackResult,
  AdStatsResult,
  ArticleEventsResult,
  DeviceBreakdownResult,
  DeviceCountItem,
  EventTrackPayload,
  EventTrackResult,
  PageViewTrackPayload,
  PageViewTrackResult,
  PopularPageItem,
  PopularPagesResult,
  SearchStatItem,
  SearchStatsResult,
  SearchTrackPayload,
  SearchTrackResult,
  SessionStatsResult,
  TopAdItem,
  TrafficSourceItem,
  TrafficSourcesResult,
} from './modules/tracking'
```

`frontend/web/src/api/modules/tracking.ts` 由本目录 `api/tracking.ts` 落位（文件名 `tracking.ts`，import 路径 `../request`
正好解析到 `src/api/request.ts`）。

## 菜单 / i18n 事项

- **菜单无需新增**：本方案把报表并入既有 `/dashboard`（菜单项 `Dashboard`，权限 `module_analytics:dashboard:view`
  已存在），不新增路由/菜单项。若父代理改采「新建独立页」方案，则需在 `frontend/web/src/utils/menus.ts` 的 `Analytics` 分组（
  `path: '/analytics'`，`order: 4`）新增一项，形如
  `{name: 'AnalyticsTracking', path: '/analytics/tracking', title: '访问统计', permission: 'module_analytics:dashboard:view'}`。
- **i18n**：把 `i18n.json` 的 `admin.analytics.tracking` 并入两份语言文件的 `admin.analytics` 对象内（该对象现含
  `report` / `search` / `seo`，在其后追加 `tracking` 即可，键名无冲突）。`admin.analytics.tracking.refresh` 与
  `noTrafficData` 当前 UI 用到的分别是按钮图标（未用 refresh 文案）与空态文案；`refresh` 键为将来文案化保留，可保留或删去。
