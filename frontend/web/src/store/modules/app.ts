/** 应用级 UI 状态 */

import {defineStore} from 'pinia'

export const useAppStore = defineStore(
  'app',
  {
    state: () => ({
      sidebarCollapsed: false,
      /** 窄屏下侧边栏以抽屉形式浮出（不持久化：每次进入都回到收起状态） */
      mobileSidebarOpen: false,
      /** 命令面板（⌘K/Ctrl+K）开关 */
      commandPaletteOpen: false,
      /** 面包屑/标签页可扩展，此处先保留最小状态 */
      pageTitle: '',
    }),

    actions: {
      toggleSidebar(): void {
        this.sidebarCollapsed = !this.sidebarCollapsed
      },
      openMobileSidebar(): void {
        this.mobileSidebarOpen = true
      },
      closeMobileSidebar(): void {
        this.mobileSidebarOpen = false
      },
      toggleCommandPalette(): void {
        this.commandPaletteOpen = !this.commandPaletteOpen
      },
      closeCommandPalette(): void {
        this.commandPaletteOpen = false
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
