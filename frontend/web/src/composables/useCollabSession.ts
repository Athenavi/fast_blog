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
 * ## 两条从旧页面继承的硬约束（踩过坑，不要改回去）
 *
 * 1. **Y.Text → DOM 直接写**：不能用 Vue 的受控绑定。用户输入、CRDT 同步、
 *    手动光标三者在受控 patch 下会互相覆盖 —— 旧页面实测出现过
 *    「Y.Text 已是 22 字符、而 textarea 仍为空」。
 * 2. **本地输入算最小差量**再写回 Y.Text：整篇重写会让所有远端光标跳到文末。
 *
 * ## 邀请
 *
 * 邀请本身是**后端已有的真能力**（`collaboration_invites` 表 + `invite_service`）：
 * 有效期 `expires_at`、人数上限 `max_uses`、仅所有者可签发，全部由后端强制。
 * 这里只负责调接口、把链接给用户 —— **不在前端做任何准入判断**（前端判断等于没有边界）。
 */

import * as Y from 'yjs'
import {CollabProvider, type CollabStatus} from '@/lib/yjs/collab-provider'
import http from '@/api/request'

/** 邀请参数：由所有者在开启协作时配置 */
export interface InviteOptions {
  /** 有效期（小时）。不传走后端默认 */
  expiresInHours?: number
  /** 最大使用次数（= 最大协作人数）。不传走后端默认 */
  maxUses?: number
}

export function useCollabSession(articleId: Ref<number>) {
  const {t} = useI18n()

  /** 是否处于协作态（false = 普通编辑，由 ArticleEditor 承担） */
  const active = ref(false)
  const status = ref<CollabStatus>('connecting')
  const statusDetail = ref('')
  const online = ref(0)
  /** 协作态正文（**只用于展示字数/诊断**，不参与输入绑定，见文件头约束 1） */
  const text = ref('')
  /** 邀请链接（所有者开启后可复制） */
  const inviteUrl = ref('')
  const inviting = ref(false)
  const saving = ref(false)
  /** 是否为本次会话的所有者（协作者进来时没有"邀请/结束"权限） */
  const isOwner = ref(true)

  let doc: Y.Doc | null = null
  let yText: Y.Text | null = null
  let provider: CollabProvider | null = null

  const statusLabel = computed(() => t(`myPosts.collab.${status.value}`))

  /** 所有者的身份令牌（协作者可能是免登录进来的，那时没有这个） */
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

    provider = new CollabProvider({
      documentId: id,
      doc,
      token,
      invite,
    })
    provider.onStatus = (next, detail) => {
      status.value = next
      statusDetail.value = detail ?? ''
      // peers() 已包含自己（Awareness 把自己的状态也算在内），不要再 +1
      online.value = provider?.peers().length ?? 0
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
    provider?.destroy()
    provider = null
    doc = null
    yText = null
    text.value = ''
    online.value = 0
    status.value = 'connecting'
    statusDetail.value = ''
  }

  /**
   * 本地输入 → 写回 Y.Text（**最小差量**）
   *
   * 不能做 `yText.delete(0, len); yText.insert(0, next)` —— 那是整篇替换，
   * 远端每个光标都会跳到文末。这里只找公共前缀/后缀，替换中间变化的那一段。
   */
  function applyLocal(next: string): void {
    if (!yText) return
    const prev = yText.toString()
    if (prev === next) return

    let start = 0
    const maxStart = Math.min(prev.length, next.length)
    while (start < maxStart && prev[start] === next[start]) start++

    let endPrev = prev.length
    let endNext = next.length
    while (endPrev > start && endNext > start && prev[endPrev - 1] === next[endNext - 1]) {
      endPrev--
      endNext--
    }

    doc!.transact(() => {
      if (endPrev > start) yText!.delete(start, endPrev - start)
      if (endNext > start) yText!.insert(start, next.slice(start, endNext))
    })
  }

  /** 读取当前 Y.Text（渲染用；渲染走 modelValue，故需响应式快照） */
  function snapshotText(): string {
    return yText?.toString() ?? ''
  }

  /** 把协作内容落库（显式动作，不做隐式自动保存 —— 与旧页面口径一致） */
  async function saveToArticle(): Promise<void> {
    const id = Number(articleId.value)
    if (!id || !yText) return
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
    online,
    text,
    inviteUrl,
    inviting,
    saving,
    isOwner,
    createInvite,
    start,
    stop,
    /** 仅加入房间、不签发邀请 —— 协作者从邀请链接进入时用这个 */
    join,
    applyLocal,
    snapshotText,
    saveToArticle,
  }
}
