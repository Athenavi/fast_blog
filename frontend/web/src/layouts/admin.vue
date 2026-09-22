<template>
  <div v-if="!ready" class="layout-loading">{{ $t('common.preparing') }}</div>

  <el-container v-else class="layout">
    <el-aside v-if="!isNarrow" :width="appStore.sidebarCollapsed ? '64px' : '210px'" class="layout__aside">
      <AppSidebar/>
    </el-aside>

    <el-container>
      <el-header class="layout__header" height="56px">
        <AppHeader :narrow="isNarrow"/>
      </el-header>

      <el-main class="layout__main">
        <slot/>
      </el-main>
    </el-container>

    <!-- 窄屏：侧边栏改为抽屉，不再挤压内容区（<lg 时表格才有横向空间） -->
    <el-drawer
      v-if="isNarrow"
      v-model="appStore.mobileSidebarOpen"
      :with-header="false"
      class="layout__mobile-nav"
      direction="ltr"
      size="min(248px, 82vw)"
    >
      <AppSidebar :collapsed="false" @navigate="appStore.closeMobileSidebar()"/>
    </el-drawer>
  </el-container>

  <!-- 性能面板 / 命令面板：按需加载，避免进入初始包（layouts 属 app 层，静态 import 会全站生效） -->
  <ClientOnly>
    <component :is="PerfDashboard" v-if="ready"/>
    <component :is="CommandPalette" v-if="ready"/>
  </ClientOnly>
</template>

<script lang="ts" setup>
/**
 * 后台布局
 *
 * **Element Plus 在这里懒加载，而不是静态 import、也不是全局插件。**
 *
 * 原因：Element Plus + dayjs 约 1.1 MB。layouts 属于 app 层、不按页面分割，
 * 一旦静态 import 就会进入**初始包**，连前台博客首页都被迫下载管理端 UI 库
 * （实测前台首页因此多了 1.1 MB）。改为动态 import 后，它只会在真正进入
 * 后台路由时按需加载。
 *
 * 代价是后台首屏有一个极短的"准备中"瞬间（`ready` 为 false 时不渲染 el-* 结构）。
 *
 * 响应式：`<lg`（1024px）时侧边栏换成抽屉（`el-drawer`），内容区独占整宽；
 * 折叠状态仍由 `appStore.sidebarCollapsed` 记忆在宽屏使用。
 */
import {useMediaQuery} from '@vueuse/core'
import type {Component} from 'vue'

// Nuxt 只自动导入 `~/components`（见 nuxt.config.ts 的 components 配置），
// layouts/components 不在扫描范围内，必须显式 import
import AppHeader from './components/AppHeader.vue'
import AppSidebar from './components/AppSidebar.vue'

import {useAppStore} from '@/store/modules/app'
import {useRecentPages} from '@/composables/useRecentPages'

const appStore = useAppStore()
const route = useRoute()
const {remember: rememberPage} = useRecentPages()

const ready = ref(false)

/** 与 Element Plus 的 `lg` 断点一致：窄屏走抽屉导航 */
const isNarrow = useMediaQuery('(max-width: 1023px)')

/** 性能面板按需加载：layouts 属 app 层，静态 import 会进初始包 */
const PerfDashboard = defineAsyncComponent(() => import('@/components/admin/PerfDashboard.vue'))
/** 命令面板同样按需加载（它依赖 Element Plus，绝不能静态 import 进 app 层） */
const CommandPalette = defineAsyncComponent(() => import('@/components/admin/CommandPalette.vue'))

/** 侧边栏与头部按字符串名引用图标，这里显式注册用到的那些 */
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
  'Menu',
  'Lock',
  'User',
  'Search',
  'Plus',
  'Edit',
  'Delete',
  'Refresh',
  'Promotion',
  'MagicStick',
  'ChatDotRound',
  'Money',
  'Coin',
  'Top',
  'Collection',
  'Briefcase',
  'Files',
  'Layout',
  'Sunny',
  'Moon',
  'Brush',
] as const

// 视口回到宽屏时收起抽屉，避免"看不见的浮层"留在状态里
watch(isNarrow, (narrow) => {
  if (!narrow) appStore.closeMobileSidebar()
})

onMounted(async () => {
  const [{default: ElementPlus}, icons, {default: zhCn}] = await Promise.all([
    import('element-plus'),
    import('@element-plus/icons-vue'),
    import('element-plus/es/locale/lang/zh-cn'),
  ])

  // 样式按"基础 → 暗色变量 → 后台令牌"顺序串行加载，保证覆盖关系正确
  await import('element-plus/dist/index.css')
  await import('element-plus/theme-chalk/dark/css-vars.css')
  await import('@/styles/admin.css')

  const nuxtApp = useNuxtApp()
  nuxtApp.vueApp.use(ElementPlus, {locale: zhCn})

  const registry = (icons as unknown as { default?: Record<string, Component> }).default ?? {}
  for (const name of ICONS) {
    const icon = (registry as Record<string, Component>)[name]
    if (icon) nuxtApp.vueApp.component(name, icon)
  }

  ready.value = true
})

/** 路由变化即收起抽屉（菜单点击已处理，这里兜住面包屑/程序化跳转），并记录"最近访问" */
watch(
  () => route.fullPath,
  () => {
    appStore.closeMobileSidebar()
    if (route.path) rememberPage(route.path)
  },
)
</script>

<style scoped>
.layout-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  font-size: 14px;
  color: var(--admin-fg-subtle, #909399);
  background: var(--admin-canvas, #f5f7fa);
}

.layout {
  height: 100%;
  font-size: 14px;
  color: var(--admin-fg, #303133);
  background-color: var(--admin-canvas, #f5f7fa);
}

.layout__aside {
  background-color: var(--admin-sidebar-bg, #1f2937);
  transition: width 0.2s ease;
  overflow-x: hidden;
}

.layout__header {
  display: flex;
  align-items: center;
  height: 56px;
  background-color: var(--admin-surface, #fff);
  border-bottom: 1px solid var(--admin-line, #e5e7eb);
  padding: 0 16px;
}

.layout__main {
  background-color: var(--admin-canvas, #f5f7fa);
  padding: 0;
  overflow-y: auto;
}

/* 抽屉内边距的清理见 styles/admin.css（`.layout__mobile-nav` 落在 EP 内部节点上，scoped 匹配不到） */
</style>
