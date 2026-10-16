import {CODE_SUCCESS} from '@/composables/useApi'
import {STORAGE_TOKEN} from '@/constants'
import {storage} from '@/utils/storage'

/**
 * 插件动作统一调用器
 *
 * 数据源：v3 `POST /api/v3/extension/plugin/{slug}/action`（T5-10 已自 v2 收敛，
 * 权限码 `module_extension:plugin:configure`）。`@/api/request` 的 axios 把 baseURL
 * 固定成 `/api/v3`，这里继续用 `$fetch` 打同源绝对路径，并手动带上 Bearer token。
 *
 * 响应：v3 envelope `{code, msg, data}`，`data` 是插件方法的**原样返回值**
 * （通常是 `{success, ...}`，也可能是数组等宽松形状）。判定规则：
 *  - envelope `code === 200` 只代表「调度成功」；
 *  - 插件返回 `{success: false, error}` 时整体按失败处理，并把 `error` 透传给调用方。
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
    const response = await $fetch<{ code?: number; data?: T; msg?: string }>(
      `/api/v3/extension/plugin/${slug}/action`,
      {
        method: 'POST',
        body: {action, params},
        headers: token ? {Authorization: `Bearer ${token}`} : {},
      },
    )

    const pluginResult = (response?.data ?? null) as { success?: boolean; error?: string } | null
    const dispatched = response?.code === CODE_SUCCESS
    const pluginOk = pluginResult ? pluginResult.success !== false : true

    return {
      success: dispatched && pluginOk,
      data: pluginResult as T | null,
      error: pluginResult?.error || response?.msg,
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
