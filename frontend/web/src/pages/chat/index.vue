<script lang="ts" setup>
/**
 * 群聊消息页（批次 17）
 *
 * 登录可见：`middleware: 'auth'` 未登录时跳 /login（与 messages.vue 一致）。
 * `/chat` 与 `/chat/**` 在 nuxt.config.ts 中配置为 `ssr: false`，本页纯 CSR 渲染。
 *
 * 数据流：
 *  - 左侧群列表：`chatApi.listGroups`（后端 `/chat/group` 需 `module_chat:group:view`，
 *    非管理员会拿不到数据 → 显示空态）；
 *  - 右侧消息区：进入群后 `chatMessageApi.list(groupId)` 拉历史，
 *    并用原生 WebSocket 订阅实时消息（`import.meta.client` 后才建连接）；
 *  - 自己的消息靠右、带「撤回」按钮；发送 Enter 提交、Shift+Enter 换行。
 *
 * 降级策略：
 *  - 群列表 / 消息加载失败 → 空态卡片 + 重试按钮；
 *  - 实时连接断开 → 顶部状态提示 + 重试按钮；
 *  - 发送 / 撤回失败 → 输入保留并提示（错误 toast 由 request 层统一提示）。
 */
import {chatMessageApi, type ChatMessageItem, type MyChatGroup} from '@/api'
import {useUserStore} from '@/store/modules/user'
import {formatDateTime} from '@/utils/format'

definePageMeta({layout: 'default', middleware: 'auth', title: 'chatRoom.title'})

const {t} = useI18n()
const userStore = useUserStore()
const currentUserId = computed(() => userStore.userInfo?.id ?? null)

/** 每次拉取最近 50 条消息 */
const PAGE_SIZE = 50

// ---- 群列表 ----
const groups = ref<MyChatGroup[]>([])
const groupsLoading = ref(false)
const groupsError = ref(false)

// ---- 当前群 / 消息 ----
const activeGroupId = ref<number | null>(null)
const messages = ref<ChatMessageItem[]>([])
const messagesLoading = ref(false)
const messagesError = ref(false)
/** 服务端消息总数（> 已加载条数时说明还有更早的消息） */
const messagesTotal = ref(0)
/** 已加载到的最早一页（`page=1` 为最近一段，逐页向更早翻） */
const oldestPage = ref(1)
const olderLoading = ref(false)
const olderError = ref(false)

const hasOlder = computed(() => messages.value.length < messagesTotal.value)

// ---- 发送 / 撤回 ----
const draft = ref('')
const sending = ref(false)
const sendError = ref(false)
const recallError = ref(false)

// ---- 实时连接状态 ----
type ConnState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'
const connState = ref<ConnState>('disconnected')
/** 当前重连到第几次（用于提示，连上即归零） */
const reconnectAttempt = ref(0)

const listBody = ref<HTMLElement | null>(null)

const activeGroup = computed(
  () => groups.value.find((group) => group.id === activeGroupId.value) ?? null,
)

function scrollToBottom(): void {
  const el = listBody.value
  if (el) el.scrollTop = el.scrollHeight
}

function isOwn(message: ChatMessageItem): boolean {
  return currentUserId.value !== null && message.user_id === currentUserId.value
}

function groupLabel(group: MyChatGroup): string {
  return group.name || `#${group.id}`
}

/** 附件链接的展示名：取 URL 最后一段（去掉 query/hash 后 decode），取不到就回退原文 */
function attachmentName(url: string): string {
  const [withoutQuery = ''] = url.split('?')
  const [path = ''] = withoutQuery.split('#')
  const name = path.substring(path.lastIndexOf('/') + 1)
  if (!name) return url
  try {
    return decodeURIComponent(name)
  } catch {
    return name
  }
}

