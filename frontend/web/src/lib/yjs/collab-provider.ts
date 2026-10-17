/**
 * Yjs 协同 provider —— 原生 WebSocket + y-protocols（不用 y-websocket）。
 *
 * **为什么自己写**：后端 `/api/v3/content/collaboration/yjs/ws/{document_id}`
 * （`content/collaboration/controller.py`）自己实现了 y-protocols 的 sync + awareness 处理，
 * 且鉴权走「Cookie `access_token` → 子协议 → query `token`」三级回退；SPA 的 JWT 存在
 * localStorage，前两种拿不到，实际用 query。y-websocket 的 URL/房间约定与它不匹配，
 * 自己写反而更短、更可控。
 *
 * **协议（与后端逐字节对齐）**：
 * ```
 * 帧 = [messageType][payload]
 *   messageType: 0 = SYNC（y-protocols sync 消息）, 1 = AWARENESS
 * 连接建立后【服务端主动发 sync step1】（状态向量）→ 客户端回 step2 → 初始同步完成；
 * 之后双向只发增量 update。服务端把收到的帧转发给同房间其他连接（本进程 + Redis 跨 worker）。
 * ```
 *
 * 真实行为，无占位：连接失败/被拒（4401 未登录 / 4403 无权限）都会如实上报状态，
 * 不会假装已同步。
 */

import * as awarenessProtocol from 'y-protocols/awareness'
import * as decoding from 'lib0/decoding'
import * as encoding from 'lib0/encoding'
import * as syncProtocol from 'y-protocols/sync'
import type * as Y from 'yjs'

/** 与后端 `YMessageType` 一致 */
export const MESSAGE_SYNC = 0
export const MESSAGE_AWARENESS = 1

/** WS 关闭码（与后端 `WS_CLOSE_*` 一致） */
export const WS_CLOSE_UNAUTHORIZED = 4401
export const WS_CLOSE_FORBIDDEN = 4403

export type CollabStatus = 'connecting' | 'connected' | 'synced' | 'disconnected' | 'rejected'

export interface CollabProviderOptions {
  /** 文档 ID（= 文章 ID） */
  documentId: number
  /** Y.Doc；必须由调用方创建（页面持有多份事务/撤销栈时不会被 provider 抢走） */
  doc: Y.Doc
  /** JWT 或 API Token；走 query 参数传给后端 */
  token?: string | null
  /** 协作邀请码（非作者时必填） */
  invite?: string | null
  /** WebSocket 基址，默认按当前页面推导（同源 /api/v3） */
  baseUrl?: string
  /** 最大重连次数（超过后转 disconnected，不再无限重试） */
  maxRetries?: number
}

/** 推导 WS 基址。
 *
 * **dev 与生产不同源**：Nuxt 的 devProxy（nitro）只代理 HTTP，**不转发 WebSocket 升级**，
 * 因此开发时直连后端；生产由 nginx/网关转发 WS（路径不变，仍是同源）。
 * 后端地址取 `VITE_PROXY_TARGET`（就是 nuxt.config 里 devProxy 的目标），与代理保持同一处配置。
 */
