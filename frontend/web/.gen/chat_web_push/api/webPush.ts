/**
 * Web Push 接口（`/api/v3/chat/web_push`，chat 域）
 *
 * 覆盖 v3 `chat/web_push` 模块的全部 8 个端点：
 *  - `GET  /vapid-public-key`  VAPID 公钥下发（**匿名可读**，供 PushManager.subscribe）
 *  - `POST /subscribe`         登记本人推送订阅（**仅认证**，只操作本人）
 *  - `POST /unsubscribe`       退订本人推送（**仅认证**，只操作本人）
 *  - `GET  /subscriptions`     本人订阅列表（**仅认证**，不返回 keys 材料）
 *  - `POST /send`              按用户推送（**管理端**，`module_ops:notification:edit`）
 *  - `POST /broadcast`         广播推送（**管理端**，`module_ops:notification:edit`）
 *  - `GET  /stats`             订阅统计（**管理端**，`module_ops:notification:view`）
 *  - `POST /cleanup`           清理失效 / 过期订阅（**管理端**，`module_ops:notification:edit`）
 *
 * 认证与 401 静默刷新由 `../request` 统一处理；成功（`code === 200`）时解包 `data`。
 *
 * **真实失败约定**：`send` / `broadcast` 在缺 `pywebpush` 或 VAPID 密钥等前置条件时，
 * 后端**如实返回 400**（HTTP 200 + `code=400`，`msg` 说明缺什么）；本模块不吞错误、
 * 不伪造 `sent` —— 调用方按常规错误流处理（拦截器已弹提示，这里让 Promise reject）。
 */
import http from '../request'

/** 浏览器 PushSubscription 的公钥材料（schema.SubscriptionKeys，base64url） */
export interface WebPushSubscriptionKeys {
  /** 客户端公钥（base64url，来自 `PushSubscription.toJSON().keys.p256dh`） */
  p256dh: string
  /** 客户端认证密钥（base64url，来自 `PushSubscription.toJSON().keys.auth`） */
  auth: string
}

/** 登记一条订阅（schema.WebPushSubscriptionIn） */
export interface WebPushSubscriptionIn {
  /** 推送服务 endpoint（https，来自 `PushSubscription.endpoint`） */
  endpoint: string
  /** 客户端公钥材料 */
  keys: WebPushSubscriptionKeys
  /** 登记时的 UA（可选，来自 `navigator.userAgent`） */
  user_agent?: string | null
}

/** 退订入参（schema.WebPushUnsubscribeIn）：`subscription_id` 与 `endpoint` 至少给一个；都不给则退订本人全部 */
export interface WebPushUnsubscribeIn {
  /** 订阅 ID（本人订阅列表返回的 `id`） */
  subscription_id?: string | null
  /** 推送 endpoint（与 subscription_id 二选一） */
  endpoint?: string | null
}

/** 按用户推送入参（schema.WebPushSendIn） */
export interface WebPushSendIn {
  /** 目标用户 ID */
  user_id: number
  /** 通知标题（1..200） */
  title: string
  /** 通知内容（1..2000） */
  body: string
  /** 通知图标 URL（可选） */
  icon?: string | null
  /** 通知徽章 URL（可选） */
  badge?: string | null
  /** 附加数据（可选） */
  data?: Record<string, unknown> | null
}

/** 广播推送入参（schema.WebPushBroadcastIn） */
export interface WebPushBroadcastIn {
  /** 通知标题（1..200） */
  title: string
  /** 通知内容（1..2000） */
  body: string
  /** 通知图标 URL（可选） */
  icon?: string | null
  /** 通知徽章 URL（可选） */
  badge?: string | null
  /** 附加数据（可选） */
  data?: Record<string, unknown> | null
  /** 单次广播覆盖的用户上限（默认 500，1..5000） */
  max_users?: number
}

/** 清理入参（schema.WebPushCleanupIn） */
export interface WebPushCleanupIn {
  /** 超过该天数的订阅被清理（默认 30，1..3650） */
  max_age_days?: number
  /** 仅统计不删除（默认 false） */
  dry_run?: boolean
}

/** 一条订阅（schema.WebPushSubscriptionOut；**不含** keys 材料） */
export interface WebPushSubscriptionOut {
  /** 订阅 ID */
  id: string
  /** 推送 endpoint */
  endpoint: string
  /** 登记时的 UA（可能为空） */
  user_agent?: string | null
  /** 创建时间（ISO 字符串） */
  created_at?: string | null
  /** 最近一次成功发送时间（ISO 字符串） */
  last_sent_at?: string | null
  /** 累计成功发送次数 */
  send_count: number
  /** 累计失败次数 */
  fail_count: number
}

/** `POST /subscribe` 的返回（service.subscribe） */
export interface WebPushSubscribeOut {
  /** 是否新增（`false` 表示按 endpoint 幂等更新了既有订阅） */
  created: boolean
  /** 登记 / 更新后的订阅（不含 keys） */
  subscription: WebPushSubscriptionOut
}

