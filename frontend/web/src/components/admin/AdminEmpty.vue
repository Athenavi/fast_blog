<script lang="ts" setup>
/**
 * 空状态：统一的"暂无数据"呈现（轻量线条插画 + 文案 + 可选操作）。
 *
 * 与 Element Plus 的 `el-empty` 相比，这里文案与按钮由调用方决定，
 * 便于"筛选无结果"与"还没有任何数据"两种情况给出不同的引导。
 */
withDefaults(
  defineProps<{
    title?: string
    desc?: string
    /** 视觉样式：默认（数据为空）/ error（加载失败） */
    variant?: 'default' | 'error'
  }>(),
  {variant: 'default'},
)
</script>

<template>
  <div :role="variant === 'error' ? 'alert' : 'status'" class="admin-empty">
    <svg v-if="variant === 'default'" aria-hidden="true" class="admin-empty__art" viewBox="0 0 64 64">
      <rect fill="none" height="30" rx="4" stroke="currentColor" stroke-width="2" width="44" x="10" y="18"/>
      <path d="M10 28h44" stroke="currentColor" stroke-width="2"/>
      <path d="M22 40h20" stroke="currentColor" stroke-linecap="round" stroke-width="2"/>
      <path d="M18 12h28" stroke="currentColor" stroke-linecap="round" stroke-width="2"/>
    </svg>
    <svg v-else aria-hidden="true" class="admin-empty__art" viewBox="0 0 64 64">
      <circle cx="32" cy="32" fill="none" r="22" stroke="currentColor" stroke-width="2"/>
      <path d="M32 22v14" stroke="currentColor" stroke-linecap="round" stroke-width="2"/>
      <circle cx="32" cy="42" fill="currentColor" r="1.6"/>
    </svg>

    <p v-if="title" class="admin-empty__title">{{ title }}</p>
    <p v-if="desc" class="admin-empty__desc">{{ desc }}</p>

    <div v-if="$slots.default" class="admin-empty__actions">
      <slot/>
    </div>
  </div>
</template>

<style scoped>
.admin-empty__art {
  width: 64px;
  height: 64px;
  color: var(--admin-fg-subtle, #9ca3af);
  opacity: 0.75;
}
</style>
