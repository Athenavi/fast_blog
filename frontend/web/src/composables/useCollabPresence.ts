/**
 * 协作在场的**共享出口**
 *
 * ## 为什么不是 props、也不是 Teleport
 *
 * 头像要显示在**全站顶栏**（`SiteHeader` / `AppHeader`），而会话由页面里的
 * `useCollabSession` 持有 —— 顶栏在布局层，页面在它下面，props 传不上去。
 * 用 `<Teleport>` 也能做，但顶栏要留挂载点、页面要管挂载时序，两套布局各加一份；
 * 而这份状态本来就是「客户端、瞬时、全局唯一」的，一个模块级 ref 就是它最省的形状。
 *
 * 因此：会话把解析好的在场列表**发布**到这里，两个顶栏各渲染同一个组件。
 * 会话结束（离开/卸载）时必须 `close()`，否则顶栏会留着已经不在场的人。
 *
 * 只存显示需要的数据，鉴权信息一概不经过这里 —— 见 `lib/yjs/presence.ts` 文件头。
 */

import type {CollabStatus} from '@/lib/yjs/collab-provider'
import type {CollabPeer} from '@/lib/yjs/presence'

interface PresenceSession {
  peers: CollabPeer[]
  status: CollabStatus
}

/**
 * 活动会话列表。
 *
 * 支持多会话只是**不把话说死**：目前只有编辑页能开启协作，实际同时最多一个。
 */
const sessions = ref<PresenceSession[]>([])

export interface PresenceHandle {
  publish(peers: CollabPeer[], status: CollabStatus): void
  close(): void
}

/** 由 `useCollabSession` 调用（页面不要直接用） */
export function openPresenceSession(): PresenceHandle {
  // 先 reactive 再入数组：直接 push 字面量、之后改**原始对象**的话，
  // 写入绕开代理，顶栏不会重算（Vue 响应式的经典坑）。
  const session = reactive<PresenceSession>({peers: [], status: 'connecting'})
  sessions.value.push(session)

  return {
    publish(peers, status) {
      session.peers = peers
      session.status = status
    },
    close() {
      const index = sessions.value.findIndex((entry) => toRaw(entry) === toRaw(session))
      if (index >= 0) sessions.value.splice(index, 1)
    },
  }
}

/** 由顶栏组件调用 */
export function useCollabPresence() {
  const peers = computed(() => sessions.value.flatMap((session) => session.peers))

  /**
   * 整体连接状态：任一会话掉线就报掉线。
   *
   * 没有连接时 awareness 不再更新，在场列表会停在最后一份已知状态 ——
   * 与其安静地展示一排假头像，不如标出来。
   */
  const status = computed<CollabStatus>(() => {
    const broken = sessions.value.find(
      (session) => session.status === 'disconnected' || session.status === 'rejected',
    )
    if (broken) return broken.status
    if (!sessions.value.length) return 'disconnected'
    if (sessions.value.every((session) => session.status === 'synced')) return 'synced'
    return 'connecting'
  })

  return {
    peers,
    status,
    /** 在场人数（含自己），与会话内 `online` 同一口径 */
    count: computed(() => peers.value.length),
  }
}
