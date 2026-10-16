<template>
  <!-- 就绪前先给一个**布局骨架**（纯 HTML/CSS，不依赖 Element Plus，所以能先于 EP 绘出），
       而不是整屏只剩一行「准备中」的空白 —— 前者观感是"内容正在到位"，
       后者容易被读成"页面坏了"。`role="status"` 让读屏用户听到正在准备。 -->
  <div v-if="!ready" :aria-label="$t('common.preparing')" class="skeleton" role="status">
    <div class="skeleton__aside"/>
    <div class="skeleton__body">
      <div class="skeleton__header"/>
      <div class="skeleton__main">
        <div v-for="row in 3" :key="row" :class="{'skeleton__block--short': row === 3}" class="skeleton__block"/>
      </div>
    </div>
  </div>

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

const {locale, mergeLocaleMessage, t, te} = useI18n()

/**
 * 后台专属文案**按需加载**。
 *
 * `admin` 命名空间占全部文案的 77.5%（zh-CN 约 187 KB），而前台访客永远用不到它 ——
 * 此前它和前台文案一起打包成一份 193 KB 的 messages.json，每个页面加载后都要额外请求一次。
 * `scripts/split-i18n.mjs` 把它拆到 `public/i18n/admin/<locale>.json`，只在进入后台时取一次。
 *
 * 加载与 Element Plus 一起纳入 `ready` 门禁：文案没到位就先不渲染，
 * 免得整屏先闪一遍 `admin.xxx.yyy` 这样的原始 key。
 */
const adminMessagesLoaded = new Set<string>()

async function loadAdminMessages(): Promise<void> {
  const code = String(locale.value)
  if (adminMessagesLoaded.has(code)) return
  try {
    const messages = await $fetch<Record<string, unknown>>(`/i18n/admin/${code}.json`)
    mergeLocaleMessage(code, messages)
    adminMessagesLoaded.add(code)
  } catch {
    // 取不到就维持现状（未命中的 key 以原文显示），不阻塞进入后台
  }
}

// 后台内切换语言时同样需要补上该语言的 admin 文案
watch(locale, () => void loadAdminMessages())

/**
 * 文档标题（`document-title` 那条违规的修法）。
 *
 * 后台页面只用 `definePageMeta({title})` 声明自己 —— `AppHeader` 的面包屑读的是同一份
 * `route.matched[].meta.title` —— 但**没有任何地方把它写进 document.title**，
 * 于是 12 个后台页在 axe 的 `document-title` 上全红（读屏与浏览器标签页都拿不到名字）。
 *
 * 在布局层统一兜底：取路由链上最后一个有 title 的 meta，`te()` 判 i18n key 后翻译
 * （与面包屑同一套渐进式策略）。页面若自己用 `useSeoMeta`/`useHead` 设了标题，
 * 组件级会覆盖这一层，不会互相打架。
 */
const pageTitle = computed(() => {
  const titles = route.matched
    .map((item) => item.meta?.title as string | undefined)
    .filter((title): title is string => Boolean(title))
  const last = titles[titles.length - 1]
  if (!last) return ''
  return te(last) ? t(last) : last
})

useHead({
  // 取不到就交给 Nuxt 保持原值（不写空 title）
  title: computed(() => pageTitle.value || undefined),
})

/**
 * 可滚动区域补键盘焦点（axe `scrollable-region-focusable`，10 个后台页稳定报同一条）。
 *
 * Element Plus 把表格/列表内容放进 `.el-scrollbar__wrap`（`overflow: auto`），但它
 * **不可聚焦** —— 键盘用户没法滚动它（WCAG 2.1.1 键盘可达）。EP 不会自己加 `tabindex`。
 *
 * 在布局层兜住：首次挂载、以及 DOM 变化后（表格分页/筛选会整块重渲染）给**确实溢出**
 * 的容器补上 `tabindex="0"`。两个细节：
 *  - 只给真溢出的加：给不可滚动的容器补 `tabindex` 只会多出无意义的 Tab 停靠点；
 *  - 用 rAF 合并连续的 mutation，避免每次变更都全量遍历。
 */
let scrollFixScheduled = false

function ensureScrollableFocusable(): void {
  // ⚠️ 实测 `scrollable-region-focusable` 命中的主要不是表格滚动容器，而是**后台侧边栏**
  // （`aside` / `.el-aside`：菜单比视口高时它会滚动，但自身不可聚焦、内部又未必有可聚焦项）。
  // 所以两类都要覆盖。
  const selector = [
    '.el-scrollbar__wrap:not([tabindex])',
    '.el-table__body-wrapper:not([tabindex])',
    '.el-aside:not([tabindex])',
    'aside:not([tabindex])',
  ].join(', ')
  for (const el of document.querySelectorAll<HTMLElement>(selector)) {
    if (el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth) {
      el.setAttribute('tabindex', '0')
    }
  }
}

