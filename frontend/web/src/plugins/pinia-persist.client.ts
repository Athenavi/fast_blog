/**
 * pinia 持久化（仅客户端）
 *
 * 放在 `.client` 插件里，避免 SSR 阶段访问 localStorage。
 */
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.$pinia.use(piniaPluginPersistedstate)
})
