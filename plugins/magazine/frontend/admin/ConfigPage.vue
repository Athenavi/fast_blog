<script lang="ts" setup>
import ThemeConfigPanel from '@/components/admin/ThemeConfigPanel.vue'

/**
 * 杂志主题配置（magazine 插件后台页）
 *
 * 对应 `plugins/magazine/frontend/admin/ConfigPage.tsx`：
 * 表单由共用的 `ThemeConfigPanel`（`components/admin/`）渲染。
 */
</script>

<template>
  <div class="p-4">
    <ThemeConfigPanel
      plugin-slug="magazine"
      theme-description="杂志风格主题 - 网格布局、特色图片展示、多栏目支持"
      theme-name="Magazine"
    />
  </div>
</template>