// ---------------------------------------------------------------- 群列表
async function loadGroups(): Promise<void> {
  groupsLoading.value = true
  groupsError.value = false
  try {
    // 只列本人加入的群（`/chat/message/my-groups`，不需要 group:view 管理权限）
    groups.value = await chatMessageApi.myGroups()
  } catch {
    groupsError.value = true
  } finally {
    groupsLoading.value = false
  }
}

// ---------------------------------------------------------------- 消息
async function loadMessages(groupId: number): Promise<void> {
  messagesLoading.value = true
  messagesError.value = false
  olderError.value = false
  oldestPage.value = 1
  try {
    const result = await chatMessageApi.list(groupId, {page: 1, page_size: PAGE_SIZE})
    if (activeGroupId.value !== groupId) return // 等待期间已切换群，丢弃过期结果
    messages.value = result.items
    messagesTotal.value = result.total
    void nextTick(scrollToBottom)
  } catch {
    if (activeGroupId.value === groupId) messagesError.value = true
  } finally {
    messagesLoading.value = false
  }
}

/** 向更早翻一页；插入后保持视口位置（不跳到顶部也不跳到底部） */
async function loadOlder(): Promise<void> {
  const groupId = activeGroupId.value
  if (groupId === null || olderLoading.value || !hasOlder.value) return
  olderLoading.value = true
  olderError.value = false
  const el = listBody.value
  const beforeHeight = el?.scrollHeight ?? 0
  const beforeTop = el?.scrollTop ?? 0
  try {
    const nextPage = oldestPage.value + 1
    const result = await chatMessageApi.list(groupId, {page: nextPage, page_size: PAGE_SIZE})
    if (activeGroupId.value !== groupId) return // 等待期间已切换群，丢弃过期结果
    const known = new Set(messages.value.map((item) => item.id))
    const older = result.items.filter((item) => !known.has(item.id))
    messages.value = [...older, ...messages.value]
    messagesTotal.value = result.total
    oldestPage.value = nextPage
    if (older.length) {
      await nextTick()
      if (el) el.scrollTop = el.scrollHeight - beforeHeight + beforeTop
    }
  } catch {
    if (activeGroupId.value === groupId) olderError.value = true
  } finally {
    olderLoading.value = false
  }
}

/** 追加 / 覆盖一条消息（WS 回显与本地乐观追加共用，按 id 去重） */
function upsertMessage(item: ChatMessageItem): void {
  const index = messages.value.findIndex((existing) => existing.id === item.id)
  if (index >= 0) {
    messages.value[index] = item
    return
  }
  messages.value.push(item)
  messages.value.sort((a, b) => {
    const byTime = String(a.created_at ?? '').localeCompare(String(b.created_at ?? ''))
    return byTime !== 0 ? byTime : a.id - b.id
  })
  void nextTick(scrollToBottom)
}

// ---------------------------------------------------------------- WebSocket
/**
 * 实时连接
 *
 * 此前只有"断了显示已断开、等用户点重试"：移动网络切换、锁屏唤醒、服务端重启之后
 * 连接都不会自己回来。这里补齐三个真实信号驱动的恢复：
 *  1. 断线后按退避重连（1s→2s→4s→8s→10s 封顶），连上即归零；
 *  2. 网络恢复（`online`）立刻重连，不等退避；
 *  3. 页面从后台回到前台（`visibilitychange`）时检查一次连接。
 * 浏览器 WebSocket API **不能发 ping 帧**，所以不做应用层心跳（那会往聊天记录里塞假消息），
 * 改用上面三个信号 + 服务端自身的 idle 关闭来驱动恢复。
 */
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 10_000]

let socket: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
/** 主动切换群 / 离开页面导致的关闭：不触发重连 */
let intentionalClose = false

function clearReconnect(): void {
  if (reconnectTimer !== null) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
}

function closeSocket(): void {
  clearReconnect()
  if (!socket) return
  intentionalClose = true
  socket.onopen = socket.onmessage = socket.onclose = socket.onerror = null
  socket.close()
  socket = null
}

