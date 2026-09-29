# chat/web_push 前端接线报告

产物目录：`frontend/web/.gen/chat_web_push/`
写入边界：本子任务**只写**该目录，未改动仓库任何其它文件。

后端事实（已核对 `src/api/v3/modules/chat/web_push/{controller,schema,service}.py`）：

- 订阅落 `system_settings`，键 `chat.web_push.subscriptions.{uid}`，值为订阅记录数组（JSON）。
- `GET /vapid-public-key` 匿名可读；`configured=false` 时 **`public_key=null` 且给出 `reason`，不编造公钥**。
- `POST /subscribe` / `POST /unsubscribe` / `GET /subscriptions`：**仅认证、只操作本人**，不发权限码。
- `POST /send` / `POST /broadcast` / `POST /cleanup`：管理端，权限码 `module_ops:notification:edit`。
- `GET /stats`：管理端，权限码 `module_ops:notification:view`。
- `send` / `broadcast` 在缺 `pywebpush` 或 VAPID 私钥等前置条件时**抛 `BadRequestError`（HTTP 200 + code=400）如实失败**
  ，绝不返回假的 `sent`。

---

## 1. 端点映射表

| 后端端点（方法 路径）                                  | 权限                             | 前端 API 方法（`webPushApi`） | 承载页 UI                                                               |
|----------------------------------------------|--------------------------------|-------------------------|----------------------------------------------------------------------|
| `GET /api/v3/chat/web_push/vapid-public-key` | 匿名                             | `vapidPublicKey()`      | VAPID 配置状态卡（如实展示 `configured` / `reason` / `subject` / `public_key`） |
| `POST /api/v3/chat/web_push/subscribe`       | 仅认证                            | `subscribe(payload)`    | 「浏览器订阅（本机）」→ 启用按钮（经 composable 抓取 `PushSubscription` 后登记）            |
| `POST /api/v3/chat/web_push/unsubscribe`     | 仅认证                            | `unsubscribe(payload)`  | 「我的订阅」逐条退订；「全部退订」（`unsubscribe({})`）；composable 停用                   |
| `GET /api/v3/chat/web_push/subscriptions`    | 仅认证                            | `mySubscriptions()`     | 「我的订阅」表格                                                             |
| `POST /api/v3/chat/web_push/send`            | `module_ops:notification:edit` | `send(payload)`         | 「按用户发送推送」表单 + 结果明细表                                                  |
| `POST /api/v3/chat/web_push/broadcast`       | `module_ops:notification:edit` | `broadcast(payload)`    | 「广播推送」表单 + 每用户明细表                                                    |
| `GET /api/v3/chat/web_push/stats`            | `module_ops:notification:view` | `stats()`               | 「订阅统计」卡                                                              |
| `POST /api/v3/chat/web_push/cleanup`         | `module_ops:notification:edit` | `cleanup(payload)`      | 「清理失效 / 过期订阅」表单（`max_age_days` / `dry_run`）+ 结果                      |

`baseURL` 为 `/api/v3`（`@/api/request`），故方法内路径写 `/chat/web_push/...`（注意是**下划线** `web_push`）。

---

## 2. 字段来源

所有类型直接对齐 `schema.py` 的 Pydantic 模型（字段名逐一照抄，未改名）：

| 前端类型（`api/webPush.ts`）    | 来源模型（`schema.py`）        | 说明                                                                                                             |
|---------------------------|--------------------------|----------------------------------------------------------------------------------------------------------------|
| `WebPushSubscriptionKeys` | `SubscriptionKeys`       | `p256dh` / `auth`（base64url）                                                                                   |
| `WebPushSubscriptionIn`   | `WebPushSubscriptionIn`  | `endpoint` / `keys` / `user_agent?`（`extra="forbid"`，不多传字段）                                                    |
| `WebPushUnsubscribeIn`    | `WebPushUnsubscribeIn`   | `subscription_id?` / `endpoint?`                                                                               |
| `WebPushSendIn`           | `WebPushSendIn`          | `user_id` / `title` / `body` / `icon?` / `badge?` / `data?`                                                    |
| `WebPushBroadcastIn`      | `WebPushBroadcastIn`     | 同上 + `max_users`（默认 500，1..5000）                                                                               |
| `WebPushCleanupIn`        | `WebPushCleanupIn`       | `max_age_days?`（默认 30）/ `dry_run?`                                                                             |
| `WebPushSubscriptionOut`  | `WebPushSubscriptionOut` | `id` / `endpoint` / `user_agent?` / `created_at?` / `last_sent_at?` / `send_count` / `fail_count`（**不含 keys**） |
| `WebPushVapidOut`         | `WebPushVapidOut`        | `configured` / `public_key?` / `subject?` / `webpush_available` / `reason?`                                    |
| `WebPushStatsOut`         | `WebPushStatsOut`        | `total_users` / `total_subscriptions` / `average_per_user` / `vapid_configured` / `webpush_available`          |
| `WebPushSendResult`       | `WebPushSendResult`      | `subscription_id?` / `endpoint?` / `success` / `status?` / `error?`                                            |
| `WebPushSendResponse`     | `WebPushSendResponse`    | `total` / `sent` / `failed` / `pruned` / `results`                                                             |
| `WebPushCleanupOut`       | `WebPushCleanupOut`      | `scanned_users` / `scanned_subscriptions` / `removed` / `dry_run` / `removed_ids`                              |

