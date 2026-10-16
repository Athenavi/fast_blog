<script lang="ts" setup>
/**
 * 内联图标组件
 *
 * 用法：`<Icon name="search" class="h-4 w-4"/>`
 * 颜色继承 `currentColor`，因此自动跟随主题与自选配色。
 */
import {ICON_PATHS, type IconName} from '@/lib/icons'
import {cn} from '@/lib/utils'

const props = withDefaults(
  defineProps<{ name: IconName; size?: number | string; class?: string }>(),
  {size: 24},
)
</script>

<template>
  <svg
    :class="cn('shrink-0', props.class)"
    :height="props.size"
    :width="props.size"
    fill="none"
    stroke="currentColor"
    stroke-linecap="round"
    stroke-linejoin="round"
    stroke-width="2"
    viewBox="0 0 24 24"
    xmlns="http://www.w3.org/2000/svg"
    v-html="ICON_PATHS[props.name]"
  />
</template>
