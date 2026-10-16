<script lang="ts" setup>
import {cn} from '@/lib/utils'

const props = defineProps<{
  class?: string
  modelValue?: string | number
  type?: string
  placeholder?: string
  disabled?: boolean
}>()

const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

function onInput(event: Event) {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}
</script>

<template>
  <input
    :type="props.type ?? 'text'"
    :value="props.modelValue"
    :class="cn(
      'flex h-9 w-full rounded-control border border-line bg-surface px-3 py-1 text-sm text-fg transition-colors',
      'placeholder:text-fg-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
      'disabled:cursor-not-allowed disabled:opacity-50',
      props.class,
    )"
    :disabled="props.disabled"
    :placeholder="props.placeholder"
    @input="onInput"
  >
</template>
