<script lang="ts" setup>
import {cn} from '@/lib/utils'

const props = withDefaults(defineProps<{ variant?: 'default' | 'secondary' | 'outline'; class?: string }>(), {
  variant: 'default',
})

const VARIANTS: Record<string, string> = {
  default: 'bg-slate-900 text-white hover:bg-slate-800',
  secondary: 'bg-slate-100 text-slate-700 hover:bg-slate-200',
  outline: 'border border-slate-200 text-slate-700',
}
</script>

<template>
  <span
    :class="cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors', VARIANTS[props.variant], props.class)"
  >
    <slot/>
  </span>
</template>
