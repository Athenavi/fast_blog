<script lang="ts" setup>
/**
 * 列表加载页脚
 *
 * 对应原 astro 的 `ListLoadingFooter.tsx`：把「加载中 / 已加载完 / 出错可重试」
 * 三种状态收敛到一个组件，供无限滚动或分页列表复用。
 */
const props = withDefaults(
  defineProps<{
    /** 正在加载 */
    isLoading?: boolean
    /** 已加载完，没有更多数据 */
    hasLoadedAll?: boolean
    /** 已加载条数（用于文案） */
    totalLoaded?: number
    /** 错误信息；非空时展示重试 */
    error?: string | null
  }>(),
  {isLoading: false, hasLoadedAll: false, totalLoaded: 0, error: null},
)

const emit = defineEmits<{ (e: 'retry'): void }>()

const show = computed(() => props.isLoading || props.hasLoadedAll || Boolean(props.error))
</script>

<template>
  <div v-if="show" class="flex flex-col items-center gap-2 py-6 text-sm">
    <template v-if="props.error">
      <p class="text-danger">{{ props.error }}</p>
      <Button size="sm" variant="outline" @click="emit('retry')">重试</Button>
    </template>

    <template v-else-if="props.isLoading">
      <Icon class="h-4 w-4 animate-spin text-fg-subtle" name="loader-circle"/>
      <span class="text-fg-subtle">加载中…</span>
    </template>

    <p v-else class="text-fg-subtle">
      已经到底了
      <template v-if="props.totalLoaded">（共 {{ props.totalLoaded }} 条）</template>
    </p>
  </div>
</template>
