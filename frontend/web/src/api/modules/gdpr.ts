/** GDPR 合规同意记录接口（/api/v3/system/gdpr，system 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface GdprConsentItem {
  id: number
  user_id?: number | null
  consent_type?: string | null
  granted: boolean
  details?: string | null
  ip_address?: string | null
  user_agent?: string | null
  created_at?: string | null
}

export interface GdprConsentQuery extends PageQuery {
  user_id?: number
  consent_type?: string
  granted?: boolean
}

export interface GdprStats {
  total: number
  granted: number
  revoked: number
  by_type: Record<string, number>
}

// ─────────────────────── 合规检查与文档生成（追加） ───────────────────────
// 对齐 v3 controller.py：GET /system/gdpr/compliance/{check,cookie-consent,privacy-policy}
// 字段严格对应 compliance_service.py 的返回结构（checklist / privacy_policy / cookie_consent_html）。

/** 单条检查项（checklist 返回的 gdpr/pci_dss items 元素） */
export interface GdprCheckItem {
  key: string
  status: 'ok' | 'warn' | 'fail'
  message: string
  evidence: Record<string, unknown>
}

/** 检查项汇总计数（按 status 计数） */
export interface GdprCheckSummary {
  ok: number
  warn: number
  fail: number
}

/** 一组检查（GDPR 或 PCI DSS） */
export interface GdprCheckGroup {
  items: GdprCheckItem[]
  summary: GdprCheckSummary
}

/** 合规配置（system_settings 键 gdpr.compliance.settings） */
export interface GdprComplianceSettings {
  retention_days: number
  require_consent: boolean
  allow_data_export: boolean
  allow_data_deletion: boolean
  contact_email: string
  privacy_policy_url: string
}

/** GET /system/gdpr/compliance/check 返回 */
export interface GdprComplianceReport {
  generated_at: string
  settings: GdprComplianceSettings
  gdpr: GdprCheckGroup
  pci_dss: GdprCheckGroup
}

/** 文档生成时回显的站点信息（compliance_service.site_info） */
export interface GdprSiteInfo {
  name: string
  url: string
  contact_email: string
  privacy_policy_url: string
  retention_days: string
}

/** GET /system/gdpr/compliance/privacy-policy 返回（format 决定 content 是 markdown 还是 html） */
export interface GdprPrivacyPolicy {
  site: GdprSiteInfo
  format: 'markdown' | 'html'
  content: string
}

/** GET /system/gdpr/compliance/cookie-consent 返回 */
export interface GdprCookieConsent {
  site: GdprSiteInfo
  content: string
}

export const gdprApi = {
  list: (params?: GdprConsentQuery) => http.page<GdprConsentItem>('/system/gdpr/consent', params),

  stats: () => http.get<GdprStats>('/system/gdpr/consent/stats'),

  remove: (id: number) => http.delete<null>(`/system/gdpr/consent/${id}`),

  /** GDPR / PCI DSS 合规检查（权限 module_system:gdpr:view） */
  checkCompliance: () => http.get<GdprComplianceReport>('/system/gdpr/compliance/check'),

  /** 生成隐私政策（as_html=true 返回 HTML，false 返回 Markdown；权限 module_system:gdpr:view） */
  privacyPolicy: (asHtml = false) =>
    http.get<GdprPrivacyPolicy>('/system/gdpr/compliance/privacy-policy', {as_html: asHtml}),

  /** 生成 Cookie 同意横幅 HTML（权限 module_system:gdpr:view） */
  cookieConsent: () => http.get<GdprCookieConsent>('/system/gdpr/compliance/cookie-consent'),
}
