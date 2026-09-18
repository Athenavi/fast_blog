/** 应用级 UI 状态 */

import {defineStore} from 'pinia'

export const useAppStore = defineStore(
  'app',
  {
    state: () => ({
      sidebarCollapsed: false,
      /** 面包屑/标签页可扩展，此处先保留最小状态 */
      pageTitle: '',
    }),

    actions: {
      toggleSidebar(): void {
        this.sidebarCollapsed = !this.sidebarCollapsed
      },
      setPageTitle(title: string): void {
        this.pageTitle = title
      },
    },

    persist: {
      key: 'fastblog.app',
      pick: ['sidebarCollapsed'],
    },
  },
)
