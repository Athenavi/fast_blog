/**
 * 统一的 HTTP 客户端
 *
 * 约定（与后端 v3 契约对齐）：
 *   - 请求前缀 API_BASE_URL（默认 /api/v3）
 *   - 自动注入 Authorization: Bearer <access_token>
 *   - 响应体 code === 200 视为成功；HTTP 401 触发一次静默刷新后重放请求
 *   - 失败统一 ElMessage 提示并 reject（调用方只需 try/catch）
 */

import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import {ElMessage} from 'element-plus'

import {API_BASE_URL, CODE_SUCCESS, STORAGE_REFRESH_TOKEN, STORAGE_TOKEN} from '@/constants'
import {storage} from '@/utils/storage'

import type {ApiResponse, PageQuery, PageResult} from './types'

/** 401 时是否正在刷新 token（避免并发重复刷新） */
let refreshing = false
/** 刷新期间挂起的请求 */
let waiters: Array<(token: string | null) => void> = []

function readToken(): string | null {
  return storage.get<string>(STORAGE_TOKEN)
}

function writeToken(token: string): void {
  storage.set(STORAGE_TOKEN, token)
}

export function clearTokens(): void {
  storage.remove(STORAGE_TOKEN)
  storage.remove(STORAGE_REFRESH_TOKEN)
}

/** 会话失效时跳登录（由 router 注入实际跳转，避免循环依赖） */
let onUnauthorized: () => void = () => {
  if (import.meta.client) window.location.href = '/login'
}

export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler
}

const instance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  withCredentials: true,
})

instance.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = readToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

async function tryRefreshToken(): Promise<string | null> {
  const refreshToken = storage.get<string>(STORAGE_REFRESH_TOKEN)
  try {
    // 直接用裸 axios，避免走拦截器造成递归
    const resp = await axios.post<ApiResponse<{ access_token?: string; refresh_token?: string }>>(
      `${API_BASE_URL}/system/auth/refresh`,
      {refresh_token: refreshToken},
      {withCredentials: true, timeout: 15_000},
    )
    const token = resp.data?.data?.access_token
    if (resp.data?.code === CODE_SUCCESS && token) {
      writeToken(token)
      if (resp.data.data?.refresh_token) {
        storage.set(STORAGE_REFRESH_TOKEN, resp.data.data.refresh_token)
      }
      return token
    }
    return null
  } catch {
    return null
  }
}

instance.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => response,
  async (error) => {
    const status = error?.response?.status as number | undefined
    if (status !== 401) {
      const msg = error?.response?.data?.msg || error?.message || '网络请求失败'
      ElMessage.error(String(msg))
      return Promise.reject(error)
    }

    // 401：尝试静默刷新一次
    const original = error.config as AxiosRequestConfig & { _retried?: boolean }
    if (original?._retried || original?.url?.includes('/system/auth/refresh')) {
      clearTokens()
      onUnauthorized()
      return Promise.reject(error)
    }

    if (refreshing) {
      // 等待正在进行的刷新
      const token = await new Promise<string | null>((resolve) => waiters.push(resolve))
      if (!token) return Promise.reject(error)
      original._retried = true
      original.headers = {...(original.headers as object), Authorization: `Bearer ${token}`}
      return instance.request(original)
    }

    refreshing = true
    const token = await tryRefreshToken()
    refreshing = false
    waiters.forEach((resolve) => resolve(token))
    waiters = []

    if (!token) {
      clearTokens()
      ElMessage.error('登录已过期，请重新登录')
      onUnauthorized()
      return Promise.reject(error)
    }

    original._retried = true
    original.headers = {...(original.headers as object), Authorization: `Bearer ${token}`}
    return instance.request(original)
  },
)

function unwrap<T>(response: AxiosResponse<ApiResponse<T>>, silent = false): T {
  const body = response.data
  if (body?.code === CODE_SUCCESS) {
    return body.data
  }
  if (!silent) {
    ElMessage.error(body?.msg || '请求失败')
  }
  return Promise.reject(new Error(body?.msg || '请求失败')) as unknown as T
}

export const http = {
  /** GET，返回 data */
  async get<T = unknown>(url: string, params?: Record<string, unknown>): Promise<T> {
    const resp = await instance.get<ApiResponse<T>>(url, {params})
    return unwrap(resp)
  },

  /** GET 分页列表，返回 { items, total, ... } */
  async page<T = unknown>(url: string, params?: PageQuery): Promise<PageResult<T>> {
    const resp = await instance.get<ApiResponse<T[]>>(url, {params})
    const body = resp.data
    if (body?.code !== CODE_SUCCESS) {
      ElMessage.error(body?.msg || '请求失败')
      throw new Error(body?.msg || '请求失败')
    }
    return {
      items: body.data ?? [],
      total: body.pagination?.total ?? (body.data?.length ?? 0),
      page: body.pagination?.page ?? (params?.page ?? 1),
      pageSize: body.pagination?.page_size ?? (params?.page_size ?? 20),
      pages: body.pagination?.pages ?? 0,
    }
  },

  async post<T = unknown>(url: string, data?: unknown, params?: Record<string, unknown>): Promise<T> {
    const resp = await instance.post<ApiResponse<T>>(url, data, {params})
    return unwrap(resp)
  },

  async put<T = unknown>(url: string, data?: unknown, params?: Record<string, unknown>): Promise<T> {
    const resp = await instance.put<ApiResponse<T>>(url, data, {params})
    return unwrap(resp)
  },

  async patch<T = unknown>(url: string, data?: unknown): Promise<T> {
    const resp = await instance.patch<ApiResponse<T>>(url, data)
    return unwrap(resp)
  },

  async delete<T = unknown>(url: string, params?: Record<string, unknown>): Promise<T> {
    const resp = await instance.delete<ApiResponse<T>>(url, {params})
    return unwrap(resp)
  },

  /** 文件上传（multipart） */
  async upload<T = unknown>(url: string, formData: FormData): Promise<T> {
    const resp = await instance.post<ApiResponse<T>>(url, formData, {
      headers: {'Content-Type': 'multipart/form-data'},
      timeout: 120_000,
    })
    return unwrap(resp)
  },

  /** 原始实例（极少数需要自定义配置的场景） */
  raw: instance,
}

export default http
