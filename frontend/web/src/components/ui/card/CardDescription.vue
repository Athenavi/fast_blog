<script lang="ts" setup>
import {cn} from '@/lib/utils'

const props = defineProps<{ class?: string }>()
</script>

<template>
  <p :class="cn('text-sm text-fg-muted', props.class)">
    <slot/>
  </p>
</template>
