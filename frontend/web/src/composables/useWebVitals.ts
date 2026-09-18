import {shallowRef} from 'vue'

/**
 * 核心 Web Vitals 采集（RUM）
 *
 * 对应原 astro 的 `lib/hooks/useWebVitals` + `components/RUMMonitor.tsx`。
 * 用行业标准库 `web-vitals` 采集 5 项核心指标（LCP / INP / CLS / FCP / TTFB），
 * 评级（good / needs-improvement / poor）与上报批量由这里统一处理。
 *
 * **上报默认关闭**：后端 v3 目前没有 RUM 接收端点，`endpoint` 默认为空字符串，
 * 因此只做本地采集（存 sessionStorage）供后台「性能面板」查看，不产生任何请求。
 * 后端补上端点后，把端点传给 `endpoint` 即开启批量上报（优先 `sendBeacon`）。
 */

export type VitalRating = 'good' | 'needs-improvement' | 'poor'

export type VitalName = 'LCP' | 'INP' | 'CLS' | 'FCP' | 'TTFB'

export interface VitalSample {
  name: VitalName
  value: number
  rating: VitalRating
  /** web-vitals 的指标 id（同一指标的不同报告共享前缀） */
  id: string
  ts: number
  /** 采样时的路径（不含 query，避免把敏感参数写进存储） */
  path: string
  sessionId: string
}

/** 与 web-vitals 默认阈值一致的评级界限 */
export const VITAL_THRESHOLDS: Record<VitalName, { good: number; poor: number }> = {
  LCP: {good: 2500, poor: 4000},
  INP: {good: 200, poor: 500},
  CLS: {good: 0.1, poor: 0.25},
  FCP: {good: 1800, poor: 3000},
  TTFB: {good: 800, poor: 1800},
}

export const VITAL_LABELS: Record<VitalName, string> = {
  LCP: '最大内容绘制',
  INP: '交互到下次绘制',
  CLS: '累计布局偏移',
  FCP: '首次内容绘制',
  TTFB: '首字节时间',
}

export const VITAL_ORDER: VitalName[] = ['LCP', 'INP', 'CLS', 'FCP', 'TTFB']

const SESSION_KEY = '__rum_session__'
const STORAGE_KEY = '__rum_samples__'
const MAX_SAMPLES = 200

/** 采样结果（模块级单例）：采集端写入，性能面板读取 */
const samples = shallowRef<VitalSample[]>([])

function getSessionId(): string {
  try {
    let id = sessionStorage.getItem(SESSION_KEY)
    if (!id) {
      id = `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`
      sessionStorage.setItem(SESSION_KEY, id)
    }
    return id
  } catch {
    return 'anonymous'
  }
}

function restore(): void {
  if (samples.value.length) return
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (raw) samples.value = JSON.parse(raw) as VitalSample[]
  } catch {
    // 存储损坏时从空开始，不影响页面
  }
}

function persist(): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(samples.value.slice(-MAX_SAMPLES)))
  } catch {
    // 配额不足时放弃持久化，内存中的样本仍然可用
  }
}

export interface RumOptions {
  /** 上报端点；留空（默认）表示只本地采集 */
  endpoint?: string
  /** 累积多少条后上报一次 */
  batchSize?: number
  /** 采样率 0~1，默认 1（全采） */
  sampleRate?: number
}

let started = false

/**
 * 启动采集并返回共享的样本列表。
 * 幂等：重复调用只会启动一次（首个调用者的 options 生效）。
 */
export function useWebVitals(options: RumOptions = {}) {
  const {endpoint = '', batchSize = 10, sampleRate = 1} = options

  async function start(): Promise<void> {
    if (started) return
    started = true

    restore()

    const {onCLS, onFCP, onINP, onLCP, onTTFB} = await import('web-vitals')

    const buffer: VitalSample[] = []
    const canReport =
      Boolean(endpoint) && typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function'

    function flush(): void {
      if (!canReport || !buffer.length) return
      const batch = buffer.splice(0, buffer.length)
      try {
        navigator.sendBeacon(endpoint, new Blob([JSON.stringify(batch)], {type: 'application/json'}))
      } catch {
        // 上报失败不影响本地采集
      }
    }

    function record(metric: { name: string; value: number; rating: string; id: string }): void {
      if (sampleRate < 1 && Math.random() > sampleRate) return

      const sample: VitalSample = {
        name: metric.name as VitalName,
        value: metric.value,
        rating: (metric.rating as VitalRating) || 'good',
        id: metric.id,
        ts: Date.now(),
        path: typeof location === 'undefined' ? '' : location.pathname,
        sessionId: getSessionId(),
      }

      samples.value = [...samples.value, sample].slice(-MAX_SAMPLES)
      persist()

      if (canReport) {
        buffer.push(sample)
        if (buffer.length >= batchSize) flush()
      }
    }

    onCLS(record)
    onFCP(record)
    onINP(record)
    onLCP(record)
    onTTFB(record)

    if (canReport) {
      // 页面隐藏/卸载前把剩余样本送出（sendBeacon 在卸载阶段仍可靠）
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') flush()
      })
      window.addEventListener('pagehide', flush)
    }
  }

  function clear(): void {
    samples.value = []
    persist()
  }

  return {samples, start, clear}
}

/** 按阈值给数值评级（面板展示用；web-vitals 自带的 rating 已写入样本） */
export function rateVital(name: VitalName, value: number): VitalRating {
  const threshold = VITAL_THRESHOLDS[name]
  if (!threshold) return 'good'
  if (value <= threshold.good) return 'good'
  if (value <= threshold.poor) return 'needs-improvement'
  return 'poor'
}
