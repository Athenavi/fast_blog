import {CODE_SUCCESS} from '@/composables/useApi'
import {STORAGE_TOKEN} from '@/constants'
import {storage} from '@/utils/storage'

/**
 * 主题配置调用器（`GET/PUT /api/v3/extension/theme/{slug}/config`）
 *
 * 自 v2 收敛到 v3（T5-10）：v3 的按 slug 配置端点与 `/active/config`（只管激活主题）
 * 分离，主题配置页（fastblog-default / magazine / modern-minimal）配置各自的 slug。
 *
 * 与 `pluginAction` 同理：`@/api/request` 的 axios 把 baseURL 固定成 `/api/v3`，
 * 所以这里绕开实例、直接用 `$fetch` 打同源绝对路径，并带上 Bearer token。
 */
export interface LegacyResult<T> {
  success: boolean
  data: T | null
  error?: string
}

async function request<T>(
  method: 'GET' | 'PUT',
  path: string,
  body?: unknown,
): Promise<LegacyResult<T>> {
  const token = storage.get<string>(STORAGE_TOKEN)
  try {
    const response = await $fetch<{ code?: number; data?: T; msg?: string }>(`/api/v3${path}`, {
      method,
      ...(body === undefined ? {} : {body}),
      headers: token ? {Authorization: `Bearer ${token}`} : {},
    })
    return {
      success: response?.code === CODE_SUCCESS,
      data: (response?.data ?? null) as T | null,
      error: response?.msg,
    }
  } catch (error) {
    return {
      success: false,
      data: null,
      // 兜底文案（纯工具层，无 i18n 上下文）
      error: error instanceof Error ? error.message : '请求失败',
    }
  }
}

export function legacyGet<T = unknown>(path: string): Promise<LegacyResult<T>> {
  return request<T>('GET', path)
}

export function legacyPut<T = unknown>(path: string, body: unknown): Promise<LegacyResult<T>> {
  return request<T>('PUT', path, body)
}
