<script lang="ts" setup>
import {cn} from '@/lib/utils'

const props = defineProps<{ class?: string }>()
</script>

<template>
  <p :class="cn('text-sm text-slate-500', props.class)">
    <slot/>
  </p>
</template>
