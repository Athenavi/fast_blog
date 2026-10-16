<script lang="ts" setup>
import {cn} from '@/lib/utils'

type BadgeVariant = 'default' | 'secondary' | 'outline' | 'success' | 'warning' | 'danger'

const props = withDefaults(
  defineProps<{ variant?: BadgeVariant; class?: string }>(),
  {variant: 'default'},
)

/** 变体到语义令牌的映射，避免任何写死色值 */
const VARIANTS: Record<BadgeVariant, string> = {
  default: 'bg-primary text-primary-fg',
  secondary: 'bg-surface-soft text-fg-muted',
  outline: 'border border-line text-fg-muted',
  success: 'bg-success-soft text-success',
  warning: 'bg-warning-soft text-warning',
  danger: 'bg-danger-soft text-danger',
}
</script>

<template>
  <span
    :class="cn(
      'inline-flex items-center rounded-pill px-2.5 py-0.5 text-xs font-medium transition-colors',
      VARIANTS[props.variant ?? 'default'],
      props.class,
    )"
  >
    <slot/>
  </span>
</template>
