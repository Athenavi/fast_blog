<script lang="ts" setup>
import ThemeConfigPanel from '@/components/admin/ThemeConfigPanel.vue'

/**
 * 默认主题配置（fastblog-default 插件后台页）
 *
 * 对应 `plugins/fastblog-default/frontend/admin/ConfigPage.tsx`：
 * 该页只是把主题信息交给共用的 `ThemeConfigPanel`（`components/admin/`）渲染，
 * 与 magazine / modern-minimal 两个主题共用同一份表单实现。
 */
</script>

<template>
  <div class="p-4">
    <ThemeConfigPanel
      plugin-slug="fastblog-default"
      theme-description="简洁、现代、响应式设计"
      theme-name="FastBlog Default"
    />
  </div>
</template>
