import {STORAGE_TOKEN} from '@/constants'
import {storage} from '@/utils/storage'

/**
 * 插件动作统一调用器
 *
 * 后端插件动作端点是 **v2** 的 `POST /api/v2/plugins/{slug}/action`
 * （`src/api/v2/plugins/plugin_management.py`，需管理员权限），
 * 而 `@/api/request` 的 axios 实例把 baseURL 固定成 `/api/v3`，
 * 所以这里绕开实例、直接用 `$fetch` 打同源绝对路径，并手动带上 Bearer token。
 *
 * 响应形如 `{success, data, error}`（v2 风格，与 v3 的 `{code, msg, data}` 不同）。
 *
 * 仅 v2 有该端点这件事已登记在 `docs/refactor/FUTURE_WORK_PLAN.md` §5。
 */
export interface PluginActionResult<T> {
  success: boolean
  data: T | null
  error?: string
}

export async function pluginAction<T = unknown>(
  slug: string,
  action: string,
  params: Record<string, unknown> = {},
): Promise<PluginActionResult<T>> {
  const token = storage.get<string>(STORAGE_TOKEN)
  try {
    const response = await $fetch<{ success?: boolean; data?: T; error?: string; msg?: string }>(
      `/api/v2/plugins/${slug}/action`,
      {
        method: 'POST',
        body: {action, params},
        headers: token ? {Authorization: `Bearer ${token}`} : {},
      },
    )
    return {
      success: response?.success === true,
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
