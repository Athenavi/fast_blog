<script lang="ts" setup>
import type {ToastKind} from '@/composables/useToast'
import {cn} from '@/lib/utils'

/**
 * 前台 toast 宿主
 *
 * 挂在 `layouts/default.vue`，页面里用 `useToast()` 推入即可。
 * 底部居中堆叠，`aria-live="polite"` 保证读屏在空闲时播报；点击可立即关闭。
 */
const {items, dismiss} = useToast()

const STYLES = {
  success: {icon: 'circle-check', cls: 'border-success/40'},
  error: {icon: 'alert-circle', cls: 'border-danger/40'},
  info: {icon: 'info', cls: 'border-line'},
} as const

function styleOf(kind: ToastKind) {
  return STYLES[kind] ?? STYLES.info
}
</script>

<template>
  <div
    aria-live="polite"
    class="pointer-events-none fixed inset-x-0 bottom-24 z-[80] flex flex-col items-center gap-2 px-4 sm:bottom-8"
  >
    <TransitionGroup name="toast">
      <button
        v-for="item in items"
        :key="item.id"
        :class="cn('pointer-events-auto flex max-w-md items-start gap-2 rounded-card border bg-surface px-3.5 py-2.5 text-left text-sm text-fg shadow-lg', styleOf(item.kind).cls)"
        type="button"
        @click="dismiss(item.id)"
      >
        <Icon :name="styleOf(item.kind).icon" class="mt-0.5 h-4 w-4 shrink-0 text-fg-muted"/>
        <span class="leading-snug">{{ item.text }}</span>
      </button>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(0.5rem);
}
</style>
