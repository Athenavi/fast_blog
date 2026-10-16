/** 第三方集成接口（/api/v3/system/integration，system 域） */

import http from '../request'

export interface SsoProviderItem {
  id: number
  provider_type?: string | null
  name?: string | null
  client_id?: string | null
  has_client_secret: boolean
  authorization_url?: string | null
  token_url?: string | null
  userinfo_url?: string | null
  scope?: string | null
  redirect_uri?: string | null
  attribute_mapping?: string | null
  auto_provision_users: boolean
  default_role?: string | null
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface SsoProviderPayload {
  provider_type: string
  name: string
  client_id: string
  client_secret: string
  authorization_url?: string | null
  token_url?: string | null
  userinfo_url?: string | null
  scope?: string | null
  redirect_uri?: string | null
  attribute_mapping?: string | null
  auto_provision_users?: boolean
  default_role?: string | null
  is_active?: boolean
}

export interface LdapConfigItem {
  id: number
  server_url?: string | null
  bind_dn?: string | null
  has_bind_password: boolean
  base_dn?: string | null
  user_filter?: string | null
  username_attribute?: string | null
  email_attribute?: string | null
  use_ssl: boolean
  verify_certificates: boolean
  auto_sync_users: boolean
  sync_interval: number
  default_role?: string | null
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface LdapConfigPayload {
  server_url: string
  bind_dn?: string | null
  bind_password?: string | null
  base_dn?: string | null
  user_filter?: string | null
  username_attribute?: string | null
  email_attribute?: string | null
  use_ssl?: boolean
  verify_certificates?: boolean
  auto_sync_users?: boolean
  sync_interval?: number
  default_role?: string | null
  is_active?: boolean
}

export const integrationApi = {
  // SSO
  listSso: () => http.get<SsoProviderItem[]>('/system/integration/sso'),

  createSso: (data: SsoProviderPayload) =>
    http.post<SsoProviderItem>('/system/integration/sso', data),

  updateSso: (id: number, data: Partial<SsoProviderPayload>) =>
    http.put<SsoProviderItem>(`/system/integration/sso/${id}`, data),

  removeSso: (id: number) => http.delete<null>(`/system/integration/sso/${id}`),

  // LDAP
  listLdap: () => http.get<LdapConfigItem[]>('/system/integration/ldap'),

  createLdap: (data: LdapConfigPayload) =>
    http.post<LdapConfigItem>('/system/integration/ldap', data),

  updateLdap: (id: number, data: Partial<LdapConfigPayload>) =>
    http.put<LdapConfigItem>(`/system/integration/ldap/${id}`, data),

  removeLdap: (id: number) => http.delete<null>(`/system/integration/ldap/${id}`),
}
