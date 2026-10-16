<script lang="ts" setup>
/**
 * Halo Style 主题配置页
 *
 * 表单由 `ThemeConfigPanel` 统一渲染（读取主题的 `settings_schema`），
 * 主题只声明 schema、不自己写表单 —— 与其余主题保持一致。
 */
import ThemeConfigPanel from '@/components/admin/ThemeConfigPanel.vue'
</script>

<template>
  <ThemeConfigPanel slug="halo"/>
</template>
