<script lang="ts" setup>
import {cn} from '@/lib/utils'

const props = defineProps<{ class?: string }>()
</script>

<template>
  <div :class="cn('rounded-lg border border-slate-200 bg-white text-slate-900 shadow-sm', props.class)">
    <slot/>
  </div>
</template>
