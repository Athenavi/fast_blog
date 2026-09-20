<script lang="ts" setup>
/**
 * 站内信
 *
 * 登录可见：`middleware: 'auth'` 未登录时跳 /login 并携带回跳地址（与 my/posts 一致）。
 * /messages 在 nuxt.config.ts 中配置为 `ssr: false`，本页纯 CSR 渲染。
 * 接口走 `mobile/message` 域（`@/api/modules/message`），认证与 mobile.ts 相同：
 * `@/api/request` 自动注入 Bearer token，401 时静默刷新。
 *
 * 降级策略：
 *  - 会话 / 消息加载失败 → 空态卡片 + 重试按钮；
 *  - 空会话 / 空消息 → EmptyState 引导文案；
 *  - 发送失败 → 输入内容保留并提示，可重试；
 *  - 已读回执上报失败 → 静默忽略（前端已标记，不影响交互）。
 */
import {messageApi, type MessageContact, type MessageItem} from '@/api/modules/message'
import {formatDateTime} from '@/utils/format'

const {t} = useI18n()

definePageMeta({layout: 'default', middleware: 'auth', title: 'messages.title'})

/** 每次拉取最近 50 条消息（足够一屏回看，翻历史暂不开放） */
const PAGE_SIZE = 50

// ---- 会话列表 ----
const contacts = ref<MessageContact[]>([])
const contactsLoading = ref(false)
const contactsError = ref(false)

// ---- 当前会话 ----
const activePeerId = ref<number | null>(null)
const messages = ref<MessageItem[]>([])
const messagesLoading = ref(false)
const messagesError = ref(false)

// ---- 发送 ----
const draft = ref('')
const sending = ref(false)
const sendError = ref(false)

/** 移动端两态：false=会话列表，true=已进入会话（<md 生效，桌面端始终双栏） */
const conversationOpen = ref(false)

const listBody = ref<HTMLElement | null>(null)

const activeContact = computed(
  () => contacts.value.find((contact) => contact.peer_id === activePeerId.value) ?? null,
)

const activePeerName = computed(() => {
  const peerId = activePeerId.value
  if (peerId === null) return ''
  return activeContact.value?.peer_name || t('messages.peerFallback', {id: peerId})
})

function scrollToBottom(): void {
  const el = listBody.value
  if (el) el.scrollTop = el.scrollHeight
}

async function loadContacts(): Promise<void> {
  contactsLoading.value = true
  contactsError.value = false
  try {
    contacts.value = await messageApi.contacts()
  } catch {
    contactsError.value = true
  } finally {
    contactsLoading.value = false
  }
}

/**
 * 会话按时间正序 + offset 分页：第 1 页是最旧的消息，
 * 因此先探测总数、长会话再取最后一页，保证展示的是最近一段对话。
 */
async function fetchLatestMessages(peerId: number): Promise<MessageItem[]> {
  const first = await messageApi.list({peer_id: peerId, page: 1, page_size: PAGE_SIZE})
  const lastPage = Math.max(1, Math.ceil(first.total / PAGE_SIZE))
  if (lastPage <= 1) return first.items
  return (await messageApi.list({peer_id: peerId, page: lastPage, page_size: PAGE_SIZE})).items
}

async function loadMessages(): Promise<void> {
  const peerId = activePeerId.value
  if (peerId === null) return
  messagesLoading.value = true
  messagesError.value = false
  try {
    const items = await fetchLatestMessages(peerId)
    if (activePeerId.value !== peerId) return // 等待期间已切换会话，丢弃过期结果
    messages.value = items
    markIncomingRead()
    void nextTick(scrollToBottom)
  } catch {
    if (activePeerId.value === peerId) messagesError.value = true
  } finally {
    messagesLoading.value = false
  }
}

/**
 * 进入会话后把收到的未读消息标记为已读：
 * 前端先本地标记（未读数清零、气泡视为已读），再逐条异步上报已读回执，失败静默。
 */
function markIncomingRead(): void {
  const unreadIds = messages.value
    .filter((msg) => msg.direction === 'in' && !msg.is_read)
    .map((msg) => msg.id)
  if (!unreadIds.length) return
  for (const id of unreadIds) {
    void messageApi.markRead(id).catch(() => undefined)
  }
  messages.value = messages.value.map((msg) =>
    msg.direction === 'in' ? {...msg, is_read: true} : msg,
  )
  const contact = activeContact.value
  if (contact) contact.unread = 0
}

