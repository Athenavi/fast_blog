<script lang="ts" setup>
import {cn} from '@/lib/utils'

const props = defineProps<{ class?: string; modelValue?: string | number; type?: string; placeholder?: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

function onInput(event: Event) {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}
</script>

<template>
  <input
    :class="cn('flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 disabled:cursor-not-allowed disabled:opacity-50', props.class)"
    :placeholder="props.placeholder"
    :type="props.type ?? 'text'"
    :value="props.modelValue"
    @input="onInput"
  >
</template>
