/**
 * 文章协作会话
 *
 * 把「开启协作 → 签发邀请 → 加入房间 → 落库」这一串封装成一个组合式，
 * 供 `my/posts/edit/[id]` 页面在**同一页内**切换普通编辑 / 协作编辑两种状态。
 *
 * ## 与 `content/collab-editor` 页面的关系
 *
 * 那个页面是 Yjs 协同的独立入口（本组合式的前身）。集成进编辑页后，
 * **协议层完全复用** `lib/yjs/collab-provider`（帧格式、鉴权、重连都在那里），
 * 这里只做"页面状态"的编排，不重新实现协议。
 *
 * ## 三条从旧页面继承的硬约束（踩过坑，不要改回去）
 *
 * 1. **正文不能走 Vue 的受控绑定**：用户输入、CRDT 同步、远端光标三者在
 *    「v-model → 重渲染 → 覆盖」这条受控链上会互相踩。旧页面实测出现过
 *    「Y.Text 已是 22 字符、而 textarea 仍为空」。现在这一半交给
 *    `y-codemirror.next` 直接绑定 Y.Text，本文件不再参与正文的读写。
 * 2. **改动要算最小差量**：整篇重写会让所有远端光标跳到文末。上一版本地输入靠
 *    手写的公共前后缀 diff 做到这点，现在由绑定层做（它订阅 Y.Text 的增量事件）。
 * 3. **`Y.Text` / `Awareness` 不能进深响应**：这两个对象靠自身引用与事件表工作，
 *    被 Vue 代理包起来后 `observe` 收到的就是代理，合并与撤销会静默错乱。
 *    所以对外暴露的是 `shallowRef`，见下面的 `binding`。
 *
 * ## 邀请
 *
 * 邀请本身是**后端已有的真能力**（`collaboration_invites` 表 + `invite_service`）：
 * 有效期 `expires_at`、人数上限 `max_uses`、仅所有者可签发，全部由后端强制。
 * 这里只负责调接口、把链接给用户 —— **不在前端做任何准入判断**（前端判断等于没有边界）。
 */

import * as Y from 'yjs'
import type {Awareness} from 'y-protocols/awareness'
import {CollabProvider, type CollabStatus} from '@/lib/yjs/collab-provider'
import {
  localPresenceMeta,
  PRESENCE_USER_FIELD,
  presenceColorOf,
  resolvePeers,
  type CollabPeer,
} from '@/lib/yjs/presence'
import {openPresenceSession, type PresenceHandle} from '@/composables/useCollabPresence'
import {useUserStore} from '@/store/modules/user'
import http from '@/api/request'

/** 邀请参数：由所有者在开启协作时配置 */
export interface InviteOptions {
  /** 有效期（小时）。不传走后端默认 */
  expiresInHours?: number
  /** 最大使用次数（= 最大协作人数）。不传走后端默认 */
  maxUses?: number
}

/**
 * 编辑器绑定协作房间所需的两样东西。
 *
 * 结构上与 `MarkdownEditor` 的 `collab` prop 相同（TS 按结构赋值，不必互相 import），
 * 但**这里独立声明**：会话层不该反过来依赖某个组件模块。
 */
export interface CollabBinding {
  ytext: Y.Text
  awareness: Awareness
}