/** 退避重连（仅当用户还停留在同一个群时才继续） */
function scheduleReconnect(groupId: number): void {
  clearReconnect()
  const index = Math.min(reconnectAttempt.value, RECONNECT_DELAYS.length - 1)
  const delay = RECONNECT_DELAYS[index] ?? 10_000
  reconnectAttempt.value += 1
  reconnectTimer = setTimeout(() => {
    if (activeGroupId.value === groupId) connectSocket(groupId)
  }, delay)
}

function handleSocketMessage(raw: string): void {
  let data: unknown
  try {
    data = JSON.parse(raw)
  } catch {
    return
  }
  if (!data || typeof data !== 'object') return
  const payload = data as Record<string, unknown>

  if (payload.type === 'recall') {
    const target = messages.value.find((item) => item.id === payload.id)
    if (target) {
      target.is_deleted = true
      target.content = ''
    }
    return
  }
  if (typeof payload.id === 'number') {
    upsertMessage(payload as unknown as ChatMessageItem)
  }
}

function connectSocket(groupId: number): void {
  if (!import.meta.client) return
  closeSocket()
  intentionalClose = false
  connState.value = reconnectAttempt.value > 0 ? 'reconnecting' : 'connecting'
  const ws = new WebSocket(chatMessageApi.wsUrl(groupId))
  socket = ws
  ws.onopen = () => {
    if (socket !== ws) return
    reconnectAttempt.value = 0
    connState.value = 'connected'
  }
  ws.onmessage = (event) => handleSocketMessage(String(event.data))
  ws.onclose = () => {
    if (socket !== ws) return
    socket = null
    if (intentionalClose) return
    connState.value = 'disconnected'
    scheduleReconnect(groupId)
  }
  ws.onerror = () => {
    /* 出错后 onclose 紧随其后，重连统一在那里处理 */
  }
}

/** 手动重试：立即重来一次并清零退避 */
function retryConnection(): void {
  const groupId = activeGroupId.value
  if (groupId === null) return
  reconnectAttempt.value = 0
  connectSocket(groupId)
}

/** 网络恢复 / 回到前台：连接不可用时立即重连（不等退避） */
function reviveConnection(): void {
  const groupId = activeGroupId.value
  if (groupId === null) return
  if (socket && socket.readyState === WebSocket.OPEN) return
  reconnectAttempt.value = 0
  connectSocket(groupId)
}

function onOnline(): void {
  reviveConnection()
}

function onVisibilityChange(): void {
  if (document.visibilityState === 'visible') reviveConnection()
}

// ---------------------------------------------------------------- 交互
function openGroup(groupId: number): void {
  if (activeGroupId.value === groupId) return
  sendError.value = false
  recallError.value = false
  activeGroupId.value = groupId
  messages.value = []
  messagesTotal.value = 0
  void loadMessages(groupId)
  connectSocket(groupId)
}

async function sendMessage(): Promise<void> {
  const content = draft.value.trim()
  const groupId = activeGroupId.value
  if (!content || groupId === null || sending.value) return
  sending.value = true
  sendError.value = false
  try {
    const sent = await chatMessageApi.send({group_id: groupId, content})
    upsertMessage(sent) // 乐观追加；WS 回显同 id 时按 id 覆盖，不会重复
    draft.value = ''
    void nextTick(scrollToBottom)
  } catch {
    sendError.value = true // 输入保留，用户可重试
  } finally {
    sending.value = false
  }
}

async function recallMessage(message: ChatMessageItem): Promise<void> {
  recallError.value = false
  try {
    await chatMessageApi.remove(message.id)
    message.is_deleted = true
    message.content = ''
  } catch {
    recallError.value = true
  }
}

/** Enter 发送、Shift+Enter 换行 */
function onDraftKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void sendMessage()
  }
}

