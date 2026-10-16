<script lang="ts" setup>
/**
 * 主题页面宿主（页面级接管）
 *
 * 把"当前主题是否提供了这个页面"的判断收敛到**一处**：主题提供了就用它的实现，
 * 否则渲染默认插槽（内置页）。这样每个前台页面只需包一层，不必各自写判断，
 * 也不会出现"某个页面忘了接主题"的不一致。
 *
 * 用法：
 *
 * ```vue
 * <ThemePage page="ArticlePage">
 *   <!-- 内置默认实现 -->
 * </ThemePage>
 * ```
 *
 * 主题侧只需在 `plugins/<slug>/frontend/site/` 放 `ArticlePage.vue` ——
 * 扫描器会把 `frontend/**` 整体复制进加载表，无需改任何构建配置。
 */
import {computed, defineAsyncComponent} from 'vue'

const props = defineProps<{
  /** 页面名（不带扩展名），如 `ArticlePage`；主题需提供 `frontend/site/<page>.vue` */
  page: string
}>()

const loader = useThemePage(props.page)

/**
 * `import.meta.glob` 返回的是**加载器函数**而非组件本身，必须包一层
 * `defineAsyncComponent`；主题没提供该页面时返回 null，模板走默认插槽。
 */
const impl = computed(() =>
  loader.value ? defineAsyncComponent(loader.value) : null,
)
</script>

<template>
  <!-- 透传 attrs（如 class / data-*），让主题实现与内置页处在同一层 DOM 上 -->
  <component :is="impl" v-if="impl" v-bind="$attrs"/>
  <slot v-else/>
</template>
