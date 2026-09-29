# gamification/points 前端接线 REPORT

把后端 v3 `gamification/points` 模块**剩余 4 个缺失端点**接到前端。产物只落在
`frontend/web/.gen/gamification_points/` 下；未修改仓库任何其它文件。

## 0. 文件映射（产物 → 仓库落点）

| 产物                                          | 覆盖的既有文件                                                | 说明                                    |
|---------------------------------------------|--------------------------------------------------------|---------------------------------------|
| `.gen/gamification_points/api/points.ts`    | `frontend/web/src/api/modules/points.ts`               | 完整替换：逐字保留原内容，仅追加类型与方法                 |
| `.gen/gamification_points/pages/points.vue` | `frontend/web/src/pages/gamification/points.vue`       | 完整替换：逐字保留原内容，仅改 2 行 import 并追加 4 块 UI |
| `.gen/gamification_points/i18n.json`        | 合并进 `frontend/web/i18n/locales/zh-CN.json` 与 `en.json` | 只含新增键，双语对称                            |

> **落点判断（重要）**：任务把「既有 `src/api/modules/points.ts` 与
> `src/pages/gamification/points.vue`」列为已接 11 个端点、需要完整替换的对象。
> 因此 `pages/points.vue` 对应的是**后台积分管理页** `src/pages/gamification/points.vue`，
> 而**不是**同名前台页 `src/pages/points.vue`（后者仅作为参考，未产出替换）。
> 依据：`award` 需要权限码 `module_gamification:points:edit`、页面用 Element Plus 表单 +
> `ElMessageBox` 二次确认，符合后台页（`layout:'admin'`）的既有技术栈；前台页刻意不加载 EP。
> 详见「4. 存疑」。

## 1. 映射表（端点 → API 方法 → 页面位置）

| 后端端点（controller.py）                              | API 方法（api/points.ts）                             | 页面位置（pages/points.vue）             | 权限                                |
|--------------------------------------------------|---------------------------------------------------|------------------------------------|-----------------------------------|
| `POST /api/v3/gamification/points/award`         | `award(userId, amount, reason?)` → `PointsLedger` | 「手动奖励（award）」卡片：`submitAward()`    | `module_gamification:points:edit` |
| `GET  /api/v3/gamification/points/me`            | `me(recent = 10)` → `PointsMeResult`              | 「我的积分账户」卡片：`loadAuxiliary()`       | 仅认证                               |
| `GET  /api/v3/gamification/points/ranking`       | `ranking(limit = 20)` → `LeaderboardItem[]`       | 「排行榜（ranking）」卡片：`loadAuxiliary()` | 公开                                |
| `GET  /api/v3/gamification/points/level/{score}` | `level(score)` → `PointsLevel`                    | 「等级详情」卡片：`queryLevel()`            | 公开                                |

**路径以 controller 为准**：任务描述写作 `level/{level}`，controller 实为
`@router.get("/level/{score}")`（`score: int`，纯函数 `level_for`）。因此前端用
`/gamification/points/level/${score}`。

**未新增同义方法**：

- `ranking` 与既有 `leaderboard` 是**同数据、同结构**（controller 里 `ranking` 直接
  调用 `points_service.leaderboard`，`limit` 默认 20 / 范围 1~100 一致）。二者是**别名端点**，
  都保留（既有 `leaderboard` 不动；`ranking` 是本次待接端点，如实接线）。
- 页面**只有一个**排行榜卡片（用 `ranking`），没有为 `leaderboard` 再建一块，避免重复 UI。
- `me` 与既有 `mine` **不是**同义：`mine` 只返回 `PointsAccount`；`me` 返回
  `{account, level, recent_transactions}`（多出「当前等级」与「最近流水」）。两者返回结构不同，
  `mine` 保留供既有调用方（`src/pages/points.vue` 用），`me` 为本次新增。
- `award` 与既有 `grant` 是**同实现别名**（controller 里均为 `points_service.grant(...)`，
  写 `admin_grant` 流水、返回 `PointsLedger`）。既有 `grant`/`deduct` 表单**逐字保留未动**；
  `award` 是本次待接端点，在页面**新增独立卡片**并带**二次确认**，不改造既有表单。

## 2. 字段来源（字段 → schema / service 出处）

