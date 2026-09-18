import {useWebVitals} from '@/composables/useWebVitals'

/**
 * RUM（真实用户监控）采集
 *
 * 对应原 astro 的 `components/RUMMonitor.tsx`（挂在应用根节点）。这里做成
 * 客户端插件：前台与后台都会采集。
 *
 * 两点刻意的设计：
 *  1. **不产生网络请求**：`web-vitals` 通过动态 `import()` 引入，且上报端点默认
 *     为空 —— 后端 v3 没有 RUM 接收端点，所以只把样本写进 sessionStorage，
 *     供后台「性能面板」查看。后端补上端点后，注入 `NUXT_PUBLIC_RUM_ENDPOINT`
 *     即自动开启批量上报（sendBeacon）。
 *  2. **不抢首屏**：等 `requestIdleCallback`（或 1s 兜底）后再启动采集。
 *     `web-vitals` 会补报启动前已发生的指标，所以不会漏掉 LCP/FCP。
 */
export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig()
  const endpoint = (config.public.rumEndpoint as string) || ''

  const {start} = useWebVitals({endpoint})

  const run = () => void start()

  if (typeof window.requestIdleCallback === 'function') {
    window.requestIdleCallback(run, {timeout: 3000})
  } else {
    window.setTimeout(run, 1000)
  }
})
