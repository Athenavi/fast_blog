<script lang="ts" setup>
import {computed} from 'vue'

import type {ToastKind} from '@/composables/useToast'
import {cn} from '@/lib/utils'

/**
 * 前台 toast 宿主
 *
 * 挂在 `layouts/default.vue`（以及 app.vue，覆盖 `layout: false` 的页面），页面里用 `useToast()` 推入即可。
 *
 * 三条无障碍/可用性约定：
 *  1. **按严重程度分两个 live region** —— 错误/警告用 `assertive`（读屏立即播报），
 *     其余用 `polite`（排队播报，不打断）；
 *  2. **每条都有明确的关闭按钮**（此前只能靠点击整块，用户看不出来能关）；
 *  3. **鼠标悬停暂停计时** —— 正在读的时候提示不会溜走（时限可控）。
 */
const {items, dismiss, pause, resume} = useToast()

const STYLES = {
  success: {icon: 'circle-check', cls: 'border-success/40'},
  error: {icon: 'alert-circle', cls: 'border-danger/40'},
  warning: {icon: 'alert-triangle', cls: 'border-warning/40'},
  info: {icon: 'info', cls: 'border-line'},
} as const

function styleOf(kind: ToastKind) {
  return STYLES[kind] ?? STYLES.info
}

/** 需要打断播报的（错误/警告）与可以排队播报的（成功/信息）分开渲染 */
const urgent = computed(() => items.value.filter((item) => item.kind === 'error' || item.kind === 'warning'))
const calm = computed(() => items.value.filter((item) => item.kind !== 'error' && item.kind !== 'warning'))

function onEnter(): void {
  items.value.forEach((item) => pause(item.id))
}

function onLeave(): void {
  items.value.forEach((item) => resume(item.id))
}
</script>

<template>
  <div class="pointer-events-none fixed inset-x-0 bottom-24 z-[80] flex flex-col items-center gap-2 px-4 sm:bottom-8">
    <div
      aria-live="assertive"
      class="flex flex-col items-center gap-2"
      @mouseenter="onEnter"
      @mouseleave="onLeave"
    >
      <TransitionGroup name="toast">
        <div
          v-for="item in urgent"
          :key="item.id"
          :class="cn('pointer-events-auto flex max-w-md items-start gap-2 rounded-card border bg-surface px-3.5 py-2.5 text-sm text-fg shadow-lg', styleOf(item.kind).cls)"
        >
          <Icon :name="styleOf(item.kind).icon" class="mt-0.5 h-4 w-4 shrink-0 text-fg-muted"/>
          <span class="leading-snug">{{ item.text }}</span>
          <button
            :aria-label="$t('site.dismissAriaLabel')"
            class="toast__close"
            type="button"
            @click="dismiss(item.id)"
          >
            <Icon class="h-3.5 w-3.5" name="x"/>
          </button>
        </div>
      </TransitionGroup>
    </div>

    <div
      aria-live="polite"
      class="flex flex-col items-center gap-2"
      @mouseenter="onEnter"
      @mouseleave="onLeave"
    >
      <TransitionGroup name="toast">
        <div
          v-for="item in calm"
          :key="item.id"
          :class="cn('pointer-events-auto flex max-w-md items-start gap-2 rounded-card border bg-surface px-3.5 py-2.5 text-sm text-fg shadow-lg', styleOf(item.kind).cls)"
        >
          <Icon :name="styleOf(item.kind).icon" class="mt-0.5 h-4 w-4 shrink-0 text-fg-muted"/>
          <span class="leading-snug">{{ item.text }}</span>
          <button
            :aria-label="$t('site.dismissAriaLabel')"
            class="toast__close"
            type="button"
            @click="dismiss(item.id)"
          >
            <Icon class="h-3.5 w-3.5" name="x"/>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<style scoped>
.toast__close {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  margin-left: 2px;
  color: var(--color-fg-subtle);
  cursor: pointer;
  background: transparent;
  border: none;
  border-radius: 4px;
  transition: background-color 0.12s ease, color 0.12s ease;
}

.toast__close:hover {
  color: var(--color-fg);
  background: var(--color-surface-soft);
}

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
