<script lang="ts" setup>
/** 空状态：列表 / 搜索 / 分类页复用 */

const props = withDefaults(defineProps<{ title?: string; description?: string }>(), {
  title: '暂无内容',
  description: '',
})
</script>

<template>
  <div
    class="flex flex-col items-center justify-center gap-1.5 rounded-card border border-dashed border-line py-16 text-center">
    <Icon class="h-8 w-8 text-fg-subtle" name="inbox"/>
    <p class="mt-2 text-sm font-medium text-fg">{{ props.title }}</p>
    <p v-if="props.description" class="text-sm text-fg-subtle">{{ props.description }}</p>
    <slot/>
  </div>
</template>
