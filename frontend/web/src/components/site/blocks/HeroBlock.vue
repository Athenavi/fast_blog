<script lang="ts" setup>
/**
 * 区块：hero —— 首屏标题区
 *
 * 参数：
 *  - `title`（不填则用站点名）
 *  - `subtitle`（不填则用站点描述）
 *  - `align`（`left` | `center`，默认 `left`）
 *  - `actions`（数组，每项 `{label, href}`），生成按钮组
 *
 * 站点名/描述取自 `useSiteInfo()`（与布局同一份数据，不额外请求）。
 */
import type {BlockContext} from './types'
import {useSiteInfo} from '@/composables/useSiteInfo'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const site = await useSiteInfo()

function textProp(key: string, fallback: string): string {
  const raw = props.propsData[key]
  return typeof raw === 'string' && raw.trim() ? raw : fallback
}

const title = computed(() => textProp('title', site.value.site_name || 'FastBlog'))
const subtitle = computed(() => textProp('subtitle', site.value.site_description || ''))
const alignClass = computed(() => (props.propsData.align === 'center' ? 'text-center' : 'text-left'))

interface HeroAction {
  label?: unknown
  href?: unknown
}

const actions = computed(() => {
  const raw = props.propsData.actions
  if (!Array.isArray(raw)) return []
  return (raw as HeroAction[])
    .filter((item) => item && typeof item === 'object')
    .map((item) => ({
      label: typeof item.label === 'string' ? item.label : '',
      href: typeof item.href === 'string' ? item.href : '/',
    }))
    .filter((item) => item.label)
})
</script>

<template>
  <header :class="[alignClass, props.blockClass]">
    <h1 class="text-3xl font-bold tracking-tight text-fg sm:text-4xl">{{ title }}</h1>
    <p v-if="subtitle" class="t-muted mx-auto mt-4 max-w-read text-base leading-relaxed">
      {{ subtitle }}
    </p>
    <div v-if="actions.length" :class="alignClass === 'text-center' ? 'justify-center' : ''"
         class="mt-8 flex flex-wrap gap-3">
      <NuxtLink v-for="action in actions" :key="action.href" :to="action.href" class="t-button">
        {{ action.label }}
      </NuxtLink>
    </div>
  </header>
</template>
