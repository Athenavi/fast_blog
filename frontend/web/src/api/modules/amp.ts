/**
 * AMP 接口（/api/v3/content/amp）
 *
 * 对齐后端 v3 模块 `content/amp`（controller.py / schema.py / service.py）：
 *   - GET  /content/amp/article/{article_id}  按真文章生成完整 AMP 文档（需 module_content:article:view）
 *   - POST /content/amp/convert               HTML → AMP 元素级转换（需 module_content:article:edit）
 *   - POST /content/amp/validate              AMP 违规校验（需 module_content:article:view）
 *
 * 字段来源：`service.AmpService.render_document` / `convert_to_amp` / `validate_amp` /
 * `generate_for_article` 的返回字典，以及 `schema.AmpConvertRequest` / `AmpValidateRequest`
 * 的请求模型；`site` 复用 `analytics/seo` 的 `schema_org_service.site_context`。
 */

import http from '../request'

/** 自定义 CSS 使用情况（service.render_document 的 css / css_bytes / css_limit / css_truncated） */
export interface AmpCssInfo {
  /** 实际写入 `<style amp-custom>` 的 CSS 字节数 */
  bytes: number
  /** AMP 规范上限（75KB = 76800 字节，service.CSS_LIMIT_BYTES） */
  limit: number
  /** 是否因超限被按字节截断 */
  truncated: boolean
}

/** 单条违规 / 警告（service.validate_amp 的 errors / warnings 元素） */
export interface AmpViolation {
  /** 规则标识，如 missing-canonical / forbidden-tag / forbidden-script / css-limit */
  rule: string
  /** 人类可读说明 */
  message: string
}

/** 校验汇总（service.validate_amp 返回的 summary） */
export interface AmpValidationSummary {
  errors: number
  warnings: number
  css_bytes: number
  css_limit: number
  elements_checked: number
}

/** 校验结果（POST /content/amp/validate 与 convert / generate 内嵌的 validation 同构） */
export interface AmpValidationResult {
  /** 无 errors 即视为合规 */
  valid: boolean
  errors: AmpViolation[]
  warnings: AmpViolation[]
  summary: AmpValidationSummary
}

/** 站点上下文（复用 analytics/seo 的 schema_org_service.site_context） */
export interface AmpSiteContext {
  /** 站点名（sites.name 或 system_settings.site_name，缺省 FastBlog） */
  name: string
  /** 站点基址（已去掉末尾斜杠） */
  base_url: string
  /** 站点 logo（可能为空串） */
  logo?: string
  /** 站点信息来源：sites / system_settings */
  source?: string
}

/** GET /content/amp/article/{article_id} 的响应（service.generate_for_article） */
export interface AmpArticleDocument {
  article_id: number
  title?: string | null
  slug?: string | null
  /** 最终 canonical：article_seo.canonical_url 或 base_url + /article/{slug} */
  canonical_url: string
  site: AmpSiteContext
  /** 文档里实际用到的 AMP 组件（amp-img / amp-video / amp-audio） */
  components: string[]
  /** 转换阶段整棵移除的禁用标签（去重） */
  removed_tags: string[]
  css: AmpCssInfo
  /** 完整 AMP 文档字符串 */
  amp_html: string
  validation: AmpValidationResult
}

/** POST /content/amp/convert 的请求体（schema.AmpConvertRequest） */
export interface AmpConvertPayload {
  /** 待转换的正文 HTML，必填，1..500000 字符 */
  html: string
  /** 标题，可选，≤255 */
  title?: string
  /** 作者，可选，≤255 */
  author_name?: string
  /** canonical URL，可选，≤500 */
  canonical_url?: string
  /** 站点名，可选，≤255 */
  site_name?: string
  /** 封面图 URL，可选，≤1000 */
  featured_image?: string
  /** 发布时间 ISO 字符串，可选，≤64 */
  published_at?: string
  /** 额外 CSS，会并入 `<style amp-custom>`，可选，≤200000 */
  extra_css?: string
}

/** POST /content/amp/convert 的响应（service.convert_to_amp） */
export interface AmpConvertResult {
  amp_html: string
  canonical_url: string
  components: string[]
  removed_tags: string[]
  css: AmpCssInfo
  validation: AmpValidationResult
}

/** POST /content/amp/validate 的请求体（schema.AmpValidateRequest） */
export interface AmpValidatePayload {
  /** 待校验的 HTML，必填，1..500000 字符 */
  html: string
}

export const ampApi = {
  /** 按真文章生成完整 AMP 文档 */
  articleDocument: (articleId: number) =>
    http.get<AmpArticleDocument>(`/content/amp/article/${articleId}`),
  /** 把 HTML 元素级转换为 AMP 文档（响应内嵌一次校验结果） */
  convert: (payload: AmpConvertPayload) =>
    http.post<AmpConvertResult>('/content/amp/convert', payload),
  /** 校验 HTML 是否符合 AMP 规范 */
  validate: (payload: AmpValidatePayload) =>
    http.post<AmpValidationResult>('/content/amp/validate', payload),
}