function scheduleScrollFix(): void {
  if (scrollFixScheduled) return
  scrollFixScheduled = true
  window.requestAnimationFrame(() => {
    scrollFixScheduled = false
    ensureScrollableFocusable()
  })
}

let scrollObserver: MutationObserver | null = null

onMounted(() => {
  ensureScrollableFocusable()
  scrollObserver = new MutationObserver(scheduleScrollFix)
  scrollObserver.observe(document.body, {childList: true, subtree: true})
})

onBeforeUnmount(() => {
  scrollObserver?.disconnect()
  scrollObserver = null
})

/** 与 Element Plus 的 `lg` 断点一致：窄屏走抽屉导航 */
const isNarrow = useMediaQuery('(max-width: 1023px)')

/** 性能面板按需加载：layouts 属 app 层，静态 import 会进初始包 */
const PerfDashboard = defineAsyncComponent(() => import('@/components/admin/PerfDashboard.vue'))
/** 命令面板同样按需加载（它依赖 Element Plus，绝不能静态 import 进 app 层） */
const CommandPalette = defineAsyncComponent(() => import('@/components/admin/CommandPalette.vue'))

// 图标清单不再在这里维护 —— 见 onMounted 里的**具名解构**：那份解构列表即"实际用到的"，
// 同时让 Rollup 能把 `@element-plus/icons-vue` 裁剪到这几个（整包 166 KB / 42 KB gzip）。

// 视口回到宽屏时收起抽屉，避免"看不见的浮层"留在状态里
watch(isNarrow, (narrow) => {
  if (!narrow) appStore.closeMobileSidebar()
})

onMounted(async () => {
  // 图标走 `components/admin/iconRegistry`：那边是**静态具名导入**（Rollup 能裁剪到
  // 实际用到的 31 个），这里只把这个小模块动态加载进来。
  // 注意：直接 `await import('@element-plus/icons-vue')` 即使具名解构也**裁不掉** ——
  // 动态 import 返回的是整个模块命名空间，整包 166 KB / 42 KB gzip 照样进产物（实测）。
  const [
    {default: ElementPlus},
    {default: zhCn},
    {adminIcons},
    ,
  ] = await Promise.all([
    import('element-plus'),
    import('element-plus/es/locale/lang/zh-cn'),
    import('@/components/admin/iconRegistry'),
    // 后台专属文案（占全部文案 77.5%）与 Element Plus 并发加载，一起纳入 ready 门禁
    loadAdminMessages(),
    // 样式走合并入口，一次加载、顺序确定（见 styles/admin-bundle.css 的说明）
    import('@/styles/admin-bundle.css'),
  ])

  const nuxtApp = useNuxtApp()
  nuxtApp.vueApp.use(ElementPlus, {locale: zhCn})

  // 按各自的 `name` 注册成全局组件（侧边栏 / 头部是按**字符串名**引用的：
  // `<component :is="menu.icon"/>`）。清单在 `components/admin/iconRegistry.ts`。
  for (const icon of adminIcons) {
    if (icon?.name) nuxtApp.vueApp.component(icon.name, icon)
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
/* 就绪前的布局骨架：刻意只用语义令牌 + 兜底色值，且不引用任何 el-* 组件，
   因此它在 Element Plus 与后台样式到位之前就能正确绘制。 */
.skeleton {
  display: flex;
  height: 100%;
  background: var(--admin-canvas, #f5f7fa);
}

.skeleton__aside {
  width: 210px;
  flex: none;
  background: var(--admin-sidebar-bg, #1f2937);
  opacity: 0.4;
}

.skeleton__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.skeleton__header {
  height: 56px;
  flex: none;
  border-bottom: 1px solid var(--admin-line, #e4e7ed);
}

.skeleton__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
}

.skeleton__block {
  height: 88px;
  border-radius: 6px;
  background: var(--admin-surface, #fff);
  opacity: 0.75;
}

.skeleton__block--short {
  width: 60%;
  height: 48px;
}

/* 窄屏下侧边栏本来就是抽屉（与 admin.vue 的 isNarrow 一致），骨架也不画它 */
@media (max-width: 1023px) {
  .skeleton__aside {
    display: none;
  }
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