/** `POST /unsubscribe` 的返回（service.unsubscribe） */
export interface WebPushUnsubscribeOut {
  /** 被移除的订阅数 */
  removed: number
  /** 剩余订阅数 */
  remaining: number
}

/** VAPID 公钥下发（schema.WebPushVapidOut） */
export interface WebPushVapidOut {
  /** 后端是否已可真实发送（pywebpush + 公私钥齐备） */
  configured: boolean
  /** VAPID 公钥（`configured=false` 时为 null，**不会编造**） */
  public_key?: string | null
  /** VAPID subject（如 mailto:…） */
  subject?: string | null
  /** `pywebpush` 是否可用 */
  webpush_available: boolean
  /** 不可配置时的如实原因（缺库 / 缺私钥 / 缺公钥） */
  reason?: string | null
}

/** 订阅统计（schema.WebPushStatsOut） */
export interface WebPushStatsOut {
  /** 有订阅的用户数 */
  total_users: number
  /** 订阅总条数 */
  total_subscriptions: number
  /** 平均每用户订阅数 */
  average_per_user: number
  /** 后端 VAPID 是否已配置（可真实发送） */
  vapid_configured: boolean
  /** `pywebpush` 是否可用 */
  webpush_available: boolean
}

/** 单端点推送结果（schema.WebPushSendResult） */
export interface WebPushSendResult {
  /** 订阅 ID */
  subscription_id?: string | null
  /** 推送 endpoint */
  endpoint?: string | null
  /** 是否成功 */
  success: boolean
  /** 推送服务返回的状态码（如 404/410 表示订阅失效；未知时为 null） */
  status?: number | null
  /** 失败原因（成功时为 null） */
  error?: string | null
}

/** 一次推送（按用户 / 广播）的汇总结果（schema.WebPushSendResponse） */
export interface WebPushSendResponse {
  /** 参与本次发送的订阅总数 */
  total: number
  /** 成功数 */
  sent: number
  /** 失败数 */
  failed: number
  /** 因失效（404/410）被剔除的订阅数 */
  pruned: number
  /** 每条订阅的结果明细 */
  results: WebPushSendResult[]
}

/** 广播按用户的明细（service.broadcast 的 `details` 元素） */
export interface WebPushBroadcastUserDetail {
  /** 用户 ID */
  user_id: number
  /** 该用户参与发送的订阅数 */
  total: number
  /** 该用户成功数 */
  sent: number
  /** 该用户被剔除的失效订阅数 */
  pruned: number
}

/** `POST /broadcast` 的返回（service.broadcast） */
export interface WebPushBroadcastOut {
  /** 本次覆盖的用户数（受 `max_users` 限制） */
  total_users: number
  /** 订阅总数 */
  total: number
  /** 成功数 */
  sent: number
  /** 失败数 */
  failed: number
  /** 被剔除的失效订阅数 */
  pruned: number
  /** 每用户明细 */
  details: WebPushBroadcastUserDetail[]
}

/** 清理结果（schema.WebPushCleanupOut） */
export interface WebPushCleanupOut {
  /** 扫描的用户数 */
  scanned_users: number
  /** 扫描的订阅数 */
  scanned_subscriptions: number
  /** 移除的订阅数（`dry_run=true` 时仅统计） */
  removed: number
  /** 是否仅演练未删除 */
  dry_run: boolean
  /** 被移除的订阅 ID 列表 */
  removed_ids: string[]
}

export const webPushApi = {
  /** VAPID 公钥下发（公开；未配置时 `configured=false` 且 `reason` 说明缺什么） */
  vapidPublicKey: () => http.get<WebPushVapidOut>('/chat/web_push/vapid-public-key'),

  /** 登记（或更新）本人的一条订阅；同一 endpoint 幂等 */
  subscribe: (payload: WebPushSubscriptionIn) =>
    http.post<WebPushSubscribeOut>('/chat/web_push/subscribe', payload),

  /** 退订本人推送（给 subscription_id / endpoint 精确退订；都不给则退订全部） */
  unsubscribe: (payload: WebPushUnsubscribeIn) =>
    http.post<WebPushUnsubscribeOut>('/chat/web_push/unsubscribe', payload),

  /** 本人订阅列表（不含 keys 材料） */
  mySubscriptions: () => http.get<WebPushSubscriptionOut[]>('/chat/web_push/subscriptions'),

  /** 按用户推送（管理端；未配置 → 400 真实失败） */
  send: (payload: WebPushSendIn) =>
    http.post<WebPushSendResponse>('/chat/web_push/send', payload),

  /** 广播推送（管理端；未配置 → 400 真实失败） */
  broadcast: (payload: WebPushBroadcastIn) =>
    http.post<WebPushBroadcastOut>('/chat/web_push/broadcast', payload),

  /** 订阅统计（管理端） */
  stats: () => http.get<WebPushStatsOut>('/chat/web_push/stats'),

  /** 清理失效 / 过期订阅（管理端；`dry_run=true` 只统计不删除） */
  cleanup: (payload: WebPushCleanupIn) =>
    http.post<WebPushCleanupOut>('/chat/web_push/cleanup', payload),
}
