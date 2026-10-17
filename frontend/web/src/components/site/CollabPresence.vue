<script lang="ts" setup>
/**
 * 顶栏里的协作在场头像
 *
 * 数据来自 `useCollabPresence`（模块级共享状态）：会话由编辑页持有，而这里在布局层，
 * 两者不在一条 props 链上 —— 为什么不改成 Teleport，见 `composables/useCollabPresence.ts`。
 *
 * 前台顶栏与后台顶栏都渲染它，所以样式只用 `--color-*` 这套两端都存在的令牌
 * （后台的 `--admin-*` 本来就别名到它们，见 `styles/admin.css`）。
 */
import type {CollabPeer} from '@/lib/yjs/presence'

/** 超过这个数量折成「+N」：顶栏只有 56px 高，房间再大也不能把导航挤没 */
const MAX_VISIBLE = 5

const {peers, status, count} = useCollabPresence()
const {t} = useI18n()

const visible = computed(() => peers.value.slice(0, MAX_VISIBLE))
const overflow = computed(() => Math.max(0, peers.value.length - MAX_VISIBLE))

/** 头像地址读失败时退回首字母（外链失效是常态，不能让顶栏出现裂图） */
const failed = ref(new Set<number>())

function onAvatarError(peer: CollabPeer): void {
  failed.value = new Set(failed.value).add(peer.clientId)
}

function useInitials(peer: CollabPeer): boolean {
  return !peer.avatar || failed.value.has(peer.clientId)
}

/** 悬停/聚焦时逐个念名字；屏幕阅读器读整组，不然只是一排没有含义的圆 */
const groupLabel = computed(() =>
  [
    t('myPosts.collab.presenceAriaLabel', {count: count.value}),
    peers.value.map((peer) => peer.name).join('、'),
  ].join(': '),
)

const offline = computed(() => status.value === 'disconnected' || status.value === 'rejected')
</script>

<template>
  <ClientOnly>
    <div
      v-if="peers.length"
      :aria-label="groupLabel"
      class="presence"
      role="group"
      :title="groupLabel"
    >
      <span
        v-for="peer in visible"
        :key="peer.clientId"
        :data-self="peer.isSelf ? 'true' : undefined"
        :style="{backgroundColor: useInitials(peer) ? peer.color : undefined}"
        class="presence__item"
        :title="peer.name"
      >
        <img
          v-if="!useInitials(peer)"
          :alt="peer.name"
          :src="peer.avatar || ''"
          class="presence__avatar"
          loading="lazy"
          @error="onAvatarError(peer)"
        >
        <span v-else class="presence__initials">{{ peer.initials }}</span>
      </span>

      <span v-if="overflow" class="presence__more">+{{ overflow }}</span>

      <!-- 掉线时头像会停在最后一份已知状态：不明确标出来，就是在假装还有人 -->
      <span
        v-if="offline"
        :aria-label="t('myPosts.collab.presenceOffline')"
        :title="t('myPosts.collab.presenceOffline')"
        class="presence__warn"
      >
        <Icon class="h-3.5 w-3.5" name="wifi-off"/>
      </span>
    </div>
    <template #fallback>
      <span class="presence"/>
    </template>
  </ClientOnly>
</template>

<style scoped>
.presence {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
}

.presence__item,
.presence__more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 24px;
  height: 24px;
  overflow: hidden;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  color: #fff;
  border: 2px solid var(--color-surface);
  border-radius: 50%;
}

/* 叠放：后一个压前一个，人数多时总宽度仍可控 */
.presence__item + .presence__item,
.presence__item + .presence__more,
.presence__more + .presence__warn {
  margin-left: -7px;
}

/* 自己排在最前，用主色描边标出来 —— 不用文字，一排圆里也能一眼认出自己 */
.presence__item[data-self='true'] {
  border-color: var(--color-primary);
}

.presence__avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
  background: var(--color-surface-soft);
}

.presence__initials {
  letter-spacing: 0.02em;
}

.presence__more {
  color: var(--color-fg-muted);
  background: var(--color-surface-soft);
}

.presence__warn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  margin-left: -4px;
  color: var(--color-danger);
  background: var(--color-surface);
  border-radius: 50%;
}
</style>
