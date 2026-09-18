<script lang="ts" setup>
/** 空状态：列表/搜索/分类页共用 */
import {Inbox} from '@lucide/vue'

const props = withDefaults(defineProps<{ title?: string; description?: string }>(), {
  title: '暂无内容',
  description: '',
})
</script>

<template>
  <div
    class="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 py-16 text-center">
    <Inbox class="h-8 w-8 text-slate-300"/>
    <p class="mt-3 text-sm font-medium text-slate-700">{{ props.title }}</p>
    <p v-if="props.description" class="mt-1 text-sm text-slate-400">{{ props.description }}</p>
    <slot/>
  </div>
</template>