| 前端字段                                 | 来源                                                                                                                                                               |
|--------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `PointsLevel.*`                      | `service.level_for()` 返回 dict：`score, level, name, min_score, next_level, next_level_name, next_level_score, points_to_next, progress`（纯函数，无 DB 依赖；`LEVELS` 阈值表） |
| `PointsMeResult.account`             | `PointsAccountOut`（`schema.py`）：`user_id, balance, total_earned, total_spent, last_checkin_at, checked_in_today, updated_at`                                     |
| `PointsMeResult.level`               | `service.level_for(int(row.total_earned or 0))`（按**累计获得**积分定位等级）                                                                                                 |
| `PointsMeResult.recent_transactions` | `PointsTransactionOut[]`，`recent` 默认 10、范围 1~50（`Query(default=10, ge=1, le=50)`）                                                                                |
| `LeaderboardItem.*`                  | `schema.LeaderboardItem`：`rank, user_id, username, balance`（`rank_entries` 按 `balance` 降序、`user_id` 升序赋名次）                                                       |
| `PointsLedger.*`（award 返回）           | `{account: PointsAccountOut, transaction: PointsTransactionOut}`（`service.grant`）                                                                                |
| 手动奖励请求体                              | `PointsGrantRequest`：`user_id: int`、`amount: int (gt=0, le=100000)`、`reason?: str (max_length 255)` → 前端发送 `{user_id, amount, reason}`                           |

## 3. 未接线及原因

| 未接项                            | 原因                                                                                                                                                                                                                                                |
|--------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `POST /record-action`（v2 抢分口）  | 后端**刻意不暴露**（controller 文档头明确说明：任何登录用户可刷分）。前端不造该端点，页面也不存在「上报行为换积分」入口。                                                                                                                                                                              |
| 前台页 `src/pages/points.vue` 的改动 | 不在本次产出清单内。该页已具备能力：账户概览（`mine`）、签到/流水、排行榜（`leaderboard`）、规则、兑换项、兑换。**未接** `me`/`ranking`/`level`——它已用 `mine` 覆盖账户、用 `leaderboard` 覆盖排行榜，等价度足够；`level` 详情属后台查询工具，前台无对应入口。若后续想让前台「账户概览」并入等级 + 最近流水，可把 `mine()` 换为 `me()`（返回结构不同，需改渲染逻辑）。**归为待办，未改。** |
| `src/api/index.ts` 的 re-export | 不在产出清单（不得修改仓库其它文件）。需追加的 re-export 块见「6.」                                                                                                                                                                                                          |

## 4. 存疑

1. **产物落点**：`pages/points.vue` 明确指向后台页 `src/pages/gamification/points.vue` 的**替换**
   （理由见第 0 节）。若本意是替换前台 `src/pages/points.vue`，则内容需要换成前台的
   自研组件风格（`Button`/`Icon`/`Skeleton`/`ErrorState`/`EmptyState`/`Badge`），且
   「手动奖励表单」需改用前台 toast（`pushToast`）而非 EP `ElMessageBox`——**请核对落点**。
2. **`award` 与 `grant` UI 并存**：后端二者同实现，页面上「管理端加减分（grant/deduct）」与
   「手动奖励（award）」两块表单功能重叠。为满足「逐字保留既有 grant/deduct + 新增 award + 二次确认」
   的要求而并存。若产品上只想要一个入口，可二选一。
3. **等级阈值文案**：`LEVELS` 等级名（新手/学徒/…）来自后端，前端**不硬编码**，直接展示
   `name` 字段，避免与后端常量漂移。
4. **`me` 的进度**：`progress` 已封顶时为 `1`，页面按 `Math.round(progress * 100)` 显示 100%；
   `next_level === null` 时显示「已达最高等级」。
5. **`levelResult.next_level_name ?? ''`**：`next_level_name` 类型为 `string | null`；仅在
   `next_level !== null` 时取用，`?? ''` 仅为满足类型收窄，非编造数据。

## 5. 未编译声明

本产物**未在仓库内编译/运行**（子智能体无 shell 权限，且不得改动仓库其它文件）：

- 未执行 `npm run build` / `vue-tsc` / ESLint。
- `src/api/index.ts` 的 re-export **尚未追加**（不在写入边界内），因此 `pages/points.vue`
  里 `import {… type PointsLevel, type PointsMeResult …} from '@/api'` 在应用 re-export 块之前
  **无法解析**——这是预期状态，见「6.」。
- 模板用到的 `AdminTableSkeleton` / `AdminEmpty` 沿用既有页面的**自动导入全局组件**约定，
  与既有代码一致，未新增 import。
- 新增 i18n 键尚未合并进 `zh-CN.json` / `en.json`。

## 6. re-export 块（追加到 `frontend/web/src/api/index.ts`）

位置：既有「批次 12（积分与勋章）」`pointsApi` 导出块附近，把**新增类型**并入同一条 `export type {…}`：

```ts
export {pointsApi} from './modules/points'
export type {
  CheckinResult,
  ExchangeResult,
  ExchangeRule,
  LeaderboardItem,
  PointsAccount,
  PointsLedger,
  PointsLevel,      // 新增
  PointsMeResult,   // 新增
  PointsRule,
  PointsStats,
  PointsTransaction,
} from './modules/points'
```

> 说明：`pointsApi` 值本身已是既有导出，无需改动；仅**补两个类型名**。
> `pages/points.vue` 依赖 `@/api` 暴露 `PointsLevel`、`PointsMeResult`。
> 若跳过此步，页面内 `import type` 会报「模块无导出成员」。
