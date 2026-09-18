/**
 * 三方脚本管理
 *
 * 对应原 astro 的 `ThirdPartyScripts.tsx`。
 *
 * astro 侧是手动往 `<head>` 插 `<script>`；Nuxt 里用 **`@nuxt/scripts`** 的 `useScript()`：
 *  - 按需加载（`trigger: 'onNuxtReady' | 'client' | 'manual'`），不阻塞首屏
 *  - 统一管理加载状态（`status`），失败可降级
 *  - 便于将来接入同意管理（隐私合规）时集中收口
 *
 * 目前项目**没有配置任何三方脚本**（没有统计代码、没有外链 SDK），
 * 所以这里只提供能力与调用约定，不产生任何网络请求。
 *
 * 用法（将来需要时）：
 * ```ts
 * const {status} = useThirdPartyScript('umami', {
 *   src: 'https://analytics.example.com/script.js',
 *   trigger: 'idle',
 * })
 * ```
 */

export interface ThirdPartyScriptOptions {
  /** 脚本地址 */
  src: string
  /**
   * 加载时机（`@nuxt/scripts` 的取值）：
   *  - `onNuxtReady`：Nuxt 就绪后加载（默认，不阻塞首屏）
   *  - `client`：客户端挂载时加载
   *  - `manual`：完全手动控制
   */
  trigger?: 'onNuxtReady' | 'client' | 'manual'
  /** 透传到 script 标签的属性 */
  attrs?: Record<string, string>
  /** 是否只在生产环境加载（开发时不污染统计） */
  productionOnly?: boolean
}

export function useThirdPartyScript(name: string, options: ThirdPartyScriptOptions) {
  const enabled = computed(() => {
    if (options.productionOnly === false) return true
    return import.meta.env.PROD
  })

  /**
   * `useScript(input, options)`：
   *  - 第一个参数只接受 script 标签属性（src / async / data-* 等）
   *  - `trigger` 属于第二个参数的选项
   * 未启用时不加载任何第三方资源。
   */
    // `useScript` 要求 input 上必须有 src；禁用时给空对象并断言，
    // 运行时不会产生任何请求（@nuxt/scripts 只在有 src 时才加载）。
  const input = (enabled.value ? {src: options.src, ...(options.attrs ?? {})} : {}) as {
      src: string
    }

  const script = useScript(input, {
    trigger: options.trigger ?? 'onNuxtReady',
    use: () => ({}),
  })

  return {
    status: computed(() => script.status.value),
    /** 脚本是否已就绪 */
    ready: computed(() => script.status.value === 'loaded'),
  }
}

/**
 * 统一的三方脚本清单。
 *
 * 保持为空是**有意为之**：加任何统计/客服/地图 SDK 都应在这里登记，
 * 便于一处审计「页面到底加载了哪些第三方代码」。
 */
export const THIRD_PARTY_SCRIPTS: Record<string, ThirdPartyScriptOptions> = {}

/** 按登记表批量启用（在 app.vue 或布局里调用一次） */
export function useThirdPartyScripts() {
  const scripts: Record<string, ReturnType<typeof useThirdPartyScript>> = {}
  for (const [name, options] of Object.entries(THIRD_PARTY_SCRIPTS)) {
    scripts[name] = useThirdPartyScript(name, options)
  }
  return scripts
}
