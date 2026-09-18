<script lang="ts" setup>
/** 前台布局：顶部导航 + 内容 + 页脚 */
const site = await useSiteInfo()
</script>

<template>
  <div class="flex min-h-screen flex-col bg-white">
    <SiteHeader :site-name="site.site_name"/>
    <main class="flex-1">
      <slot/>
    </main>
    <SiteFooter :footer="site.site_footer" :icp="site.icp" :site-name="site.site_name"/>
  </div>
</template>
