/**
 * 主题与配色
 *
 * 设计约束：组件不感知具体色值，只引用语义令牌（见 `styles/index.css` 的 `@theme`）。
 * 因此这里只做两件事——切换 `data-theme` 与 `data-accent`：
 *  - `data-theme`：`light` / `dark` / `system`（跟随系统）
 *  - `data-accent`：主色系，用户可以自选，后续接入后台设置即可无需改代码
 *
 * ## 存储：localStorage，**不用 cookie**
 *
 * 此前用 cookie，理由是"SSR 首屏就能带上正确属性"。但公开页现在开了 `swr`
 * 边缘缓存（见 `nuxt.config.ts` 的 routeRules），要求"同一份响应可以发给任何访问者"；
 * 而主题/配色是**用户级**状态，一旦参与 SSR 直出就会串号：
 *  - 缓存里某个用户的 `data-theme="dark"` 会被发给所有人；
 *  - 更糟的是 `useCookie` 带 `default` 时会在响应头 `Set-Cookie` 写回默认值，
 *    被缓存后会把别人已选的配色**持久化覆盖**（365 天）。
 *
 * 因此改成：**首屏主题/配色由 `app.vue` 的 `<head>` 内联脚本在 CSS 加载前决定**
 * （早于首次绘制，不会闪色），本 composable 只负责用户交互后的切换与持久化。
 *
 * ⚠️ 两个 localStorage 键与 `app.vue` 内联脚本里的字面量**必须保持一致**。
 */

export type ThemeMode = 'light' | 'dark' | 'system'
export type AccentName = 'blue' | 'violet' | 'emerald' | 'rose' | 'amber'

/** 深浅色模式的 localStorage 键（`app.vue` 内联脚本读同一个键） */
export const THEME_STORAGE_KEY = 'fb-theme-mode'
/** 自选配色的 localStorage 键（`app.vue` 内联脚本读同一个键） */
export const ACCENT_STORAGE_KEY = 'fb-accent-name'

/** 旧版把配色写在 cookie 里，读取时兜底一次，避免老用户丢设置 */
const LEGACY_ACCENT_COOKIE = 'fb-accent'

export const THEME_MODES: Array<{ labelKey: string; value: ThemeMode }> = [
  {labelKey: 'themeModeLight', value: 'light'},
  {labelKey: 'themeModeDark', value: 'dark'},
  {labelKey: 'themeModeSystem', value: 'system'},
]

export const ACCENTS: Array<{ labelKey: string; value: AccentName }> = [
  {labelKey: 'accentBlue', value: 'blue'},
  {labelKey: 'accentViolet', value: 'violet'},
  {labelKey: 'accentEmerald', value: 'emerald'},
  {labelKey: 'accentRose', value: 'rose'},
  {labelKey: 'accentAmber', value: 'amber'},
]

function isThemeMode(value: unknown): value is ThemeMode {
  return value === 'light' || value === 'dark' || value === 'system'
}

function isAccent(value: unknown): value is AccentName {
  return ACCENTS.some((item) => item.value === value)
}

/** 从 localStorage（必要时回落到旧 cookie）读出配色 */
function readStoredAccent(): AccentName {
  try {
    const stored = localStorage.getItem(ACCENT_STORAGE_KEY)
    if (isAccent(stored)) return stored
    const matched = document.cookie.match(new RegExp(`(?:^|;\\s*)${LEGACY_ACCENT_COOKIE}=([^;]+)`))
    const raw = matched?.[1]
    const fromCookie = raw ? decodeURIComponent(raw) : ''
    if (isAccent(fromCookie)) return fromCookie
  } catch {
    // 隐私模式等场景下 localStorage 不可用，走默认值
  }
  return 'blue'
}

/** 从 localStorage 读出深浅色模式 */
function readStoredTheme(): ThemeMode {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    if (isThemeMode(stored)) return stored
  } catch {
    // 同上
  }
  return 'system'
}

export function useTheme() {
  // 用 `useState` 而不是 `useCookie`：
  //  1. 多个调用点（SiteHeader 的 ThemeSwitcher、后台 AppHeader / 命令面板 / 图表）
  //     共享同一份状态；
  //  2. **SSR 阶段不写任何响应头** —— 这是开 swr 共享缓存的前提；
  //  3. 首屏由内联脚本负责，这里不需要参与 SSR 直出。
  // 初始值是中性默认，客户端 `onMounted` 时从 localStorage 恢复。
  const theme = useState<ThemeMode>('theme-mode', () => 'system')
  const accent = useState<AccentName>('theme-accent', () => 'blue')

  /** 当前**实际**生效的深浅色（system 会解析成 light/dark） */
  const isDark = ref(false)

  function applyDom(): void {
    if (!import.meta.client) return
    const root = document.documentElement
    const mode = theme.value
    const dark =
      mode === 'dark' ||
      (mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
    root.dataset.theme = dark ? 'dark' : 'light'
    root.dataset.accent = accent.value
    // Element Plus 官方暗色主题（theme-chalk/dark/css-vars.css）挂在 `html.dark` 上；
    // 后台令牌样式也同时匹配 `.dark` 与 `[data-theme='dark']`，两者保持一致。
    root.classList.toggle('dark', dark)
    isDark.value = dark
    try {
      localStorage.setItem(THEME_STORAGE_KEY, mode)
      localStorage.setItem(ACCENT_STORAGE_KEY, accent.value)
    } catch {
      // 写不进去（隐私模式）不影响本次会话的显示
    }
  }

  /**
   * 主题/配色切换时的过渡只在**切换瞬间**生效。
   *
   * 颜色过渡本身由 `.theme-transitioning` 授给全文档（见 styles/index.css 的说明），
   * 常态下不挂这个类 —— 原先 CSS 用 `body *` 常驻通配，等于给每个元素都挂一份
   * transition 计算：常态下任何颜色变化都被拖慢 150ms，切主题时还会触发全文档的
   * 样式失效与大面积重绘。
   */
  function withTransition(mutate: () => void): void {
    if (!import.meta.client || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      mutate()
      return
    }
    const root = document.documentElement
    root.classList.add('theme-transitioning')
    mutate()
    window.setTimeout(() => root.classList.remove('theme-transitioning'), 200)
  }

  function setTheme(mode: ThemeMode): void {
    theme.value = mode
    withTransition(applyDom)
  }

  function setAccent(name: AccentName): void {
    accent.value = name
    withTransition(applyDom)
  }

  /** 在浅色/深色之间快速切换（system 视为其解析结果的反面） */
  function toggleDark(): void {
    setTheme(isDark.value ? 'light' : 'dark')
  }

  onMounted(() => {
    // 客户端恢复用户设置（SSR 阶段读不到 localStorage，故放在这里）
    theme.value = readStoredTheme()
    accent.value = readStoredAccent()
    applyDom()
    // system 模式下跟随系统变化
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    media.addEventListener('change', () => {
      if (theme.value === 'system') applyDom()
    })
  })

  return {theme, accent, isDark, setTheme, setAccent, toggleDark}
}
