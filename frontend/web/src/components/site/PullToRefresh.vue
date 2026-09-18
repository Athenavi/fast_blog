<script lang="ts" setup>
/**
 * 下拉刷新（移动端）
 *
 * 对应原 astro 的 `PullToRefresh.tsx`（含 `usePullToRefresh` hook）。
 *
 * 用原生触摸事件实现，无第三方依赖。要点：
 *  - 只在容器**滚到顶部**时才进入下拉状态，否则交还给正常滚动
 *  - 拉动距离做**阻尼**处理（× 0.5），越拉越难，手感更接近原生
 *  - 是否"正在刷新"由父组件通过 `refreshing` 控制——因为刷新通常是异步的，
 *    组件内部无法知道父组件何时完成
 *
 * 用法：
 * ```vue
 * <PullToRefresh :refreshing="loading" @refresh="reload">
 *   ...内容...
 * </PullToRefresh>
 * ```
 */

const props = withDefaults(
  defineProps<{
    /** 触发刷新的阈值（px） */
    threshold?: number
    /** 最大下拉距离（px） */
    maxPullDistance?: number
    /** 禁用 */
    disabled?: boolean
    /** 由父组件控制的"刷新中"状态 */
    refreshing?: boolean
  }>(),
  {threshold: 70, maxPullDistance: 120, disabled: false, refreshing: false},
)

const emit = defineEmits<{ (e: 'refresh'): void }>()

const root = ref<HTMLElement | null>(null)
const scrollTop = ref(0)
const pullDistance = ref(0)
const dragging = ref(false)
let startY = 0

/** 0~1，用于指示器展示（例如旋转箭头、显示"松开刷新"） */
const progress = computed(() =>
  Math.min(1, pullDistance.value / Math.max(1, props.threshold)),
)

const reached = computed(() => pullDistance.value >= props.threshold)

const indicatorHeight = computed(() => (props.refreshing ? props.threshold : pullDistance.value))

function topOf(el: HTMLElement | null): number {
  if (!el) return 0
  // 容器自身可滚动时用 scrollTop；否则看文档滚动位置
  return el.scrollHeight > el.clientHeight ? el.scrollTop : window.scrollY
}

function onTouchStart(event: TouchEvent): void {
  if (props.disabled || props.refreshing) return
  if (topOf(root.value) > 0) return
  startY = (event.touches[0]?.clientY ?? 0)
  dragging.value = true
}

function onTouchMove(event: TouchEvent): void {
  if (!dragging.value) return
  const delta = (event.touches[0]?.clientY ?? 0) - startY
  if (delta <= 0) {
    pullDistance.value = 0
    return
  }
  // 阻尼：拉动感受更自然
  pullDistance.value = Math.min(props.maxPullDistance, delta * 0.5)
}

function onTouchEnd(): void {
  if (!dragging.value) return
  dragging.value = false

  if (reached.value) {
    pullDistance.value = props.threshold
    emit('refresh')
    return
  }
  pullDistance.value = 0
}

// 父组件刷新结束后收起指示器
watch(
  () => props.refreshing,
  (value, old) => {
    if (old && !value) pullDistance.value = 0
  },
)

function onScroll(): void {
  scrollTop.value = topOf(root.value)
}
</script>

<template>
  <div
    ref="root"
    class="relative"
    @touchcancel="onTouchEnd"
    @touchend="onTouchEnd"
    @scroll.passive="onScroll"
    @touchmove.passive="onTouchMove"
    @touchstart.passive="onTouchStart"
  >
    <!-- 下拉指示器 -->
    <div
      :style="{height: `${indicatorHeight}px`}"
      aria-live="polite"
      class="flex items-center justify-center overflow-hidden transition-[height] duration-200"
    >
      <slot :progress="progress" :refreshing="props.refreshing" name="indicator">
        <div class="flex items-center gap-2 text-sm text-fg-subtle">
          <Icon v-if="props.refreshing" class="h-4 w-4 animate-spin" name="loader-circle"/>
          <Icon
            v-else
            :class="reached ? 'rotate-180' : ''"
            class="h-4 w-4 transition-transform"
            name="arrow-down"
          />
          <span>{{ props.refreshing ? '正在刷新…' : reached ? '松开即可刷新' : '下拉刷新' }}</span>
        </div>
      </slot>
    </div>

    <slot/>
  </div>
</template>
