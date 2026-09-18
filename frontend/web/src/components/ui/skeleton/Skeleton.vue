<script lang="ts" setup>
import {cn} from '@/lib/utils'

const props = defineProps<{ class?: string }>()
</script>

<template>
  <div :class="cn('animate-pulse rounded-md bg-slate-200', props.class)"/>
</template>