function defaultWsBase(): string {
  const path = '/api/v3/content/collaboration/yjs/ws'
  if (import.meta.dev) {
    const target = (import.meta.env.VITE_PROXY_TARGET as string | undefined) || 'http://localhost:9421'
    try {
      return `ws://${new URL(target).host}${path}`
    } catch {
      return `ws://localhost:9421${path}`
    }
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}${path}`
}

export class CollabProvider {
  readonly doc: Y.Doc
  readonly awareness: awarenessProtocol.Awareness
  readonly url: string

  /** 连接状态（页面据此显示"已同步 / 重连中 / 被拒绝"） */
  status: CollabStatus = 'connecting'
  /** 状态变化回调 */
  onStatus: ((status: CollabStatus, detail?: string) => void) | null = null

  private ws: WebSocket | null = null
  private readonly maxRetries: number
  private retries = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private destroyed = false
  /** 本地 awareness 变更时立刻广播（节流由 awareness 自身负责） */
  private awarenessHandler: ((changes: {
    added: number[];
    updated: number[];
    removed: number[]
  }, origin: unknown) => void) | null = null

  constructor(private readonly options: CollabProviderOptions) {
    this.doc = options.doc
    this.awareness = new awarenessProtocol.Awareness(this.doc)
    this.maxRetries = options.maxRetries ?? 6

    const params = new URLSearchParams()
    if (options.token) params.set('token', options.token)
    if (options.invite) params.set('invite', options.invite)
    const query = params.toString()
    this.url = `${options.baseUrl ?? defaultWsBase()}/${options.documentId}${query ? `?${query}` : ''}`

    // 本地改动 → 发给服务端（origin 为自己时说明来自远端，避免回声）
    this.doc.on('update', this.handleDocUpdate)
  }

  connect(): void {
    if (this.destroyed) return
    this.setStatus('connecting')

    const ws = new WebSocket(this.url)
    ws.binaryType = 'arraybuffer'
    this.ws = ws

    ws.onopen = () => {
      this.retries = 0
      this.setStatus('connected')
      // 报一次本地 awareness（服务端会扇出给同房间其他人）
      this.broadcastAwareness([this.doc.clientID])
      this.awarenessHandler = (changes, origin) => {
        if (origin === this) return
        const ids = [...changes.added, ...changes.updated, ...changes.removed]
        if (ids.length) this.broadcastAwareness(ids)
      }
      this.awareness.on('update', this.awarenessHandler)
    }

    ws.onmessage = (event: MessageEvent) => this.handleMessage(event)
    ws.onerror = () => {
      // onerror 之后必有 onclose，这里不重复处理
    }
    ws.onclose = (event: CloseEvent) => {
      this.detachAwareness()
      this.ws = null
      if (event.code === WS_CLOSE_UNAUTHORIZED) {
        // 如实上报：不是"暂时断开"，重连也没用
        this.setStatus('rejected', '未登录或登录已过期（4401）')
        return
      }
      if (event.code === WS_CLOSE_FORBIDDEN) {
        this.setStatus('rejected', '没有该文档的协作权限（4403）')
        return
      }
      this.setStatus('disconnected', `连接已断开（code ${event.code}）`)
      this.scheduleReconnect()
    }
  }

  /** 主动关闭（组件卸载时调用） */
  destroy(): void {
    this.destroyed = true
    this.detachAwareness()
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.reconnectTimer = null
    this.doc.off('update', this.handleDocUpdate)
    // 广播"我要走了"，让其他人清掉本端 awareness
    try {
      awarenessProtocol.removeAwarenessStates(this.awareness, [this.doc.clientID], 'destroy')
    } catch {
      /* 连接已断时忽略 */
    }
    this.ws?.close()
    this.ws = null
    this.awareness.destroy()
  }

  // ─────────────────────────────────────────────── 内部

  private setStatus(status: CollabStatus, detail?: string): void {
    this.status = status
    this.onStatus?.(status, detail)
  }

  private detachAwareness(): void {
    if (this.awarenessHandler) {
      this.awareness.off('update', this.awarenessHandler)
      this.awarenessHandler = null
    }
  }

  private scheduleReconnect(): void {
    if (this.destroyed || this.retries >= this.maxRetries) {
      if (!this.destroyed && this.retries >= this.maxRetries) {
        this.setStatus('disconnected', `重连 ${this.maxRetries} 次仍失败`)
      }
      return
    }
    // 指数退避：0.5s, 1s, 2s, 4s ...（上限 8s）
    const delay = Math.min(500 * 2 ** this.retries, 8000)
    this.retries += 1
    this.reconnectTimer = setTimeout(() => this.connect(), delay)
  }

  private send(frame: Uint8Array): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return
    // TS 5.7 起 Uint8Array 被泛型化，其 buffer 类型是 ArrayBufferLike，与 WebSocket.send
    // 要求的 BufferSource（ArrayBufferView<ArrayBuffer>）不兼容。运行时 Uint8Array 是
    // 完全合法的 WebSocket 二进制载荷，这里只做类型层面的收窄。
    this.ws.send(frame as unknown as ArrayBufferView<ArrayBuffer>)
  }

  private handleDocUpdate = (update: Uint8Array, origin: unknown): void => {
    // origin === this 表示该更新来自远端消息，已经被服务端知道，不再回传
    if (origin === this) return
    const encoder = encoding.createEncoder()
    encoding.writeVarUint(encoder, MESSAGE_SYNC)
    syncProtocol.writeUpdate(encoder, update)
    this.send(encoding.toUint8Array(encoder))
  }

  private broadcastAwareness(clientIds: number[]): void {
    if (!clientIds.length) return
    const encoder = encoding.createEncoder()
    encoding.writeVarUint(encoder, MESSAGE_AWARENESS)
    encoding.writeVarUint8Array(
      encoder,
      awarenessProtocol.encodeAwarenessUpdate(this.awareness, clientIds),
    )
    this.send(encoding.toUint8Array(encoder))
  }

  private handleMessage(event: MessageEvent): void {
    const data = new Uint8Array(event.data as ArrayBuffer)
    if (!data.length) return

    const decoder = decoding.createDecoder(data)
    const messageType = decoding.readVarUint(decoder)

    if (messageType === MESSAGE_SYNC) {
      const encoder = encoding.createEncoder()
      encoding.writeVarUint(encoder, MESSAGE_SYNC)
      // origin 传 this：applyUpdate 触发的本地 update 事件不会回声给服务端
      syncProtocol.readSyncMessage(decoder, encoder, this.doc, this)
      if (encoding.length(encoder) > 1) {
        // 有回复（step1→step2 或需要补发状态）→ 发回服务端
        this.send(encoding.toUint8Array(encoder))
      }
      // 收到过 sync 消息即视为完成初始同步（服务端在 accept 后立刻发 step1）
      if (this.status === 'connected') this.setStatus('synced')
      return
    }

    if (messageType === MESSAGE_AWARENESS) {
      awarenessProtocol.applyAwarenessUpdate(
        this.awareness,
        decoding.readVarUint8Array(decoder),
        this,
      )
    }
  }
}
