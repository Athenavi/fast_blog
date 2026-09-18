<script lang="ts" setup>
import {cn} from '@/lib/utils'

const props = defineProps<{ class?: string }>()
</script>

<template>
  <h3 :class="cn('text-base font-semibold leading-snug tracking-tight text-fg', props.class)">
    <slot/>
  </h3>
</template>
