<script lang="ts" setup>
import {type VariantProps, cva} from 'class-variance-authority'

import {cn} from '@/lib/utils'

/**
 * 按钮
 *
 * 颜色只引用语义令牌（`primary` / `surface` / `line` / `fg`…），
 * 因此换主题或切换用户自选配色时无需改动本文件。
 */
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-control text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-fg hover:bg-primary-hover',
        outline: 'border border-line bg-surface text-fg hover:bg-surface-soft',
        ghost: 'text-fg-muted hover:bg-surface-soft hover:text-fg',
        soft: 'bg-primary-soft text-primary hover:opacity-90',
        danger: 'bg-danger text-primary-fg hover:opacity-90',
        link: 'text-primary underline-offset-4 hover:underline',
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
  defineProps<{
    variant?: ButtonVariants['variant']
    size?: ButtonVariants['size']
    class?: string
    type?: 'button' | 'submit' | 'reset'
  }>(),
  {variant: 'default', size: 'default', type: 'button'},
)
</script>

<template>
  <button
    :class="cn(buttonVariants({variant: props.variant, size: props.size}), props.class)"
    :type="props.type"
  >
    <slot/>
  </button>
</template>
