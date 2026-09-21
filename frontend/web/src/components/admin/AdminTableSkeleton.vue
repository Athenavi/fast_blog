<script lang="ts" setup>
/**
 * 表格骨架屏：首次加载（还没有任何数据）时替代 `v-loading` 遮罩，
 * 避免"白屏 + 转圈"的廉价观感；已有数据时的二次加载仍用 `v-loading`（不跳版）。
 */
withDefaults(
  defineProps<{
    rows?: number
    columns?: number
  }>(),
  {rows: 6, columns: 4},
)
</script>

<template>
  <div class="admin-skeleton" role="status">
    <div v-for="row in rows" :key="row" class="admin-skeleton__row">
      <span
        v-for="col in columns"
        :key="col"
        :style="{flex: col === 1 ? 2 : 1}"
        class="admin-skeleton__cell"
      />
    </div>
  </div>
</template>

<style scoped>
.admin-skeleton__row {
  display: flex;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--admin-line, #ebeef5);
}

.admin-skeleton__cell {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(
    90deg,
    var(--admin-surface-soft, #f2f3f5) 25%,
    var(--admin-surface-hover, #e9ebef) 37%,
    var(--admin-surface-soft, #f2f3f5) 63%
  );
  background-size: 400% 100%;
  animation: admin-skeleton-loading 1.4s ease infinite;
}

@keyframes admin-skeleton-loading {
  0% {
    background-position: 100% 50%;
  }

  100% {
    background-position: 0 50%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .admin-skeleton__cell {
    animation: none;
  }
}
</style>
