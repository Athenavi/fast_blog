<script lang="ts" setup>
import {cn} from '@/lib/utils'

const props = defineProps<{ class?: string }>()
</script>

<template>
  <div :class="cn('rounded-card border border-line bg-surface text-fg', props.class)">
    <slot/>
  </div>
</template>
