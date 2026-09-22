<script lang="ts" setup>
/**
 * 环形占比图
 *
 * 为什么值得引入图表：后台有 `echarts` 依赖却一处未用（`package.json` 里 `^6.0.0`，
 * 源码 0 引用），报表/监控/仪表盘全靠表格，容量与占比只能靠肉眼比较数字。
 *
 * 三个设计约束：
 *  1. **按需加载** —— 只 import `echarts/core` + `PieChart` + `CanvasRenderer`，
 *     且是动态 import，不进后台初始包；
 *  2. **颜色取自语义令牌** —— 深浅色与用户自选主色都会跟着变（不写死色值）；
 *  3. **没有数据/加载失败都不留白** —— 分别给占位与错误文案。
 */
import {computed, onBeforeUnmount, onMounted, ref, watch} from 'vue'

interface DonutItem {
  label: string
  value: number
  /** 不给就用语义令牌里的默认色序 */
  color?: string
}

const props = withDefaults(
  defineProps<{
    items: DonutItem[]
    /** 圆心下方的小字（通常是口径名，如"文章"） */
    centerLabel?: string
    /** 画布尺寸（px） */
    size?: number
  }>(),
  {centerLabel: '', size: 168},
)

/** 令牌名 → 兜底色（令牌取不到时的后备，例如首次渲染早于样式加载） */
const TOKEN_COLORS: Array<[string, string]> = [
  ['--admin-primary', '#2f6fed'],
  ['--admin-success', '#0f9d63'],
  ['--admin-warning', '#c98a16'],
  ['--admin-danger', '#d64545'],
  ['--admin-fg-subtle', '#98a2b3'],
]

const {isDark} = useTheme()

const canvasRef = ref<HTMLElement | null>(null)
const loading = ref(true)
const failed = ref(false)

/** 用 ResizeObserver 而不是 window resize：容器宽度随侧边栏折叠/窗口都变 */
let observer: ResizeObserver | null = null
let chart: { setOption: (option: unknown) => void; resize: () => void; dispose: () => void } | null = null

const total = computed(() => props.items.reduce((sum, item) => sum + (Number(item.value) || 0), 0))
const isEmpty = computed(() => total.value === 0)

function tokenColor(name: string, fallback: string): string {
  if (!import.meta.client) return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

function colorOf(item: DonutItem, index: number): string {
  if (item.color) return item.color
  const entry: [string, string] = TOKEN_COLORS[index % TOKEN_COLORS.length] ?? ['--admin-primary', '#2f6fed']
  return tokenColor(entry[0], entry[1])
}

async function render(): Promise<void> {
  if (!import.meta.client || !canvasRef.value) return
  if (isEmpty.value) {
    loading.value = false
    return
  }

  loading.value = true
  failed.value = false
  try {
    const [{init, use}, {PieChart}, {CanvasRenderer}] = await Promise.all([
      import('echarts/core'),
      import('echarts/charts'),
      import('echarts/renderers'),
    ])
    use([PieChart, CanvasRenderer])

    if (!canvasRef.value) return
    chart?.dispose()
    chart = init(canvasRef.value)

    const surface = tokenColor('--admin-surface', '#ffffff')
    chart.setOption({
      animationDuration: 260,
      tooltip: {trigger: 'item', formatter: '{b}: {c} ({d}%)'},
      series: [
        {
          type: 'pie',
          radius: ['60%', '84%'],
          center: ['50%', '50%'],
          avoidLabelOverlap: true,
          label: {show: false},
          labelLine: {show: false},
          itemStyle: {borderWidth: 2, borderColor: surface},
          data: props.items.map((item, index) => ({
            name: item.label,
            value: Number(item.value) || 0,
            itemStyle: {color: colorOf(item, index)},
          })),
        },
      ],
    })
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void render()
  if (import.meta.client && canvasRef.value && typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => chart?.resize())
    observer.observe(canvasRef.value)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
  chart?.dispose()
  chart = null
})

// 数据、主题（深浅色）、主色变化都要重画
watch([() => props.items, isDark], () => void render(), {deep: true})
</script>

<template>
  <div class="donut">
    <div :style="{width: `${size}px`, height: `${size}px`}" class="donut__canvas-wrap">
      <div ref="canvasRef" class="donut__canvas"/>

      <div v-if="loading || isEmpty || failed" class="donut__overlay">
        <span v-if="isEmpty" class="donut__overlay-text">{{ $t('admin.common.empty') }}</span>
        <span v-else-if="failed" class="donut__overlay-text">{{ $t('admin.common.loadFailed') }}</span>
      </div>

      <div v-else class="donut__center">
        <span class="donut__total">{{ total }}</span>
        <span v-if="centerLabel" class="donut__center-label">{{ centerLabel }}</span>
      </div>
    </div>

    <ul class="donut__legend">
      <li v-for="(item, index) in items" :key="item.label" class="donut__legend-item">
        <span :style="{backgroundColor: colorOf(item, index)}" class="donut__dot"/>
        <span class="donut__legend-label">{{ item.label }}</span>
        <span class="donut__legend-value">{{ item.value }}</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.donut {
  display: flex;
  gap: var(--admin-gap-lg, 24px);
  align-items: center;
  flex-wrap: wrap;
}

.donut__canvas-wrap {
  position: relative;
  flex: 0 0 auto;
}

.donut__canvas {
  width: 100%;
  height: 100%;
}

.donut__center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.donut__total {
  font-size: 20px;
  font-weight: 600;
  color: var(--admin-fg);
}

.donut__center-label {
  font-size: 12px;
  color: var(--admin-fg-subtle);
}

.donut__overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.donut__overlay-text {
  font-size: var(--admin-font-sm, 13px);
  color: var(--admin-fg-subtle);
}

.donut__legend {
  flex: 1 1 140px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.donut__legend-item {
  display: flex;
  gap: var(--admin-gap-sm, 8px);
  align-items: center;
  padding: 3px 0;
  font-size: var(--admin-font-sm, 13px);
}

.donut__dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  flex: 0 0 auto;
}

.donut__legend-label {
  color: var(--admin-fg-muted);
}

.donut__legend-value {
  margin-left: auto;
  font-weight: 600;
  color: var(--admin-fg);
}
</style>
