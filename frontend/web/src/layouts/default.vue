<script lang="ts" setup>
/** 前台布局：顶部导航 + 正文区 + 页脚 */
const site = await useSiteInfo()
// 主题槽位（component_slots）：决定文章卡片等组件使用哪个变体
await initThemeSlots()
</script>

<template>
  <div class="flex min-h-screen flex-col bg-canvas pb-16 md:pb-0">
    <SiteHeader :site-name="site.site_name"/>
    <main class="flex-1">
      <slot/>
    </main>
    <SiteFooter :footer="site.site_footer" :icp="site.icp" :site-name="site.site_name"/>

    <!-- 可安装时提示装到桌面（浏览器未提供安装能力时不显示） -->
    <PWAInstallPrompt/>

    <!-- 移动端底部导航：首页 / 关于 / 我的（仅 <md 显示，见组件注释） -->
    <MobileBottomNav/>
  </div>
</template>
