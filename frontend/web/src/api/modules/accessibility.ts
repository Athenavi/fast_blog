/** 无障碍（WCAG 2.1）接口（`/api/v3/system/accessibility`，system 域）
 *
 * 8 个端点（与后端 controller.py 一一对应）：
 *   - `config` 读写：读**公开**，写需 `module_system:setting:edit`
 *   - `css` / `skip-links` / `shortcuts` / `aria` / `guide`：纯生成，**公开**
 *   - `validate`：按元素解析的 HTML 校验，需 `module_content:article:edit`
 *
 * 配置落 `system_settings`（键 `accessibility.config`，JSON）。`PUT config`
 * 刻意收原始 dict：未知键会被后端**明确拒绝**（不是静默忽略），非法字号同样 400。
 */

import http from '../request'

/** 无障碍配置（键与后端 `DEFAULT_CONFIG` 一致） */
export interface AccessibilityConfig {
  keyboard_navigation: boolean
  screen_reader_support: boolean
  high_contrast_mode: boolean
  /** small / medium / large / x-large */
  font_size: string
  reduce_motion: boolean
  focus_visible: boolean
  skip_links: boolean
}

/** 保存时只需传改动项；未知键后端会 400 */
export type AccessibilityConfigUpdate = Partial<AccessibilityConfig>

/** 跳过链接项 */
export interface AccessibilitySkipLink {
  id: string
  text: string
  target: string
  aria_label: string
}

/** 键盘快捷键项 */
export interface AccessibilityShortcut {
  keys: string
  action: string
}

/** 可注入前台的样式表生成结果 */
export interface AccessibilityCss {
  config: AccessibilityConfig
  css: string
}

/** ARIA 建议请求 */
export interface AriaSuggestionRequest {
  element_type: string
  /** 可覆盖默认标签，如 {label: '主导航'} */
  context?: Record<string, unknown>
}

/** ARIA 建议结果 */
export interface AriaSuggestion {
  element_type: string
  attributes: Record<string, string>
}

/** 单条无障碍问题（rule 名 + 严重级别 + 定位片段） */
export interface AccessibilityViolation {
  rule: string
  message: string
  /** critical / serious / moderate / minor */
  severity: string
  snippet: string
}

/** HTML 校验结果 */
export interface AccessibilityValidationResult {
  valid: boolean
  score: number
  errors: AccessibilityViolation[]
  warnings: AccessibilityViolation[]
  infos: AccessibilityViolation[]
  summary: {
    errors: number
    warnings: number
    infos: number
    elements_checked: number
  }
}

/** 指南里的一个无障碍特性 */
export interface AccessibilityGuideFeature {
  key: string
  label: string
  hint: string
}

/** 使用指南 */
export interface AccessibilityGuide {
  standard: string
  features: AccessibilityGuideFeature[]
  shortcuts: AccessibilityShortcut[]
  skip_links: AccessibilitySkipLink[]
}

export const accessibilityApi = {
  /** 读取无障碍配置（公开） */
  getConfig: () => http.get<AccessibilityConfig>('/system/accessibility/config'),

  /** 保存无障碍配置（需 `module_system:setting:edit`；未知键 / 非法字号后端会 400） */
  saveConfig: (data: AccessibilityConfigUpdate) =>
    http.put<AccessibilityConfig>('/system/accessibility/config', data),

  /** 生成可注入前台的样式表（公开） */
  getCss: () => http.get<AccessibilityCss>('/system/accessibility/css'),

  /** 跳过链接（公开） */
  skipLinks: () => http.get<AccessibilitySkipLink[]>('/system/accessibility/skip-links'),

  /** 键盘快捷键（公开） */
  shortcuts: () => http.get<AccessibilityShortcut[]>('/system/accessibility/shortcuts'),

  /** 元素 ARIA 建议（公开） */
  aria: (elementType: string, context: Record<string, unknown> = {}) =>
    http.post<AriaSuggestion>('/system/accessibility/aria', {
      element_type: elementType,
      context,
    }),

  /** HTML 无障碍校验（需 `module_content:article:edit`） */
  validate: (html: string) =>
    http.post<AccessibilityValidationResult>('/system/accessibility/validate', {html}),

  /** 使用指南（公开） */
  guide: () => http.get<AccessibilityGuide>('/system/accessibility/guide'),
}
