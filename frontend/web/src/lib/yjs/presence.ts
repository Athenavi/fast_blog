/**
 * 协作在场（presence）—— 从 y-protocols Awareness 里解析「谁在这个房间」
 *
 * ## 为什么不需要动后端
 *
 * 后端 `content/collaboration/controller.py` 收到 AWARENESS 帧后**不解析内容，只按房间扇出**
 * （它只读第一字节的 messageType 决定是否转发）。因此身份写在 awareness 的本地状态里
 * （`setLocalStateField('user', …)`）就会原样到达同房间每个人，**后端一行都不用改**。
 *
 * 实测过：第二个端设 `user.name='浏览器探针'`，第一个端的头像栏直接念出了这个名字。
 *
 * 反过来说，这条通道**不是鉴权**：任何人都能自称任何名字。这里拿它只用于显示头像和名字，
 * 谁能进房间由后端决定。
 *
 * 实测的鉴权边界（决定了要不要留「没有身份」这一支）：WS 握手带 query token 能过，
 * **不带 token 也能过**（`/system/auth/me` 带 cookie 200、不带 cookie 401 —— 登录时后端种了
 * 一个 HttpOnly cookie，JS 读不到但握手会自动带上）；而两者都没有的客户端被 4401 拒掉。
 * 于是存在这种组合：**cookie 有效、但 localStorage 里没有 token** —— 此时
 * `userStore.isLoggedIn` 为假、房间照样连得上，这一端就报不出身份。
 * 所以 `resolvePeers` 必须留「对方没有身份」的兜底名，不能假设在场的人一定登录过。
 *
 * ## 过期与心跳
 *
 * `Awareness` 自带 30s 的 `outdatedTimeout`，并会在过半时自动续期本地时钟，
 * 断开的端会被其他端的 `setTimeout` 清掉。所以**不要**在这里加 keep-alive 定时器。
 * 实测：另一端 `ws.close()` 后头像约 34s 内自行消失，无需额外处理。
 *
 * ## 语言
 *
 * 状态里存的是**用户名原文**，不是翻译好的文案。若把「协作者」这种译名写进去，
 * 中文用户会给英文用户留下一个中文标签。兜底标签由**查看端**决定，见 `resolvePeers`
 * 的 `fallbacks` 参数。
 */

import type {Awareness} from 'y-protocols/awareness'

/** awareness 本地状态里存身份的字段名（自己约定，不与后端协议相关） */
export const PRESENCE_USER_FIELD = 'user'

/** 写进 awareness 的本地身份 */
export interface CollabUserMeta {
  /** 登录用户名；匿名时为 undefined，由查看端决定显示什么 */
  name?: string
  /** 未登录（本端没有 token；靠 cookie 连上时会出现，见文件头） */
  anonymous?: boolean
  avatar?: string | null
}

export interface CollabPeer {
  clientId: number
  /** 已按查看端语言兜底：自己的「你」> 对方用户名 > 「匿名协作者」> 「协作者」 */
  name: string
  initials: string
  avatar: string | null
  /** 头像底色（clientID 派生，见 `presenceColorOf`） */
  color: string
  isSelf: boolean
}

/**
 * 头像底色：按 `clientID` 取模，同一端在每个人屏幕上颜色一致，且不需要任何通信。
 *
 * 刻意**不**把颜色写进 awareness —— 它是 clientID 的纯函数，写出去只是多占一份同步。
 */
const PRESENCE_COLORS = [
  '#3b82f6',
  '#ef4444',
  '#10b981',
  '#f59e0b',
  '#8b5cf6',
  '#ec4899',
  '#14b8a6',
  '#f97316',
]

export function presenceColorOf(clientId: number): string {
  // 兜底色实际取不到（数组非空、取模必在范围内），但下标访问在类型层面是可能失败的，
  // 与其断言不如给个中性灰。
  return PRESENCE_COLORS[Math.abs(clientId) % PRESENCE_COLORS.length] ?? '#64748b'
}

/**
 * 头像上的字：拉丁名取词首字母（最多两个），其余文字取前两个字符。
 *
 * 按「是否空白/连接符分词」判断，而不是按 Unicode 区间判断 ——
 * 「张三丰」作为一个词取前两个字得到「张三」，与按 CJK 特判的结果相同，
 * 少一份区间表也就少一处会过期的知识。
 */
export function initialsOf(name: string): string {
  const words = name.trim().split(/[\s\-_.]+/).filter(Boolean)
  const first = words[0]
  if (!first) return ''

  const second = words[1]
  return (takeHead(first) + (second ? takeHead(second) : '')).toUpperCase()
}

/** 取词首：ASCII 取 1 个字符，其他文字取 2 个（否则中文头像只有一个字，认不出是谁） */
function takeHead(word: string): string {
  const first = word.codePointAt(0) ?? 0
  return first < 0x250 ? word.slice(0, 1) : Array.from(word).slice(0, 2).join('')
}

/** 本地要广播的身份；未登录时只标记 anonymous，不伪造名字 */
export function localPresenceMeta(input: {
  loggedIn: boolean
  name?: string | null
  avatar?: string | null
}): CollabUserMeta {
  if (!input.loggedIn) return {anonymous: true}
  const name = input.name?.trim()
  return {
    ...(name ? {name} : {}),
    ...(input.avatar ? {avatar: input.avatar} : {}),
  }
}

/**
 * 把 awareness 的状态表映射成有序在场列表。
 *
 * **自己排在最前** —— 房间里的第一眼是「我在，然后是别人」；
 * 之后按 clientID 稳定排序，避免每次远端抖动都重排一次头像（看起来像闪烁）。
 *
 * `fallbacks` 由查看端传（本地化后的「协作者」「匿名协作者」）：状态里存的是用户名原文，
 * 译名不能跟着走，否则中文用户会给英文用户留下一个中文标签 —— 见文件头。
 */
export function resolvePeers(
  awareness: Awareness,
  local: {clientId: number; selfName: string; selfAvatar?: string | null},
  fallbacks: {peer: string; anonymous: string},
): CollabPeer[] {
  const peers: CollabPeer[] = []

  for (const [clientId, raw] of awareness.getStates()) {
    const meta = (raw?.[PRESENCE_USER_FIELD] ?? undefined) as CollabUserMeta | undefined
    const anonymous = meta?.anonymous === true
    const isSelf = clientId === local.clientId

    // 名字优先级：自己 > 对方报的用户名 > 匿名 > 无身份兜底。
    // 自己这端用界面语言里的「你」而不是用户名：头像再多，也能一眼认出哪个是我。
    let name: string
    if (isSelf) name = local.selfName
    else if (meta?.name) name = meta.name
    else if (anonymous) name = fallbacks.anonymous
    else name = fallbacks.peer

    peers.push({
      clientId,
      name,
      initials: initialsOf(name),
      // 自己这端不读回环过来的 avatar，直接用本地用户 store：换头像时不用等一轮同步，
      // 也不会因为「状态还是连接前那一份」而短暂显示旧图。
      avatar: isSelf ? local.selfAvatar ?? null : meta?.avatar ?? null,
      color: presenceColorOf(clientId),
      isSelf,
    })
  }

  return peers.sort((a, b) => {
    if (a.isSelf !== b.isSelf) return a.isSelf ? -1 : 1
    return a.clientId - b.clientId
  })
}
