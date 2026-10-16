<script lang="ts" setup>
/**
 * 前台布局：顶部导航 + 正文区 + 页脚
 *
 * 站点信息 / 主题槽位 / 顶部导航由**一个聚合接口**一次取回并做服务端缓存
 * （`server/routes/__site/bootstrap.get.ts`，前端入口见 `composables/useSiteBootstrap.ts`），
 * 所以这里 `await` 一次就够了 —— `SiteHeader` 的 `useSiteNav()` 与
 * `ThemeArticleCard` 的 `slot()` 读的都是同一份 `useState`，不会再多发请求。
 *
 * 历史：这三者原先是三个后端请求（后来改成并发，只占一轮往返），但那一轮往返
 * **串在页面自己取数的前面**（布局 setup 先于页面 setup），等于每页两轮往返。
 * 现在布局只等一次**同进程的 Nitro 调用**，后端只在缓存未命中时才被问一次。
 */
const site = await useSiteInfo()

/**
 * 主题 CSS 服务端内联
 *
 * 与 `app.vue` 里那条"不要用 useHead 声明主题"的约束**不冲突** —— 那里禁止的是
 * **用户级**的 `data-theme` / `data-accent`：公开页开了 swr 边缘缓存，用户级状态
 * 一旦参与直出就会被发给所有人。主题 CSS 是**服务器级**的（同一份发给所有访问者），
 * 直出既安全，又省掉一次额外请求。
 *
 * 空值时不注入任何 `<style>`（而不是塞一个空标签）—— 未取到主题样式时页面保持原样。
 */
const themeCss = useThemeCss()
useHead({
  style: computed(() => (themeCss.value ? [{innerHTML: themeCss.value}] : [])),
})
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
