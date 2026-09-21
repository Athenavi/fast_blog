<script lang="ts" setup>
const {t} = useI18n()
/**
 * 加载失败态（前台）
 *
 * 与 `EmptyState` 视觉同构，但明确区分"没有内容"与"加载失败"，
 * 并给出重试入口 —— 否则接口异常会被伪装成"暂无数据"，误导读者。
 */
const props = withDefaults(
  defineProps<{
    title?: string
    description?: string
    retryText?: string
  }>(),
  {title: '', description: '', retryText: ''},
)

const emit = defineEmits<{ (e: 'retry'): void }>()
</script>

<template>
  <div
    class="flex flex-col items-center justify-center gap-1.5 rounded-card border border-dashed border-danger/40 py-16 text-center">
    <Icon class="h-8 w-8 text-danger" name="alert-circle"/>
    <p class="mt-2 text-sm font-medium text-fg">{{ props.title || t('site.loadFailed') }}</p>
    <p v-if="props.description" class="text-sm text-fg-subtle">{{ props.description }}</p>
    <Button class="mt-3" size="sm" variant="outline" @click="emit('retry')">
      <Icon class="h-4 w-4" name="refresh-cw"/>
      {{ props.retryText || t('common.retry') }}
    </Button>
  </div>
</template>
