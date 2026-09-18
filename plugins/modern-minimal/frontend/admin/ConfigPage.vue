<script lang="ts" setup>
import ThemeConfigPanel from '@/components/admin/ThemeConfigPanel.vue'

/**
 * 简约主题配置（modern-minimal 插件后台页）
 *
 * 对应 `plugins/modern-minimal/frontend/admin/ConfigPage.tsx`：
 * 表单由共用的 `ThemeConfigPanel`（`components/admin/`）渲染。
 */
</script>

<template>
  <div class="p-4">
    <ThemeConfigPanel
      plugin-slug="modern-minimal"
      theme-description="现代简约风格 - 支持代码高亮和深色模式"
      theme-name="Modern Minimal"
    />
  </div>
</template>
