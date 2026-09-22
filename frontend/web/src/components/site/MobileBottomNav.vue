<script lang="ts" setup>
const {t} = useI18n()
import type {IconName} from '@/lib/icons'

/**
 * 移动端底部导航
 *
 * 对应 astro 版 `components/MobileBottomNav.tsx`（React 岛）。
 *
 * **入口是与用户确认后重设的**：原版 5 个入口里，`/messages`（站内信，v3 无接口）
 * 与 `/admin/editor`（Nuxt 侧不存在）都不可用。
 *
 * 这一版把拇指区留给**最常用的四个动作**：首页 / 文章 / 搜索 / 我的 ——
 * 此前是"首页 / 关于 / 我的"，把最贵的位置给了「关于」，而"浏览文章""搜索"反而没有入口。
 *
 * 与原实现的两点差异：
 *  1. 原版用 JS 判断 `window.innerWidth < 768` 决定是否渲染 —— 首屏会闪一下；
 *     这里改用 CSS `md:hidden`，SSR 直接不输出，更稳。
 *  2. 原版写死灰阶色（`text-fg-muted` / `text-blue-600`），这里用语义令牌，
 *     跟随主题与用户自选配色。
 *
 * 文案用 `computed`：此前是 setup 期求值的常量数组，切换语言后不会更新。
 */
const navItems = computed<Array<{ name: string; href: string; icon: IconName }>>(() => [
  {name: t('site.navHome'), href: '/', icon: 'house'},
  {name: t('site.navArticles'), href: '/articles', icon: 'file-text'},
  {name: t('site.navSearch'), href: '/search', icon: 'search'},
  {name: t('site.navProfile'), href: '/profile', icon: 'user'},
])

const route = useRoute()

/** 首页精确匹配，其余按前缀匹配（如 /about 的子路径也算选中） */
function isActive(href: string): boolean {
  return href === '/' ? route.path === '/' : route.path.startsWith(href)
}
</script>

<template>
  <nav :aria-label="$t('site.mobileNavAriaLabel')"
       class="fixed inset-x-0 bottom-0 z-50 border-t border-line bg-surface md:hidden">
    <div
      class="flex h-16 items-center justify-around"
      style="padding-bottom: env(safe-area-inset-bottom, 0px)"
    >
      <NuxtLink
        v-for="item in navItems"
        :key="item.href"
        :aria-current="isActive(item.href) ? 'page' : undefined"
        :class="isActive(item.href) ? 'text-primary' : 'text-fg-muted'"
        :to="item.href"
        class="flex flex-1 flex-col items-center justify-center py-2 text-xs transition-colors"
      >
        <Icon :name="item.icon" class="mb-1 h-6 w-6"/>
        <span>{{ item.name }}</span>
      </NuxtLink>
    </div>
  </nav>
</template>
