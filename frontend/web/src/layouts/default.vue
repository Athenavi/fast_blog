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
const themeVariables = useThemeVariables()
// 布局契约用：挂到根元素的 `data-theme`，供主题 styles.css 定向
const themeSlug = useThemeSlug()

/**
 * 主题样式：**变量块在前、主题 CSS 在后**
 *
 * 顺序不能反 —— 主题 CSS 引用这些变量（`var(--color-primary)`），并允许覆盖默认值。
 *
 * 两段都是**服务器级**内容（同一份发给所有访问者），可以安全 SSR 直出；
 * 这与 `app.vue` 里禁止直出的**用户级**配色（`data-theme` / `data-accent`）
 * 不是一回事：那些会被公开页的 swr 边缘缓存串号。
 *
 * 空值时不注入任何 `<style>`，而不是塞空标签。
 */
useHead({
  // 挂在 **`html`**（不是根 div）：深色的 `[data-theme]` 由 useTheme() 写在 html 上，
  // 两者同层，主题才能写 `[data-active-theme='x'][data-theme='dark']` 适配深色。
  // 与 app.vue 禁止声明 data-theme 不冲突：那条针对**用户级**状态（会被 swr 缓存串号），
  // 这里的 slug 是**服务器级**数据。
  // 这里刻意**不用** computed：unhead 的 htmlAttrs 类型不接受 Ref，
  // 而 themeSlug 是服务器级数据（SSR 时确定、同一份发给所有访问者），
  // 无需响应式 —— 换主题本身就要重新取 bootstrap。
  htmlAttrs: {
    'data-active-theme': themeSlug.value ?? '',
  },
  style: computed(() => {
    const blocks: Array<{ innerHTML: string }> = []
    if (themeVariables.value) blocks.push({innerHTML: themeVariables.value})
    if (themeCss.value) blocks.push({innerHTML: themeCss.value})
    return blocks
  }),
})
</script>

<template>
  <!--
    布局契约（参考 Halo 2.26 的 `layout.html`）：主题 slug 挂在 **`html`** 上
    （见 script 的 `useHead({htmlAttrs})`），主题 styles.css 便能定向
    `[data-active-theme='<slug>']`，且与深色的 `[data-theme]` **同层**、可适配深色。

    主题因此不需要在 templates 里声明 site-header / site-footer（那会画两遍）。
  -->
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
