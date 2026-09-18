<script lang="ts" setup>
import {computed, onBeforeUnmount, onMounted, ref} from 'vue'

import {useWebVitals, VITAL_LABELS, VITAL_ORDER, type VitalName, type VitalSample,} from '@/composables/useWebVitals'

/**
 * 性能面板（后台浮动）
 *
 * 对应原 astro 的 `components/PerfDashboard.tsx`：展示核心 Web Vitals
 * （LCP / INP / CLS / FCP / TTFB）、长任务累计、慢资源（>1s）与可获取时的 JS 堆内存。
 *
 * 显示规则：开发环境默认展开；生产环境默认隐藏，可用 `Ctrl/Cmd + Shift + P`
 * 切换，或在 URL 上追加 `?perf=1` 强制打开。选择记在 localStorage。
 *
 * 数据来自 `useWebVitals`（web-vitals 采集 + sessionStorage 持久化），
 * 面板只读，不产生任何网络请求。
 */
const {samples, clear} = useWebVitals()

const open = ref(false)

const longTasks = ref(0)
const slowResources = ref<Array<{ name: string; duration: number }>>([])
const heap = ref<{ used: number; limit: number } | null>(null)

const RATING_COLORS: Record<string, string> = {
  good: '#10b981',
  'needs-improvement': '#f59e0b',
  poor: '#ef4444',
}

/** 每项指标只保留最新一次采样 */
const latest = computed(() => {
  const map = new Map<VitalName, VitalSample>()
  for (const sample of samples.value) map.set(sample.name, sample)
  return map
})

function vitalText(name: VitalName): string {
  const sample = latest.value.get(name)
  if (!sample) return '—'
  return sample.name === 'CLS' ? sample.value.toFixed(3) : `${Math.round(sample.value)} ms`
}

function vitalColor(name: VitalName): string {
  const sample = latest.value.get(name)
  return sample ? (RATING_COLORS[sample.rating] ?? '#9ca3af') : '#9ca3af'
}

function formatBytes(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)))
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}

let observers: PerformanceObserver[] = []
let heapTimer: ReturnType<typeof setInterval> | null = null

function setupObservers(): void {
  if (typeof PerformanceObserver === 'undefined') return

  try {
    const long = new PerformanceObserver((list) => {
      longTasks.value += list.getEntries().length
    })
    long.observe({entryTypes: ['longtask']})
    observers.push(long)
  } catch {
    // 浏览器不支持 longtask
  }

  try {
    const resource = new PerformanceObserver((list) => {
      const slow = list
        .getEntries()
        .filter((entry) => entry.duration > 1000)
        .map((entry) => ({name: entry.name, duration: Math.round(entry.duration)}))
      if (slow.length) slowResources.value = [...slow, ...slowResources.value].slice(0, 8)
    })
    resource.observe({entryTypes: ['resource']})
    observers.push(resource)
  } catch {
    // 浏览器不支持 resource timing
  }
}

function sampleHeap(): void {
  const perf = performance as Performance & {
    memory?: { usedJSHeapSize: number; jsHeapSizeLimit: number }
  }
  heap.value = perf.memory
    ? {used: perf.memory.usedJSHeapSize, limit: perf.memory.jsHeapSizeLimit}
    : null
}

function toggle(): void {
  open.value = !open.value
  try {
    localStorage.setItem('__perf_panel__', open.value ? '1' : '0')
  } catch {
    // 隐私模式下忽略
  }
}

function reset(): void {
  clear()
  longTasks.value = 0
  slowResources.value = []
}

function onKeydown(event: KeyboardEvent): void {
  if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 'p') {
    event.preventDefault()
    toggle()
  }
}

