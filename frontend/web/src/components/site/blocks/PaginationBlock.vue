<script lang="ts" setup>
/**
 * 区块：pagination —— 分页
 *
 * 参数：`page`（当前页）、`totalPages`（总页数）、`param`（query 参数名，默认 `page`）。
 *
 * 通常由 `post-list`（`paginated: true`）自己渲染；这个独立区块用于
 * **主题想自己控制分页位置**的场景（例如把分页放到侧栏下方）。
 * 用链接而非按钮：可分享、可抓取、无 JS 也能用。
 */
import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const route = useRoute()

const page = computed(() => {
  const raw = Number(props.propsData.page ?? props.context.page ?? route.query.page ?? 1)
  return Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : 1
})

const totalPages = computed(() => {
  const raw = Number(props.propsData.totalPages ?? props.context.totalPages ?? 1)
  return Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : 1
})

const param = computed(() => {
  const raw = props.propsData.param
  return typeof raw === 'string' && /^[a-z][a-z0-9_]*$/i.test(raw) ? raw : 'page'
})

function hrefFor(target: number): string {
  const query = {...route.query, [param.value]: String(target)}
  const search = Object.entries(query)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&')
  return `${route.path}?${search}`
}
</script>

<template>
  <nav v-if="totalPages > 1" :class="['flex items-center justify-center gap-3', props.blockClass]">
    <NuxtLink v-if="page > 1" :to="hrefFor(page - 1)" class="t-tag">上一页</NuxtLink>
    <span class="t-muted text-sm">{{ page }} / {{ totalPages }}</span>
    <NuxtLink v-if="page < totalPages" :to="hrefFor(page + 1)" class="t-tag">下一页</NuxtLink>
  </nav>
</template>
