<script lang="ts" setup>
/**
 * 前台布局：顶部导航 + 正文区 + 页脚
 *
 * 三个数据源**并发**取：站点信息、主题槽位、以及预热顶部导航。
 *
 * 原先是一个个 `await`，把 3 次后端往返串起来全压在 TTFB 上 —— 而且布局的 setup
 * 先于页面执行，页面里的取数只能排在它之后，等于每页至少多两轮往返。
 * 导航在这里预热后，`SiteHeader` 内部那次调用会直接命中 `useSiteNav` 的缓存。
 */
const [site] = await Promise.all([
  useSiteInfo(),
  initThemeSlots(),
  useSiteNav(),
])
</script>

<template>
  <div class="flex min-h-dvh flex-col bg-canvas pb-16 md:pb-0">
    <!-- 跳过导航直达正文：键盘用户按第一下 Tab 就能越过整条导航（WCAG 2.4.1）。
         平时移出视口，获得焦点时滑入 —— 见 styles/index.css 的 .skip-link。 -->
    <a class="skip-link" href="#main-content">{{ $t('site.skipToContent') }}</a>

    <SiteHeader :site-name="site.site_name"/>
    <main id="main-content" class="flex-1">
      <slot/>
    </main>
    <SiteFooter :footer="site.site_footer" :icp="site.icp" :site-name="site.site_name"/>

    <!-- 断网 / 弱网提示条（仅客户端渲染，见组件注释） -->
    <OfflineBanner/>

    <!-- 可安装时提示装到桌面（浏览器未提供安装能力时不显示） -->
    <PWAInstallPrompt/>

    <!-- 移动端底部导航：首页 / 关于 / 我的（仅 <md 显示，见组件注释） -->
    <MobileBottomNav/>

  </div>
</template>