export function useCollabSession(articleId: Ref<number>) {
  const {t} = useI18n()
  const userStore = useUserStore()

  /** 是否处于协作态（false = 普通编辑，由 ArticleEditor 承担） */
  const active = ref(false)
  const status = ref<CollabStatus>('connecting')
  const statusDetail = ref('')
  /**
   * 在场列表（含自己），由 awareness 身份状态解析而来，见 `lib/yjs/presence`。
   *
   * 排序稳定、自己在前；页面与全站顶栏读同一份（顶栏走 `useCollabPresence`，
   * 因为布局在页面之上，props 传不上去）。
   */
  const peers = ref<CollabPeer[]>([])
  /** 在线人数（含自己）—— 与 `peers` 同一份来源，不再各算各的 */
  const online = computed(() => peers.value.length)
  /** 协作态正文快照（**只用于目录/字数/预览**，正文本身由编辑器直接绑 Y.Text） */
  const text = ref('')
  /**
   * 交给编辑器的房间绑定。
   *
   * `shallowRef` 是**必须的**，不是风格问题：换成 `ref` 会让 Vue 把 `Y.Text`
   * 包成深响应代理，CRDT 的观察者与撤销栈拿到代理后行为就不可预期了
   * （见文件头约束 3）。房间生命周期内这个对象本身不会原地变，所以外层不需要响应。
   */
  const binding = shallowRef<CollabBinding | null>(null)
  /** 邀请链接（所有者开启后可复制） */
  const inviteUrl = ref('')
  const inviting = ref(false)
  const saving = ref(false)
  /** 是否为本次会话的所有者（协作者进来时没有"邀请/结束"权限） */
  const isOwner = ref(true)

  let doc: Y.Doc | null = null
  let yText: Y.Text | null = null
  let provider: CollabProvider | null = null
  /** 顶栏在场头像的发布句柄（离开会话时必须 close，否则顶栏留着已不在场的人） */
  let presence: PresenceHandle | null = null

  const statusLabel = computed(() => t(`myPosts.collab.${status.value}`))

  /**
   * 从 awareness 重算在场列表，同时推给本页与全站顶栏。
   *
   * 直接绑在 `awareness` 的 `update` 事件上：远端加入、离开、30s 超时清除都会触发它，
   * 不需要自己轮询（`CollabProvider` 里的连接事件覆盖不到超时清除这条路）。
   */
  function publishPeers(): void {
    if (!provider || !doc || !presence) return
    const next = resolvePeers(
      provider.awareness,
      {
        clientId: doc.clientID,
        selfName: t('myPosts.collab.presenceSelf'),
        selfAvatar: userStore.userInfo?.profile_picture,
      },
      {
        peer: t('myPosts.collab.presencePeer'),
        anonymous: t('myPosts.collab.presenceAnonymous'),
      },
    )
    peers.value = next
    presence.publish(next, provider.status)
  }

  /**
   * 本端的身份令牌（走 query 传给后端）。
   *
   * 可能为 null，而**连接仍可能成功**：登录时后端种了 HttpOnly cookie，握手会自动带上，
   * 于是「有 cookie、localStorage 里没 token」这一端也进得来房间（实测边界记在
   * `lib/yjs/presence.ts` 文件头）。这一端报不出用户名，所以在场头像退成兜底标签 ——
   * 不要把「没有 token」当成「没有连接」。
   */
  function authToken(): string | null {
    if (typeof localStorage === 'undefined') return null
    return localStorage.getItem('fastblog.token')
  }

  /** 从当前 URL 取邀请码（协作者通过邀请链接进入） */
  function inviteFromUrl(): string | null {
    if (typeof window === 'undefined') return null
    return new URLSearchParams(window.location.search).get('invite')
  }

  // ---------------------------------------------------------------- 邀请

  /**
   * 签发邀请（仅所有者）。返回可直接分享的链接。
   *
   * 把 `expiresInHours` / `maxUses` 交给后端落库 —— 它们必须由后端强制，
   * 否则有人改一下前端参数就能绕过人数上限。
   */
  async function createInvite(options: InviteOptions = {}): Promise<string> {
    inviting.value = true
    try {
      const payload: Record<string, unknown> = {
        target_type: 'article',
        target_id: articleId.value,
        permission: 'edit',
      }
      if (options.expiresInHours) {
        payload.expires_at = new Date(Date.now() + options.expiresInHours * 3600_000).toISOString()
      }
      if (options.maxUses) payload.max_uses = options.maxUses

      const invite = await http.post<{ invite_code?: string }>('/content/collaboration/invite', payload)
      const code = invite?.invite_code
      if (!code) {
        pushToast(t('myPosts.collab.inviteMissingCode'), 'error')
        return ''
      }

      const base = typeof window !== 'undefined' ? window.location.origin : ''
      inviteUrl.value = `${base}/my/posts/edit/${articleId.value}?invite=${encodeURIComponent(code)}`
      pushToast(t('myPosts.collab.inviteCreated'), 'success')
      return inviteUrl.value
    } catch {
      // 已经在 request 层统一 toast 过了，这里不重复提示
      return ''
    } finally {
      inviting.value = false
    }
  }

  /** 是否已尝试过把文章现有正文灌入房间（只做一次） */
  let seeded = false

  /**
   * 把文章**现有正文**灌进 Y.Text，让协作者进来就能看到原文。
   *
   * 没有这一步，协作房间是一个**空文档** —— 协作者一保存就把原文覆盖没了，
   * 那是数据损坏，不是显示问题。
   *
   * ## 为什么用 `doc.getMap('meta')` 而不是一个普通变量
   *
   * 两个人同时进入房间时，两端都会跑这段。如果各自无条件 insert，
   * 结果是「初始正文初始正文」（旧页面的注释记录了这次实测）。
   * `meta` 是**文档内的共享标记**，会随 CRDT 同步到另一端，
   * 把并发窗口从"必然翻倍"缩小到"极小概率"。
   */
  async function seedFromArticle(): Promise<void> {
    if (seeded || !yText || !doc) return
    seeded = true
    if (yText.length > 0) return // 房间已有内容（别人先到 / 服务端恢复）

    try {
      const detail = await http.get<{ content?: string }>(
        `/content/article/${Number(articleId.value)}`,
      )
      const content = String(detail?.content ?? '')
      if (!content) return

      const meta = doc.getMap<boolean>('meta')
      if (meta.get('seeded') || yText.length > 0) return

      doc.transact(() => {
        meta.set('seeded', true)
        yText!.insert(0, content)
      })
    } catch {
      // 读不到正文不阻断协作（空文档也能开始），但要如实提示
      pushToast(t('myPosts.collab.seedFailed'), 'error')
    }
  }

  // ---------------------------------------------------------------- 房间

  function join(): void {
    const id = Number(articleId.value)
    if (!id) return
    if (provider) leave()

    // 进入协作态。`join()` 可能被所有者（开启协作时）或协作者（自动加入）调用，
    // 两条路都必须把状态置真 —— 否则协作编辑器不渲染，页面会空。
    active.value = true

    doc = new Y.Doc()
    yText = doc.getText('content')

    // Y.Text → 渲染快照。**必须 observe**：否则协作期间远端改动不会刷新预览，
    // 只有加入那一刻的 synced 会被渲染一次。
    // 这里只更新一个**只读快照**，不参与输入绑定（见文件头约束 1）。
    yText.observe(() => {
      text.value = yText!.toString()
    })

    const token = authToken()
    const invite = inviteFromUrl()
    isOwner.value = !invite // 带邀请码进来的不是所有者

    presence = openPresenceSession()

    provider = new CollabProvider({
      documentId: id,
      doc,
      token,
      invite,
    })

    // 身份必须在 connect() **之前**写好：provider 在 onopen 只广播一次本地 awareness，
    // 连上之后再写就错过这一班，别人要等下一次变更才看得到我是谁。
    // 未登录（邀请链接进来的访客）不编用户名，只标 anonymous，名字由查看端补。
    provider.awareness.setLocalStateField(
      PRESENCE_USER_FIELD,
      localPresenceMeta({
        clientId: doc.clientID,
        loggedIn: userStore.isLoggedIn,
        name: userStore.userInfo?.username,
        avatar: userStore.userInfo?.profile_picture,
      }),
    )
    provider.awareness.on('update', publishPeers)
    // 先把自己渲染出来（不等第一轮同步）：顶栏那一刻就该知道「我在，还没别人」
    publishPeers()
    // 交给编辑器绑定。必须在 connect() 之前：视图紧接着就要挂载，
    // 而 y-codemirror 只认装配时拿到的那一份 Y.Text。
    binding.value = {ytext: yText, awareness: provider.awareness}

    provider.onStatus = (next, detail) => {
      status.value = next
      statusDetail.value = detail ?? ''
      // 人数一律从 `peers` 来（Awareness 把自己的状态也算在内，所以含自己）
      publishPeers()
      if (next === 'synced') {
        text.value = yText?.toString() ?? ''
        // 同步完成后灌入原文：必须在 synced 之后，否则本地插入会与
        // 服务端的历史状态竞争，产生重复内容。
        void seedFromArticle()
      }
      if (next === 'rejected') {
        // 被拒绝（邀请过期 / 人数已满 / 无权限）——如实告诉用户，而不是静默重试
        pushToast(detail || t('myPosts.collab.rejected'), 'error')
      }
    }
    provider.connect()
  }

  function leave(): void {
    provider?.awareness.off('update', publishPeers)
    provider?.destroy()
    provider = null
    doc = null
    yText = null
    binding.value = null
    text.value = ''
    peers.value = []
    status.value = 'connecting'
    statusDetail.value = ''
    presence?.close()
    presence = null
    // 「灌过原文」这个标记属于**那一个房间**，房间都拆了就得还回去：
    // 不然在同一页里第二次开启协作会跳过灌入，得到一个空文档，
    // 而空文档一路按到「保存到文章」就是把文章清空了。
    seeded = false
  }

  /** 把协作内容落库（显式动作，不做隐式自动保存 —— 与旧页面口径一致） */
  async function saveToArticle(): Promise<void> {
    const id = Number(articleId.value)
    if (!id || !yText) return

    // 空正文一律不发帖：协作房间里出现空文档通常意味着**灌入原文那一步没成功**
    // （同步没完成、或读取文章的接口挂了），此时按保存就是把文章清空。
    // 这不是「防止用户误删自己的空文章」——真空文章走普通保存路径，那边不经过这里。
    if (!yText.toString().trim()) {
      pushToast(t('myPosts.collab.saveRefusedEmpty'), 'error')
      return
    }

    saving.value = true
    try {
      // 三处都必须对齐 `content/collaboration` 的契约（都踩过）：
      //   1. 路径归属 `collaboration` 模块（少模块段 → 404）
      //   2. payload 字段名是 `html` 而不是 `content`（错字段名 → 422）
      //   3. **非作者必须带邀请码**（controller:411 的 `invite` query；协作者没有归属权）
      //
      // ⚠️ 字段叫 `html` 是后端既有 schema，但项目正文现在存的是 **Markdown** ——
      // 名实不符。改 schema 影响面大，这里照契约发送并记下这个不一致。
      const url = `/content/collaboration/yjs/document/${id}/save`
      const invite = inviteFromUrl()
      await http.post(
        invite ? `${url}?invite=${encodeURIComponent(invite)}` : url,
        {html: yText.toString()},
      )
      text.value = yText.toString()
      pushToast(t('myPosts.collab.saved'), 'success')
    } finally {
      saving.value = false
    }
  }

  /** 开启协作：先签发邀请（所有者），再加入房间 */
  async function start(options: InviteOptions = {}): Promise<void> {
    active.value = true
    if (!inviteFromUrl()) {
      await createInvite(options)
    }
    join()
  }

  /** 结束协作：断开连接并回到普通编辑 */
  function stop(): void {
    leave()
    active.value = false
    inviteUrl.value = ''
  }

  onBeforeUnmount(() => {
    if (provider) leave()
  })

  return {
    active,
    status,
    statusDetail,
    statusLabel,
    peers,
    online,
    text,
    /** 编辑器的协作绑定（原始 Y.Text + Awareness，勿套响应式，见上面的说明） */
    binding,
    inviteUrl,
    inviting,
    saving,
    isOwner,
    createInvite,
    start,
    stop,
    /** 仅加入房间、不签发邀请 —— 协作者从邀请链接进入时用这个 */
    join,
    saveToArticle,
  }
}
