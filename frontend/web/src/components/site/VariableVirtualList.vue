<script lang="ts" setup>
/**
 * 虚拟列表（高度不固定）
 *
 * 对应原 astro 的 `VariableVirtualList.tsx`。
 *
 * 与 `VirtualList` 的差别：行高未知，所以先用 `estimatedItemHeight` 估算布局，
 * 渲染后用 `ResizeObserver` 实测每行高度并回填，滚动位置随之校正。
 *
 * 这套「估高 → 实测 → 重算偏移」是变高虚拟滚动的通用做法，
 * 不依赖任何虚拟滚动库，只用浏览器原生的 ResizeObserver。
 */
const props = withDefaults(
  defineProps<{
    items: unknown[]
    /** 初始估算行高（px） */
    estimatedItemHeight?: number
    height?: string
    /** 上下额外渲染的条数（变高场景适当放大） */
    overscan?: number
    emptyTitle?: string
    emptyDescription?: string
  }>(),
  {
    estimatedItemHeight: 120,
    height: '600px',
    overscan: 8,
    emptyTitle: '暂无内容',
    emptyDescription: '',
  },
)

const container = ref<HTMLElement | null>(null)
const scrollTop = ref(0)
const viewportHeight = ref(0)

/** 每行实测高度；未测量前用估算值 */
const heights = ref<number[]>([])
const measured = ref<boolean[]>([])

watch(
  () => props.items.length,
  (len) => {
    heights.value = Array.from({length: len}, (_, i) => heights.value[i] ?? props.estimatedItemHeight)
    measured.value = Array.from({length: len}, (_, i) => measured.value[i] ?? false)
  },
  {immediate: true},
)

/** 每行顶部偏移（前缀和） */
const offsets = computed(() => {
  const out: number[] = []
  let acc = 0
  for (let i = 0; i < heights.value.length; i += 1) {
    out.push(acc)
    acc += heights.value[i] ?? props.estimatedItemHeight
  }
  return out
})

const totalHeight = computed(() =>
  heights.value.reduce((sum, h) => sum + h, 0),
)

/** 二分查找：当前滚动位置对应的起始下标 */
function findStart(top: number): number {
  const arr = offsets.value
  let lo = 0
  let hi = arr.length - 1
  let ans = 0
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if ((arr[mid] ?? 0) <= top) {
      ans = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }
  return ans
}

const range = computed(() => {
  if (!props.items.length) return {start: 0, end: 0}
  const start = Math.max(0, findStart(scrollTop.value) - props.overscan)
  const bottom = scrollTop.value + viewportHeight.value
  let end = start
  while (end < offsets.value.length && (offsets.value[end] ?? 0) < bottom) end += 1
  end = Math.min(props.items.length, end + props.overscan)
  return {start, end}
})

const visible = computed(() =>
  props.items.slice(range.value.start, range.value.end).map((item, i) => ({
    item,
    index: range.value.start + i,
  })),
)

function onScroll(): void {
  scrollTop.value = container.value?.scrollTop ?? 0
}

// ---- 实测行高 ----
let resizeObserver: ResizeObserver | null = null

function measure(el: Element, index: number): void {
  const height = (el as HTMLElement).offsetHeight
  if (height > 0 && Math.abs(height - (heights.value[index] ?? 0)) > 1) {
    heights.value[index] = height
    measured.value[index] = true
  }
}

function setRowRef(el: Element | null, index: number): void {
  if (!el) return
  if (typeof ResizeObserver === 'undefined') {
    // 不支持时退回同步测量一次
    nextTick(() => measure(el, index))
    return
  }
  resizeObserver?.observe(el)
  nextTick(() => measure(el, index))
}

onMounted(() => {
  viewportHeight.value = container.value?.clientHeight ?? 0
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const index = Number((entry.target as HTMLElement).dataset.index)
        if (!Number.isNaN(index)) measure(entry.target, index)
      }
    })
  }
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
})
</script>

<template>
  <div>
    <div
      v-if="props.items.length"
      ref="container"
      :style="{height: props.height}"
      class="overflow-y-auto rounded-card border border-line"
      @scroll.passive="onScroll"
    >
      <div :style="{height: `${totalHeight}px`, position: 'relative'}">
        <div
          v-for="row in visible"
          :key="row.index"
          :ref="(el) => setRowRef(el as Element | null, row.index)"
          :data-index="row.index"
          :style="{transform: `translateY(${offsets[row.index] ?? 0}px)`}"
          class="absolute inset-x-0 top-0 border-b border-line last:border-b-0"
        >
          <slot :index="row.index" :item="row.item"/>
        </div>
      </div>
    </div>

    <EmptyState v-else :description="props.emptyDescription" :title="props.emptyTitle"/>
  </div>
</template>
