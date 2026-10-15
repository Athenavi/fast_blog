/** 用户会话状态：token、用户信息、权限判断 */

import {defineStore} from 'pinia'

import type {CurrentUser, LoginParams} from '@/api/modules/auth'
import {STORAGE_REFRESH_TOKEN, STORAGE_TOKEN, STORAGE_USER} from '@/constants'
import {storage} from '@/utils/storage'

/**
 * 延迟加载鉴权接口模块。
 *
 * ## 为什么不是文件顶部 `import {authApi} from '@/api/modules/auth'`
 *
 * `api/modules/auth.ts` 用的是 axios 客户端（`../request`），而**本 store 被全局代码引用**：
 * `plugins/directives.client.ts`（`v-auth` / `v-role` 指令，每个页面都装）与
 * `SiteHeader`（前台顶栏）都会 `useUserStore()`。于是那一行静态 import 把
 * **axios（约 20 KB gzip）钉在了所有页面（含匿名访客的公开页）的首屏关键路径上** ——
 * 实测它正是前台首页那 29 个 `<script>` 之一的来源。
 *
 * 改成动态 `import()` 之后：axios 只在**真的发生鉴权请求**时才下载 ——
 * 也就是登录、登出，以及 `middleware/auth.ts` 在受保护路由上调 `fetchUserInfo()` 时。
 * 匿名读者访问文章页/首页不再付这份代价。
 *
 * 类型仍用 `import type` 静态引入：它在编译期被完全擦除，不会把模块带回依赖图。
 */
async function loadAuthApi() {
  const {authApi} = await import('@/api/modules/auth')
  return authApi
}

interface UserState {
  token: string
  refreshToken: string
  userInfo: CurrentUser | null
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    token: storage.get<string>(STORAGE_TOKEN) || '',
    refreshToken: storage.get<string>(STORAGE_REFRESH_TOKEN) || '',
    userInfo: storage.get<CurrentUser>(STORAGE_USER),
  }),

  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    isSuperuser: (state) => Boolean(state.userInfo?.is_superuser),
    permissions: (state) => state.userInfo?.permissions ?? [],
    menuCodes: (state) => state.userInfo?.menu_codes ?? [],
    roles: (state) => state.userInfo?.roles ?? [],
    // 兜底文案：Pinia getter 里拿不到 i18n 上下文；界面若要本地化请用 username 自行翻译
    displayName: (state) => state.userInfo?.username || '未登录',
  },

  actions: {
    async login(params: LoginParams): Promise<{ requires2fa: boolean; tempToken?: string }> {
      const authApi = await loadAuthApi()
      const data = await authApi.login(params)

      if (data.requires_2fa) {
        return {requires2fa: true, tempToken: data.temp_token}
      }
      this.setToken(data.access_token || '', data.refresh_token || '')
      await this.fetchUserInfo()
      return {requires2fa: false}
    },

    setToken(accessToken: string, refreshToken = ''): void {
      this.token = accessToken
      storage.set(STORAGE_TOKEN, accessToken)
      if (refreshToken) {
        this.refreshToken = refreshToken
        storage.set(STORAGE_REFRESH_TOKEN, refreshToken)
      }
    },

    async fetchUserInfo(): Promise<CurrentUser> {
      const authApi = await loadAuthApi()
      const info = await authApi.me()
      this.userInfo = info
      storage.set(STORAGE_USER, info)
      return info
    },

    /** 权限判断：超级管理员直接放行；支持单个码或数组（数组为 AND 语义） */
    hasPermission(code?: string | string[]): boolean {
      if (!code || (Array.isArray(code) && code.length === 0)) return true
      if (this.userInfo?.is_superuser) return true

      const owned = new Set(this.permissions)
      const codes = Array.isArray(code) ? code : [code]
      return codes.every((item) => owned.has(item))
    },

    hasAnyPermission(code: string[]): boolean {
      if (this.userInfo?.is_superuser) return true
      const owned = new Set(this.permissions)
      return code.some((item) => owned.has(item))
    },

    clear(): void {
      this.token = ''
      this.refreshToken = ''
      this.userInfo = null
      storage.clear([STORAGE_TOKEN, STORAGE_REFRESH_TOKEN, STORAGE_USER])
    },

    async logout(): Promise<void> {
      try {
        if (this.token) {
          const authApi = await loadAuthApi()
          await authApi.logout()
        }
      } catch {
        // 登出失败也要清本地状态
      } finally {
        this.clear()
      }
    },
  },
})
