/**
 * 主题与配色
 *
 * 设计约束：组件不感知具体色值，只引用语义令牌（见 `styles/index.css` 的 `@theme`）。
 * 因此这里只做两件事——切换 `data-theme` 与 `data-accent`：
 *  - `data-theme`：`light` / `dark` / `system`（跟随系统）
 *  - `data-accent`：主色系，用户可以自选，后续接入后台设置即可无需改代码
 *
 * 存储策略：
 *  - Vue 侧用 cookie（`fb-theme` / `fb-accent`），保证 SSR 首屏就带上正确属性；
 *  - 另外把 `system` 这一模式记在 localStorage（`fb-theme-mode`），供 `app.vue` 的
 *    内联脚本在首屏前解析，避免闪色。
 */

export type ThemeMode = 'light' | 'dark' | 'system'
export type AccentName = 'blue' | 'violet' | 'emerald' | 'rose' | 'amber'

export const THEME_MODES: Array<{ label: string; value: ThemeMode }> = [
  {label: '浅色', value: 'light'},
  {label: '深色', value: 'dark'},
  {label: '跟随系统', value: 'system'},
]

export const ACCENTS: Array<{ label: string; value: AccentName }> = [
  {label: '默认蓝', value: 'blue'},
  {label: '紫罗兰', value: 'violet'},
  {label: '翡翠绿', value: 'emerald'},
  {label: '玫瑰红', value: 'rose'},
  {label: '琥珀黄', value: 'amber'},
]

export function useTheme() {
  const theme = useCookie<ThemeMode>('fb-theme', {
    default: () => 'system',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 365,
  })
  const accent = useCookie<AccentName>('fb-accent', {
    default: () => 'blue',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 365,
  })

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
    isDark.value = dark
    localStorage.setItem('fb-theme-mode', mode)
  }

  function setTheme(mode: ThemeMode): void {
    theme.value = mode
    applyDom()
  }

  function setAccent(name: AccentName): void {
    accent.value = name
    applyDom()
  }

  /** 在浅色/深色之间快速切换（system 视为其解析结果的反面） */
  function toggleDark(): void {
    setTheme(isDark.value ? 'light' : 'dark')
  }

  onMounted(() => {
    applyDom()
    // system 模式下跟随系统变化
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    media.addEventListener('change', () => {
      if (theme.value === 'system') applyDom()
    })
  })

  return {theme, accent, isDark, setTheme, setAccent, toggleDark}
}
