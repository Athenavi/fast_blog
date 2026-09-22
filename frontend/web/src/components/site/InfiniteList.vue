<script lang="ts" setup>
/**
 * 无限滚动列表
 *
 * 对应原 astro 的 `InfiniteList.tsx`（还有 `InfiniteGrid` 变体，这里用 `layout` 一个属性覆盖）。
 *
 * 实现基于 `@vueuse/core` 的 `useInfiniteScroll`——**零新增依赖**，
 * 它用 IntersectionObserver 监听哨兵元素，进入 `distance` 范围内就触发 `load-more`。
 *
 * 用法：
 * ```vue
 * <InfiniteList :items="items" :has-more="hasMore" :is-loading="loading"
 *               empty-title="暂无内容" @load-more="loadMore">
 *   <template #default="{item}">
 *     <ArticleCard :article="item"/>
 *   </template>
 * </InfiniteList>
 * ```
 */
import {useInfiniteScroll} from '@vueuse/core'

const props = withDefaults(
  defineProps<{
    /** 数据项；泛型用 unknown，调用方在插槽里自行断言 */
    items: unknown[]
    /** 是否还有更多 */
    hasMore?: boolean
    /** 是否正在加载 */
    isLoading?: boolean
    /** 触发距离（px），越大触发越早 */
    distance?: number
    /** 网格列数；>1 时按网格排布 */
    columns?: number
    /** 空状态文案 */
    emptyTitle?: string
    emptyDescription?: string
    /** 单元格最小宽度（网格模式下与 columns 二选一） */
    minColumnWidth?: string
  }>(),
  {
    hasMore: true,
    isLoading: false,
    distance: 300,
    columns: 1,
    emptyTitle: '',
    emptyDescription: '',
    minColumnWidth: '',
  },
)

const emit = defineEmits<{ (e: 'load-more'): void }>()

const sentinel = ref<HTMLElement | null>(null)

const gridClass = computed(() => {
  if (props.columns > 1) {
    const map: Record<number, string> = {
      2: 'grid-cols-2',
      3: 'grid-cols-2 sm:grid-cols-3',
      4: 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4',
    }
    return map[props.columns] || 'grid-cols-2 sm:grid-cols-3'
  }
  return ''
})

onMounted(() => {
  useInfiniteScroll(
    sentinel,
    () => {
      if (!props.hasMore || props.isLoading) return
      emit('load-more')
    },
    {
      distance: props.distance,
      // canLoadMore 让 VueUse 在校验阶段就跳过，避免重复触发
      canLoadMore: () => props.hasMore && !props.isLoading,
    },
  )
})
</script>

<template>
  <div>
    <div v-if="props.items.length" :class="props.columns > 1 ? `grid gap-6 ${gridClass}` : 'space-y-4'">
      <template v-for="(item, index) in props.items" :key="index">
        <slot :index="index" :item="item"/>
      </template>
    </div>

    <EmptyState v-else-if="!props.isLoading" :description="props.emptyDescription"
                :title="props.emptyTitle || $t('site.emptyContent')"/>

    <!-- 哨兵：进入视口即触发加载 -->
    <div ref="sentinel" aria-hidden="true" class="h-px w-full"/>

    <ListLoadingFooter
      :has-loaded-all="!props.hasMore && props.items.length > 0"
      :is-loading="props.isLoading"
      :total-loaded="props.items.length"
    />
  </div>
</template>