`schema.py` **没有**给 `subscribe` / `unsubscribe` / `broadcast` 定义出参模型，二者按 `service.py` 实际返回的字典建型：

| 前端类型                                                 | 来源（`service.py`）                                                                                                    |
|------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| `WebPushSubscribeOut`                                | `subscribe()` 返回 `{"created": bool, "subscription": {…}}`                                                           |
| `WebPushUnsubscribeOut`                              | `unsubscribe()` 返回 `{"removed": int, "remaining": int}`                                                             |
| `WebPushBroadcastOut` / `WebPushBroadcastUserDetail` | `broadcast()` 返回 `{"total_users","total","sent","failed","pruned","details":[{"user_id","total","sent","pruned"}]}` |

composable 的字段来源：`PushSubscription.toJSON()` → `{endpoint, keys:{p256dh,auth}}` 映射为 `WebPushSubscriptionIn`；
`user_agent` 取 `navigator.userAgent`；`applicationServerKey` 由 `vapid-public-key` 的 `public_key`（base64url）解码为
`Uint8Array`。

---

## 3. 载重页选择与落位

**新建管理页**（而非改造 `pages/chat/groups.vue`）：

- 理由一：`groups.vue` 是**群组 CRUD**，用 `module_chat:group:*` 权限；本模块管理端点借用的是 **ops 通知**权限码（
  `module_ops:notification:view|edit`）。混进同一个页面会让页面级 `permission` 与按钮 `v-auth` 语义错位。
- 理由二：8 个端点里管理端（send/broadcast/stats/cleanup）与前台本人端点（subscribe/unsubscribe/subscriptions）受众不同，独立页更清晰；本机
  `PushManager` 订阅也自然归属该页。
- 理由三：`nuxt.config.ts` 已有 `'/chat/**': {ssr: false}`，新路由 `/chat/web-push` **无需改配置**；`request.ts` 的 admin
  判定优先看 `meta.layout==='admin'`，错误提示会走 EP `ElMessage`。

产品落位（本任务不执行，交父代理复制）：

| 产物                                      | 目标位置                                                     |
|-----------------------------------------|----------------------------------------------------------|
| `api/webPush.ts`                        | `frontend/web/src/api/modules/webPush.ts`                |
| `pages/chat/web-push.vue`               | `frontend/web/src/pages/chat/web-push.vue`               |
| `composables/useWebPushSubscription.ts` | `frontend/web/src/composables/useWebPushSubscription.ts` |

依赖的解构即用（**未改**，无需父代理改）：`@/api`（需按第 6 节补 re-export）、`@/utils/feedback`（`ElMessage`/`ElMessageBox`）、
`@/utils/format`（`formatDateTime(value?: string|null)`）、`useAdminList` 未使用（本页非分页列表）、`AdminPage` 自动导入。

### 菜单项建议（新建后台菜单）

| 字段                   | 建议值                                          |
|----------------------|----------------------------------------------|
| `name`               | `ChatWebPush`                                |
| `path`               | `/chat/web-push`                             |
| `title`（i18n 键 / 中文） | `admin.chat.webPush.title` / 浏览器推送（Web Push） |
| `permission`         | `module_ops:notification:view`               |
| 上级                   | 与「群聊管理」（`/chat/groups`）同级，chat 分组下           |

> 说明：菜单的 `permission` 用 `view`（与页面级一致，能看统计即可进）；发送 / 广播 / 清理按钮再由
`module_ops:notification:edit` 单独把关。

---

## 4. 未接线 / 如实降级及理由

1. **后端权限审计登记（非前端，交父代理）**：`controller.py` 顶部注明 `POST /subscribe`、`POST /unsubscribe` 是**仅认证无码写端点
   **，需补登 `src/api/v3/core/permission/audit.py` 的 `EXEMPT_WRITE_ENDPOINTS`，否则启动期审计告警，
   `PERMISSION_AUDIT_STRICT=1` 下拒绝启动。**不在本任务写入范围**，前端无法代做。
