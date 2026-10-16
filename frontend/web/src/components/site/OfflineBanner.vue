<script lang="ts" setup>
const {t} = useI18n()
/**
 * 断网 / 弱网提示条（前台）
 *
 * 对应 astro 版 `OfflineBanner.tsx`（T1-3 迁移）：
 *  - 离线 → danger 色横幅 + 「重试」（整页刷新）；
 *  - 在线但 2G 及以下 → warning 色横幅提示慢网（对应原版 isSlow 分支）；
 *  - 右侧 × 可关闭；离线 ↔ 在线状态切换后重新显示（手动关闭只对当前状态生效）。
 * 与原版的差异：关闭改用响应式 `dismissed`（原来是 DOM `display:none` hack）；
 * 配色从硬编码灰阶/红黄改为语义令牌；`useNetwork()` 来自已装的 @vueuse/core。
 * mounted 后才渲染：SSR 首帧不输出，避免 `navigator.onLine` 读写差异造成水合错位。
 */
import {useNetwork} from '@vueuse/core'

const {isOnline, effectiveType} = useNetwork()

const mounted = ref(false)
const dismissed = ref(false)

onMounted(() => {
  mounted.value = true
})

watch(isOnline, () => {
  dismissed.value = false
})

/** 2G 及以下视为慢网（原版 isSlow 的等价判定） */
const isSlow = computed(
  () => isOnline.value && (effectiveType.value === 'slow-2g' || effectiveType.value === '2g'),
)

const visible = computed(() => mounted.value && !dismissed.value && (isSlow.value || !isOnline.value))

function retry(): void {
  window.location.reload()
}
</script>

<template>
  <div
    v-if="visible"
    :class="isOnline ? 'bg-warning-soft text-warning' : 'bg-danger-soft text-danger'"
    class="fixed inset-x-0 top-0 z-[60] flex items-center justify-between gap-2 px-4 py-2 text-sm"
    role="alert"
  >
    <div class="flex min-w-0 items-center gap-2">
      <Icon v-if="isOnline" class="h-4 w-4 shrink-0 animate-spin" name="refresh-cw"/>
      <Icon v-else class="h-4 w-4 shrink-0" name="wifi-off"/>
      <span class="truncate">
        {{
          isOnline ? t('site.networkSlow', {type: effectiveType || t('site.networkUnknown')}) : t('site.networkOffline')
        }}
      </span>
    </div>
    <div class="ml-2 flex shrink-0 items-center gap-1">
      <button
        v-if="!isOnline"
        class="flex items-center gap-1 rounded-control bg-surface px-2 py-1 text-xs transition-colors hover:bg-surface-soft"
        type="button"
        @click="retry"
      >
        <Icon class="h-3 w-3" name="refresh-cw"/>
        {{ $t('common.retry') }}
      </button>
      <button
        :aria-label="$t('site.dismissAriaLabel')"
        class="rounded-control p-1 transition-colors hover:bg-surface"
        type="button"
        @click="dismissed = true"
      >
        <Icon class="h-4 w-4" name="x"/>
      </button>
    </div>
  </div>
</template>
