<script lang="ts" setup>
import {type VariantProps, cva} from 'class-variance-authority'

import {cn} from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-slate-900 text-white hover:bg-slate-800',
        outline: 'border border-slate-200 bg-white text-slate-900 hover:bg-slate-50',
        ghost: 'text-slate-700 hover:bg-slate-100',
        link: 'text-slate-900 underline-offset-4 hover:underline',
      },
      size: {
        sm: 'h-8 px-3 text-xs',
        default: 'h-9 px-4',
        lg: 'h-11 px-6 text-base',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: {variant: 'default', size: 'default'},
  },
)

type ButtonVariants = VariantProps<typeof buttonVariants>

const props = withDefaults(
  defineProps<{ variant?: ButtonVariants['variant']; size?: ButtonVariants['size']; class?: string }>(),
  {variant: 'default', size: 'default'},
)
</script>

<template>
  <button :class="cn(buttonVariants({variant: props.variant, size: props.size}), props.class)">
    <slot/>
  </button>
</template>
