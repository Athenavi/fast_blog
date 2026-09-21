<script lang="ts" setup>
const {t} = useI18n()
import type {IconName} from '@/lib/icons'

/**
 * 移动端底部导航
 *
 * 对应 astro 版 `components/MobileBottomNav.tsx`（React 岛）。
 *
 * **入口是与用户确认后重设的**：原版 5 个入口里，`/messages`（站内信，v3 无接口）
 * 与 `/admin/editor`（Nuxt 侧不存在）都不可用，所以改为 3 个实际存在的：
 * 首页 / 关于 / 我的。
 *
 * 与原实现的两点差异：
 *  1. 原版用 JS 判断 `window.innerWidth < 768` 决定是否渲染 —— 首屏会闪一下；
 *     这里改用 CSS `md:hidden`，SSR 直接不输出，更稳。
 *  2. 原版写死灰阶色（`text-fg-muted` / `text-blue-600`），这里用语义令牌，
 *     跟随主题与用户自选配色。
 */
const navItems: Array<{ name: string; href: string; icon: IconName }> = [
  {name: t('site.navHome'), href: '/', icon: 'house'},
  {name: t('site.navAbout'), href: '/about', icon: 'info'},
  {name: t('site.navProfile'), href: '/profile', icon: 'user'},
]

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
