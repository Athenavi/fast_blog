/**
 * 前台数据层（SSR 友好）
 *
 * 与后台的 axios 客户端分开：
 *  - 后台是 CSR（`ssr: false`），token 存本地存储，用 `@/api/request`；
 *  - 前台需要首屏直出与 SEO，因此用 Nuxt 的 `$fetch`，
 *    服务端渲染时通过 `runtimeConfig.public.apiBaseUrl` 走绝对地址，
 *    浏览器侧留空表示同源（生产由 nginx 转发 /api）。
 *
 * 后端统一响应体为 `{code, msg, data, pagination}`，`code === 200` 视为成功。
 */

export interface ApiEnvelope<T> {
  code: number
  msg: string
  data: T
  pagination?: {
    page: number
    page_size: number
    total: number
    pages: number
  }
}

export const CODE_SUCCESS = 200

/** 统一的后端请求前缀 */
export const API_PREFIX = '/api/v3'

/** 构造请求基址：服务端用绝对地址，客户端走同源 */
export function useApiBase(): string {
  if (import.meta.server) {
    const config = useRuntimeConfig()
    const base = config.public.apiBaseUrl || 'http://127.0.0.1:9421'
    return `${base}${API_PREFIX}`
  }
  return API_PREFIX
}

/**
 * 发起一次 GET 请求并解包 `data`。
 *
 * 失败（网络异常或 `code !== 200`）返回 `null`，由调用方决定降级展示，
 * 避免前台因单个区块接口异常而整页 500。
 */
export async function apiGet<T>(
  url: string,
  params?: Record<string, unknown>,
): Promise<T | null> {
  const key = `${useApiBase()}${url}`
  try {
    const resp = await $fetch<ApiEnvelope<T>>(key, {
      params,
      // 前台公开数据无需凭据；登录态接口单独加 headers
      credentials: 'omit',
    })
    if (resp?.code === CODE_SUCCESS) return resp.data
    return null
  } catch {
    return null
  }
}

/** 与 `apiGet` 相同，但同时返回分页信息（列表页需要） */
export async function apiPage<T>(
  url: string,
  params?: Record<string, unknown>,
): Promise<{ items: T[]; total: number; page: number; pageSize: number; pages: number }> {
  const key = `${useApiBase()}${url}`
  const empty = {items: [] as T[], total: 0, page: 1, pageSize: 20, pages: 0}
  try {
    const resp = await $fetch<ApiEnvelope<T[]>>(key, {params, credentials: 'omit'})
    if (resp?.code !== CODE_SUCCESS) return empty
    const items = resp.data ?? []
    return {
      items,
      total: resp.pagination?.total ?? items.length,
      page: resp.pagination?.page ?? Number(params?.page ?? 1),
      pageSize: resp.pagination?.page_size ?? Number(params?.page_size ?? 20),
      pages: resp.pagination?.pages ?? 0,
    }
  } catch {
    return empty
  }
}
