/**
 * OAuth 第三方登录接口（/api/v3/system/oauth，system 域）
 *
 * 字段逐条对照后端 `src/api/v3/modules/system/oauth/schema.py`：
 *   - ProviderOut / AuthorizeUrlOut / CallbackRequest / BindingOut / CallbackResultOut
 * 路径省略 `/api/v3` 前缀（由 request.ts 的 baseURL 提供）。
 *
 * 端点语义（见 controller.py 顶部 docstring）：
 *   - `/providers`、`/{provider}/callback` 为**公开**；
 *   - `/bindings`、`/{provider}/authorize-url`、`DELETE /{provider}` 为**仅认证**，且只操作本人数据；
 *   - 本模块**没有**管理权限码（管理端查看/解除任意用户绑定由 `/system/social` 的
 *     `module_system:social:view` / `module_system:social:delete` 覆盖，职责不重叠）。
 */

import http from '../request'

/** 单个 OAuth 提供方（`configured` 表示系统设置里是否已填 client_id/client_secret） */
export interface OAuthProviderItem {
  key: string
  name: string
  icon: string
  configured: boolean
  supports_pkce: boolean
}

/** 本人已绑定的第三方账号（脱敏：只返回是否已存到 token） */
export interface OAuthBindingItem {
  id: number
  provider?: string | null
  provider_user_id?: string | null
  has_token: boolean
  token_expires_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

/**
 * 授权跳转信息
 *
 * `code_verifier` 由调用方在回调时原样回传（标准 PKCE 做法）；
 * 仅对支持 PKCE 的提供方（后端 `PKCE_PROVIDERS`）返回，其余为 `null`。
 */
export interface OAuthAuthorizeUrl {
  provider: string
  name: string
  authorize_url: string
  state: string
  redirect_uri: string
  code_verifier?: string | null
  code_challenge?: string | null
  code_challenge_method?: string | null
}

/** 回调请求体（POST 形态；GET 回调从同名 query 读取） */
export interface OAuthCallbackPayload {
  code: string
  state: string
  code_verifier?: string | null
  remember_me?: boolean
}

/** 回调结果：登录态 + 绑定信息 */
export interface OAuthCallbackResult {
  provider: string
  user_id: number
  username?: string | null
  bound: boolean
  created_user: boolean
  access_token?: string | null
  refresh_token?: string | null
  token_type: string
  expires_in?: number | null
}

/** 解绑结果 */
export interface OAuthUnbindResult {
  provider: string
  unbound: boolean
}

export const oauthApi = {
  /** 支持的提供方 + 是否已配置（公开；返回数组，非分页） */
  providers: () => http.get<OAuthProviderItem[]>('/system/oauth/providers'),

  /** 本人已绑定的第三方账号（仅认证；返回数组，非分页） */
  bindings: () => http.get<OAuthBindingItem[]>('/system/oauth/bindings'),

  /**
   * 生成授权跳转信息（仅认证）
   *
   * 真实拼接 scope / 带签名的 state / PKCE 的 S256 challenge；凭据未配置时后端返回 400，
   * 前端**不伪造**授权地址。`redirect_uri` 缺省时后端使用配置值。
   */
  authorizeUrl: (provider: string, redirect_uri?: string) =>
    http.get<OAuthAuthorizeUrl>(
      `/system/oauth/${provider}/authorize-url`,
      redirect_uri ? {redirect_uri} : undefined,
    ),

  /**
   * 回调（公开，POST 形态；与 GET 回调同实现）
   *
   * 第三方重定向入口，正常流程由后端直接承接（GET 形态 + 浏览器 cookie）；
   * 这里保留真实接线，供 SPA 侧拿到 code/state 时以 POST 提交。
   */
  callback: (provider: string, payload: OAuthCallbackPayload) =>
    http.post<OAuthCallbackResult>(`/system/oauth/${provider}/callback`, payload),

  /** 解绑本人该提供方（仅认证；未绑定返回 404） */
  unbind: (provider: string) => http.delete<OAuthUnbindResult>(`/system/oauth/${provider}`),
}
