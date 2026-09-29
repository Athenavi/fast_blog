/**
 * 浏览器推送订阅 composable（Web Push / Push API）
 *
 * 📍 目标位置：`src/composables/useWebPushSubscription.ts`
 *   （本文件由父代理从 `.gen/chat_web_push/composables/` 落位到该路径后生效）
 *
 * 职责：把「浏览器端拿到 `PushSubscription` 并登记到后端」这一段封成可复用逻辑：
 *   1. 探测环境（`serviceWorker` / `PushManager` / `Notification`）；
 *   2. 取后端 VAPID 公钥（`webPushApi.vapidPublicKey`）——**未配置即如实失败**（不伪造订阅）；
 *   3. 走 `PushManager.subscribe` 拿订阅，转成 `WebPushSubscriptionIn` 提交后端登记；
 *   4. 退订：`PushSubscription.unsubscribe()` + 后端 `webPushApi.unsubscribe`。
 *
 * 鉴权根据 `webPushApi`（走 `@/api/request`，自动注入 Bearer token）。本 composable 只负责
 * **返回如实的成败与原因**，文案由调用页面按 `reason` 选 i18n 键。
 *
 * ⚠️ 当前仓库的真实断点（**不在本任务写入范围内，见 REPORT.md**）：
 *   - `nuxt.config.ts` 的 PWA 用 `@vite-pwa/nuxt` 默认的 **generateSW**（Workbox），生成的
 *     Service Worker **不含 `push` / `notificationclick` 监听**，且 `pwa.devOptions.enabled=false`
 *     （开发期不注册 SW）。后果：
 *       · 生产环境（SW 已注册）可完成订阅登记；
 *       · 但后端**真实推送到达时不会弹出通知** —— 需父代理把 PWA 改成
 *         `strategies: 'injectManifest'` 并提供自定义 `sw.ts` 监听 `push` / `notificationclick`，
 *         或另用 `workbox.importScripts` 注入同样的 handler。
 *   - 本 composable **不**伪造「订阅成功即可收通知」的结论：环境/权限/后端配置任一不满足都返回 `reason`。
 */
import {onMounted, ref, type Ref} from 'vue'

import {webPushApi, type WebPushSubscriptionIn} from '@/api'

/** 启用推送失败的**如实**原因（页面据此选文案） */
export type WebPushFailReason =
/** 浏览器不支持 Push / Service Worker / Notification */
  | 'unsupported'
  /** 用户拒绝了通知权限 */
  | 'permission'
  /** 后端未配置 VAPID / pywebpush（`configured=false`） */
  | 'not-configured'
  /** 后端标记已配置但未下发公钥（异常态，如实上报） */
  | 'no-key'
  /** `PushManager.subscribe` 或登记请求失败 */
  | 'subscribe-failed'

/** 启用结果 */
export type WebPushEnableResult = { ok: true } | { ok: false; reason: WebPushFailReason }

/** 返回对象 */
export interface UseWebPushSubscription {
  /** 当前浏览器是否支持浏览器推送（SW + PushManager + Notification） */
  supported: Ref<boolean>
  /** 当前通知权限（不支持时为 `'unsupported'`） */
  permission: Ref<NotificationPermission | 'unsupported'>
  /** 是否有正在进行的启用 / 停用操作 */
  busy: Ref<boolean>
  /** 本机当前是否已存在 PushSubscription（不代表后端一定登记成功） */
  hasLocalSubscription: Ref<boolean>
  /** 重新读取本机订阅状态 */
  refreshLocal: () => Promise<void>
  /** 启用：取 VAPID 公钥 → 申请权限 → subscribe → 登记后端 */
  enable: () => Promise<WebPushEnableResult>
  /** 停用：本机 unsubscribe → 后端退订 */
  disable: () => Promise<boolean>
}

/**
 * base64url（VAPID 公钥）→ `Uint8Array`（`applicationServerKey` 所需）
 *
 * 纯函数：补 padding、把 `-`/`_` 还原为 `+`/`/`，再逐字节读取。
 */
function urlBase64ToUint8Array(base64Url: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64Url.length % 4)) % 4)
  const base64 = (base64Url + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const output = new Uint8Array(raw.length)
  for (let index = 0; index < raw.length; index += 1) {
    output[index] = raw.charCodeAt(index)
  }
  return output
}

/** 把浏览器订阅转成后端入参；缺任一必需字段返回 `null`（如实判失败，不补占位） */
function toSubscriptionPayload(subscription: PushSubscription): WebPushSubscriptionIn | null {
  const json = subscription.toJSON()
  const endpoint = json.endpoint
  const p256dh = json.keys?.p256dh
  const auth = json.keys?.auth
  if (!endpoint || !p256dh || !auth) return null
  return {
    endpoint,
    keys: {p256dh, auth},
    user_agent: navigator.userAgent,
  }
}

export function useWebPushSubscription(): UseWebPushSubscription {
  const supported = ref(
    import.meta.client &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window,
  )
  const permission = ref<NotificationPermission | 'unsupported'>(
    supported.value ? Notification.permission : 'unsupported',
  )
  const busy = ref(false)
  const hasLocalSubscription = ref(false)

  async function refreshLocal(): Promise<void> {
    if (!supported.value) return
    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      hasLocalSubscription.value = subscription !== null
    } catch {
      hasLocalSubscription.value = false
    }
  }

  async function enable(): Promise<WebPushEnableResult> {
    if (!supported.value) return {ok: false, reason: 'unsupported'}
    busy.value = true
    try {
      const vapid = await webPushApi.vapidPublicKey()
      if (!vapid.configured) return {ok: false, reason: 'not-configured'}
      if (!vapid.public_key) return {ok: false, reason: 'no-key'}

      const granted = await Notification.requestPermission()
      permission.value = granted
      if (granted !== 'granted') return {ok: false, reason: 'permission'}

      const registration = await navigator.serviceWorker.ready
      let subscription = await registration.pushManager.getSubscription()
      if (!subscription) {
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapid.public_key),
        })
      }

      const payload = toSubscriptionPayload(subscription)
      if (!payload) return {ok: false, reason: 'subscribe-failed'}

      await webPushApi.subscribe(payload)
      hasLocalSubscription.value = true
      return {ok: true}
    } catch {
      return {ok: false, reason: 'subscribe-failed'}
    } finally {
      busy.value = false
    }
  }

  async function disable(): Promise<boolean> {
    if (!supported.value) return false
    busy.value = true
    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      if (!subscription) {
        hasLocalSubscription.value = false
        return true
      }
      const endpoint = subscription.endpoint
      await subscription.unsubscribe()
      await webPushApi.unsubscribe({endpoint})
      hasLocalSubscription.value = false
      return true
    } catch {
      return false
    } finally {
      busy.value = false
    }
  }

  onMounted(() => {
    void refreshLocal()
  })

  return {supported, permission, busy, hasLocalSubscription, refreshLocal, enable, disable}
}
