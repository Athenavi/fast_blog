<script lang="ts" setup>
/**
 * 虚拟列表（固定行高）
 *
 * 对应原 astro 的 `VirtualList.tsx`（含 `VirtualGrid` 变体）。
 *
 * 实现基于 `@vueuse/core` 的 `useVirtualList`——**零新增依赖**：
 * 只渲染可视区域附近的 `overscan` 条，DOM 数量与数据量解耦。
 * 适合长列表（几百上千条），固定高度场景性能最好；高度不固定请用 `VariableVirtualList`。
 */
import {useVirtualList} from '@vueuse/core'

const props = withDefaults(
  defineProps<{
    items: unknown[]
    /** 每项高度（px），必须固定 */
    itemHeight?: number
    /** 容器高度（px 或 CSS 值）；不传则用 `height` class */
    height?: string
    /** 上下额外渲染的条数 */
    overscan?: number
    emptyTitle?: string
    emptyDescription?: string
  }>(),
  {itemHeight: 64, height: '520px', overscan: 6, emptyTitle: '暂无内容', emptyDescription: ''},
)

const {list, containerProps, wrapperProps} = useVirtualList(
  computed(() => props.items),
  {itemHeight: () => props.itemHeight, overscan: props.overscan},
)

const containerStyle = computed(() => ({height: props.height}))
</script>

<template>
  <div>
    <div
      v-if="props.items.length"
      :style="containerStyle"
      class="overflow-y-auto rounded-card border border-line"
      v-bind="containerProps"
    >
      <div v-bind="wrapperProps">
        <div
          v-for="row in list"
          :key="row.index"
          :style="{height: `${props.itemHeight}px`}"
          class="border-b border-line last:border-b-0"
        >
          <slot :index="row.index" :item="row.data"/>
        </div>
      </div>
    </div>

    <EmptyState v-else :description="props.emptyDescription" :title="props.emptyTitle"/>
  </div>
</template>
