<script lang="ts" setup>
/**
 * 面包屑
 *
 * 对应原 astro 的 `seo/Breadcrumbs.tsx`（它还顺带输出 BreadcrumbList 结构化数据，
 * 这里拆开：结构化数据由 `useBreadcrumbJsonLd()` 负责，组件只做展示）。
 *
 * 用法：
 * ```vue
 * <Breadcrumbs :items="[{label: '首页', to: '/'}, {label: article.title}]"/>
 * ```
 */
const props = withDefaults(
  defineProps<{
    items: Array<{ label: string; to?: string }>
    class?: string
  }>(),
  {items: () => []},
)
</script>

<template>
  <nav v-if="props.items.length" :class="props.class" aria-label="面包屑">
    <ol class="flex flex-wrap items-center gap-1.5 text-sm">
      <li v-for="(item, index) in props.items" :key="index" class="flex items-center gap-1.5">
        <span v-if="index" aria-hidden="true" class="text-fg-subtle/70">/</span>
        <NuxtLink
          v-if="item.to && index < props.items.length - 1"
          :to="item.to"
          class="text-fg-muted transition-colors hover:text-fg"
        >
          {{ item.label }}
        </NuxtLink>
        <span v-else aria-current="page" class="font-medium text-fg">{{ item.label }}</span>
      </li>
    </ol>
  </nav>
</template>