2. **真实送达断点（关键，未伪造）**：仓库 PWA 用 `@vite-pwa/nuxt` 的默认 **generateSW（Workbox）**，生成的 Service Worker *
   *不含 `push` / `notificationclick` 监听**，且 `pwa.devOptions.enabled=false`（开发期不注册 SW）。因此：
    - `PushManager.subscribe` 在**生产环境**（SW 已注册）可完成订阅登记；**开发环境无 SW，`navigator.serviceWorker.ready` 不
      resolve，启用会失败**（composable 如实返回 `reason:'subscribe-failed'`）。
    - 即便订阅成功，后端**真实推送到达时不会弹出通知**。要端到端可用，需父代理把 PWA 改成 `strategies: 'injectManifest'`
      并提供自定义 `sw.ts`（监听 `push` → `showNotification`，`notificationclick` → 打开窗口），或用 `workbox.importScripts`
      注入同样的 handler。**本页不声称"订阅成功就能收通知"**，页面顶部 `deliveryNote` 已如实提示。
    - 不新建/修改 `nuxt.config.ts`、`public/sw.ts`（超出写入边界）。
3. **`broadcast` 不提供「按主题 / 分组」选项**：后端 `service.broadcast` 明确「本项目无 topic / 分组表，如实不做」，前端不虚构该能力。
4. **无 VAPID 私钥 / `pywebpush` 缺失时的真实失败路径**（后端 400 → 前端 reject）：
    - `send` / `broadcast` → 请求 reject，拦截器弹出后端 `msg`（如「缺少 VAPID 私钥…」），**页面不渲染任何成功结果**（
      `sendResult`/`broadcastResult` 保持 `null`）。
    - `vapidPublicKey()` → 正常返回，卡片显示 `configured=false` 与 `reason`。
    - 「启用浏览器通知」→ composable 先探测 `configured`，为 false 时**不做 `PushManager.subscribe`**，返回
      `reason:'not-configured'`，页面以 warning 文案提示。
    - `stats` → 正常返回（`vapid_configured=false`），如实展示。
    - `subscribe` / `unsubscribe` / `subscriptions` / `cleanup` **不依赖 VAPID 配置**：订阅登记与清理照常真实执行。

---

## 5. 存疑

1. **前端项目无 TS 编译环境可跑**：本子任务无 shell 权限，未能 `vue-tsc`/`npm run build` 验证。类型对齐系**人工逐一比对**
   `schema.py` 与 `service.py` 得出（见第 2 节）。`typeCheck:false`（`nuxt.config.ts`），但不代表类型无误。
2. **`WebPushSendResult.status` 与广播 details 的数值类型**：`service` 用 `.model_dump(mode="json")`，`status` 可能是
   `null` 或 HTTP 码（number）；前端按 `number | null` 建模。若后端以字符串返回需微调。
3. **`permission` 命令式提示**：早期上线的稳定版应满足，代码补了 `String(raw)` 相关类型收窄（render）。若目标浏览器不支持
   `PushManager`，按钮仍渲染但点击后返回 `reason:'unsupported'`；未做「不支持即隐藏按钮」的处理（保持信息可见）。
4. **`AdminPage` / `$t` / `v-auth` / `useI18n` 为自动导入**：与 `pages/chat/groups.vue`、`pages/ops/notification.vue`
   用法一致；若目标工程关闭了某项自动导入需显式 import。
5. **i18n 花括号**：`i18n.json` 的 `extraDataPlaceholder` 中含字面花括号，已按规则写成 `{'{'}` / `{'}'}`（见
   `webPush.*.extraDataPlaceholder`）。合并时请**原样保留**，勿被 JSON 美化工具改写。
6. **`formatDateTime(row.created_at)`**：`created_at` / `last_sent_at` 可能为 `null`，函数签名 `value?: string | null`
   ，已兼容。

---

## 6. 未编译声明

**本产物未经过编译 / 类型检查 / 运行验证**（无 shell）。所有代码均按 `frontend/web` 现有约定手工书写：
`import http from '../request'`、页面从 `@/api` 导入、无 `as` 掩盖类型、无 mock / 占位。落地时需要父代理完成第 3
节的「产品落位」与下面的 re-export 补丁，方可编译。

---

## 7. re-export 块（追加到 `frontend/web/src/api/index.ts`）

在 `src/api/index.ts` 末尾（或任一 `// ----` 分组处）追加：

```ts
// ---------------------------------------------------------------- chat 域（浏览器推送 / Web Push）
export {webPushApi} from './modules/webPush'
export type {
  WebPushBroadcastIn,
  WebPushBroadcastOut,
  WebPushBroadcastUserDetail,
  WebPushCleanupIn,
  WebPushCleanupOut,
  WebPushSendIn,
  WebPushSendResponse,
  WebPushSendResult,
  WebPushStatsOut,
  WebPushSubscribeOut,
  WebPushSubscriptionIn,
  WebPushSubscriptionKeys,
  WebPushSubscriptionOut,
  WebPushUnsubscribeIn,
  WebPushUnsubscribeOut,
  WebPushVapidOut,
} from './modules/webPush'
```

> 补齐后，`pages/chat/web-push.vue` 的 `import {webPushApi, type WebPushSendResponse, …} from '@/api'` 与
> `composables/useWebPushSubscription.ts` 的 `import {webPushApi, type WebPushSubscriptionIn} from '@/api'` 才会解析。
> 未补之前，这两处会报「模块无导出成员」。
