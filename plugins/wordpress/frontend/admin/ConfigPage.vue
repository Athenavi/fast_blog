<script lang="ts" setup>
/**
 * WordPress Style 主题配置页
 *
 * 配置表单由 `ThemeConfigPanel` 统一渲染（读取主题的 `settings_schema`），
 * 所以主题只需声明 schema，不必自己写表单 —— 与其余主题保持一致。
 */
import ThemeConfigPanel from '@/components/admin/ThemeConfigPanel.vue'
</script>

<template>
  <ThemeConfigPanel slug="wordpress"/>
</template>
