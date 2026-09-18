import {STORAGE_TOKEN} from '@/constants'
import {storage} from '@/utils/storage'

/**
 * v2 兼容层调用器
 *
 * 只给「v3 还没有对应域」的能力用 —— 目前是主题配置面板的
 * `GET/PUT /api/v2/themes/{slug}/config`（v3 的 `/extension/theme` 没有
 * `settings_schema` / `component_slots` 这套读写）。
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
    const response = await $fetch<{ success?: boolean; data?: T; error?: string; msg?: string }>(
      `/api/v2${path}`,
      {
        method,
        ...(body === undefined ? {} : {body}),
        headers: token ? {Authorization: `Bearer ${token}`} : {},
      },
    )
    return {
      success: response?.success !== false,
      data: (response?.data ?? null) as T | null,
      error: response?.error || response?.msg,
    }
  } catch (error) {
    return {
      success: false,
      data: null,
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