onMounted(loadGroups)
onMounted(() => {
  window.addEventListener('online', onOnline)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onBeforeUnmount(() => {
  window.removeEventListener('online', onOnline)
  document.removeEventListener('visibilitychange', onVisibilityChange)
  closeSocket()
})
</script>

<template>
  <div class="mx-auto max-w-wide px-4 py-10">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('chatRoom.title') }}</h1>
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('chatRoom.subtitle') }}</p>
      </div>
      <span
        :class="{
          'text-success': connState === 'connected',
          'text-warning': connState === 'connecting' || connState === 'reconnecting',
          'text-fg-subtle': connState === 'disconnected',
        }"
        class="text-xs"
      >
        {{
          connState === 'connected'
            ? $t('chatRoom.connected')
            : connState === 'connecting'
              ? $t('chatRoom.connecting')
              : connState === 'reconnecting'
                ? $t('chatRoom.reconnecting', {n: reconnectAttempt})
                : $t('chatRoom.disconnected')
        }}
      </span>
    </div>

    <div class="mt-6 flex h-[70dvh] min-h-[26rem] gap-4">
      <!-- 左侧：群列表 -->
      <section
        class="flex min-h-0 w-full flex-col overflow-hidden rounded-card border border-line bg-surface md:w-72 md:shrink-0"
      >
        <div v-if="groupsLoading" class="flex-1 space-y-3 p-4">
          <Skeleton v-for="i in 5" :key="i" class="h-12 w-full"/>
        </div>

        <div v-else-if="groupsError" class="flex flex-1 items-center justify-center p-4">
          <EmptyState :description="$t('common.networkError')" :title="$t('chatRoom.loadFailed')">
            <Button class="mt-3" size="sm" variant="outline" @click="loadGroups">
              {{ $t('chatRoom.retry') }}
            </Button>
          </EmptyState>
        </div>

        <div v-else-if="groups.length" class="flex-1 overflow-y-auto">
          <button
            v-for="group in groups"
            :key="group.id"
            :class="group.id === activeGroupId ? 'bg-primary-soft' : ''"
            class="flex w-full items-center gap-3 border-b border-line px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-surface-soft"
            type="button"
            @click="openGroup(group.id)"
          >
            <span
              class="flex h-9 w-9 shrink-0 items-center justify-center rounded-pill bg-surface-soft text-fg-muted"
            >
              <Icon class="h-4 w-4" name="users"/>
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-medium text-fg">{{ groupLabel(group) }}</span>
              <span class="mt-0.5 block text-xs text-fg-muted">
                {{ $t('chatRoom.members', {n: group.member_count}) }}
              </span>
            </span>
          </button>
        </div>

        <div v-else class="flex flex-1 items-center justify-center p-4">
          <EmptyState :title="$t('chatRoom.emptyGroups')"/>
        </div>
      </section>

      <!-- 右侧：消息区 -->
      <section
        class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-card border border-line bg-surface"
      >
        <div v-if="activeGroupId === null" class="flex flex-1 items-center justify-center p-4">
          <EmptyState :title="$t('chatRoom.selectGroup')"/>
        </div>

        <template v-else>
          <!-- 群头 -->
          <header class="flex items-center gap-2 border-b border-line px-4 py-3">
            <p class="min-w-0 truncate text-sm font-semibold text-fg">
              {{ activeGroup ? groupLabel(activeGroup) : `#${activeGroupId}` }}
            </p>
            <Button
              v-if="connState === 'disconnected' || connState === 'reconnecting'"
              class="ml-auto"
              size="sm"
              variant="outline"
              @click="retryConnection"
            >
              <Icon class="h-4 w-4" name="refresh-cw"/>
              {{ $t('chatRoom.retry') }}
            </Button>
          </header>

          <!-- 消息流 -->
          <div ref="listBody" class="min-h-0 flex-1 space-y-2 overflow-y-auto p-4">
            <div v-if="messagesLoading" class="space-y-3">
              <Skeleton
                v-for="i in 4"
                :key="i"
                :class="i % 2 ? '' : 'ml-auto'"
                class="h-10 w-2/3"
              />
            </div>

            <div v-else-if="messagesError" class="flex h-full items-center justify-center">
              <EmptyState :description="$t('common.networkError')" :title="$t('chatRoom.loadFailed')">
                <Button class="mt-3" size="sm" variant="outline" @click="loadMessages(activeGroupId)">
                  {{ $t('chatRoom.retry') }}
                </Button>
              </EmptyState>
            </div>

            <EmptyState v-else-if="!messages.length" :title="$t('chatRoom.emptyMessages')"/>

            <template v-else>
              <!-- 更早的消息：后端按页向更早翻（page=1 即最近一段） -->
              <div v-if="hasOlder" class="flex flex-col items-center gap-1 pb-2">
                <Button :disabled="olderLoading" size="sm" variant="outline" @click="loadOlder">
                  {{ $t('chatRoom.loadMore') }}
                </Button>
                <p v-if="olderError" class="text-xs text-danger">{{ $t('chatRoom.loadFailed') }}</p>
              </div>
              <div
                v-for="message in messages"
                :key="message.id"
                :class="isOwn(message) ? 'justify-end' : 'justify-start'"
                class="flex"
              >
                <div class="max-w-[75%]">
                  <p v-if="!isOwn(message)" class="mb-0.5 text-xs text-fg-muted">
                    {{ message.username || `#${message.user_id}` }}
                  </p>
                  <div
                    :class="
                      isOwn(message) ? 'bg-primary text-primary-fg' : 'bg-surface-soft text-fg'
                    "
                    class="break-words rounded-control px-3 py-2 text-sm whitespace-pre-wrap"
                  >
                    <em v-if="message.is_deleted" class="opacity-70">{{ $t('chatRoom.recalled') }}</em>
                    <template v-else>
                      {{ message.content }}
                      <a
                        v-if="message.attachment_url"
                        :class="isOwn(message) ? 'text-primary-fg' : 'text-primary'"
                        :href="message.attachment_url"
                        class="mt-1 flex items-center gap-1 text-xs underline"
                        rel="noopener"
                        target="_blank"
                      >
                        <Icon class="h-3.5 w-3.5 shrink-0" name="file-text"/>
                        <span class="truncate">
                          {{ $t('chatRoom.attachment') }} · {{ attachmentName(message.attachment_url || '') }}
                        </span>
                      </a>
                    </template>
                  </div>
                  <p
                    :class="isOwn(message) ? 'text-right' : ''"
                    class="mt-0.5 flex items-center gap-2 text-[11px] text-fg-subtle"
                  >
                    <span>{{ formatDateTime(message.created_at) }}</span>
                    <button
                      v-if="isOwn(message) && !message.is_deleted"
                      class="underline hover:text-danger"
                      type="button"
                      @click="recallMessage(message)"
                    >
                      {{ $t('chatRoom.recall') }}
                    </button>
                  </p>
                </div>
              </div>
            </template>
          </div>

          <!-- 发送条 -->
          <footer class="border-t border-line p-3">
            <p v-if="sendError" class="mb-2 text-xs text-danger">{{ $t('chatRoom.sendFailed') }}</p>
            <p v-if="recallError" class="mb-2 text-xs text-danger">
              {{ $t('chatRoom.recallFailed') }}
            </p>
            <div class="flex items-end gap-2">
              <textarea
                v-model="draft"
                :aria-label="$t('chatRoom.inputPlaceholder')"
                :placeholder="$t('chatRoom.inputPlaceholder')"
                class="max-h-32 min-h-9 flex-1 resize-none rounded-control border border-line bg-surface px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-primary focus:outline-none"
                rows="1"
                @input="sendError = false"
                @keydown="onDraftKeydown"
              />
              <Button :disabled="sending || !draft.trim()" @click="sendMessage">
                <Icon class="h-4 w-4" name="send"/>
                {{ $t('chatRoom.send') }}
              </Button>
            </div>
          </footer>
        </template>
      </section>
    </div>
  </div>
</template>
