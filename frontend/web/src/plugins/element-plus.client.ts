/**
 * Element Plus 全局注册（仅客户端）
 *
 * 后台页面使用 Element Plus（表格、表单、消息提示），前台使用 shadcn-vue，两套 UI 暂时并存：
 *  - 前台（`layouts/default.vue`）只引用 `components/ui/*`；
 *  - 后台（`layouts/admin.vue`）只引用 `el-*`。
 *
 * 侧边栏与头部按**字符串名**引用图标（如 `<component :is="'Odometer'"/>`），
 * 因此这里显式注册用到的图标——按名注册可避免全量引入整套图标库。
 */
import * as ElementPlusIcons from '@element-plus/icons-vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import type {Component} from 'vue'

import 'element-plus/dist/index.css'

/** 后台菜单图标 + 通用操作图标 */
const ICONS = [
  'Odometer',
  'Document',
  'Setting',
  'DataLine',
  'Grid',
  'Tools',
  'Bell',
  'ArrowDown',
  'Fold',
  'Expand',
  'Lock',
  'User',
  'Search',
  'Plus',
  'Edit',
  'Delete',
  'Refresh',
] as const

export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.use(ElementPlus, {locale: zhCn})

  const registry = ElementPlusIcons as unknown as Record<string, Component>
  for (const name of ICONS) {
    const icon = registry[name]
    if (icon) nuxtApp.vueApp.component(name, icon)
  }
})
