<script lang="ts" setup>
const {t} = useI18n()
/** 空状态：列表 / 搜索 / 分类页复用 */

const props = withDefaults(
  defineProps<{
    title?: string
    description?: string
    /** 紧凑模式：用于选项卡/区块内的小范围空态（内边距减半） */
    compact?: boolean
  }>(),
  {
    title: '',
    description: '',
    compact: false,
  },
)
</script>

<template>
  <div
    :class="[
      'flex flex-col items-center justify-center gap-1.5 rounded-card border border-dashed border-line text-center',
      props.compact ? 'py-8' : 'py-16',
    ]"
    role="status"
  >
    <Icon class="h-8 w-8 text-fg-subtle" name="inbox"/>
    <p class="mt-2 text-sm font-medium text-fg">{{ props.title || t('site.emptyContent') }}</p>
    <p v-if="props.description" class="text-sm text-fg-subtle">{{ props.description }}</p>
    <slot/>
  </div>
</template>