function openConversation(peerId: number): void {
  sendError.value = false
  conversationOpen.value = true
  if (activePeerId.value === peerId && (messages.value.length || messagesLoading.value)) {
    return // 已在该会话：仅移动端切回会话视图
  }
  activePeerId.value = peerId
  messages.value = []
  void loadMessages()
}

function backToContacts(): void {
  conversationOpen.value = false // 保留 activePeerId，桌面端仍显示当前会话
}

async function sendMessage(): Promise<void> {
  const content = draft.value.trim()
  const peerId = activePeerId.value
  if (!content || peerId === null || sending.value) return
  sending.value = true
  sendError.value = false
  try {
    const sent = await messageApi.send({recipient_id: peerId, content})
    messages.value.push(sent)
    draft.value = ''
    void nextTick(scrollToBottom)
    // 刷新会话列表的 last_content / last_at（失败不影响已发送的消息展示）
    void loadContacts()
  } catch {
    sendError.value = true // 输入保留，用户可重试；错误 toast 由 request 层统一提示
  } finally {
    sending.value = false
  }
}

/** Enter 发送、Shift+Enter 换行 */
function onDraftKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void sendMessage()
  }
}

onMounted(loadContacts)
</script>

<template>
  <div class="mx-auto max-w-wide px-4 py-10">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('messages.title') }}</h1>
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('messages.subtitle') }}</p>
      </div>
      <Button :disabled="contactsLoading" size="sm" variant="outline" @click="loadContacts">
        <Icon class="h-4 w-4" name="refresh-cw"/>
        {{ $t('common.refresh') }}
      </Button>
    </div>

    <div class="mt-6 flex h-[70vh] min-h-[26rem] gap-4">
      <!-- 左侧：会话列表（移动端进入会话后隐藏） -->
      <section
        :class="conversationOpen ? 'hidden md:flex' : 'flex'"
        class="min-h-0 w-full flex-col overflow-hidden rounded-card border border-line bg-surface md:w-72 md:shrink-0"
      >
        <div v-if="contactsLoading" class="flex-1 space-y-3 p-4">
          <Skeleton v-for="i in 5" :key="i" class="h-12 w-full"/>
        </div>

        <div v-else-if="contactsError" class="flex flex-1 items-center justify-center p-4">
          <EmptyState :description="$t('common.networkError')" :title="$t('messages.loadFailed')">
            <Button class="mt-3" size="sm" variant="outline" @click="loadContacts">
              {{ $t('common.retry') }}
            </Button>
          </EmptyState>
        </div>

        <div v-else-if="contacts.length" class="flex-1 overflow-y-auto">
          <button
            v-for="contact in contacts"
            :key="contact.peer_id"
            :class="contact.peer_id === activePeerId ? 'bg-primary-soft' : ''"
            class="flex w-full items-center gap-3 border-b border-line px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-surface-soft"
            type="button"
            @click="openConversation(contact.peer_id)"
          >
            <span
              class="flex h-9 w-9 shrink-0 items-center justify-center rounded-pill bg-surface-soft text-fg-muted"
            >
              <Icon class="h-4 w-4" name="user"/>
            </span>
            <span class="min-w-0 flex-1">
              <span class="flex items-center gap-2">
                <span class="truncate text-sm font-medium text-fg">
                  {{ contact.peer_name || t('messages.peerFallback', {id: contact.peer_id}) }}
                </span>
                <span v-if="contact.last_at" class="ml-auto shrink-0 text-[11px] text-fg-subtle">
                  {{ formatDateTime(contact.last_at) }}
                </span>
              </span>
              <span class="mt-0.5 flex items-center gap-2">
                <span class="truncate text-xs text-fg-muted">{{ contact.last_content }}</span>
                <Badge
                  v-if="contact.unread > 0"
                  :title="t('messages.unreadCount', {n: contact.unread})"
                  class="ml-auto shrink-0"
                >
                  {{ contact.unread > 99 ? '99+' : contact.unread }}
                </Badge>
              </span>
            </span>
          </button>
        </div>

        <div v-else class="flex flex-1 items-center justify-center p-4">
          <EmptyState
            :description="$t('messages.emptyContactsDesc')"
            :title="$t('messages.emptyContacts')"
          />
        </div>
      </section>

      <!-- 右侧：消息流（移动端选中会话后显示） -->
      <section
        :class="conversationOpen ? 'flex' : 'hidden md:flex'"
        class="min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-card border border-line bg-surface"
      >
        <div v-if="activePeerId === null" class="flex flex-1 items-center justify-center p-4">
          <EmptyState :title="$t('messages.selectConversation')"/>
        </div>

        <template v-else>
          <!-- 会话头 -->
          <header class="flex items-center gap-2 border-b border-line px-4 py-3">
            <Button
              :aria-label="$t('messages.backToList')"
              class="md:hidden"
              size="icon"
              variant="ghost"
              @click="backToContacts"
            >
              <Icon class="h-4 w-4" name="chevron-left"/>
            </Button>
            <p class="min-w-0 truncate text-sm font-semibold text-fg">{{ activePeerName }}</p>
          </header>

          <!-- 消息流 -->
          <div ref="listBody" class="min-h-0 flex-1 space-y-1 overflow-y-auto p-4">
            <div v-if="messagesLoading" class="space-y-3">
              <Skeleton
                v-for="i in 4"
                :key="i"
                :class="i % 2 ? '' : 'ml-auto'"
                class="h-10 w-2/3"
              />
            </div>

            <div v-else-if="messagesError" class="flex h-full items-center justify-center">
              <EmptyState :description="$t('common.networkError')" :title="$t('messages.loadFailed')">
                <Button class="mt-3" size="sm" variant="outline" @click="loadMessages">
                  {{ $t('common.retry') }}
                </Button>
              </EmptyState>
            </div>

            <EmptyState
              v-else-if="!messages.length"
              :description="$t('messages.emptyConversationDesc')"
              :title="$t('messages.emptyConversation')"
            />

            <template v-else>
              <div
                v-for="msg in messages"
                :key="msg.id"
                :class="msg.direction === 'out' ? 'justify-end' : 'justify-start'"
                class="flex"
              >
                <div class="max-w-[75%]">
                  <div
                    :class="msg.direction === 'out' ? 'bg-primary text-primary-fg' : 'bg-surface-soft text-fg'"
                    class="break-words rounded-control px-3 py-2 text-sm whitespace-pre-wrap"
                  >
                    {{ msg.content }}
                    <a
                      v-if="msg.attachment_url"
                      :class="msg.direction === 'out' ? 'text-primary-fg' : 'text-primary'"
                      :href="msg.attachment_url"
                      class="mt-1 flex items-center gap-1 text-xs underline"
                      rel="noopener"
                      target="_blank"
                    >
                      <Icon class="h-3.5 w-3.5 shrink-0" name="file-text"/>
                      {{ $t('messages.viewAttachment') }}
                    </a>
                  </div>
                  <p
                    :class="msg.direction === 'out' ? 'text-right' : ''"
                    class="mt-0.5 text-[11px] text-fg-subtle"
                  >
                    {{ formatDateTime(msg.created_at) }}
                  </p>
                </div>
              </div>
            </template>
          </div>

          <!-- 发送条 -->
          <footer class="border-t border-line p-3">
            <p v-if="sendError" class="mb-2 text-xs text-danger">{{ $t('messages.sendFailed') }}</p>
            <div class="flex items-end gap-2">
              <textarea
                v-model="draft"
                :aria-label="$t('messages.inputPlaceholder')"
                :placeholder="$t('messages.inputPlaceholder')"
                class="max-h-32 min-h-9 flex-1 resize-none rounded-control border border-line bg-surface px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-primary focus:outline-none"
                rows="1"
                @input="sendError = false"
                @keydown="onDraftKeydown"
              />
              <Button :disabled="sending || !draft.trim()" @click="sendMessage">
                <Icon class="h-4 w-4" name="send"/>
                {{ sending ? $t('messages.sending') : $t('messages.send') }}
              </Button>
            </div>
          </footer>
        </template>
      </section>
    </div>
  </div>
</template>
