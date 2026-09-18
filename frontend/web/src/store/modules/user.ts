/** 用户会话状态：token、用户信息、权限判断 */

import {defineStore} from 'pinia'

import {authApi, type CurrentUser, type LoginParams} from '@/api/modules/auth'
import {STORAGE_REFRESH_TOKEN, STORAGE_TOKEN, STORAGE_USER} from '@/constants'
import {storage} from '@/utils/storage'

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
    roles: (state) => state.userInfo?.roles ?? [],
    displayName: (state) => state.userInfo?.username || '未登录',
  },

  actions: {
    async login(params: LoginParams): Promise<{ requires2fa: boolean; tempToken?: string }> {
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
        if (this.token) await authApi.logout()
      } catch {
        // 登出失败也要清本地状态
      } finally {
        this.clear()
      }
    },
  },
})
