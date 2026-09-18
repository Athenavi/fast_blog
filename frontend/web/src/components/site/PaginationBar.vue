<script lang="ts" setup>
/** 分页条：多列表场景复用 */
const props = defineProps<{ page: number; pages: number }>()
const emit = defineEmits<{ (e: 'change', page: number): void }>()

const items = computed(() => {
  const total = props.pages
  const current = props.page
  const out: (number | '...')[] = []
  for (let i = 1; i <= total; i += 1) {
    if (i === 1 || i === total || Math.abs(i - current) <= 1) out.push(i)
    else if (out[out.length - 1] !== '...') out.push('...')
  }
  return out
})
</script>

<template>
  <nav v-if="props.pages > 1" class="flex items-center justify-center gap-1 py-8">
    <Button :disabled="props.page <= 1" size="sm" variant="outline" @click="emit('change', props.page - 1)">
      {{ $t('site.prevPage') }}
    </Button>
    <template v-for="(item, index) in items" :key="index">
      <span v-if="item === '...'" class="px-2 text-sm text-fg-subtle">…</span>
      <Button
        v-else
        :variant="item === props.page ? 'default' : 'ghost'"
        size="sm"
        @click="emit('change', item as number)"
      >
        {{ item }}
      </Button>
    </template>
    <Button :disabled="props.page >= props.pages" size="sm" variant="outline" @click="emit('change', props.page + 1)">
      {{ $t('site.nextPage') }}
    </Button>
  </nav>
</template>