onMounted(() => {
  let remembered = false
  try {
    remembered = localStorage.getItem('__perf_panel__') === '1'
  } catch {
    remembered = false
  }
  const forced = new URLSearchParams(window.location.search).has('perf')
  open.value = forced || remembered || Boolean(import.meta.dev)

  setupObservers()
  sampleHeap()
  heapTimer = setInterval(sampleHeap, 3000)

  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  observers.forEach((observer) => observer.disconnect())
  observers = []
  if (heapTimer) clearInterval(heapTimer)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <!-- 折叠态：右下角悬浮入口 -->
  <button
    v-if="!open"
    class="perf-toggle"
    :title="$t('admin.shared.admin.PerfDashboard.performancePanelCtrlShiftP')"
    type="button"
    @click="toggle"
  >
    <Icon class="h-4 w-4" name="monitor"/>
  </button>

  <section v-else class="perf-panel">
    <header class="perf-panel__header">
      <span class="perf-panel__title">{{ $t('admin.shared.admin.PerfDashboard.performancePanel') }}</span>
      <button class="perf-panel__action" type="button" @click="reset">{{
          $t('admin.shared.admin.PerfDashboard.clear')
        }}
      </button>
      <button class="perf-panel__action" type="button" @click="toggle">
        {{ $t('admin.shared.admin.PerfDashboard.collapse') }}
      </button>
    </header>

    <div class="perf-panel__body">
      <ul class="perf-panel__vitals">
        <li v-for="name in VITAL_ORDER" :key="name" class="perf-panel__vital">
          <span :title="VITAL_LABELS[name]" class="perf-panel__vital-name">{{ name }}</span>
          <span :style="{color: vitalColor(name)}" class="perf-panel__vital-value">{{ vitalText(name) }}</span>
        </li>
      </ul>

      <dl class="perf-panel__meta">
        <div>
          <dt>{{ $t('admin.shared.admin.PerfDashboard.longTasks') }}</dt>
          <dd>{{ longTasks }}</dd>
        </div>
        <div v-if="heap">
          <dt>{{ $t('admin.shared.admin.PerfDashboard.jsHeap') }}</dt>
          <dd>{{ formatBytes(heap.used) }} / {{ formatBytes(heap.limit) }}</dd>
        </div>
        <div>
          <dt>{{ $t('admin.shared.admin.PerfDashboard.samples') }}</dt>
          <dd>{{ samples.length }}</dd>
        </div>
      </dl>

      <div v-if="slowResources.length" class="perf-panel__slow">
        <p class="perf-panel__label">{{ $t('admin.shared.admin.PerfDashboard.slowResourcesGt1S') }}</p>
        <ul>
          <li v-for="(item, index) in slowResources" :key="`${item.name}-${index}`">
            <span class="perf-panel__slow-name">{{ item.name.split('/').pop() }}</span>
            <span>{{ item.duration }} ms</span>
          </li>
        </ul>
      </div>

      <p v-else class="perf-panel__label perf-panel__label--muted">
        {{ $t('admin.shared.PerfDashboard.noSlowResources') }}
      </p>
    </div>
  </section>
</template>

<style scoped>
.perf-toggle {
  position: fixed;
  right: 16px;
  bottom: 16px;
  z-index: 2000;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  color: #e5e7eb;
  cursor: pointer;
  background-color: #1f2937;
  border: 1px solid #374151;
  border-radius: 9999px;
  box-shadow: 0 4px 12px rgb(0 0 0 / 25%);
  transition: opacity 0.15s ease;
  opacity: 0.75;
}

.perf-toggle:hover {
  opacity: 1;
}

.perf-panel {
  position: fixed;
  right: 16px;
  bottom: 16px;
  z-index: 2000;
  width: 268px;
  overflow: hidden;
  font-size: 12px;
  color: #e5e7eb;
  background-color: #1f2937;
  border: 1px solid #374151;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgb(0 0 0 / 30%);
}

.perf-panel__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background-color: #111827;
}

.perf-panel__title {
  flex: 1;
  font-size: 12px;
  font-weight: 600;
}

.perf-panel__action {
  padding: 2px 6px;
  font-size: 11px;
  color: #9ca3af;
  cursor: pointer;
  background: transparent;
  border: 1px solid #374151;
  border-radius: 4px;
}

.perf-panel__action:hover {
  color: #e5e7eb;
  border-color: #4b5563;
}

.perf-panel__body {
  padding: 8px 10px 10px;
}

.perf-panel__vitals {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 4px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.perf-panel__vital {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 3px 6px;
  background-color: rgb(255 255 255 / 4%);
  border-radius: 5px;
}

.perf-panel__vital-name {
  color: #9ca3af;
}

.perf-panel__vital-value {
  font-variant-numeric: tabular-nums;
}

.perf-panel__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin: 8px 0 0;
}

.perf-panel__meta div {
  display: flex;
  gap: 4px;
}

.perf-panel__meta dt {
  color: #9ca3af;
}

.perf-panel__meta dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}

.perf-panel__label {
  margin: 8px 0 4px;
  color: #9ca3af;
}

.perf-panel__label--muted {
  color: #6b7280;
}

.perf-panel__slow ul {
  padding: 0;
  margin: 0;
  list-style: none;
}

.perf-panel__slow li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 2px 0;
}

.perf-panel__slow-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
